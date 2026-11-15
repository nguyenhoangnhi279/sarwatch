# Methodology and evaluation

Scientific methods, measured results and limitations for the Hue case.

---

<a id="radar-ml"></a>

## Radar processing and machine learning

This report accompanies the historical NISAR case. Measured results below are
local computations, not values copied from publications.

### Raw radar recovered and processed

All four original Harmony GeoTIFF subsets are now available in `data/inputs/raw/`.
They are 3,247 by 3,361 pixels, EPSG:32648, 10 m. SHA-256 checksums are recorded
in `data/products/radar_rerun/report.json`. Source granule metadata is retained under
`data/inputs/metadata/`. No Earthdata credentials are required to process these files.

`run_radar.py` aligns the grids, excludes nonpositive/nonfinite power, applies
a 5 by 5 mean in linear power and converts to dB. A valid centre and at least
80% valid window support are required. Missing boundaries are not reflected.
The common processed-valid mask contains 10,634,303 pixels (97.4447%).

| Channel | Delta p05 | Median | p95 |
|---|---:|---:|---:|
| HH | -2.2222 dB | -0.5705 dB | 1.2810 dB |
| HV | -1.9971 dB | -0.3594 dB | 1.1512 dB |

Pooled HH Otsu threshold: -10.8488 dB. Require a transition from above the
threshold before to at/below it after, simultaneous HH/HV decrease, and an
eight-connected patch of at least 25 pixels.

| Setting | HH / HV decrease limits | Rerun area before auxiliary screening |
|---|---|---:|
| Loose | -1 / -0.5 dB | 13.6731 km2 |
| Middle | -1.5 / -0.75 dB | 10.5433 km2 |
| Strict | -2 / -1 dB | 7.4782 km2 |

The original Colab middle result was 10.3143 km2 before JRC/terrain screening,
9.3045 km2 afterward. The rerun makes boundary/support/connectivity rules
explicit and estimates its own threshold; it is not an exact reproduction of
the original notebook. Original JRC and DEM subsets are not identical to the new public source crops.
The full rerun now applies JRC v1.5 occurrence >=90% and DEM slope >5 degrees
using the documented source crops, giving 9.3809 km2. It removes 434 historical-
water pixels and 11,190 additional steep-slope pixels; no candidate lacks
auxiliary coverage. Slope cutoffs 3/5/10 give 8.7184 / 9.3809 / 10.1870 km2.
Jaccard with the published original is 0.8961, a product-agreement diagnostic,
not flood accuracy. The DEM source uses PixelIsPoint: tiepoint coordinates
are correctly shifted by half a pixel when constructing an outer-corner affine.
JRC uses PixelIsArea. Slope is calculated on a 30 m UTM grid, then aligned
bilinearly; occurrence uses nearest-neighbour resampling.
The published polygons remain pinned to the original bundle. Outputs are kept
separate so their provenance and differences remain inspectable.

### Radiometric diagnostics

Sentinel-2 SCL classes persistent at both optical dates provide diagnostic
strata. They are not proven invariant calibration targets. With a 60 m cloud
buffer, median HH / HV changes are:

| Optical stratum | Radar pixels | Median HH | Median HV |
|---|---:|---:|---:|
| Vegetation at both dates | 3,865,810 | -0.7234 dB | -0.5231 dB |
| Bare/built at both dates | 851,009 | -0.6544 dB | -0.4579 dB |
| Water at both dates | 1,854,264 | -0.2812 dB | -0.0521 dB |

These widespread shifts justify caution. Moisture, seasonality, wind and
different NISAR processing maturities remain confounded. No inferred global
offset is subtracted automatically. Raw details: `radiometry.json`.

### Trained Random Forest: optical-water proxy agreement

Task: classify open water from per-date NISAR HH, HV and HH-HV (dB), using
Sentinel-2 SCL class 6 versus classes 4/5 as weak labels. Other SCL classes and
a 60 m invalid/cloud boundary are excluded. Features are on a 20 m grid.
The optical times differ from NISAR by +16.2 and -31.8 hours.

Geographic blocks are 2 km; a deterministic coordinate hash assigns the same
block to the same split at both dates. Exclude 100 m block borders. Train /
validation / test contain 175 / 53 / 68 blocks and 120,000 / 100,000 / 100,000
sampled pixels. Pixels are spatially correlated, not independent observations.
The test set has 22,675 water labels and 77,325 other clear labels.

100 trees, max depth 14, minimum leaf size 10, balanced-subsample class weights,
seed 42. The threshold (0.60) maximizes validation IoU over 0.10-0.90 in steps
of 0.05. Otsu uses training HH only. Neither threshold uses held-out test labels.

| Held-out proxy agreement | Otsu baseline | Random Forest |
|---|---:|---:|
| Precision | 0.8131 | 0.8459 |
| Recall | 0.9036 | 0.9223 |
| F1 | 0.8560 | 0.8825 |
| IoU | 0.7482 | 0.7897 |

