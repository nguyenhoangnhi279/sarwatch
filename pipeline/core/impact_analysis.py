"""Area-weighted population exposure and auditable review ordering.

Requires rasterio, shapely, pyproj and numpy in the processing environment.
Web viewers and the HTTP server do not need these libraries.
"""
from collections import defaultdict
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.windows import from_bounds
from shapely import make_valid
from shapely.geometry import shape, mapping, box, Point, LineString, Polygon
from shapely.ops import transform, unary_union, polygonize
from shapely.strtree import STRtree

TO_METRES = Transformer.from_crs(4326, 32648, always_xy=True).transform
TO_LONLAT = Transformer.from_crs(32648, 4326, always_xy=True).transform
FACILITIES = {'hospital', 'clinic', 'school', 'kindergarten', 'fire_station', 'police'}
EXCLUDED_ROADS = {'footway', 'path', 'steps', 'cycleway', 'bridleway', 'corridor', 'proposed', 'construction'}


def project(geometry):
    return transform(TO_METRES, make_valid(geometry))


def population_exposure(features, raster_path):
    """Conserve persons per original cell; weight by projected area fraction.

    NoData never becomes zero population. Estimates with partial valid coverage
    are explicitly reported as partial. A zero is returned only on valid cells.
    """
    overlay, cache, results = {}, {}, {}
    with rasterio.open(raster_path) as ds:
        if ds.crs.to_epsg() != 4326:
            raise ValueError('Expected original WorldPop WGS84 population grid')
        a = ds.read(1, masked=True)
        mask = np.ma.getmaskarray(a)
        for feature in features:
            geo = make_valid(shape(feature['geometry']))
            geom = project(geo)
            if geom.area <= 0:
                raise ValueError('Candidate must have positive polygon area')
            window = from_bounds(*geo.bounds, ds.transform)
            r0, r1 = max(0, math.floor(window.row_off)), min(ds.height, math.ceil(window.row_off+window.height))
            c0, c1 = max(0, math.floor(window.col_off)), min(ds.width, math.ceil(window.col_off+window.width))
            total, valid_area = 0.0, 0.0
            for row in range(r0, r1):
                for col in range(c0, c1):
                    if mask[row, col] or not np.isfinite(a[row, col]) or a[row, col] < 0:
                        continue
                    key = (row, col)
                    if key not in cache:
                        x0, y0 = ds.transform*(col, row)
                        x1, y1 = ds.transform*(col+1, row+1)
                        cell = box(min(x0,x1), min(y0,y1), max(x0,x1), max(y0,y1))
                        cache[key] = cell, project(cell)
                    cell, cell_m = cache[key]
                    if not geom.intersects(cell_m):
                        continue
                    overlap = geom.intersection(cell_m).area
                    fraction = min(1.0, max(0.0, overlap/cell_m.area))
                    if not fraction:
                        continue
                    people = float(a[row, col])
                    total += people*fraction
                    valid_area += overlap
                    if people > 0:
                        if key not in overlay:
                            overlay[key] = {'type':'Feature', 'geometry':mapping(cell), 'properties':{
                                'people_in_cell': people, 'estimated_exposed': 0.0}}
                        overlay[key]['properties']['estimated_exposed'] += people*fraction
            coverage = min(1.0, valid_area/geom.area)
            results[str(feature['properties']['id'])] = {
                'population_estimate': round(total, 6) if coverage > 0 else None,
                'population_valid_area_fraction': round(coverage, 6),
                'population_status': 'complete' if coverage >= .999 else 'partial' if coverage > 0 else 'no_valid_cells',
            }
    return results, {'type':'FeatureCollection', 'features':list(overlay.values())}


