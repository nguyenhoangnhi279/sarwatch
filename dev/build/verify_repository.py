"""Verify shipped inputs, checksums and repository assets."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'data/manifest.json'
IGNORED={'.git','.venv','node_modules','__pycache__','standalone','releases','.pytest_cache'}


def generated(path):
    relative=path.relative_to(ROOT)
    return (path.suffix=='.tif' and ('radar_rerun' in relative.parts or path.name.endswith('_source_crop.tif'))
            or len(relative.parts)>2 and relative.parts[:2]==('data','products') and relative.parts[2] in ['forecasts','verification']
            or path.suffix in ['.log','.pyc','.part'])


def shipped_files():
    return sorted((p for p in ROOT.rglob('*') if p.is_file() and not IGNORED.intersection(p.relative_to(ROOT).parts)
                   and not generated(p)),key=str)


def inputs():
    paths=list((ROOT/'data/inputs').rglob('*'))
    paths+=[ROOT/'data/products/sarwatch_demo_bundle.zip',ROOT/'data/products/ml/water_proxy_rf.joblib']
    paths+=list((ROOT/'app/web').glob('*-data.js'))+list((ROOT/'app/web/fonts').glob('*'))
    return sorted({p for p in paths if p.is_file() and p!=MANIFEST and p.name!='README.md' and not generated(p)},key=str)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-manifest',action='store_true');args=parser.parse_args()
    if args.write_manifest:
        entries={p.relative_to(ROOT).as_posix():dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in inputs()}
        MANIFEST.write_text(json.dumps(dict(schema_version=1,description='Shipped actual inputs, model and browser data; generated radar rasters can be rebuilt.',files=entries),indent=2),encoding='utf-8')
        reports=['radar_rerun/report.json','radar_rerun/screening.json','radar_rerun/product_comparison.json',
                 'radar_rerun/radiometry.json','ml/evaluation.json','validation/optical_crosscheck.json','impact/review_analysis.json']
        report_hashes={'data/products/'+name:hashlib.sha256((ROOT/'data/products'/name).read_bytes()).hexdigest()
                       for name in reports if (ROOT/'data/products'/name).is_file()}
        (ROOT/'data/products/reproduction_checksums.json').write_text(json.dumps(report_hashes,indent=2),encoding='utf-8')
    if not MANIFEST.exists():raise SystemExit('Input manifest missing. Run python run.py manifest.')
    expected=json.loads(MANIFEST.read_text(encoding='utf-8'))['files'];errors=[]
    mandatory=['data/products/sarwatch_demo_bundle.zip','data/products/ml/water_proxy_rf.joblib',
               'data/inputs/auxiliary/worldpop_hue_2026_100m.tif','data/inputs/auxiliary/osm_collection.json']
    mandatory += ['data/inputs/auxiliary/'+name+ext for name in ['dem_source_crop','jrc_source_crop'] for ext in ['.bin','.json']]
    mandatory += ['data/inputs/reference/S2B_48QYD_202610'+day+'_0_L2A'+ext for day in ['16','26'] for ext in ['_scl.tif','_rgb.bin','_rgb.json']]
    for name in mandatory:
        if name not in expected:errors.append('Required input absent from manifest: '+name)
    for name,meta in expected.items():
        path=ROOT/name
        if not path.is_file():errors.append('Missing: '+name);continue
        if path.stat().st_size!=meta['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:errors.append('Checksum mismatch: '+name)
    for name in ['before_HH','before_HV','after_HH','after_HV']:
        if 'data/inputs/raw/'+name+'.tif' not in expected:errors.append('Raw input absent from manifest: '+name)
    records=json.loads((ROOT/'data/inputs/auxiliary/osm_collection.json').read_text(encoding='utf-8'))
    for row in records:
        if row.get('status')=='ok' and not (ROOT/'data/inputs/auxiliary/osm'/(row['id']+'.osm')).is_file():errors.append('Missing OSM source: '+row['id'])
    files=shipped_files();too_large=[p.relative_to(ROOT).as_posix() for p in files if p.stat().st_size>=100*1024*1024]
    errors+=['GitHub 100 MiB limit: '+p for p in too_large]
    secrets=re.compile(r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}|X-Amz-Signature=[0-9a-f]{30,}',re.I)
    absolute=re.compile(r'(?:[A-Za-z]:[\\/](?:Users|workspace|home)|/content/drive|/mnt/data)')
    for path in files:
        if path.suffix not in ['.py','.js','.mjs','.cjs','.html','.css','.json','.md','.ipynb','.txt','.yml']:continue
        text=path.read_text(encoding='utf-8',errors='replace')
        if secrets.search(text):errors.append('Secret-like content: '+path.relative_to(ROOT).as_posix())
        if path.suffix in ['.py','.mjs','.cjs','.ipynb'] and path.name!='verify_repository.py' and absolute.search(text):errors.append('Machine-specific executable path: '+path.relative_to(ROOT).as_posix())
    for path in (ROOT/'data/inputs/raw').iterdir():
        if path.is_symlink():errors.append('External raw-data symlink: '+path.name)
    with zipfile.ZipFile(ROOT/'data/products/sarwatch_demo_bundle.zip') as z:
        meta=json.loads(z.read('manifest.json'));geo=json.loads(z.read('screened_candidates.geojson'))
        if len(geo['features'])!=1646:errors.append('Published October case candidate count changed unexpectedly.')
    if errors:
        print('\n'.join(errors),file=sys.stderr);raise SystemExit(1)
    size=sum(p.stat().st_size for p in files)
    print(f'PASS: {len(expected)} checksummed inputs/assets; {len(files)} repository files; {size/1048576:.1f} MiB; no external project paths, credentials or files >=100 MiB.')


if __name__=='__main__':main()
