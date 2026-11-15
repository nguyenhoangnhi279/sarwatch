"""Build the local case-study notebook."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
cells=[]
def add(kind,source):
    cell=dict(cell_type=kind,metadata={},source=source.splitlines(keepends=True))
    if kind=='code':cell.update(execution_count=None,outputs=[])
    cells.append(cell)

add('markdown','# SARWatch — Huế\n\nCompleted local workflow for the real October 2026 case. Run from the project folder with the saved inputs. All case-study inputs are shipped inside this repository. NASA Earthdata/Harmony is needed only to acquire a different case. This notebook contains no credentials or generated results. The original published case and numerical rerun remain separate.\n')
steps=[
('1. Environment','Install the scientific dependencies in your notebook environment.',
 "from pathlib import Path\nrequirements_path=next(p/'requirements.txt' for p in [Path.cwd(), *Path.cwd().parents] if (p/'run.py').is_file())\n%pip install -r {requirements_path}\n"),
('2. Project configuration','Resolve the actual project folder. No Drive mount is needed locally.',
 '''from pathlib import Path
import sys, json
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p/'run.py').is_file() and (p/'app/web').is_dir())
sys.path.insert(0,str(ROOT))
RUN_EXPENSIVE = False  # Set True to recompute cached reference/impact/model products.
print(ROOT)
'''),
('3. Actual raw inputs','The four original Harmony subsets are shipped in data/inputs/raw and are verified by checksum.',
 '''import hashlib
raw = [ROOT/'data/inputs/raw'/f'{date}_{ch}.tif' for date in ['before','after'] for ch in ['HH','HV']]
for path in raw:
    if not path.is_file(): raise FileNotFoundError(f'Missing {path.name}: obtain the actual HH/HV subset; do not create synthetic data.')
    print(path.name,path.stat().st_size,hashlib.sha256(path.read_bytes()).hexdigest())
'''),
('4. Scene metadata','Exact collection IDs preserve the mixed-maturity issue.',
 '''scenes = [
 {'date':'2026-10-15','granule':'G4372302369-ASF','collection':'C2854338529-ASF','maturity':'Provisional'},
 {'date':'2026-10-27','granule':'G4406688609-ASF','collection':'C3622241360-ASF','maturity':'Validated'}]
print(json.dumps(scenes,indent=2))
print('Track 047 / frame 080; descending; HH/HV. AOI 107.45,16.30,107.75,16.60.')
'''),
('5. Load and inspect','Inspect numerical power values, not just the PNG previews.',
 '''import numpy as np, rasterio
for path in raw:
    with rasterio.open(path) as ds:
        a=ds.read(1);valid=np.isfinite(a)&(a>0)
        print(path.name,ds.crs,a.shape,ds.res,'positive valid %',round(100*valid.mean(),3))
'''),
('6. Geospatial grid check','Confirm the actual input grids are identical before comparison.',
 '''grids=[]
for path in raw:
    with rasterio.open(path) as ds: grids.append((ds.crs,ds.transform,ds.width,ds.height))
assert all(g==grids[0] for g in grids),'Grid mismatch: review alignment before analysis.'
print('All four input grids match.')
'''),
('7. Numerical processing and quality control','Run the implemented pipeline: positive-power masks, NaN-safe 5×5 mean, 80% support, dB, common valid mask.',
 '''from pipeline.radar import run as run_radar
run_radar()
rerun=json.loads((ROOT/'data/products/radar_rerun/report.json').read_text())
print('Common processed-valid %:',rerun['valid_percent'])
'''),
('8. Features and radiometry','Observed changes and persistent-optical-class diagnostics. These strata are not invariant calibration targets.',
 '''from pipeline.radiometry import run as audit_radiometry
audit_radiometry()
print(json.dumps(rerun['delta_db'],indent=2))
'''),
('9. Baseline candidates','Threshold and sensitivity are measured from actual data. No confirmed-flood claim.',
 '''print('Pooled HH Otsu dB:',rerun['otsu_pooled_hh_db'])
for setting in rerun['settings']: print(setting)
print('Raster products:',ROOT/'data/products/radar_rerun')
'''),
('10. Auxiliary screening and product comparison','New documented public DEM/JRC crops complete the rerun. Keep its output separate from the original export.',
 '''from pipeline.screening import run as screen_radar
from pipeline.comparison import run as compare_rerun
screen_radar()
compare_rerun()
from app.server.data_loader import load_bundle
meta,geo,_,_=load_bundle((ROOT/'data/products/sarwatch_demo_bundle.zip').read_bytes())
print('Published original candidate count:',len(geo['features']))
print('Original area before / after auxiliary screening:',meta['initial_area_km2'],meta['screened_area_km2'])
assert abs(meta['screened_area_km2']-9.3045)<1e-6
'''),
('11. Independent-source optical cross-check','Recompute with actual SCL and RGB source inputs when requested. Temporal gaps prevent flood-ground-truth claims.',
 '''if RUN_EXPENSIVE:
    from pipeline.reference import build
    build()
reference=json.loads((ROOT/'data/products/validation/optical_crosscheck.json').read_text())
print(json.dumps(reference.get('summary',reference),indent=2)[:6000])
'''),
('12. Random Forest water-proxy experiment','Spatial blocks stay in the same split at both dates. This measures optical-water agreement, not flood accuracy.',
 '''if RUN_EXPENSIVE:
    from pipeline.training import run as train_water
    train_water()
evaluation=json.loads((ROOT/'data/products/ml/evaluation.json').read_text())
for key in ['task','sample_counts','spatial_block_counts','test_random_forest','test_otsu','bootstrap_95']:
    print(key,evaluation[key])
'''),
('13. Population and infrastructure exposure','Population counts are conserved by area allocation; missing cells stay unknown. Current OSM is not a historical road-status observation.',
 '''if RUN_EXPENSIVE:
    from pipeline.exposure import build as build_impact
    build_impact()
impact=json.loads((ROOT/'data/products/impact/review_analysis.json').read_text())
print(json.dumps(impact['summary'],indent=2))
'''),
('14. Build the complete HTML app','Three views, actual embedded data, local Vietnamese fonts. Public viewers do not upload data.',
 '''from dev.build.build_science_summary import build as build_summary
build_summary()
import runpy
runpy.run_path(str(ROOT/'dev/build/build_standalone.py'),run_name='__main__')
print('Open:',ROOT/'app/standalone'/'index.html')
'''),
('15. Save and review artifacts','Checksums identify exactly which measured reports belong to this run.',
 '''reports=['data/products/radar_rerun/report.json','data/products/radar_rerun/screening.json','data/products/radar_rerun/product_comparison.json','data/products/radar_rerun/radiometry.json','data/products/ml/evaluation.json','data/products/validation/optical_crosscheck.json','data/products/impact/review_analysis.json']
checksums={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in reports}
(ROOT/'data/products/reproduction_checksums.json').write_text(json.dumps(checksums,indent=2))
print(json.dumps(checksums,indent=2))
print('Read docs/METHODOLOGY.md before presenting results.')
''')]
for title,description,code in steps:
    add('markdown','## '+title+'\n\n'+description+'\n')
    add('code',code)
notebook=dict(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'),language_info=dict(name='python',version='3.11')),nbformat=4,nbformat_minor=5)
(ROOT/'pipeline/notebooks/Hue_Flood_Analysis.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=1),encoding='utf-8')
print('Built completed 15-step notebook.')
