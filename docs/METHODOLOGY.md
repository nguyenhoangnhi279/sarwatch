# SARWatch — Phương pháp và đánh giá

Tài liệu mô tả dữ liệu, quy trình xử lý và kết quả nghiên cứu tại Huế với hai ảnh NISAR ngày 15 và 27/10/2026. Các chỉ số được tính từ dữ liệu lưu trong kho mã nguồn. SARWatch là nghiên cứu thử nghiệm phục vụ kiểm chứng dấu hiệu ngập; chưa phải hệ thống cảnh báo hoặc bản đồ ngập đã được xác nhận.

## Mục lục

1. [Mục tiêu và phạm vi](#1-mục-tiêu-và-phạm-vi)
2. [Dữ liệu nghiên cứu](#2-dữ-liệu-nghiên-cứu)
3. [Phân tích thay đổi radar](#radar-ml)
4. [Mô hình phân loại nước](#4-mô-hình-phân-loại-nước)
5. [Đối chiếu quang học](#optical-validation)
6. [Phơi nhiễm và thứ tự kiểm chứng](#exposure)
7. [Thông tin mưa bổ trợ](#rainfall)
8. [Tái lập kết quả](#8-tái-lập-kết-quả)
9. [Giới hạn và hướng phát triển](#9-giới-hạn-và-hướng-phát-triển)
10. [Nguồn và giấy phép](#sources)
11. [Khai báo công cụ hỗ trợ](#ai-disclosure)

## 1. Mục tiêu và phạm vi

SARWatch phân tích thay đổi tán xạ ngược radar để khoanh vùng cần xem xét, đối chiếu với ảnh quang học, sau đó kết hợp dân số và hạ tầng nhằm xác định thứ tự kiểm chứng. Nghiên cứu tập trung vào ba câu hỏi:

- Vị trí nào có biến đổi radar đáp ứng điều kiện phát hiện nước được lựa chọn?
- Những vị trí đó có bằng chứng tương ứng trong ảnh Sentinel-2 hay không?
- Với dữ liệu hiện có, nên ưu tiên kiểm chứng vị trí nào?

Các khái niệm được dùng thống nhất:

| Khái niệm | Ý nghĩa |
|---|---|
| Vùng ứng viên | Vùng đáp ứng các điều kiện xử lý; chưa đồng nghĩa với vùng ngập |
| Phơi nhiễm | Dân số hoặc hạ tầng giao với vùng ứng viên; chưa phải thiệt hại thực tế |
| Mức khớp nhãn nước | Sự phù hợp với phân lớp tự động của Sentinel-2; chưa phải độ chính xác phát hiện lũ |
| Thứ tự kiểm chứng | Thứ tự xem xét theo dữ liệu phơi nhiễm; chưa phải cấp độ nguy hiểm |

## 2. Dữ liệu nghiên cứu

Phạm vi yêu cầu dữ liệu là 107,45–107,75°Đ và 16,30–16,60°B. Diện tích, chiều dài và giao cắt được tính trong hệ tọa độ UTM múi 48 Bắc, EPSG:32648.

| Dữ liệu | Thời điểm hoặc phiên bản | Vai trò | Vị trí lưu |
|---|---|---|---|
| NISAR L2 GCOV, frequencyA, HHHH/HVHV | 15 và 27/10/2026 | Phân tích radar | `data/inputs/raw/`, `data/inputs/metadata/` |
| Sentinel-2 L2A, ô 48QYD | 16 và 26/10/2026 | Ảnh đối chiếu và nhãn nước tham chiếu | `data/inputs/reference/` |
| JRC Global Surface Water | Tần suất nước v1.5, đến năm 2024 | Loại nước thường xuyên | `data/inputs/auxiliary/jrc_source_crop.*` |
| Copernicus DEM GLO-30 | Ô N16 E107, khoảng 30 m | Tính độ dốc | `data/inputs/auxiliary/dem_source_crop.*` |
| WorldPop Global2 R2025A v1 | Dân số ước tính năm 2026, ô khoảng 100 m | Ước tính phơi nhiễm dân số | `data/inputs/auxiliary/worldpop_*` |
| OpenStreetMap | 37 phần trích xuất ngày 15/11/2026 | Đường và cơ sở thiết yếu | `data/inputs/auxiliary/osm/`, `osm_collection.json` |
| Open-Meteo / ECMWF IFS | Dự báo lấy khi có mạng | Thông tin mưa bổ trợ | `data/products/forecasts/` khi chạy server |

### 2.1. Thời điểm quan sát

| Quan sát | Thời gian UTC | So với NISAR tương ứng |
|---|---|---|
| NISAR trước | 15/10/2026, 11:21:40 | — |
| Sentinel-2 trước | 16/10/2026, 03:33:25,922 | Muộn hơn khoảng 16,2 giờ |
| NISAR sau | 27/10/2026, 11:21:40 | — |
| Sentinel-2 sau | 26/10/2026, 03:33:27,659 | Sớm hơn khoảng 31,8 giờ |

Ảnh Sentinel-2 ngày 28/10 có mức mây công bố 100% nên không được chọn. Hai ảnh sử dụng cùng ô và cùng lưới phân lớp 20 m. Chênh lệch thời gian giữa cảm biến là giới hạn của phép đối chiếu.

### 2.2. Truy nguyên và chất lượng đầu vào

Hai ảnh NISAR cùng quỹ đạo xuống, track 047, frame 080, nhưng khác mức xử lý: ảnh trước là **Provisional**, ảnh sau là **Validated**. Mã collection/granule lần lượt là `C2854338529-ASF / G4372302369-ASF` và `C3622241360-ASF / G4406688609-ASF`. Siêu dữ liệu nằm trong `data/inputs/metadata/scene_metadata.json`.

Bốn ảnh radar gốc được xuất qua Harmony dưới dạng GeoTIFF, kích thước 3.247 × 3.361 pixel, độ phân giải 10 m. Kho mã nguồn giữ các phần trích xuất và thông tin nguồn để xử lý lại trường hợp này mà không cần thông tin đăng nhập Earthdata.

Danh mục `data/manifest.json` lưu kích thước và SHA-256. Với mục văn bản có `normalization=lf`, kích thước và checksum được tính sau khi chuẩn hóa xuống dòng LF; dữ liệu nhị phân được kiểm tra nguyên byte.

<a id="radar-ml"></a>

## 3. Phân tích thay đổi radar

### 3.1. Tiền xử lý

Quy trình trong `pipeline/radar.py` và `pipeline/core/` gồm:

1. Căn chỉnh bốn ảnh HH/HV về lưới chung.
2. Loại công suất không dương, giá trị không hữu hạn và vùng thiếu dữ liệu.
3. Lọc trung bình cửa sổ 5 × 5 trên công suất tuyến tính rồi chuyển sang dB.
4. Chỉ giữ pixel có tâm hợp lệ và ít nhất 80% cửa sổ hợp lệ; không phản chiếu dữ liệu qua biên thiếu.
5. Tính thay đổi theo công thức `Δ = giá trị sau − giá trị trước`.

Mặt nạ hợp lệ chung gồm 10.634.303 pixel, tương ứng 97,4447% lưới ảnh.

| Kênh | Phân vị 5% của Δ | Trung vị Δ | Phân vị 95% của Δ |
|---|---:|---:|---:|
| HH | −2,2222 dB | −0,5705 dB | 1,2810 dB |
| HV | −1,9971 dB | −0,3594 dB | 1,1512 dB |

### 3.2. Phát hiện vùng ứng viên

Ngưỡng Otsu từ phân bố HH gộp hai thời điểm là −10,8488 dB. Pixel ứng viên phải chuyển từ trên ngưỡng sang bằng hoặc dưới ngưỡng, đồng thời giảm ở cả HH và HV. Chỉ giữ vùng liên thông tám hướng có ít nhất 25 pixel.

| Cấu hình | Điều kiện giảm HH / HV | Diện tích trước sàng lọc phụ trợ |
|---|---|---:|
| Nới lỏng | −1 / −0,5 dB | 13,6731 km² |
| Trung gian | −1,5 / −0,75 dB | 10,5433 km² |
| Chặt | −2 / −1 dB | 7,4782 km² |

Sự khác nhau giữa các cấu hình thể hiện độ nhạy tham số; chưa phải khoảng tin cậy của diện tích ngập.

### 3.3. Sàng lọc nước thường xuyên và độ dốc

Với cấu hình trung gian, loại pixel có tần suất nước JRC từ 90% trở lên và độ dốc lớn hơn 5°. Tính độ dốc trên lưới UTM 30 m rồi nội suy song tuyến tính về lưới radar; JRC dùng láng giềng gần nhất.

DEM dùng quy ước `PixelIsPoint`, được dịch nửa pixel khi dựng phép biến đổi theo góc ngoài ô; JRC dùng `PixelIsArea`. DEM là mô hình bề mặt, có thể bao gồm cây và công trình, chưa phải địa hình đất trần.

Lần tái chạy loại 434 pixel nước thường xuyên và thêm 11.190 pixel dốc; không có pixel ứng viên thiếu dữ liệu phụ trợ. Diện tích còn lại là **9,3809 km²**. Với ngưỡng dốc 3°, 5° và 10°, diện tích tương ứng là 8,7184; 9,3809 và 10,1870 km².

### 3.4. Phân biệt hai sản phẩm

| Sản phẩm | Trước sàng lọc | Sau sàng lọc | Vai trò |
|---|---:|---:|---|
| Bản Colab gốc | 10,3143 km² | 9,3045 km² | 1.646 đa giác dùng trên giao diện và trong phân tích phơi nhiễm |
| Bản tái chạy trong repo | 10,5433 km² | 9,3809 km² | Kiểm tra quy trình với điều kiện xử lý và dữ liệu phụ trợ được ghi rõ |

Hai bản khác quy tắc biên, hỗ trợ cửa sổ lọc, liên thông, cách tính ngưỡng và phần trích xuất JRC/DEM. Vì vậy, bản tái chạy không phải bản sao nguyên byte của kết quả Colab. Hệ số Jaccard giữa hai sản phẩm là **0,8961**, chỉ đo mức chồng khớp sản phẩm, không đo độ chính xác ngập. Kết quả tái chạy được giữ riêng tại `data/products/radar_rerun/`.

### 3.5. Kiểm tra độ ổn định bức xạ

Dùng các nhóm có cùng phân lớp Sentinel-2 ở hai ngày để khảo sát biến đổi radar. Đây chưa phải mục tiêu hiệu chuẩn đã được chứng minh bất biến.

| Nhóm bề mặt | Số pixel radar | Trung vị ΔHH | Trung vị ΔHV |
|---|---:|---:|---:|
| Thực vật ở cả hai ngày | 3.865.810 | −0,7234 dB | −0,5231 dB |
| Bề mặt trống/xây dựng ở cả hai ngày | 851.009 | −0,6544 dB | −0,4579 dB |
| Nước ở cả hai ngày | 1.854.264 | −0,2812 dB | −0,0521 dB |

Biến đổi xuất hiện trên nhiều nhóm bề mặt. Độ ẩm, mùa vụ, gió và khác biệt mức xử lý NISAR có thể cùng ảnh hưởng; chưa tách được từng nguyên nhân. Không tự động trừ một độ lệch chung. Chi tiết: `data/products/radar_rerun/radiometry.json`.

## 4. Mô hình phân loại nước

### 4.1. Bài toán và nhãn tham chiếu

Random Forest phân loại mặt nước từ ba đặc trưng NISAR: HH, HV và HH − HV, cùng ở đơn vị dB trên lưới 20 m. Nhãn tham chiếu là phân lớp tự động SCL: lớp 6 là nước, lớp 4/5 là thực vật hoặc bề mặt không có thực vật. Loại các lớp khác và vùng đệm 60 m quanh phần không hợp lệ.

Đây là **nhãn yếu**, có sai số phân lớp và lệch thời điểm so với radar. Mô hình nhận diện nước theo từng ngày, không trực tiếp học nhãn ngập mới và không thay lớp ứng viên gốc trên giao diện.

### 4.2. Thiết kế thí nghiệm

Chia không gian thành khối 2 km. Hàm băm tọa độ xác định tập cho từng khối và giữ nguyên phân chia ở cả hai ngày. Loại dải 100 m sát biên khối để hạn chế rò rỉ không gian.

| Tập dữ liệu | Số khối | Số pixel lấy mẫu |
|---|---:|---:|
| Huấn luyện | 175 | 120.000 |
| Chọn tham số | 53 | 100.000 |
| Kiểm tra giữ riêng | 68 | 100.000 |

Mô hình dùng 100 cây, độ sâu tối đa 14, tối thiểu 10 mẫu mỗi lá, trọng số lớp `balanced_subsample`, hạt giống 42. Ngưỡng 0,60 được chọn theo IoU trên tập chọn tham số, khảo sát 0,10–0,90 với bước 0,05. Phương pháp cơ sở Otsu chỉ dùng HH của tập huấn luyện; không chọn ngưỡng bằng nhãn tập kiểm tra.

### 4.3. Kết quả và ý nghĩa

Tập kiểm tra có 22.675 nhãn nước và 77.325 nhãn bề mặt rõ khác.

| Chỉ số | Otsu | Random Forest |
|---|---:|---:|
| Độ chính xác của dự đoán nước — Precision | 0,8131 | 0,8459 |
| Tỷ lệ thu hồi nhãn nước — Recall | 0,9036 | 0,9223 |
| F1 | 0,8560 | 0,8825 |
| Tỷ lệ giao trên hợp — IoU | 0,7482 | 0,7897 |

Random Forest có TP = 20.914, FP = 3.809, FN = 1.761, TN = 73.516 theo nhãn SCL. F1 = 2TP/(2TP + FP + FN); IoU = TP/(TP + FP + FN). Các chỉ số này chưa phải độ chính xác ngập thực địa.

F1 theo ngày là 0,9227 ở ảnh trước và 0,8319 ở ảnh sau. Lấy mẫu lại theo 68 khối kiểm tra, 1.000 lần với hạt giống 2026, cho khoảng 95% mô tả của chênh lệch IoU giữa Random Forest và Otsu là 0,0186–0,0711; khoảng của IoU Random Forest là 0,6931–0,8620.

Pixel có tương quan không gian. Các khoảng trên chỉ mô tả trường hợp này, chưa chứng minh khả năng tổng quát sang sự kiện khác. Không diễn giải đầu ra thành xác suất ngập đã hiệu chuẩn.

Mô hình: `data/products/ml/water_proxy_rf.joblib`. Cấu hình và kết quả: `data/products/ml/evaluation.json`.

<a id="optical-validation"></a>

## 5. Đối chiếu quang học

### 5.1. Quy trình

Đối chiếu toàn bộ 1.646 đa giác của bản Colab gốc theo quy tắc cố định:

1. Chỉ coi SCL lớp 4, 5 và 6 là có khả năng quan sát rõ; loại các lớp khác và thêm vùng đệm 60 m.
2. Nước mới quang học là chuyển từ lớp 4/5 sang lớp 6 trên phần rõ ở cả hai ngày; nước có sẵn là lớp 6 ở cả hai ngày.
3. Tính diện tích giao chính xác giữa đa giác và ô SCL trong EPSG:32648; giữ tỷ lệ diện tích rõ của từng vùng.
4. Ghi nhận giao nước mới nếu diện tích giao lớn hơn 1 m²; không xác nhận toàn bộ đa giác bị ngập.

Không điều chỉnh ngưỡng NISAR để tăng đồng thuận. SCL chủ yếu phục vụ xử lý khí quyển, chưa phải bản đồ ngập chuẩn. Các ô trộn tại bờ nước và chênh lệch thời điểm cần được diễn giải thận trọng.

### 5.2. Kết quả

| Trạng thái | Số vùng |
|---|---:|
| Có giao nước mới trên phần ảnh rõ | 9 |
| Chỉ giao nước đã có sẵn | 28 |
| Không có dấu nước mới trên phần ảnh rõ | 906 |
| Không có phần ảnh rõ ở cả hai ngày sau lọc chất lượng | 703 |
| **Tổng số vùng** | **1.646** |

Có 943 vùng quan sát được ít nhất một phần. Diện tích rõ giao vùng ứng viên là **3,8239 km²**, khoảng **41,1%** tổng diện tích. Diện tích giao nước mới quang học chỉ khoảng **0,0050 km²**, tức 5.000 m².

Chín mã vùng có giao nước mới là 125, 382, 401, 413, 418, 458, 921, 1119 và 1452; chưa phải chín vùng ngập xác nhận. Kết quả từng vùng: `data/products/validation/optical_crosscheck.csv` và `optical_crosscheck.json`.

### 5.3. Độ nhạy và kiểm tra trực quan

| Vùng đệm loại chất lượng | Tỷ lệ ô ứng viên có ảnh rõ | Số ô giao nước mới |
|---|---:|---:|
| 0 m | 70,81% | 28 |
| 60 m — cấu hình chính | 40,84% | 15 |
| 100 m | 27,02% | 9 |

Bảng tính trên lưới 20 m theo tâm ô, khác với diện tích giao véc-tơ chính xác ở trên. Không dùng số ô nhân diện tích ô để thay kết quả giao đa giác.

Đã xem ảnh trước/sau của 12 vùng: sáu vùng đứng đầu theo phơi nhiễm, ba vùng có giao quang học lớn và ba vùng bị che. Nhiều khu vực có dạng ruộng, thực vật, bề mặt trống hoặc rìa nước; chưa xác lập được phạm vi ngập mới rõ ràng. Tám điểm ngoài vùng ứng viên cũng được xem, gồm các ví dụ nước ổn định, đất ổn định, nước mới theo SCL và vùng bị che.

Đây là kiểm tra có chủ đích với hỗ trợ của ChatGPT/Codex, chưa phải mẫu đánh giá ngẫu nhiên, điều tra thực địa hay kết luận chuyên gia độc lập. Các điểm ngoài vùng ứng viên chưa được coi là mẫu âm đúng hoặc trường hợp bỏ sót. Ảnh và hồ sơ được giữ trong `data/products/validation/`.

### 5.4. Diễn giải

Phép đối chiếu **không đủ cơ sở coi toàn bộ 9,3045 km² là ngập thực tế**. Trên phần lớn diện tích rõ không có dấu nước mới tương ứng. Biến đổi đất, cây trồng hoặc khác biệt xử lý radar là các giả thuyết cần kiểm tra; ngập tạm thời giữa hai lần chụp cũng chưa thể loại trừ.

Bản tin và phản ánh địa phương chỉ cung cấp bối cảnh, không được chuyển thành nhãn ngập từng pixel. Tra cứu Sentinel-1 có quan sát lân cận ngày 25 và 28/10 nhưng nghiên cứu chưa tạo bản đồ ngập đối chứng từ các ảnh này.

<a id="exposure"></a>

## 6. Phơi nhiễm và thứ tự kiểm chứng

### 6.1. Dân số

WorldPop cung cấp số người ước tính trên ô gốc, không phải mật độ để phóng lên lưới radar 10 m. Đóng góp của một ô được tính bằng:

**Dân số ô × diện tích giao với đa giác / diện tích ô gốc.**

Giả định dân số phân bố đều trong ô. Loại dữ liệu thiếu, không hữu hạn hoặc âm; không coi thiếu dữ liệu là không có người. Giữ riêng tỷ lệ diện tích được dữ liệu hợp lệ bao phủ. Vùng hoàn toàn thiếu dữ liệu nhận giá trị chưa xác định; ô hợp lệ có dân số bằng 0 mới đóng góp 0.

Tổng từng phần khoảng **1.681 người ước tính**, trên **60,5%** diện tích ứng viên có dữ liệu hợp lệ. Có **488 vùng** không giao ô dân số hợp lệ. Đây chưa phải tổng dân số đầy đủ, số người hiện diện hoặc số người chịu thiệt hại.

### 6.2. Hạ tầng

Loại trùng OSM theo loại/mã đối tượng. Cắt tim đường theo đa giác trong EPSG:32648 và hợp nhất các đoạn trùng trước khi đo. Không tính cả con đường chỉ vì nó chạm vùng ứng viên. Loại lối đi bộ, bậc thang, đường xe đạp, đường dự kiến/đang xây và đa giác có nhãn đường.

Cơ sở thiết yếu gồm bệnh viện, phòng khám, trường học, trường mầm non, trạm cứu hỏa và công an. Kiểm tra giao hình học thật để tính cơ sở giao trực tiếp; cơ sở trong 500 m chỉ được ghi là lân cận. Hạn chế đếm trùng điểm nhãn và công trình tương ứng.

| Đại lượng | Kết quả |
|---|---:|
| Tổng tim đường giao vùng ứng viên | 18,689 km |
| Vùng có đường giao cắt | 300 |
| Cơ sở thiết yếu giao trực tiếp | 0 |
| Cơ sở thiết yếu lân cận trong 500 m | 19 |
| Vùng được truy vấn hạ tầng bao phủ đầy đủ theo dung sai hình học | 1.645/1.646 |

OSM được lấy sau thời điểm radar và có thể thiếu đối tượng/nhãn. Kết quả chưa xác định đường bị đóng, công trình hư hỏng hay cơ sở còn hoạt động. Vùng có độ phủ truy vấn một phần vẫn được đánh dấu.

### 6.3. Xếp thứ tự kiểm chứng

Sắp xếp lần lượt theo các tiêu chí; chỉ dùng tiêu chí sau khi tiêu chí trước bằng nhau:

1. Có cơ sở thiết yếu giao trực tiếp.
2. Dân số ước tính trên phần dữ liệu hợp lệ, giảm dần.
3. Chiều dài đường giao cắt, giảm dần.
4. Diện tích ứng viên, giảm dần; cuối cùng dùng mã vùng để giữ thứ tự ổn định.

Không sử dụng trọng số học được hoặc xác suất rủi ro đã hiệu chuẩn. Trong trường hợp này, không có cơ sở giao trực tiếp nên dân số chi phối đầu danh sách. Thiếu dữ liệu có thể làm thay đổi thứ tự.

Điểm đại diện trong đa giác chỉ dùng định vị kiểm chứng, chưa phải điểm tiếp cận an toàn hoặc hướng dẫn di chuyển. Kết quả: `data/products/impact/review_analysis.json`, `review_candidates.geojson` và `review_locations.csv`.

<a id="rainfall"></a>

## 7. Thông tin mưa bổ trợ

### 7.1. Nguồn và cách tính

Ứng dụng lấy lượng giáng thủy theo giờ từ Open-Meteo, chọn ECMWF IFS tại bốn điểm khảo sát quanh Huế. Phân biệt tọa độ yêu cầu và tọa độ ô mô hình; chưa coi đây là dự báo riêng từng phường.

Tổng 5/12 giờ được tính từ các khoảng giờ giao cửa sổ cần xem. Giá trị tại thời điểm `t` đại diện cho giờ trước `t`; các giờ biên được phân bổ theo thời lượng giao, giả định mưa đều trong giờ. Nếu thiếu bất kỳ phần cần thiết nào, tổng được ghi chưa xác định, không thay bằng 0.

Server Python thu thập mỗi 15 phút và lưu phản hồi vào `data/products/forecasts/` khi còn chạy và có mạng. Thời điểm tải không đồng nghĩa với thời điểm khởi tạo dự báo. Bản HTML/GitHub Pages có thể gọi nhà cung cấp trực tiếp khi có mạng, nhưng không chạy bộ lưu định kỳ Python.

SARWatch chưa huấn luyện mô hình dự báo mưa hay cảnh báo ngập. Ngưỡng mưa người dùng đặt chỉ phục vụ theo dõi, không phải mức báo động chính thức; chưa có chức năng gửi cảnh báo điện thoại.

### 7.2. Đánh giá khi có quan trắc

`pipeline/rainfall_evaluation.py` nhận CSV với các cột:

| Cột | Nội dung |
|---|---|
| `snapshot` | Tên JSON đã lưu trong `data/products/forecasts/` |
| `site` | `hue`, `northwest`, `coast` hoặc `south` |
| `hours` | Cửa sổ 5 hoặc 12 giờ |
| `observed_mm` | Tổng quan trắc độc lập, đúng vị trí và cửa sổ từ thời điểm tải đến sau 5/12 giờ |
| `observation_source` | Nguồn quan trắc có thể truy nguyên |

Ví dụ lệnh với ngưỡng thí nghiệm, không phải mức báo động chính thức:

```powershell
python -m pipeline.rainfall_evaluation observations.csv --threshold-5 10 --threshold-12 20
```

Báo cáo lưu ở `data/products/verification/rainfall_metrics.json`, gồm MAE, RMSE, độ lệch trung bình theo mm và các chỉ số vượt ngưỡng: POD = H/(H + M), FAR = F/(H + F), CSI = H/(H + F + M). H là số dự báo trúng, F là số báo khống, M là số bỏ sót; mẫu số 0 cho kết quả chưa xác định.

Hiện chưa có kết nối tự động nguồn quan trắc độc lập và chưa công bố kỹ năng dự báo mưa của trường hợp này. Không dùng dự báo của chính nhà cung cấp làm quan trắc. Nếu dùng ước tính vệ tinh/tái phân tích phải ghi rõ bản chất và sai số nguồn. Các cửa sổ chồng nhau không phải sự kiện độc lập; kết quả đánh giá mưa chưa chứng minh độ chính xác cảnh báo ngập.

## 8. Tái lập kết quả

### 8.1. Môi trường và lệnh chạy

Từ thư mục gốc, tạo môi trường Python 3.11, cài thư viện rồi chạy các lệnh:

```powershell
python -m venv dev/.venv
dev/.venv/Scripts/python -m pip install -r requirements.txt
dev/.venv/Scripts/python run.py check
dev/.venv/Scripts/python run.py reproduce
dev/.venv/Scripts/python run.py test
```

Trên macOS/Linux thay `dev/.venv/Scripts/python` bằng `dev/.venv/bin/python`. Lệnh `reproduce` chạy radar, sàng lọc, so sánh sản phẩm, chẩn đoán bức xạ, huấn luyện, phơi nhiễm, đối chiếu quang học và dựng dữ liệu giao diện. Trường hợp khác cần tải đầu vào mới và ghi đúng phiên bản/yêu cầu trích xuất; không chỉ thay ngày.

| Thao tác riêng | Lệnh sau khi kích hoạt môi trường |
|---|---|
| Xử lý radar và sàng lọc | `python run.py radar` |
| Huấn luyện phân loại nước | `python run.py train` |
| Tính phơi nhiễm | `python run.py impact` |
| Đối chiếu quang học và điểm ngoài vùng ứng viên | `python run.py reference` |
| Dựng lại bản HTML | `python run.py build` |

### 8.2. Kiểm tra và xem kết quả

Kiểm thử gồm xử lý dữ liệu thiếu, lọc radar, giao cắt dân số/đường, thứ tự ưu tiên, phân lớp tham chiếu, checksum và chức năng HTTP. Đây là kiểm tra hành vi phần mềm, không thay đánh giá bằng nhãn độc lập.

Kiểm tra giao diện bằng Node và cấu hình trong repo:

```powershell
npm --prefix dev ci
npm --prefix dev run test:ui
```

Trên Windows, `start.bat` mở `app/standalone/index.html`; `start.bat --server` hoặc `python run.py --open` chạy server. Bản tĩnh phục vụ trường hợp lịch sử; thu thập dự báo và API Python cần server. Ảnh nền trực tuyến và dự báo mới cần internet.

## 9. Giới hạn và hướng phát triển

| Giới hạn | Hệ quả | Công việc tiếp theo |
|---|---|---|
| Chưa có nhãn ngập độc lập khớp thời điểm | Chưa đo được độ chính xác phát hiện ngập | Thu thập nhãn sự kiện từ nguồn đủ tin cậy |
| NISAR khác mức xử lý; phần xuất chưa có đủ lớp chất lượng gốc | Biến đổi radar có thể chứa yếu tố ngoài ngập | Bổ sung mặt nạ hợp lệ và kiểm tra nhất quán bức xạ |
| Sentinel-2 lệch giờ, có mây và sai số SCL | Đối chiếu chỉ hỗ trợ một phần | Chọn quan sát sát sự kiện hơn, kết hợp nhiều nguồn |
| Mô hình chỉ được đánh giá trên một trường hợp | Chưa chứng minh khả năng dùng cho sự kiện mới | Đánh giá nhiều sự kiện, chia tập theo thời gian và khu vực |
| Dân số/OSM có độ phủ hạn chế và khác thời điểm | Phơi nhiễm, thứ tự kiểm chứng có thể thiên lệch | Phân tích độ nhạy với dữ liệu thiếu, tham vấn người làm thực tế |
| Thiếu mô hình thủy văn/thủy lực và quan trắc tương ứng | Chưa thể dự báo ngập từ mưa | Kết hợp mực nước, mưa trước sự kiện, vận hành hồ và thoát nước |

Kết quả phù hợp cho khảo sát và truy nguyên bằng chứng; chưa dùng làm căn cứ duy nhất cho quyết định ứng phó hoặc sơ tán.

<a id="sources"></a>

## 10. Nguồn và giấy phép

### 10.1. Dữ liệu và phần mềm

| Nguồn | Tài liệu hoặc định danh | Ghi nguồn và điều kiện |
|---|---|---|
| NASA–ISRO NISAR | [Tài liệu tại ASF](https://nisar-docs.asf.alaska.edu/); mã sản phẩm ở mục 2 | Ghi nguồn NISAR và giữ siêu dữ liệu phiên bản |
| Copernicus Sentinel-2 | [Earth Search](https://earth-search.aws.element84.com/v1), [SCL](https://sentiwiki.copernicus.eu/web/s2-processing), [giải thích dữ liệu](https://documentation.dataspace.copernicus.eu/FAQ.html) | Sử dụng dữ liệu Copernicus Sentinel (2026) đã xử lý; URL ảnh và tra cứu lưu trong `data/inputs/reference/` |
| JRC Global Surface Water | [Trang tải](https://global-surface-water.appspot.com/download) | Ghi nguồn EC JRC/Google; trích dẫn Pekel và cộng sự (2016) |
| Copernicus DEM GLO-30 | [Danh mục](https://registry.opendata.aws/copernicus-dem/), [giấy phép](https://copernicus-dem-30m.s3.amazonaws.com/readme.html) | Giữ dòng ghi công bắt buộc bên dưới |
| WorldPop | [DOI: 10.5258/SOTON/WP00839](https://doi.org/10.5258/SOTON/WP00839), [API](https://api.worldpop.org/v3/raster) | CC BY 4.0; tác giả/trích dẫn đầy đủ ở `worldpop_metadata.json`, yêu cầu tải ở `worldpop_provenance.json` trong `data/inputs/auxiliary/` |
| OpenStreetMap | [Bản quyền](https://www.openstreetmap.org/copyright), [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) | © OpenStreetMap contributors; dữ liệu suy dẫn giữ ghi nguồn và nghĩa vụ chia sẻ tương ứng |
| Open-Meteo / ECMWF | [API](https://open-meteo.com/en/docs/ecmwf-api) | Ghi nguồn Open-Meteo / ECMWF; CC BY 4.0 |
| Esri World Imagery, tùy chọn | [Dịch vụ ảnh nền](https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer) | Giữ ghi nguồn và tuân thủ điều khoản; không dùng ảnh nền khác ngày làm nhãn ngập |
| Be Vietnam Pro | `app/web/fonts/OFL.txt` | SIL Open Font License; font lưu kèm và nhúng trong bản HTML |
| Mã nguồn SARWatch | [LICENSE](../LICENSE), [NOTICE](../NOTICE) | Apache 2.0 cho mã nguồn gốc; dữ liệu/font giữ giấy phép riêng |

Dòng ghi công DEM được giữ nguyên ngôn ngữ gốc:

> Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.

### 10.2. Tài liệu phương pháp

- Otsu (1979), chọn ngưỡng: [DOI: 10.1109/TSMC.1979.4310076](https://doi.org/10.1109/TSMC.1979.4310076).
- Breiman (2001), Random Forests: [bài báo](https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf).
- Pekel và cộng sự (2016), bản đồ nước mặt dài hạn: [DOI: 10.1038/nature20584](https://doi.org/10.1038/nature20584).
- Ayzel và cộng sự (2019), tham khảo đánh giá dự báo mưa: [DOI: 10.5194/gmd-12-1387-2019](https://doi.org/10.5194/gmd-12-1387-2019).
- Pulkkinen và cộng sự (2019), Pysteps: [DOI: 10.5194/gmd-12-4185-2019](https://doi.org/10.5194/gmd-12-4185-2019).

Các công trình là cơ sở phương pháp, không cung cấp chỉ số thay cho SARWatch. Nghiên cứu chưa triển khai FSS/Brier và không suy ra kỹ năng dự báo 5/12 giờ từ các bài báo dự báo ngắn hạn.

### 10.3. Bối cảnh sự kiện và bài thi

- [Bản tin cảnh báo lũ tại Huế ngày 28/10](https://kttv.gov.vn/kttv/vi-VN/1/tin-canh-bao-lu-tren-cac-song-o-thanh-pho-hue-post55756.html): bối cảnh, không chứng minh trạng thái từng vùng lúc NISAR chụp ngày 27/10.
- [Phản ánh tại cầu Duy Tân](https://tuongtac.hue.gov.vn/phan-anh/kien-nghi-co-phuong-an-de-dong-chay-duoc-luu-thong-tai-cau-duy-tan-lan-2-a243838.html): không chuyển thành nhãn ngập theo thời điểm radar.
- [Dancing with the SARs — NASA Space Apps 2026](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/): bài thi dự án hướng tới. Trong lần rà soát trước, trang chính không truy cập được; nội dung được đối chiếu qua [bản đăng lại](https://hackathlone.com/challenges/dancing-with-the-sars). Tác giả cần kiểm tra biểu mẫu/quy định hiện hành; tài liệu này chưa xác nhận toàn bộ điều kiện nộp bài.

<a id="ai-disclosure"></a>

## 11. Khai báo công cụ hỗ trợ

OpenAI ChatGPT/Codex hỗ trợ lập kế hoạch, triển khai phần mềm, biên tập giao diện/tài liệu, kiểm tra phương pháp, gỡ lỗi và soạn nội dung nộp bài. Tác giả chịu trách nhiệm rà soát, diễn giải và quyết định nộp bài.

Ảnh radar, quang học và sản phẩm không gian được xử lý từ dữ liệu dẫn nguồn; không sử dụng ảnh tạo sinh làm bằng chứng vệ tinh. Số liệu được tính từ file thực, không phải dữ liệu mẫu tạo để trình bày. ChatGPT không cung cấp nhãn ngập thực địa.

Random Forest được huấn luyện từ đặc trưng NISAR và nhãn SCL; dự báo mưa do ECMWF IFS cung cấp qua Open-Meteo. Phạm vi hỗ trợ cần được khai báo theo biểu mẫu nộp bài.

<a id="submission"></a>

## Phụ lục. Giới thiệu và trình bày dự án

### A. Tên và mô tả ngắn

**SARWatch — Ưu tiên kiểm chứng dấu hiệu ngập tại Huế bằng NISAR.**

SARWatch kết hợp radar NISAR nhiều thời điểm, tham chiếu Sentinel-2 và dân số–hạ tầng để giúp xác định nơi cần kiểm chứng. Mỗi vùng có thể truy nguyên ảnh, điều kiện xử lý, mức đối chiếu và giới hạn dữ liệu. Chưa có cơ sở khẳng định đã được đơn vị ứng phó áp dụng thực tế.

### B. Trình tự minh họa

1. Mở bản đồ, chỉ ngày chụp và phạm vi phân tích.
2. Chọn vị trí trong danh sách ưu tiên.
3. So sánh radar trước/sau và ảnh Sentinel-2 tương ứng.
4. Giải thích trạng thái đối chiếu, độ phủ dân số và lý do xếp thứ tự.
5. Xuất danh sách kiểm chứng; kết thúc bằng giới hạn khoa học chính.

Quay thao tác thật, không thêm cảnh ngập tạo sinh hoặc dùng ảnh nền như ảnh đúng ngày sự kiện. Khi nêu kết quả, phân biệt diện tích ứng viên, mức khớp nhãn nước và phơi nhiễm từng phần với ngập/thiệt hại xác nhận. Thời lượng và định dạng theo biểu mẫu nộp bài.

### C. Gợi ý bảy trang trình chiếu

| Trang | Nội dung |
|---|---|
| 1 | Vấn đề tại Huế và người dùng dự kiến |
| 2 | Nguồn NISAR, thời điểm và phạm vi dữ liệu |
| 3 | Quy trình radar và độ nhạy tham số |
| 4 | Đối chiếu quang học, kể cả phần thiếu bằng chứng |
| 5 | Random Forest, cách chia tập và so sánh Otsu |
| 6 | Phơi nhiễm, thứ tự kiểm chứng và giao diện |
| 7 | Giới hạn, hướng phát triển, nguồn và khai báo công cụ |

Trước khi nộp, kiểm tra đăng ký đội/sự kiện, trường bắt buộc, link repo/demo ở chế độ không đăng nhập, nguồn, khai báo công cụ, thời hạn và trạng thái nộp cuối cùng. Việc chuẩn bị tài liệu không đồng nghĩa đã nộp bài hoặc bảo đảm kết quả chấm giải.