Random Forest confusion counts: TP 20,914; FP 3,809; FN 1,761; TN 73,516.
F1 is 2TP/(2TP+FP+FN); IoU is TP/(TP+FP+FN). Precision and recall have their
usual TP/(TP+FP) and TP/(TP+FN) definitions. Undefined denominators yield null.

Per-date RF F1 is 0.9227 before and 0.8319 after. Paired bootstrap over 68
held-out blocks (1,000 resamples, seed 2026) gives a descriptive 95% interval
for RF-minus-Otsu IoU of 0.0186 to 0.0711. RF IoU interval is 0.6931-0.8620;
these intervals describe this case, not future-event performance.

This is NOT validated flood accuracy. SCL is automated, includes coastal/open
water, has cloud/classification errors, and does not observe the same moment.
Spatial holdout does not establish temporal generalization. No calibrated flood
probability is claimed; this model does not replace the published candidates.
Saved model: `data/products/ml/water_proxy_rf.joblib`; evaluation: `evaluation.json`.

### Independent-source flood-candidate cross-check

See `METHODOLOGY.md#optical-validation`: 1,646 candidates checked, 943 with some jointly
clear optical coverage, nine with some new-optical-water intersection, 703
without clear reference under the fixed protocol. New-water overlap totals
only 5,000 m2. This weak evidence is retained, not turned into confirmed flood
extent. A correct open-water classifier does not itself prove new inundation.

Exposure and priority ordering remain conditional on the unvalidated candidate
mask: see `METHODOLOGY.md#exposure` for partial population coverage and OSM dates.

### Reproduce

Install `requirements.txt`, then run from the project root:

```powershell
python -m pipeline.radar
python -m pipeline.screening
python -m pipeline.comparison
python -m pipeline.radiometry
python -m pipeline.training
python -m dev.build.build_science_summary
python -m dev.build.build_standalone
```

Public auxiliary crops and acquisition provenance are included. To reacquire them:
`npm --prefix dev ci` then `node dev/tools/collect_auxiliary.mjs`. The complete repository ships
the four raw radar subsets, all other case inputs and the trained model.
Only a different case requires acquiring HH/HV through authenticated NASA
Earthdata/Harmony; this case uses AOI 107.45,16.30,107.75,16.60. Do not publish signed
download links or Earthdata credentials. Exact original-byte reproduction
requires matching product/version and request settings, not just the dates.

Algorithm references: Otsu (1979), DOI 10.1109/TSMC.1979.4310076,
https://ieeexplore.ieee.org/document/4310076 ; Breiman (2001), Random Forests,
https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf . These references
describe methods, not the performance of SARWatch. Full data attribution is in
`METHODOLOGY.md#sources` and `NOTICE`.

---

<a id="optical-validation"></a>

## Optical reference comparison

**Completed 15 November 2026.** All 1,646 NISAR candidate polygons were compared with real Copernicus Sentinel-2 reference data. The result is a dated cross-sensor comparison, not independently confirmed inundation or a measured operational flood accuracy.

### Sources and timing

| Role | UTC acquisition | Relation to NISAR |
|---|---|---|
| NISAR before | 15 Oct 2026, 11:21:40 | Primary radar observation |
| Sentinel-2 before, S2B_48QYD_20261016_0_L2A | 16 Oct 2026, 03:33:25.922 | +16.2 hours |
| NISAR event candidate | 27 Oct 2026, 11:21:40 | Primary radar observation |
| Sentinel-2 after, S2B_48QYD_20261026_0_L2A | 26 Oct 2026, 03:33:27.659 | −31.8 hours |

The Earth Search catalogue returned nine Sentinel-2 scenes for 12–30 October. The nearest 28 October scene reported 100% cloud and was rejected. The two selected scenes share the same tile and native 20 m classification grid. Full catalogue results and the selected actual classification TIFFs and true-colour crops are saved in data/inputs/reference. This work uses Copernicus Sentinel data (2026), distributed through Element84 Earth Search / AWS.

The official NCHMF bulletin issued at 17:00 ICT on 28 October discusses flood risk during 28–29 October: https://kttv.gov.vn/kttv/vi-VN/1/tin-canh-bao-lu-tren-cac-song-o-thanh-pho-hue-post55756.html . It establishes event context, not pixel labels or evidence that all candidate polygons were flooded at 18:21 ICT on 27 October. A 27 October Hue-S report concerning Duy Tan bridge discusses drainage obstruction and recurrent flooding: https://tuongtac.hue.gov.vn/phan-anh/kien-nghi-co-phuong-an-de-dong-chay-duoc-luu-thong-tai-cau-duy-tan-lan-2-a243838.html . It was not turned into a flood label because its text does not establish inundation at the NISAR observation.

The independent Sentinel-1 catalogue was also searched. It contains nearby observations on 25 and 28 October, but none at the NISAR event acquisition. Merely finding another radar product does not create a validated reference; these metadata are retained without inventing a Sentinel-1 flood result.

