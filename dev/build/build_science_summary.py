"""Render model evaluation summaries in the methodology view."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def build():
    ml=json.loads((ROOT/'data/products/ml/evaluation.json').read_text())
    radar=json.loads((ROOT/'data/products/radar_rerun/report.json').read_text())
    radiometry=json.loads((ROOT/'data/products/radar_rerun/radiometry.json').read_text())
    screening=json.loads((ROOT/'data/products/radar_rerun/screening.json').read_text())
    comparison=json.loads((ROOT/'data/products/radar_rerun/product_comparison.json').read_text())
    rf,base=ml['test_random_forest'],ml['test_otsu']
    fmt=lambda v:f'{v:.3f}'.replace('.',',')
    rows=''.join(f'<tr><th scope="row">{label}</th><td>{fmt(base[key])}</td><td>{fmt(rf[key])}</td></tr>'
                 for key,label in [('precision','Precision'),('recall','Recall'),('f1','F1'),('iou','IoU')])
    fragment=f'''<!--SCIENCE START-->
    <section id="science-results" class="science-results" aria-labelledby="science-heading">
     <details class="science-disclosure"><summary><span>Đánh giá bộ phân loại nước</span><small>Random Forest và Otsu</small></summary><div class="science-heading"><div><p class="eyebrow">THỰC NGHIỆM CÓ THỂ TÁI CHẠY</p><h3 id="science-heading">So sánh với nhãn nước Sentinel-2</h3></div><span class="science-case">Cặp ảnh 15–27/10/2026</span></div>
     <p>Các chỉ số đo <strong>mức khớp với nhãn nước Sentinel-2</strong>; chưa đo độ chính xác phát hiện lũ.</p>
     <div class="science-cards"><article><span>F1 · baseline Otsu</span><strong>{fmt(base['f1'])}</strong><progress value="{base['f1']}" max="1" aria-label="F1 baseline Otsu"></progress></article><article><span>F1 · Random Forest</span><strong>{fmt(rf['f1'])}</strong><progress value="{rf['f1']}" max="1" aria-label="F1 Random Forest"></progress></article><article><span>Tập kiểm tra giữ riêng</span><strong>68 <small>khối</small></strong><p>100.000 pixel · khối 2 × 2 km</p></article></div>
     <details><summary>Thiết lập và giới hạn đánh giá</summary><div class="science-details"><div><table><caption>Mức khớp với nhãn quang học trên cùng tập kiểm tra</caption><thead><tr><th>Chỉ số</th><th>Otsu</th><th>Random Forest</th></tr></thead><tbody>{rows}</tbody></table><p>Train / validation / test: 175 / 53 / 68 khối, dùng cùng phân chia ở cả hai ngày. Bỏ biên khối 100 m và biên mây 60 m; chọn ngưỡng bằng validation. Số pixel không phải số mẫu độc lập.</p><p>IoU tăng {(rf['iou']-base['iou'])*100:.2f} điểm phần trăm. Khoảng bootstrap theo khối 95% cho mức tăng: {ml['bootstrap_95']['iou_difference'][0]*100:.2f}–{ml['bootstrap_95']['iou_difference'][1]*100:.2f} điểm; chỉ mô tả case này.</p></div><div><h4>Khác biệt giữa hai thời điểm</h4><p>F1 riêng ảnh trước / sau: {fmt(ml['per_date_test']['before']['f1'])} / {fmt(ml['per_date_test']['after']['f1'])}. Nhãn gồm cả nước ven biển; chưa chứng minh khả năng nhận diện ngập mới hoặc khái quát sang đợt lũ khác.</p><p>Ngay ở lớp thực vật giữ nguyên nhãn quang học, HH vẫn giảm trung vị khoảng 0,72 dB. Độ ẩm, mùa vụ và khác phiên bản xử lý còn lẫn nhau; chưa áp dụng hiệu chỉnh độ lệch.</p><p>Tái chạy với quy tắc lọc được công bố cho {radar['settings'][1]['area_km2']:.4f} km² ứng viên <strong>trước</strong> sàng lọc. Sau sàng lọc bằng JRC/DEM mới tải còn {screening['sensitivity'][1]['area_km2']:.4f} km². Bản đồ Colab gốc 9,3045 km² vẫn được lưu riêng; Jaccard giữa hai sản phẩm là {fmt(comparison['jaccard'])}, không phải điểm chính xác ngập.</p><p>Mô hình này chưa thay thế các vùng ứng viên hoặc trở thành cảnh báo hiện tại.</p></div></div></details>
    </details></section><!--SCIENCE END-->'''
    path=ROOT/'app/web/index.html';html=path.read_text(encoding='utf-8')
    if '<!--SCIENCE START-->' in html:
        html=re.sub(r'<!--SCIENCE START-->.*?<!--SCIENCE END-->',lambda _:fragment,html,flags=re.S)
    else:html=html.replace('  <div class="method-grid">',fragment+'\n  <div class="method-grid">',1)
    path.write_text(html,encoding='utf-8')
    print('Published measured science summary.')


if __name__=='__main__':build()
