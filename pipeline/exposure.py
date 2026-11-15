"""Offline operator pipeline: real candidates -> exposure -> review locations."""
import argparse
import hashlib
import json
from pathlib import Path
import csv
from datetime import datetime, timezone

from shapely.geometry import shape, box, mapping
from shapely.ops import unary_union
from app.server.data_loader import load_bundle
from pipeline.core.impact_analysis import population_exposure, read_osm, infrastructure_exposure, order_for_review

ROOT = Path(__file__).resolve().parents[1]


def prepare_queries(features):
    union = unary_union([shape(f['geometry']) for f in features])
    west,south,east,north = union.bounds
    jobs = []
    for row in range(6):
        for col in range(6):
            bounds = [west+(east-west)*col/6, south+(north-south)*row/6,
                      west+(east-west)*(col+1)/6, south+(north-south)*(row+1)/6]
            if union.intersects(box(*bounds)):
                jobs.append({'id':f'{row}_{col}', 'bbox':bounds})
    target = ROOT/'data/inputs/auxiliary'/'osm_jobs.json'
    target.write_text(json.dumps(jobs),encoding='utf-8')
    print(json.dumps({'osm_extracts_needed':len(jobs)}))


def build():
    bundle = ROOT/'data/products'/'sarwatch_demo_bundle.zip'
    manifest, geo, _, _ = load_bundle(bundle.read_bytes())
    auxiliary = ROOT/'data/inputs/auxiliary'
    population, cells = population_exposure(geo['features'], auxiliary/'worldpop_hue_2026_100m.tif')
    files = sorted((auxiliary/'osm').glob('*.osm'))
    coverage_records = json.loads((auxiliary/'osm_collection.json').read_text(encoding='utf-8'))
    coverage = unary_union([box(*j['bbox']) for j in coverage_records if j.get('status')=='ok'])
    roads, facilities = read_osm(files)
    infra, road_lines, facility_points, road_total = infrastructure_exposure(geo['features'],roads,facilities,coverage)
    for feature in geo['features']:
        ident = str(feature['properties']['id'])
        feature['properties'].update(population[ident])
        feature['properties'].update(infra[ident])
        point = shape(feature['geometry']).representative_point()
        feature['properties']['review_longitude'] = point.x
        feature['properties']['review_latitude'] = point.y
    ordered = order_for_review(geo['features'])
    data = {'schema_version':1, 'created_at':datetime.now(timezone.utc).isoformat(),
            'analysis_version':hashlib.sha256(bundle.read_bytes()).hexdigest()[:16],
            'status':'unvalidated_review_support', 'population_year':2026,
            'population_method':'area_weighted_original_100m_cells_epsg32648_nodata_unknown',
            'ordering':'essential_facility_overlap_then_population_then_road_length_then_area',
            'summary':{
                'candidate_count':len(ordered),'candidate_area_km2':manifest['screened_area_km2'],
                'population_estimate_partial':sum(p['population_estimate'] or 0 for p in population.values()),
                'regions_with_population':sum((p['population_estimate'] or 0)>0 for p in population.values()),
                'regions_without_valid_population_cells':sum(p['population_estimate'] is None for p in population.values()),
                'road_length_m':road_total,'regions_with_road_overlap':sum(v['road_length_m']>0 for v in infra.values()),
                'facility_count':len({f['osm_id'] for p in infra.values() for f in p['facilities']}),
                'nearby_facility_count':len(facility_points['features']),
                'population_valid_candidate_area_fraction':sum(population[str(f['properties']['id'])]['population_valid_area_fraction']*f['properties']['area_m2'] for f in geo['features'])/sum(f['properties']['area_m2'] for f in geo['features']),
                'infrastructure_fully_queried_regions':sum(v['infrastructure_status']=='assessed' for v in infra.values()),
            },
            'geojson':{'type':'FeatureCollection','features':ordered},
            'population_cells':cells,'roads':road_lines,'facilities':facility_points,
            'sources':{
                'worldpop':json.loads((auxiliary/'worldpop_provenance.json').read_text(encoding='utf-8')),
                'osm':{'endpoint':'https://api.openstreetmap.org/api/0.6/map','retrieved_at':datetime.now(timezone.utc).isoformat(),'licence':'ODbL 1.0','attribution':'© OpenStreetMap contributors','successful_extracts':len(files),'query_index':'data/inputs/auxiliary/osm_collection.json'},
            },
            'limitations':['Candidate polygons are not independently validated inundation.',
                          'Population totals describe only valid WorldPop cells and assume uniform within-cell distribution; NoData is unknown.',
                          'OSM is a current snapshot, not a historical reconstruction of October 2026; coverage and tagging may be incomplete.',
                          'Road overlap is geometric evidence, not evidence of closure; mapped facilities may not be operating.',
                          'Review rank is a transparent heuristic for checking locations, not a calibrated risk or flood probability.']}
    out = ROOT/'data/products'/'impact'
    out.mkdir(parents=True,exist_ok=True)
    (out/'review_analysis.json').write_text(json.dumps(data,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    (out/'review_candidates.geojson').write_text(json.dumps(data['geojson'],ensure_ascii=False,allow_nan=False),encoding='utf-8')
    with (out/'review_locations.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        columns = ['review_rank','id','review_longitude','review_latitude','area_m2','population_estimate','population_status','population_valid_area_fraction','road_length_m','facility_count','infrastructure_status','review_basis']
        writer = csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore')
        writer.writeheader();writer.writerows(f['properties'] for f in ordered)
    (ROOT/'app/web'/'impact-data.js').write_text('globalThis.SARWatchImpact='+json.dumps(data,ensure_ascii=True,allow_nan=False,separators=(',',':'))+';\n',encoding='utf-8')
    print(json.dumps(data['summary'],ensure_ascii=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare-osm',action='store_true')
    args=parser.parse_args()
    if args.prepare_osm:
        _,geo,_,_=load_bundle((ROOT/'data/products'/'sarwatch_demo_bundle.zip').read_bytes())
        prepare_queries(geo['features'])
    else: build()