### Fixed optical comparison protocol

Use native Sentinel-2 SCL classes 4 (vegetation), 5 (not vegetated) and 6 (water) as potentially clear. Exclude every other class and add a conservative 60 m buffer around excluded pixels. New optical water is a transition from class 4/5 to class 6. Existing water is class 6 at both dates. The same masks are applied throughout the study; no NISAR threshold was retuned to improve agreement.

Measure exact polygon/cell intersection area in EPSG:32648 for each candidate. Partially cloud-obscured regions retain their clear-area fraction. A positive overlap of more than 1 m² is recorded as “some intersection with the optical new-water layer”, not “the polygon is confirmed flooded”. The reference resolution is 20 m, so small mixed-pixel boundaries require particular caution.

Official classification guidance: https://sentiwiki.copernicus.eu/web/s2-processing . Copernicus explicitly notes that SCL primarily supports atmospheric processing and is not a strict land-cover map: https://documentation.dataspace.copernicus.eu/FAQ.html . Therefore even coincident class changes need corroboration, and the approximately 32-hour event-date gap further limits interpretation.

### Actual results

| Result | Candidates |
|---|---:|
| Compared with both selected optical observations | 1,646 |
| Have some jointly clear reference area | 943 |
| No jointly clear area after quality exclusions | 703 |
| Some intersection with new optical-water layer | 9 |
| Existing optical water only | 28 |
| No new-water signal on the clear part | 906 |

The final three categories sum to the 943 candidates with some clear reference area. “Some clear area” does not mean an entire polygon is observable.

- Candidate area: 9.3045 km².
- Jointly clear candidate area: 3.8239 km², approximately 41.1% of the candidate area.
- Intersection with new optical water: approximately 0.0050 km² (5,000 m²), distributed across nine candidates.
- No independently confirmed flood area is reported.

The nine candidates are 125, 382, 401, 413, 418, 458, 921, 1119 and 1452. Their clear-area fractions and overlap areas are provided in data/products/validation/optical_crosscheck.csv. These are candidates with limited corroborating classification evidence, not nine confirmed flood zones.

**Interpretation:** this optical comparison does not support treating the entire 9.3045 km² as observed flooding. On much of the clear reference area there is no matching new-water signal. Possible explanations include changed soil/crop conditions or radar-processing differences; those explanations are hypotheses. Transient flooding between the optical and radar acquisitions also cannot be excluded.

### Sensitivity to optical quality exclusion

| Extra buffer | Clear fraction of centre-rasterized candidate grid | Overlapping new-water grid cells |
|---|---:|---:|
| 0 m | 70.81% | 28 |
| 60 m — primary protocol | 40.84% | 15 |
| 100 m | 27.02% | 9 |

These are 20 m comparison-grid statistics. Region-area results above use exact vector intersections and therefore do not equal grid-cell counts multiplied by 400 m². The weak new-water agreement persists across these tested quality buffers.

### Qualitative inspection completed

True-colour before/after crops were visually inspected for twelve candidate regions: the six highest exposure-ranked locations, three with the largest optical overlap, and three obscured controls. This is purposive inspection, not unbiased accuracy sampling, and it is not a field survey.

| Regions | Observation from the optical crops |
|---|---|
| 651, 452, 333, 494, 448, 247 | Predominantly field/vegetation/bare-surface patterns; no clearly delineated new open-water extent is established by these crops. Colour/brightness changes alone are insufficient to label floodwater. |
| 413 | Small positive classification overlap; the colour crop does not establish a distinct new open-water body. Mixed surface/pixel effects remain possible. |
| 125 | River/shore-edge setting; existing water is visible at both dates. A small boundary change does not establish broad inundation. |
| 921 | Vegetation and possible cloud-edge effects in the second crop; limited classification overlap is insufficient for confirmation. |
| 1, 6, 8 | Quality-masked in the conservative protocol. The coarse colour crops do not justify overriding the mask or confirming flooding. |

Four before/after inspection sheets are saved as data/products/validation/optical_review_sheet_1.jpg through _4.jpg. This qualitative review was performed by the assistant and is not an independent expert adjudication.

Eight outside-candidate controls were also inspected: two each of stable optical water, stable optical land, new optical-water pixels outside the candidates and obscured pixels, selected with seed 42. Stable water/land examples provide useful visual checks; optical-only examples include shoreline/pond/land-use boundaries, and obscured examples show clouds or bright ambiguous surfaces. These are not labelled true negatives or false negatives. The native NISAR valid-observation mask is absent locally, and both sensor timing and optical classification uncertainty prevent that interpretation. Their coordinates, classification values and images are retained in data/products/validation/noncandidate_controls.json and noncandidate_controls_1.jpg through _4.jpg.

### What changed in the application

Every candidate now has a separate automatic optical-reference status and its actual clear-area/overlap measurements. Selecting a candidate shows dated Sentinel-2 images beside each other. Users can filter the nine with some new-water overlap or inspect obscured cases. The interface shows automatic source status; it does not collect personal notes or review status. All three original navigation tabs are retained; no raw code or JSON is displayed.

