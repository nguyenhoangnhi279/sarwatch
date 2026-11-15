# SARWatch: Methods and evaluation

This document describes the data, methods and measured results for the Hue case using NISAR observations from 15 and 27 October 2026. Results come from files included in the repository. SARWatch is an exploratory study supporting flood verification, not an operational warning system or a validated inundation map.

## Contents

1. [Objectives and scope](#1-objectives-and-scope)
2. [Study data](#2-study-data)
3. [Radar change analysis](#radar-ml)
4. [Water classification model](#4-water-classification-model)
5. [Optical cross-check](#optical-validation)
6. [Exposure and verification priorities](#exposure)
7. [Rainfall context](#rainfall)
8. [Reproducing the analysis](#8-reproducing-the-analysis)
9. [Limitations and future work](#9-limitations-and-future-work)
10. [Sources and licences](#sources)

## 1. Objectives and scope

SARWatch identifies radar changes for investigation, compares them with optical imagery, and combines population and infrastructure evidence to order verification locations. The study asks:

- Which locations meet the selected radar-change conditions for potential water transitions?
- Do Sentinel-2 observations provide corresponding evidence at those locations?
- Which locations should receive attention first, given the available exposure data?

| Term | Meaning |
|---|---|
| Candidate region | An area meeting the processing rules, not necessarily confirmed flooding |
| Exposure | Population or infrastructure intersecting candidate geometry, not observed damage |
| Water-label agreement | Agreement with automated Sentinel-2 classification, not flood-detection accuracy |
| Verification priority | An ordering for investigation, not a calibrated danger level |

## 2. Study data

The data request covers 107.45–107.75°E and 16.30–16.60°N. Areas, lengths and intersections are measured in UTM zone 48N, EPSG:32648.

| Dataset | Date or version | Purpose | Repository location |
|---|---|---|---|
| NISAR L2 GCOV, frequencyA, HHHH/HVHV | 15 and 27 October 2026 | Radar analysis | `data/inputs/raw/`, `data/inputs/metadata/` |
| Sentinel-2 L2A, tile 48QYD | 16 and 26 October 2026 | Reference imagery and water labels | `data/inputs/reference/` |
| JRC Global Surface Water | Occurrence v1.5 through 2024 | Historical-water exclusion | `data/inputs/auxiliary/jrc_source_crop.*` |
| Copernicus DEM GLO-30 | Tile N16 E107, approximately 30 m | Slope screening | `data/inputs/auxiliary/dem_source_crop.*` |
| WorldPop Global2 R2025A v1 | Population estimates for 2026, approximately 100 m | Population exposure | `data/inputs/auxiliary/worldpop_*` |
| OpenStreetMap | 37 extracts retrieved on 15 November 2026 | Roads and essential facilities | `data/inputs/auxiliary/osm/`, `osm_collection.json` |
| Open-Meteo / ECMWF IFS | Forecasts retrieved when online | Ancillary rainfall context | `data/products/forecasts/` when using the server |

### 2.1. Observation times

| Observation | Acquisition time, UTC | Offset from corresponding NISAR observation |
|---|---|---|
| NISAR before | 15 October 2026, 11:21:40 | — |
| Sentinel-2 before | 16 October 2026, 03:33:25.922 | Approximately 16.2 hours later |
| NISAR after | 27 October 2026, 11:21:40 | — |
| Sentinel-2 after | 26 October 2026, 03:33:27.659 | Approximately 31.8 hours earlier |

The Sentinel-2 scene on 28 October reported 100% cloud cover and was not selected. Both selected scenes share a tile and native 20 m classification grid. Sensor timing differences limit the comparison.

### 2.2. Provenance and input quality

Both NISAR scenes are descending acquisitions on track 047, frame 080. Their processing maturities differ: the earlier scene is **Provisional**, while the later scene is **Validated**. Their collection/granule identifiers are `C2854338529-ASF / G4372302369-ASF` and `C3622241360-ASF / G4406688609-ASF`. Metadata are retained in `data/inputs/metadata/scene_metadata.json`.

Four radar subsets exported through Harmony are included as GeoTIFFs, each 3,247 × 3,361 pixels at 10 m spacing. These subsets and their source records allow this case to be processed again without Earthdata credentials.

`data/manifest.json` records input sizes and SHA-256 checksums. For text entries marked `normalization=lf`, sizes and checksums use LF-normalized line endings. Binary files are checked byte for byte.

<a id="radar-ml"></a>

## 3. Radar change analysis

### 3.1. Preprocessing

The implementation in `pipeline/radar.py` and `pipeline/core/`:

1. Aligns all four HH/HV images to a common grid.
2. Excludes nonpositive power, nonfinite values and missing observations.
3. Applies a 5 × 5 mean filter in linear power, then converts to dB.
4. Requires a valid centre pixel and at least 80% valid window support, without reflecting values across missing boundaries.
5. Calculates change as `delta = after − before`.

The common processed-valid mask contains 10,634,303 pixels, or 97.4447% of the grid.

| Channel | Change, 5th percentile | Median change | Change, 95th percentile |
|---|---:|---:|---:|
| HH | −2.2222 dB | −0.5705 dB | 1.2810 dB |
| HV | −1.9971 dB | −0.3594 dB | 1.1512 dB |

### 3.2. Candidate detection

The pooled HH Otsu threshold is −10.8488 dB. Candidates must transition from above this threshold before to at or below it after, with simultaneous HH/HV decreases. Eight-connected regions must contain at least 25 pixels.

| Configuration | HH / HV decrease limits | Area before auxiliary screening |
|---|---|---:|
| Loose | −1 / −0.5 dB | 13.6731 km² |
| Middle | −1.5 / −0.75 dB | 10.5433 km² |
| Strict | −2 / −1 dB | 7.4782 km² |

These differences describe parameter sensitivity, not a confidence interval for flooded area.

### 3.3. Historical water and slope screening

The middle configuration excludes JRC occurrence of at least 90% and slopes above 5°. Slope is calculated on a 30 m UTM grid and aligned bilinearly to the radar grid. JRC occurrence uses nearest-neighbour resampling.

The DEM uses `PixelIsPoint` registration, requiring a half-pixel shift when constructing an outer-corner affine transform. JRC uses `PixelIsArea`. The DEM represents the surface, including possible vegetation and buildings, rather than bare-earth terrain.

The rerun removes 434 historical-water pixels and another 11,190 steep-slope pixels. No candidate pixel lacks auxiliary coverage. The remaining area is **9.3809 km²**. Slope limits of 3°, 5° and 10° produce 8.7184, 9.3809 and 10.1870 km² respectively.

### 3.4. Original and rerun products

| Product | Before screening | After screening | Use |
|---|---:|---:|---|
| Original Colab export | 10.3143 km² | 9.3045 km² | The 1,646 polygons used by the interface and exposure analysis |
| Repository rerun | 10.5433 km² | 9.3809 km² | Processing assessment with explicit rules and auxiliary provenance |

The runs differ in boundary handling, filter support, connectivity, threshold estimation and JRC/DEM subsets. The rerun is therefore not a byte-identical reproduction of the original Colab output. Their Jaccard agreement is **0.8961**, a product-overlap diagnostic rather than flood accuracy. Rerun products remain separate in `data/products/radar_rerun/`.

### 3.5. Radiometric diagnostics

Groups with the same Sentinel-2 classification at both dates provide diagnostic strata. They are not established invariant calibration targets.

| Surface stratum | Radar pixels | Median HH change | Median HV change |
|---|---:|---:|---:|
| Vegetation at both dates | 3,865,810 | −0.7234 dB | −0.5231 dB |
| Bare/built surface at both dates | 851,009 | −0.6544 dB | −0.4579 dB |
| Water at both dates | 1,854,264 | −0.2812 dB | −0.0521 dB |

Changes occur across several surface groups. Moisture, seasonality, wind and processing maturity remain confounded. No global offset is automatically subtracted. Details are in `data/products/radar_rerun/radiometry.json`.

## 4. Water classification model

### 4.1. Task and reference labels

A Random Forest classifies open water from NISAR HH, HV and HH − HV in dB on a 20 m grid. Automated Sentinel-2 SCL class 6 supplies water labels; classes 4/5 supply vegetation or nonvegetated labels. Other classes and a 60 m buffer around invalid areas are excluded.

These are **weak labels**, affected by classification errors and timing differences. The model classifies water at each date rather than learning new-inundation labels. It does not replace the original candidate layer in the interface.

### 4.2. Experimental design

The study divides space into 2 km blocks. A coordinate hash assigns blocks to splits consistently across both dates. A 100 m border strip is excluded to reduce spatial leakage.

| Split | Blocks | Sampled pixels |
|---|---:|---:|
| Training | 175 | 120,000 |
| Validation | 53 | 100,000 |
| Held-out test | 68 | 100,000 |

The model uses 100 trees, maximum depth 14, minimum leaf size 10, `balanced_subsample` class weights and seed 42. A threshold of 0.60 maximizes validation IoU over 0.10–0.90 in 0.05 increments. The Otsu baseline uses training HH only. Neither threshold is selected using test labels.

### 4.3. Results and interpretation

The test set contains 22,675 water labels and 77,325 other clear-surface labels.

| Metric | Otsu | Random Forest |
|---|---:|---:|
| Precision | 0.8131 | 0.8459 |
| Recall | 0.9036 | 0.9223 |
| F1 | 0.8560 | 0.8825 |
| Intersection over union, IoU | 0.7482 | 0.7897 |

Random Forest counts against SCL labels are TP = 20,914, FP = 3,809, FN = 1,761 and TN = 73,516. F1 = 2TP/(2TP + FP + FN); IoU = TP/(TP + FP + FN). These are not field-validated flood metrics.

Per-date F1 is 0.9227 before and 0.8319 after. A paired bootstrap over 68 test blocks, using 1,000 resamples and seed 2026, gives a descriptive 95% interval of 0.0186–0.0711 for Random-Forest-minus-Otsu IoU. The Random Forest IoU interval is 0.6931–0.8620.

Pixels are spatially correlated. These intervals describe this case and do not establish performance on future events. Model outputs are not calibrated flood probabilities.

The saved model is `data/products/ml/water_proxy_rf.joblib`; configuration and evaluation are in `data/products/ml/evaluation.json`.

<a id="optical-validation"></a>

## 5. Optical cross-check

### 5.1. Protocol

All 1,646 original candidate polygons are compared under fixed rules:

1. Treat only SCL classes 4, 5 and 6 as potentially clear; exclude other classes and add a 60 m buffer.
2. Define new optical water as class 4/5 transitioning to class 6 on jointly clear areas. Existing water is class 6 at both dates.
3. Measure exact polygon/cell intersection areas in EPSG:32648 and retain each region's clear-area fraction.
4. Record new-water intersection above 1 m² without declaring the whole polygon flooded.

NISAR thresholds are not retuned to improve agreement. SCL primarily supports atmospheric processing and is not a flood ground-truth map. Mixed shoreline pixels and acquisition-time differences require caution.

### 5.2. Results

| Reference status | Regions |
|---|---:|
| Some new-water intersection on the clear portion | 9 |
| Existing-water intersection only | 28 |
| No new-water signal on the clear portion | 906 |
| No jointly clear portion after quality exclusions | 703 |
| **Total** | **1,646** |

Some portion of 943 regions is observable. Jointly clear candidate area is **3.8239 km²**, approximately **41.1%** of total candidate area. New optical-water overlap is only approximately **0.0050 km²**, or 5,000 m².

The nine intersecting candidate IDs are 125, 382, 401, 413, 418, 458, 921, 1119 and 1452. They are not nine confirmed flooded regions. Per-region results are in `data/products/validation/optical_crosscheck.csv` and `optical_crosscheck.json`.

### 5.3. Sensitivity and visual inspection

| Quality-exclusion buffer | Clear candidate-grid fraction | Grid cells intersecting new water |
|---|---:|---:|
| 0 m | 70.81% | 28 |
| 60 m, primary configuration | 40.84% | 15 |
| 100 m | 27.02% | 9 |

These are centre-rasterized 20 m grid statistics, distinct from exact vector intersections above. Cell counts multiplied by cell area do not replace the polygon-intersection results.

Before/after imagery was inspected for 12 regions: six leading exposure-ranked regions, three with substantial optical overlap and three obscured regions. Many examples show fields, vegetation, bare surfaces or water edges without establishing a clear new inundation extent. Eight outside-candidate points were also reviewed, covering stable optical water, stable land, new SCL water and obscured areas.

This was purposive inspection assisted by ChatGPT/Codex, not random accuracy sampling, field observation or independent expert adjudication. Outside-candidate points are not established true negatives or missed floods. Images and records remain in `data/products/validation/`.

### 5.4. Interpretation

The comparison **does not justify treating all 9.3045 km² as actual flooding**. Much of the clear reference area lacks matching new-water evidence. Soil/crop changes and radar-processing differences remain hypotheses to investigate. Transient flooding between acquisitions also cannot be excluded.

Local bulletins and reports provide context rather than pixel-level flood labels. A Sentinel-1 catalogue search found nearby observations on 25 and 28 October, but this study has not produced a flood reference from those scenes.

<a id="exposure"></a>

## 6. Exposure and verification priorities

### 6.1. Population

WorldPop provides counts per original cell, not a density to upsample onto a 10 m radar grid. Each cell contributes:

**Cell population × polygon-intersection area / original cell area.**

This assumes uniform population distribution within a cell. Missing, nonfinite and negative values are excluded, not interpreted as zero people. Valid-area coverage is retained separately. A wholly unobserved region receives an unknown estimate; valid zero-valued cells contribute zero.

The partial sum is approximately **1,681 modelled people**, with valid population coverage on **60.5%** of candidate area. **488 regions** have no valid population-cell intersection. This is not a complete population total, a count of people present or an impact count.

### 6.2. Infrastructure

OSM objects are deduplicated by type/identifier. Road centrelines are clipped to candidates in EPSG:32648, and coincident segments are unioned before measuring length. A road touching a candidate does not contribute its entire length. Footpaths, steps, cycleways, proposed/construction roads and highway-tagged area polygons are excluded.

Essential facilities include hospitals, clinics, schools, kindergartens, fire stations and police. Actual geometry intersections define direct exposure; facilities within 500 m are reported separately as nearby. Matching point labels and building footprints are deduplicated where possible.

| Measure | Result |
|---|---:|
| Total intersecting road-centreline length | 18.689 km |
| Regions with road intersections | 300 |
| Directly intersecting essential facilities | 0 |
| Nearby essential facilities within 500 m | 19 |
| Regions fully covered by infrastructure queries under the geometric tolerance | 1,645/1,646 |

The OSM snapshot postdates the radar observations and may contain missing objects or tags. Intersections do not establish road closures, damage or facility operation. Partial query coverage remains flagged.

### 6.3. Priority ordering

Regions are ordered lexicographically, using the next criterion only to break ties:

1. Presence of a directly intersecting essential facility.
2. Descending population estimate on valid cells.
3. Descending intersecting road length.
4. Descending candidate area, followed by a stable region identifier.

There are no learned ranking weights or calibrated risk probabilities. With no direct facility intersections in this case, population drives the leading ranks. Missing data can change the ordering.

A representative point inside each polygon is a verification locator, not a safe access point or routing recommendation. Outputs include `data/products/impact/review_analysis.json`, `review_candidates.geojson` and `review_locations.csv`.

<a id="rainfall"></a>

## 7. Rainfall context

### 7.1. Source and accumulation

The application requests hourly precipitation from Open-Meteo, selecting ECMWF IFS at four sample locations around Hue. Requested coordinates and returned model-grid coordinates are distinguished. Results are not ward-specific forecasts.

Five- and twelve-hour totals use hourly intervals intersecting the requested window. A value at time `t` represents the preceding hour; boundary intervals are prorated by overlap duration, assuming uniform rainfall within the hour. Any missing required interval leaves the total unknown rather than zero.

The Python server collects every 15 minutes and stores responses in `data/products/forecasts/` while running and online. Retrieval time is not the model initialization time. HTML/GitHub Pages can request the provider directly when online but cannot run the Python archiver.

SARWatch has not trained a rainfall or flood-warning model. User-selected rainfall thresholds support monitoring and are not official warning levels. The application does not send telephone alerts.

### 7.2. Evaluation with observations

`pipeline/rainfall_evaluation.py` accepts a CSV with these columns:

| Column | Meaning |
|---|---|
| `snapshot` | Saved JSON filename in `data/products/forecasts/` |
| `site` | `hue`, `northwest`, `coast` or `south` |
| `hours` | Five- or twelve-hour horizon |
| `observed_mm` | Independent observed total for the same location and window, starting at retrieval time |
| `observation_source` | Traceable observation source |

Example using experimental thresholds rather than official warning levels:

```powershell
python -m pipeline.rainfall_evaluation observations.csv --threshold-5 10 --threshold-12 20
```

The report at `data/products/verification/rainfall_metrics.json` includes MAE, RMSE and mean bias in mm, plus threshold metrics: POD = H/(H + M), FAR = F/(H + F), CSI = H/(H + F + M). H denotes hits, F false alarms and M misses. Zero denominators yield an undefined result.

No automatic independent-observation feed or case-specific rainfall skill evaluation is currently available. The provider's own forecasts must not serve as observations. Satellite estimates or reanalysis require explicit identification and consideration of reference errors. Overlapping windows are not independent events, and rainfall skill does not establish flood-warning skill.

## 8. Reproducing the analysis

### 8.1. Environment and commands

From the repository root, create a Python 3.11 environment and run:

```powershell
python -m venv dev/.venv
dev/.venv/Scripts/python -m pip install -r requirements.txt
dev/.venv/Scripts/python run.py check
dev/.venv/Scripts/python run.py reproduce
dev/.venv/Scripts/python run.py test
```

On macOS/Linux, replace `dev/.venv/Scripts/python` with `dev/.venv/bin/python`. The `reproduce` command runs radar processing, screening, product comparison, radiometric diagnostics, training, exposure, optical comparison and frontend builds. A different case requires new inputs with recorded product versions and extraction settings, not merely different dates.

| Individual task | Command after activating the environment |
|---|---|
| Radar processing and screening | `python run.py radar` |
| Water-model training | `python run.py train` |
| Exposure analysis | `python run.py impact` |
| Optical comparison and outside-candidate controls | `python run.py reference` |
| Rebuild standalone HTML | `python run.py build` |

### 8.2. Checks and viewing

Tests cover missing data, radar filtering, population/road intersections, deterministic ordering, reference classification, checksums and HTTP behaviour. They assess software behaviour, not scientific accuracy against independent flood labels.

Run interface tests using the repository's Node configuration:

```powershell
npm --prefix dev ci
npm --prefix dev run test:ui
```

On Windows, `start.bat` opens `app/standalone/index.html`. `start.bat --server` or `python run.py --open` starts the server. Static viewing supports the historical case; forecast archiving and Python APIs require the server. Online basemaps and new forecasts require internet access.

## 9. Limitations and future work

| Limitation | Consequence | Next step |
|---|---|---|
| No independent time-matched flood labels | Flood-detection accuracy remains unknown | Obtain reliable event-specific labels |
| Different NISAR processing maturities and incomplete native quality layers in the export | Changes may include non-flood effects | Add native validity masks and radiometric consistency checks |
| Sentinel-2 timing offsets, clouds and SCL errors | Cross-check evidence is partial | Acquire closer observations and multiple references |
| Model evaluated on one case | Generalization to new events is unproven | Evaluate multiple events with spatial and temporal separation |
| Population/OSM coverage and timing limitations | Exposure and ordering may be biased | Assess missing-data sensitivity and consult practitioners |
| No hydrological/hydraulic model and matching observations | Rainfall cannot establish a flood forecast | Integrate water levels, antecedent rainfall, reservoir operation and drainage |

Results support investigation and evidence tracing. They should not be the sole basis for emergency response or evacuation decisions.

<a id="sources"></a>

## 10. Sources and licences

### 10.1. Data and software

| Source | Documentation or identifier | Attribution and terms |
|---|---|---|
| NASA–ISRO NISAR | [ASF documentation](https://nisar-docs.asf.alaska.edu/); identifiers in Section 2 | Credit NISAR and retain version metadata |
| Copernicus Sentinel-2 | [Earth Search](https://earth-search.aws.element84.com/v1), [SCL documentation](https://sentiwiki.copernicus.eu/web/s2-processing), [data explanation](https://documentation.dataspace.copernicus.eu/FAQ.html) | Contains modified Copernicus Sentinel data (2026); image URLs and catalogue records in `data/inputs/reference/` |
| JRC Global Surface Water | [Downloads](https://global-surface-water.appspot.com/download) | Source: EC JRC/Google; cite Pekel et al. (2016) |
| Copernicus DEM GLO-30 | [Catalogue](https://registry.opendata.aws/copernicus-dem/), [licence](https://copernicus-dem-30m.s3.amazonaws.com/readme.html) | Retain the required acknowledgement below |
| WorldPop | [DOI: 10.5258/SOTON/WP00839](https://doi.org/10.5258/SOTON/WP00839), [API](https://api.worldpop.org/v3/raster) | CC BY 4.0; full authors/citation in `worldpop_metadata.json`, request provenance in `worldpop_provenance.json`, under `data/inputs/auxiliary/` |
| OpenStreetMap | [Copyright](https://www.openstreetmap.org/copyright), [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) | © OpenStreetMap contributors; derived data retain attribution and applicable share-alike obligations |
| Open-Meteo / ECMWF | [API documentation](https://open-meteo.com/en/docs/ecmwf-api) | Credit Open-Meteo / ECMWF; CC BY 4.0 |
| Esri World Imagery, optional | [Basemap service](https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer) | Retain attribution and comply with service terms; imagery from other dates is not a flood label |
| Be Vietnam Pro | `app/web/fonts/OFL.txt` | SIL Open Font License; bundled and embedded in standalone HTML |
| SARWatch source | [LICENSE](../LICENSE), [NOTICE](../NOTICE) | Apache 2.0 for original code; third-party data/fonts retain their own terms |

Required DEM acknowledgement:

> Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.

### 10.2. Method references

- Otsu (1979), threshold selection: [DOI: 10.1109/TSMC.1979.4310076](https://doi.org/10.1109/TSMC.1979.4310076).
- Breiman (2001), Random Forests: [paper](https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf).
- Pekel et al. (2016), long-term surface-water mapping: [DOI: 10.1038/nature20584](https://doi.org/10.1038/nature20584).
- Ayzel et al. (2019), rainfall-evaluation background: [DOI: 10.5194/gmd-12-1387-2019](https://doi.org/10.5194/gmd-12-1387-2019).
- Pulkkinen et al. (2019), Pysteps: [DOI: 10.5194/gmd-12-4185-2019](https://doi.org/10.5194/gmd-12-4185-2019).

These publications inform the methods; their reported performance does not substitute for SARWatch's own evaluation.