def read_osm(paths):
    """Merge official OSM API extracts; deduplicate by object type/id."""
    nodes, ways, relations = {}, {}, {}
    for path in paths:
        tree = ET.parse(path).getroot()
        for element in tree:
            if element.tag not in {'node','way','relation'}:
                continue
            tags = {t.attrib['k']:t.attrib['v'] for t in element.findall('tag')}
            record = {'id':element.attrib['id'], 'tags':tags}
            if element.tag == 'node':
                record['coordinate'] = (float(element.attrib['lon']), float(element.attrib['lat']))
                nodes[record['id']] = record
            elif element.tag == 'way':
                record['nodes'] = [n.attrib['ref'] for n in element.findall('nd')]
                ways[record['id']] = record
            else:
                record['members'] = [dict(m.attrib) for m in element.findall('member')]
                relations[record['id']] = record
    roads, facilities = [], []
    for obj in ways.values():
        coords = [nodes[n]['coordinate'] for n in obj['nodes'] if n in nodes]
        if len(coords) != len(obj['nodes']) or len(coords) < 2:
            continue
        tags, ident = obj['tags'], 'way/'+obj['id']
        if tags.get('highway') and tags['highway'] not in EXCLUDED_ROADS and tags.get('area') != 'yes':
            roads.append({'type':'Feature', 'geometry':mapping(LineString(coords)),
                          'properties':{'osm_id':ident, 'name':tags.get('name:vi',tags.get('name','')), 'kind':tags['highway']}})
        if tags.get('amenity') in FACILITIES:
            geom = make_valid(Polygon(coords)) if len(coords)>=4 and coords[0]==coords[-1] else LineString(coords)
            facilities.append({'type':'Feature', 'geometry':mapping(geom), 'properties':{
                'osm_id':ident, 'name':tags.get('name:vi',tags.get('name','')), 'kind':tags['amenity']}})
    for obj in relations.values():
        tags = obj['tags']
        if tags.get('amenity') not in FACILITIES:
            continue
        rings = {'outer':[], 'inner':[]}
        for member in obj['members']:
            if member['type'] != 'way' or member['ref'] not in ways:
                continue
            refs = ways[member['ref']]['nodes']
            if all(n in nodes for n in refs) and len(refs)>1:
                rings['inner' if member.get('role')=='inner' else 'outer'].append(LineString([nodes[n]['coordinate'] for n in refs]))
        outer = unary_union(list(polygonize(rings['outer'])))
        inner = unary_union(list(polygonize(rings['inner'])))
        if not outer.is_empty:
            geom = make_valid(outer.difference(inner))
            facilities.append({'type':'Feature','geometry':mapping(geom),'properties':{
                'osm_id':'relation/'+obj['id'],'name':tags.get('name:vi',tags.get('name','')),'kind':tags['amenity']}})
    for obj in nodes.values():
        tags = obj['tags']
        if tags.get('amenity') not in FACILITIES:
            continue
        point = Point(obj['coordinate'])
        # Avoid counting a mapped label and its tagged footprint twice.
        if any(f['properties']['kind']==tags['amenity'] and shape(f['geometry']).covers(point) for f in facilities):
            continue
        facilities.append({'type':'Feature','geometry':mapping(point),'properties':{
            'osm_id':'node/'+obj['id'],'name':tags.get('name:vi',tags.get('name','')),'kind':tags['amenity']}})
    return roads, facilities


def infrastructure_exposure(features, roads, facilities, coverage_geometry):
    road_geoms = [project(shape(f['geometry'])) for f in roads]
    facility_geoms = [project(shape(f['geometry'])) for f in facilities]
    road_tree, facility_tree = STRtree(road_geoms), STRtree(facility_geoms)
    coverage = project(coverage_geometry)
    results, road_overlay, facility_overlay = {}, [], {}
    all_intersections = []
    for feature in features:
        geom = project(shape(feature['geometry']))
        lengths, names, segments, refs, places, nearby = [], set(), [], [], [], []
        for i in road_tree.query(geom, predicate='intersects'):
            clipped = geom.intersection(road_geoms[i])
            if clipped.length <= .01:
                continue
            lengths.append(clipped.length)
            segments.append(clipped)
            refs.append(roads[i]['properties']['osm_id'])
            if roads[i]['properties']['name']:
                names.add(roads[i]['properties']['name'])
            road_overlay.append({'type':'Feature','geometry':mapping(transform(TO_LONLAT,clipped)),
                                 'properties':{**roads[i]['properties'],'candidate_id':str(feature['properties']['id'])}})
        for i in facility_tree.query(geom, predicate='intersects'):
            obj = facilities[i]
            places.append(obj['properties'])
            facility_overlay[obj['properties']['osm_id']] = obj
        for i in facility_tree.query(geom.buffer(500), predicate='intersects'):
            distance = geom.distance(facility_geoms[i])
            if distance <= 500:
                obj = facilities[i]
                nearby.append({**obj['properties'], 'distance_m':round(distance,1)})
                display = dict(obj)
                display['properties'] = {**obj['properties'], 'display_point':list(shape(obj['geometry']).representative_point().coords)[0]}
                facility_overlay[obj['properties']['osm_id']] = display
        union_lines = unary_union(segments)
        all_intersections.append(union_lines)
        fraction = min(1, geom.intersection(coverage.buffer(.01)).area / geom.area)
        results[str(feature['properties']['id'])] = {
            'road_length_m': round(union_lines.length, 3), 'road_object_count':len(set(refs)),
            'road_names': sorted(names), 'facility_count':len(places), 'facilities':places,
            'nearby_facilities':sorted(nearby,key=lambda p:p['distance_m'])[:3],
            'infrastructure_query_coverage_fraction':round(fraction,6),
            'infrastructure_status':'assessed' if fraction>=.999 else 'partial',
        }
    return results, {'type':'FeatureCollection','features':road_overlay}, {'type':'FeatureCollection','features':list(facility_overlay.values())}, unary_union(all_intersections).length


def order_for_review(records):
    """Transparent lexicographic ordering; no risk score or flood probability."""
    def key(record):
        p = record['properties']
        return (-int(p.get('facility_count',0)>0), -(p.get('population_estimate') or 0),
                -p.get('road_length_m',0), -p['area_m2'], str(p['id']))
    ordered = sorted(records, key=key)
    for rank, record in enumerate(ordered,1):
        p = record['properties']
        p['review_rank'] = rank
        p['review_basis'] = 'essential_facility' if p.get('facility_count',0)>0 else 'population' if (p.get('population_estimate') or 0)>0 else 'road' if p.get('road_length_m',0)>0 else 'radar_only'
    return ordered