### What remains unverified, and why

An independently surveyed or otherwise sufficiently reliable same-event flood map is still absent. Optical SCL is not ground truth, the observations differ by hours/days, and the local export lacks the full NISAR quality/validity rasters. Accordingly, F1/IoU/precision/recall are not published as flood-detection accuracy. The report provides actual comparison results rather than changing every flag to “validated”. Population estimates and road intersections are conditional exposure to candidate geometry, not independently observed damage.

To strengthen the case study, obtain an observation pair that brackets a documented flood event more closely and includes the native valid masks and processing metadata. The current detection baseline should be investigated rather than tuned to create an attractive flood extent.

### Reproduce

Use the GIS processing environment and the saved public inputs:

```powershell
python -m pipeline.reference
python -m pipeline.controls
python -m dev.build.build_standalone
```

Artifacts: optical_crosscheck.json, optical_crosscheck.csv, reference imagery, inspection sheets and the embedded app/web/reference-data.js. Unit tests check the reference class-transition and cloud-edge exclusion logic; these implementation tests do not establish scientific accuracy.

---

<a id="exposure"></a>

## Population, infrastructure and review priorities

This is an analytical case study, not an operational warning system. A review rank means “look here first according to the available exposure evidence”, not “this place will flood” or “this is the most dangerous location”.

### Inputs actually processed

- The real user-provided NISAR analysis export, observation dates 15/27 October 2026: 1,646 screened candidate polygons, 9.3045 km², version aa7948379b0991c9. No independent inundation reference has been supplied.
- WorldPop 2026, Global2 R2025A v1, constrained 100 m population-count grid. Downloaded from the official WorldPop API as a GeoTIFF for the Hue rectangle. Dataset DOI: https://doi.org/10.5258/SOTON/WP00839 . CC BY 4.0. Full official metadata, citation, request and source URL are recorded under data/inputs/auxiliary/worldpop_*.json.
- Current OpenStreetMap extracts from the official /api/0.6/map endpoint, retrieved on 15 November 2026. The resumable collector issued 37 successful low-concurrency extracts covering candidate locations, subdividing a dense query when necessary. Data © OpenStreetMap contributors, ODbL 1.0. Query bounds, timestamps and request URLs are preserved in data/inputs/auxiliary/osm_collection.json. Raw public extracts are retained under data/inputs/auxiliary/osm/.

The OSM snapshot is later than the radar observations. It documents mapped objects, not their status during the October event. Overpass and ohsome endpoints were unavailable; the official OSM map API was used as a fallback. Query success does not guarantee that OSM has mapped every road or facility.

### Population exposure

Each original WorldPop cell is a population count, not a density to be upsampled. For every candidate polygon, compute its intersection with each source cell, after projecting geometries to UTM zone 48N (EPSG:32648). The contribution is:

`cell_population × intersection_area / original_cell_area`

Assume uniform distribution within each original cell. Do not resample population counts onto the 10 m radar grid. NoData and nonfinite/negative values are excluded, not interpreted as zero residents. Preserve the fraction of candidate area covered by valid population cells. An entirely unobserved candidate receives a null estimate; a candidate intersecting only valid zero-valued cells can receive zero.

The current partial sum is approximately 1,681 modelled persons across valid cells. Valid population cells cover approximately 60.5% of total candidate area; 488 candidates have no valid population cells. This is not a complete population total, a number of victims or a number of people present in floodwater. The interface and exports retain the coverage distinction.

### Infrastructure overlap

Deduplicate OSM objects by type/id across extracts. Road centerlines are clipped to candidate polygons in EPSG:32648; measure only intersecting line length, not the full length of a road touching a polygon. Union coincident clipped lines before reporting total length. Exclude footpaths, steps, cycleways, proposed/construction roads and area-like highway polygons.

Facilities include hospitals, clinics, schools, kindergartens, fire stations and police. Test actual geometry intersections for direct exposure. A facility within 500 m is shown separately as nearby context; it is not counted as directly exposed. Avoid counting a tagged point label and its matching footprint twice where possible; incomplete tagging can still affect counts.

Current results: 18.689 km mapped road-centerline overlap across 300 candidates; zero facilities directly intersect candidates; 19 distinct mapped facilities within 500 m of candidate geometries. Infrastructure query coverage is complete under the geometric tolerance for 1,645 candidates and partial for one; that partial record remains flagged. Neither road overlap nor facility proximity establishes operational disruption.

### Review ordering

Sort lexicographically by:

1. Whether a mapped essential facility directly intersects the candidate.
2. Descending estimated population on valid WorldPop cells.
3. Descending road-centerline overlap length.
4. Descending candidate area, then stable candidate identifier.

