"""Read and check Colab output bundles without extracting ZIP members."""
import io
import json
import math
import zipfile


def load_bundle(payload):
    """Return metadata, GeoJSON, PNG previews and CSV bytes from an export."""
    required = {'manifest.json', 'screened_candidates.geojson', 'before_HH.png', 'after_HH.png'}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate filenames in bundle.')
        if not required.issubset(names):
            raise ValueError('Missing required analysis outputs.')
        if sum(entry.file_size for entry in entries) > 60_000_000:
            raise ValueError('Bundle exceeds 60 MB uncompressed.')
        meta = json.loads(archive.read('manifest.json'))
        if meta.get('schema_version') != 1:
            raise ValueError('Unsupported export schema.')
        for field in ['initial_area_km2', 'screened_area_km2']:
            value = meta.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError('Invalid analysis area: ' + field)
        if meta['screened_area_km2'] > meta['initial_area_km2'] + 1e-6:
            raise ValueError('Screened area exceeds initial area.')
        for date in ['before', 'after']:
            if not isinstance(meta['dates'][date], str):
                raise ValueError('Invalid observation date.')
            bounds = meta['previews'][date]['bounds']
            if len(bounds) != 2 or any(len(pair) != 2 for pair in bounds):
                raise ValueError('Invalid preview bounds.')
            south, west = bounds[0]
            north, east = bounds[1]
            if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
                raise ValueError('Preview bounds are not WGS84 latitude/longitude.')
        geo = json.loads(archive.read('screened_candidates.geojson'))
        if geo.get('type') != 'FeatureCollection' or not isinstance(geo.get('features'), list):
            raise ValueError('Invalid candidate GeoJSON.')
        polygon_area = 0.0
        for feature in geo['features']:
            if feature.get('type') != 'Feature':
                raise ValueError('Invalid GeoJSON feature.')
            geometry = feature.get('geometry') or {}
            if geometry.get('type') not in ('Polygon', 'MultiPolygon'):
                raise ValueError('Candidates must be polygons.')
            polygons = [geometry.get('coordinates')] if geometry['type'] == 'Polygon' else geometry.get('coordinates')
            if not isinstance(polygons, list) or not polygons:
                raise ValueError('Missing polygon coordinates.')
            for polygon in polygons:
                if not isinstance(polygon, list) or not polygon:
                    raise ValueError('Missing polygon rings.')
                for ring in polygon:
                    if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                        raise ValueError('Polygon rings must be closed.')
                    for point in ring:
                        if not isinstance(point, list) or len(point) < 2:
                            raise ValueError('Invalid polygon coordinate.')
                        lon, lat = point[:2]
                        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (lon, lat)) or not (-180 <= lon <= 180 and -85.05112878 <= lat <= 85.05112878):
                            raise ValueError('Polygon coordinate is outside Web Mercator bounds.')
            properties = feature['properties']
            if 'id' not in properties:
                raise ValueError('Candidate polygon is missing its ID.')
            area = properties['area_m2']
            if not isinstance(area, (int, float)) or not math.isfinite(area) or area < 0:
                raise ValueError('Invalid polygon area.')
            polygon_area += area
        if not math.isclose(polygon_area / 1e6, meta['screened_area_km2'], rel_tol=1e-5, abs_tol=1e-5):
            raise ValueError('GeoJSON polygon areas disagree with the exported raster area.')
        images = {date: archive.read(date + '_HH.png') for date in ['before', 'after']}
        if any(not image.startswith(b'\x89PNG\r\n\x1a\n') for image in images.values()):
            raise ValueError('Invalid preview PNG.')
        tables = {name: archive.read(name) for name in names if name.endswith('.csv')}
    return meta, geo, images, tables