There are no learned weights, artificial confidence percentages or calibrated risk classes. In the present case, no facility directly intersects, so population exposure determines the leading ranks. Partial/missing population coverage can understate exposure and is explicitly retained. This ranking supports examination; it cannot replace expert judgment or independent validation.

The point suggested for checking is a representative point inside the polygon, not an assumed safe access point or a recommended navigation route.

### Human review

The viewer can select a location, compare dated radar and optical evidence, filter reference status and export the verification list. CSV export contains location coordinates, exposure values, missing-data flags, priority rationale and automatic optical cross-check fields. Personal notes and review-status controls have been removed.

### Reproduce

Processing needs Python 3.11+ and the GIS dependencies in requirements.txt. Viewing needs none of them.

```powershell
python -m pipeline.exposure --prepare-osm
```

Use dev/tools/collect_osm.mjs's collectBatch(root, count) from Node to collect/resume the public extracts. The WorldPop request and its exact source grid are saved in data/inputs/auxiliary. Then:

```powershell
python -m pipeline.exposure
python -m dev.build.build_standalone
```

Outputs: data/products/impact/review_analysis.json, review_candidates.geojson, review_locations.csv, and the embedded app/web/impact-data.js. Rebuild exposure after changing the NISAR export; the website checks that their analysis-version identifiers agree.

### Checks and remaining scientific work

Tests cover population-count conservation over adjacent cell portions, NoData handling, clipped road lengths and deterministic review ordering. The real-data DOM test checks automatic loading, priority selection, map overlays and exports. These are implementation checks, not evidence of flood-detection accuracy.

Still needed: independent date-matched flood evidence, assessment of false positives and omissions, sensitivity of the review order to missing population/OSM coverage, and review with a local practitioner. Different processing maturity between the NISAR dates remains a scientific limitation.

---

<a id="rainfall"></a>

## Rainfall context and verification

### Luồng đã triển khai

Trang chủ tự lấy tổng lượng giáng thủy theo giờ từ Open-Meteo, chọn rõ mô hình ECMWF IFS. Có bốn điểm khảo sát trong vùng Huế; đây không phải dự báo chi tiết từng phường. Mỗi điểm có tọa độ yêu cầu và tọa độ ô mô hình trả về. Nguồn cung cấp dự báo; chưa có mô hình mưa do SARWatch huấn luyện.

Máy chủ chạy bộ thu thập mỗi 15 phút và lưu bản JSON nguyên gốc theo thời điểm tải ở data/products/forecasts. Chỉ hoạt động khi máy chủ còn chạy và có mạng. Thời điểm tải không phải thời điểm khởi tạo mô hình. Không có cảnh báo gửi điện thoại, dịch vụ nền khi tắt máy hay hosting công khai.

Mưa tại timestamp t là tích lũy của giờ trước t. Tổng từ hiện tại đến +5h/+12h chia tỷ lệ các giờ biên theo độ dài giao; giả định mưa đều trong giờ. Bất kỳ khoảng thiếu dữ liệu nào làm tổng không xác định, không thay thành 0. Không tạo dữ liệu dự báo mẫu để che lỗi mạng.

### Kiểm định bằng quan trắc

Công cụ evaluate_weather.py dành cho người vận hành, không phải người dùng website. Chuẩn bị CSV với các cột:

`snapshot,site,hours,observed_mm,observation_source`

- snapshot: tên JSON đã lưu trong data/products/forecasts.
- site: đúng mã điểm hue/northwest/coast/south.
- hours: 5 hoặc 12.
- observed_mm: tổng quan trắc độc lập cho đúng vị trí và cửa sổ từ retrieved_at đến retrieved_at + hours.
- observation_source: tên trạm/đơn vị, định danh tài liệu hoặc URL có thể kiểm tra.

Không dùng dự báo của chính nhà cung cấp làm quan trắc. Nếu dùng IMERG hoặc tái phân tích, phải ghi rõ đó là sản phẩm ước tính, đánh giá sai số nguồn tham chiếu và không gọi là mưa đo trạm. Hiện chưa có kết nối quan trắc độc lập tự động.

Ví dụ lệnh (ngưỡng chỉ là lựa chọn của thí nghiệm, không phải mức báo động chính thức):

```powershell
python -m pipeline.rainfall_evaluation observations.csv --threshold-5 10 --threshold-12 20
```

Báo cáo được lưu ở data/products/verification/rainfall_metrics.json và trang chủ tự đọc khi mở qua start.bat. Kiểm định tính riêng hai cửa sổ; MAE, RMSE, bias đơn vị mm; POD=H/(H+M), FAR=F/(H+F), CSI=H/(H+F+M). Mẫu số 0 trả null. Số mẫu, nguồn và thời kỳ được công bố. Công cụ kiểm tra cấu trúc nhưng không tự chứng thực chất lượng nguồn nhập.

Phải định trước ngưỡng, chia theo thời gian/đợt mưa, kiểm tra nhiều mùa và so với baseline. Các cửa sổ chồng nhau không phải các sự kiện độc lập; không suy diễn khoảng tin cậy từ số cửa sổ. Chưa có kiểm định thì giao diện ghi chưa đo.

### Điều kiện để gọi là cảnh báo ngập

Chưa có mô hình ngập đã huấn luyện hay kiểm định. Tín hiệu vượt ngưỡng mưa do người dùng tự đặt chỉ là theo dõi mưa. Cần chuỗi mực nước, mưa trước sự kiện, vận hành hồ, địa hình/thoát nước và nhãn ngập theo thời gian để xây mô hình riêng. Đánh giá ngập bằng nhãn độc lập; chỉ số mưa tốt không chứng minh cảnh báo ngập tốt. NISAR lịch sử hỗ trợ phân tích không gian, không cung cấp dự báo mưa.

### Tài liệu

- Open-Meteo ECMWF API: https://open-meteo.com/en/docs/ecmwf-api (hourly precipitation, ECMWF IFS; CC BY 4.0).
- Ayzel et al. (2019), Optical flow models as an open benchmark for radar-based precipitation nowcasting (rainymotion v0.1), https://doi.org/10.5194/gmd-12-1387-2019. Tham khảo phương pháp kiểm định; bài nghiên cứu 5–60 phút, không chứng minh kỹ năng 5/12h của SARWatch.
- Pulkkinen et al. (2019), Pysteps v1.0, https://doi.org/10.5194/gmd-12-4185-2019. Tham khảo kiểm định dự báo mưa xác suất/không gian; chưa triển khai FSS/Brier khi chưa có dự báo và tham chiếu phù hợp.


---

<a id="sources"></a>

## Data sources and licences

### NISAR

NASA–ISRO NISAR L2 GCOV frequencyA HHHH/HVHV.

- 15 October 2026, 11:21:40 UTC: Provisional, C2854338529-ASF / G4372302369-ASF.
- 27 October 2026, 11:21:40 UTC: Validated, C3622241360-ASF / G4406688609-ASF.
- Track 047, frame 080, Descending. Approximately 18:21 ICT.
- Records: data/inputs/metadata/scene_metadata.json.
- Documentation: https://nisar-docs.asf.alaska.edu/

The user downloaded and processed subsets on Colab and reported a shared 10 m EPSG:32648 grid. Different processing maturity requires radiometric consistency checks. Flood-peak timing has not been independently verified.

### Historical water

JRC Global Surface Water occurrence v1.5 through 2024, tile occurrence_100E_20N_v1_5_2024.tif.

https://global-surface-water.appspot.com/download

Exploratory exclusion: occurrence >=90%. Historical water is not ground truth for October 2026 flooding.

### Surface elevation

Copernicus DEM GLO-30 public DSM, tile N16 E107.

https://registry.opendata.aws/copernicus-dem/

Slope computed at approximately 30 m in a projected CRS then aligned to NISAR. Tested cutoffs 3, 5, 10 degrees; selected exploratory cutoff 5 degrees. DSM includes vegetation/buildings and is not bare-earth terrain.

### Reference imagery

Optional Esri World Imagery:

https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer

Attribution retained; check service terms before public deployment. Reference imagery differs in acquisition time and is not flood validation. The new frontend does not request OSM or CARTO tiles.

### Not yet supplied

Independent inundation labels and official live-warning feeds are not included. A trained water-proxy model and its measured spatial-holdout evaluation are now included; see METHODOLOGY.md#radar-ml. The UI must not invent these values. Population and infrastructure intersections are now computed from the sources below; they are potential exposure, not verified impacts.

### Bundle

The real user-provided Colab export is installed at data/products/sarwatch_demo_bundle.zip and published into app/web/analysis-data.js and app/standalone/index.html. Visitors see it automatically, without an upload or Earthdata credentials. The 1,646 polygons total 9.3045 km2 of unvalidated screened candidates. Statistics are read from the export, not generated for presentation. The source ZIP was validated locally for geometry, imagery, bounds and area agreement; the four original numerical radar subsets have now been recovered and processed locally. Independent inundation labels remain unavailable.

### Weather context

Open-Meteo Forecast API, explicitly selecting ECMWF IFS, provides hourly precipitation at sample points around Hue. API documentation: https://open-meteo.com/en/docs/ecmwf-api . Attribution: Open-Meteo / ECMWF, CC BY 4.0. Weather is ancillary context, separate from the historical NISAR analysis, and is not a trained SARWatch flood forecast. See METHODOLOGY.md#rainfall for accumulation and verification details.

### Challenge scope

NASA Space Apps 2026, Dancing with the SARs: interactive NISAR surface-change analysis is the core of the application. Official page: https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/ . The official page returned 502 during review; the challenge text was reviewed on the local-event reproduction https://hackathlone.com/challenges/dancing-with-the-sars .

### Exposure analysis

WorldPop Global2 R2025A v1, Vietnam population counts for 2026, approximately 100 m; DOI https://doi.org/10.5258/SOTON/WP00839 , CC BY 4.0. Official API https://api.worldpop.org/v3/raster returned the geographic subset saved as data/inputs/auxiliary/worldpop_hue_2026_100m.tif. Source metadata, exact request and full attribution are retained in data/inputs/auxiliary/worldpop_provenance.json and worldpop_metadata.json. NoData is unknown, not zero people; original-cell count is allocated by intersection area in EPSG:32648.

OpenStreetMap © contributors, ODbL 1.0; https://www.openstreetmap.org/copyright . Source is the official read API https://api.openstreetmap.org/api/0.6/map . Current extracts retrieved 15 November 2026 are preserved with request bounds/timestamps in data/inputs/auxiliary/osm_collection.json. They are not a historical reconstruction of October. Derived geometry in data/products/impact and app/web/impact-data.js retains OSM provenance and share-alike data attribution. See METHODOLOGY.md#exposure for coverage, deduplication, clipping and the distinction between directly intersecting and nearby facilities.

### Typeface

Be Vietnam Pro, sourced through Google Fonts, bundled locally under the SIL Open Font License. Full licence: app/web/fonts/OFL.txt. Font files are embedded in app/standalone/index.html for offline viewing.

### Independent optical reference

Copernicus Sentinel-2 L2A, tile 48QYD, S2B_48QYD_20261016_0_L2A and S2B_48QYD_20261026_0_L2A. Actual SCL TIFFs and 20 m true-colour crops were retrieved from the public sentinel-cogs archive via Element84 Earth Search: https://earth-search.aws.element84.com/v1 . Catalogue responses and source URLs are retained in data/inputs/reference. Attribution: contains modified Copernicus Sentinel data (2026). Classification and cloud/shadow handling follow the meanings documented at https://sentiwiki.copernicus.eu/web/s2-processing ; SCL is not a strict ground-truth land-cover/flood map. See METHODOLOGY.md#optical-validation for actual cross-check results, date gaps, quality exclusions and eight outside-candidate controls. No same-time validated-flood accuracy is claimed.

### Recovered numerical inputs and complete rerun

Four Harmony GeoTIFF subsets are now local in data/inputs/raw, with SHA-256 checksums in data/products/radar_rerun/report.json. Public DEM and JRC range-read crops, exact source URLs, extraction windows, pixel-registration conventions and timestamps are retained in data/inputs/auxiliary/*_source_crop.json. Acquisition can be repeated with dev/tools/collect_auxiliary.mjs. The DEM uses point registration, correctly converted to an outer-corner affine. The JRC v1.5 public source was retrieved after the 10 November 2026 out-of-range correction noted on its official download page.

JRC map attribution: Source: EC JRC/Google. Method citation: Pekel, J.-F., Cottam, A., Gorelick, N. and Belward, A.S. (2016), High-resolution mapping of global surface water and its long-term changes, Nature 540, 418–422, doi:10.1038/nature20584. See https://global-surface-water.appspot.com/download for free-use and acknowledgement terms.

Copernicus DEM GLO-30 Public is available under the licence linked from https://copernicus-dem-30m.s3.amazonaws.com/readme.html . This is a derived surface-slope product, not bare-earth elevation or a hydraulic model.

Required derived-DEM acknowledgement:
Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.

### Dataset attribution

WorldPop Global2 R2025A v1, Vietnam population estimates for 2026, approximately 100 m: DOI https://doi.org/10.5258/SOTON/WP00839 . WorldPop / University of Southampton and dataset authors as fully listed in data/inputs/auxiliary/worldpop_metadata.json. Licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ .

OpenStreetMap data © OpenStreetMap contributors, https://www.openstreetmap.org/copyright . Open Database License (ODbL) 1.0: https://opendatacommons.org/licenses/odbl/1-0/ . OSM-derived geometries and database components in the exposure products retain this attribution and share-alike data licence. Query timestamps and bounds are recorded in data/inputs/auxiliary/osm_collection.json. Current mapped objects do not establish their historical condition or present operational status.

Derived population/intersection results include assumptions and missing-data indicators described in METHODOLOGY.md#exposure. No independent flood confirmation is implied.


---

<a id="ai-disclosure"></a>

## AI use disclosure

OpenAI ChatGPT / Codex assisted with project planning, software implementation,
interface copy, scientific checks, debugging and submission drafts. The project
author is responsible for reviewing and submitting the work.

No generative AI imagery is used as satellite evidence. Radar previews, optical
reference crops and geospatial products are derived from the cited datasets.
Maps and statistics were computed from actual files, not generated sample values.

A Random Forest was trained locally using actual NISAR features and automated
Sentinel-2 scene-classification proxy labels. Its spatially held-out results
measure agreement with optical water labels, not confirmed flood detection or
future rainfall accuracy. Model artifacts and evaluation protocol are included.
ChatGPT did not supply ground-truth flood labels.

Weather predictions are produced by ECMWF IFS and delivered through Open-Meteo.
SARWatch does not claim to have trained that forecasting model.

All submission text remains a draft until reviewed by the project author. Follow
the current Project tab's AI disclosure fields and applicable event instructions.


---

<a id="submission"></a>

## Submission draft and demonstration

### Title
SARWatch AI - Prioritizing Flood Verification in Hue with NISAR

### Short description
SARWatch turns real multi-date NISAR radar observations into an interactive
evidence map, combines candidate changes with population and road exposure,
and helps identify where flood verification should begin in Hue, Vietnam.

### Project description
Flood responders need to decide where to investigate when information is
incomplete. SARWatch AI explores this problem in Hue using NASA-ISRO NISAR
observations from 15 and 27 October 2026.

Our interactive web application compares HH/HV backscatter, shows before/after
imagery, and publishes 1,646 screened new-water candidates from a real analysis
export. It joins those candidates to WorldPop population counts and mapped
OpenStreetMap infrastructure, then orders locations using explicit exposure
criteria rather than an unexplained risk score. Viewers can inspect individual
regions, compare optical reference imagery and export a verification checklist.

We recovered all four numerical radar subsets and implemented a reproducible
local processing pipeline with quality masks, power-domain speckle smoothing,
adaptive thresholding and parameter sensitivity. A CPU-trained Random Forest
achieves F1 0.8825 versus 0.8560 for Otsu on 100,000 held-out pixels from 68
spatial blocks. These results measure agreement with automated Sentinel-2
open-water proxy labels, not validated flood detection.

The cross-check matters as much as the detection. Only nine original candidate
regions intersect any new optical-water signal; 703 lack clear reference under
our conservative protocol. We expose those limitations alongside processing-
maturity differences and acquisition-time gaps. Potential population exposure
is approximately 1,681 modelled persons on valid cells covering 60.5% of the
candidate area; 18.689 km of mapped road centreline intersects the candidates.
Neither number is a confirmed impact count.

The contribution is an auditable path from NASA observations to locations for
further investigation. The application works offline for its historical case,
uses three navigation views, and keeps optional ECMWF rainfall context separate
from the radar evidence. It is an analytical prototype, not an operational
warning or evacuation system.

### Relationship to Dancing with the SARs
NISAR is the primary analytical input, not a decorative layer. The app lets
users explore radar-observed surface change, consider physical explanations
and limitations, and combine NASA observations with supplementary geospatial
context. See README and SCIENCE_REPORT for traceable outputs.

### Innovation and impact
The emphasis is on verification decisions: each candidate has interpretable
exposure fields, optical-reference status and a downloadable location record.
The prototype makes missing evidence visible and avoids equating radar change
with confirmed inundation. Potential users include researchers and local
disaster-analysis teams; no partner adoption or field deployment is claimed.

### Demonstration script: approximately 30 seconds
In Hue, satellite change becomes useful when we know where to investigate.
SARWatch compares real NISAR observations, maps potential new water, and ranks
locations by population and road exposure. Select a region to compare radar
and Sentinel-2 evidence, then export a verification checklist. Our reproducible
Random Forest improves optical-water agreement over a baseline. We show missing
coverage and uncertainty because these are investigation priorities, not
confirmed emergency warnings.

### Suggested demonstration capture
1. Open the map and show the observation dates and analysis footprint.
2. Select a high-exposure region from the priority list.
3. Compare before/after radar and the actual optical reference for that region.
4. Show reference status, partial population coverage and checklist export.
5. Briefly show the measured RF-versus-baseline panel under Về dữ liệu.

Record actual application interaction. Do not add generated floods or present
the reference basemap as an event-dated image. The script is a draft; use the
current Project tab's required duration/format and final field limits.

### Seven-slide fallback outline
1. Hue: the decision problem and intended users.
2. Actual NISAR granules, dates, coverage and processing maturities.
3. Reproducible radar-change method and parameter sensitivity.
4. Independent-source comparison, including weak agreement and missing coverage.
5. Trained water-proxy model, spatial holdout and baseline comparison.
6. Population/roads and the interactive verification workflow.
7. Limitations, next validation milestone, sources and AI disclosure.

### Resources and disclosure
Copy the relevant original links from METHODOLOGY.md#sources, including NASA NISAR,
Copernicus Sentinel-2, WorldPop and OpenStreetMap. Original code: Apache 2.0;
data/font terms: NOTICE. Disclose ChatGPT/Codex assistance using METHODOLOGY.md#ai-disclosure.
Do not describe proxy-water F1 as flood accuracy or provider rainfall as a
SARWatch-trained forecast.

### Final submission actions for the author
- Review the current 2026 Project tab and HCMC online instructions.
- Confirm team/event registration and all required fields.
- Publish the prepared web files/repository to an account you control and test
  the links signed out; this folder alone is not a public URL.
- Attach the actual recorded demo or permitted presentation and cite sources.
- Complete submission and check its final submitted status before the deadline.

No project has been submitted or externally published by this preparation step.
Judging results cannot be promised.
