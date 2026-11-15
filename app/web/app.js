/* SARWatch: NISAR change workspace with automatically published real analysis. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const ns = 'http://www.w3.org/2000/svg';
  const WORLD = 256 * 2 ** 13;
  const state = { analysis: null, date: 'after', page: 'ban-do', regions: [], selected: null,
    box: null, fit: null, split: 50, limit: 30, dragging: null, modified: false,
    importing: false, tileWarning: false, toastTimer: null };
  const number = (value, digits = 2) => Number.isFinite(value) ? new Intl.NumberFormat('vi-VN', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value) : '—';
  const compact = value => new Intl.NumberFormat('vi-VN').format(value);
  const formatDate = value => {
    if (!value) return '—';
    const [year, month, day] = value.split('-');
    return `${day}.${month}.${year}`;
  };
  const areaLabel = area => area < 1_000_000 ? `${number(area / 10_000)} ha` : `${number(area / 1_000_000, 3)} km²`;
  function svgElement(tag, attributes = {}) {
    const element = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
    return element;
  }
  function textElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  }
  function toast(message) {
    clearTimeout(state.toastTimer);
    $('toast').textContent = message;
    $('toast').hidden = false;
    state.toastTimer = setTimeout(() => { $('toast').hidden = true; }, 6000);
  }
  function project([lon, lat]) {
    const latitude = Math.max(-85.05112878, Math.min(85.05112878, lat)) * Math.PI / 180;
    return [(lon + 180) / 360 * WORLD, (1 - Math.log(Math.tan(Math.PI / 4 + latitude / 2)) / Math.PI) / 2 * WORLD];
  }
  function unproject(x, y) {
    return [x / WORLD * 360 - 180, Math.atan(Math.sinh(Math.PI * (1 - 2 * y / WORLD))) * 180 / Math.PI];
  }
  function worldBounds(bounds) {
    const [south, west] = bounds[0], [north, east] = bounds[1];
    const [left, top] = project([west, north]), [right, bottom] = project([east, south]);
    return { x: left, y: top, width: right - left, height: bottom - top };
  }
  function geometryRings(geometry) {
    if (geometry.type === 'Polygon') return geometry.coordinates;
    if (geometry.type === 'MultiPolygon') return geometry.coordinates.flat();
    return [];
  }
  function geometryPath(geometry) {
    return geometryRings(geometry).map(ring => ring.map((coordinate, index) => {
      const [x, y] = project(coordinate);
      return `${index ? 'L' : 'M'}${x.toFixed(3)},${y.toFixed(3)}`;
    }).join(' ') + 'Z').join(' ');
  }
  function geometryBounds(geometry) {
    const points = geometryRings(geometry).flat();
    let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity;
    for (const [lon, lat] of points) {
      west = Math.min(west, lon); east = Math.max(east, lon);
      south = Math.min(south, lat); north = Math.max(north, lat);
    }
    return [[south, west], [north, east]];
  }
  function fitBox(raw, padding = 1.07) {
    const viewport = $('map-viewport');
    const ratio = Math.max(viewport.clientWidth, 1) / Math.max(viewport.clientHeight, 1);
    let width = Math.max(raw.width * padding, 1), height = Math.max(raw.height * padding, 1);
    if (width / height < ratio) width = height * ratio;
    else height = width / ratio;
    return { x: raw.x + raw.width / 2 - width / 2, y: raw.y + raw.height / 2 - height / 2, width, height };
  }
  function updateBox() {
    if (!state.box) return;
    const b = state.box;
    $('map-svg').setAttribute('viewBox', `${b.x} ${b.y} ${b.width} ${b.height}`);
    const ratio = state.fit.width / b.width;
    $('zoom-in').disabled = ratio >= 63.9;
    $('zoom-out').disabled = ratio <= 0.251;
    updateSplit(); updateScale(); updateTiles();
  }
  function zoom(factor, fx = 0.5, fy = 0.5) {
    if (!state.box) return;
    const b = state.box;
    const targetWidth = Math.max(state.fit.width / 64, Math.min(state.fit.width * 4, b.width / factor));
    const actual = b.width / targetWidth;
    const targetHeight = b.height / actual;
    state.box = { x: b.x + (b.width - targetWidth) * fx, y: b.y + (b.height - targetHeight) * fy, width: targetWidth, height: targetHeight };
    state.modified = true;
    updateBox();
  }
  function resetMap() {
    if (!state.analysis) return;
    state.fit = fitBox(worldBounds(state.analysis.manifest.previews.after.bounds));
    state.box = { ...state.fit };
    state.modified = false;
    updateBox();
  }
  function updateScale() {
    const b = state.box;
    if (!b) return;
    const [, latitude] = unproject(b.x + b.width / 2, b.y + b.height / 2);
    const metresPerScreenPixel = 40075016.686 / WORLD * Math.cos(latitude * Math.PI / 180) * b.width / Math.max($('map-viewport').clientWidth, 1);
    const maxDistance = metresPerScreenPixel * 100;
    const power = 10 ** Math.floor(Math.log10(maxDistance));
    const distance = [1, 2, 5, 10].map(n => n * power).filter(n => n <= maxDistance).pop() || power;
    $('map-scale').firstElementChild.style.width = `${distance / metresPerScreenPixel}px`;
    $('map-scale').lastElementChild.textContent = distance >= 1000 ? `${number(distance / 1000, distance % 1000 ? 1 : 0)} km` : `${Math.round(distance)} m`;
  }
  function updateSplit() {
    if (!state.box) return;
    const b = state.box;
    const cutoff = b.x + b.width * state.split / 100;
    const rect = $('before-clip-rect');
    for (const [key, value] of Object.entries({ x: b.x, y: b.y, width: b.width * state.split / 100, height: b.height })) rect.setAttribute(key, value);
    let line = $('compare-divider');
    if (!line) {
      line = svgElement('line', { id: 'compare-divider', class: 'compare-divider' });
      $('map-svg').append(line);
    }
    line.setAttribute('x1', cutoff); line.setAttribute('x2', cutoff);
    line.setAttribute('y1', b.y); line.setAttribute('y2', b.y + b.height);
    line.style.display = state.date === 'compare' && $('show-radar').checked ? '' : 'none';
  }
  function updateTiles() {
    const group = $('tile-layer');
    const enabled = $('show-basemap').checked && state.analysis && state.box;
    $('basemap-attribution').hidden = !enabled;
    if (!enabled) { group.replaceChildren(); return; }
    const b = state.box;
    const z = Math.max(2, Math.min(18, 13 + Math.round(Math.log2($('map-viewport').clientWidth / b.width))));
    const count = 2 ** z, unit = WORLD / count;
    const minX = Math.max(0, Math.floor(b.x / unit)), maxX = Math.min(count - 1, Math.floor((b.x + b.width) / unit));
    const minY = Math.max(0, Math.floor(b.y / unit)), maxY = Math.min(count - 1, Math.floor((b.y + b.height) / unit));
    const existing = new Map([...group.children].map(node => [node.dataset.key, node]));
    const needed = new Set();
    for (let y = minY; y <= maxY; y++) for (let x = minX; x <= maxX; x++) {
      if (needed.size >= 100) continue;
      const key = `${z}/${y}/${x}`; needed.add(key);
      if (existing.has(key)) continue;
      const image = svgElement('image', { x: x * unit, y: y * unit, width: unit + 0.02, height: unit + 0.02, preserveAspectRatio: 'none', href: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${key}` });
      image.dataset.key = key;
      image.addEventListener('error', () => {
        if (!state.tileWarning) { toast('Ảnh nền chưa tải được. Bạn vẫn có thể xem lớp radar NISAR.'); state.tileWarning = true; }
      });
      group.append(image);
    }
    for (const [key, node] of existing) if (!needed.has(key)) node.remove();
  }
  function updateLayers() {
    const before = $('radar-before'), after = $('radar-after');
    $('radar-layer').style.display = $('show-radar').checked ? '' : 'none';
    $('radar-layer').style.opacity = Number($('radar-opacity').value) / 100;
    $('opacity-value').textContent = `${$('radar-opacity').value}%`;
    $('polygon-layer').style.display = $('show-candidates').checked ? '' : 'none';
    before.style.display = state.date === 'after' ? 'none' : '';
    after.style.display = state.date === 'before' ? 'none' : '';
    if (state.date === 'compare') before.setAttribute('clip-path', 'url(#before-clip)');
    else before.removeAttribute('clip-path');
    $('comparison-control').hidden = !state.analysis || state.date !== 'compare';
    $('map-legend').hidden = !state.analysis || !$('show-candidates').checked;
    document.querySelectorAll('[data-date]').forEach(button => {
      const selected = button.dataset.date === state.date;
      button.classList.toggle('selected', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
    updateSplit(); updateTiles();
    if (state.analysis) {
      const label = state.date === 'compare' ? 'Đối chiếu hai quan sát HH' : `HH ngày ${formatDate(state.analysis.manifest.dates[state.date])}`;
      $('map-caption').textContent = `${label} · Ảnh xem trước, thang hiển thị −30 đến 0 dB.`;
    }
  }
  function updateRoute() {
    const requested = location.hash.replace('#', '') || 'ban-do';
    const page = ['ban-do', 'phuong-phap', 'du-bao'].includes(requested) ? requested : 'ban-do';
    state.page = page;
    document.querySelectorAll('[data-nav]').forEach(link => {
      const active = link.dataset.nav === page;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
    $('map-page').hidden = page !== 'ban-do';
    $('analysis-page').hidden = page !== 'ban-do';
    if (requested === 'phan-tich') $('analysis-page').open = true;
    $('method-page').hidden = page !== 'phuong-phap';
    if ($('weather-page')) $('weather-page').hidden = page !== 'du-bao';
    if ($('evidence-page')) $('evidence-page').hidden = page !== 'ban-do';
    if ($('review-workspace')) $('review-workspace').hidden = page !== 'ban-do' || $('review-workspace').dataset.stale === 'true';
    if ($('reference-summary-page')) $('reference-summary-page').hidden = page !== 'ban-do' || $('reference-summary-page').dataset.stale === 'true';
    document.body.classList.remove('comparison-mode');
    const copy = {
      'du-bao': ['BỐI CẢNH THỜI TIẾT · HUẾ', 'Mưa dự báo tại Huế', 'Tổng mưa 5 và 12 giờ từ ECMWF IFS.'],
      'ban-do': ['NISAR · DÂN CƯ · HẠ TẦNG', 'Kiểm tra dấu hiệu ngập tại Huế', 'So sánh radar với ảnh vệ tinh và dữ liệu dân cư.'],
      'so-sanh': ['HAI THỜI ĐIỂM · MỘT KHU VỰC', 'Ảnh radar trước và sau', 'Kéo thanh chia để đối chiếu ảnh radar trước và sau trên cùng vị trí.'],
      'phan-tich': ['PHÂN TÍCH · CÓ THỂ TRUY NGUYÊN', 'Thống kê xử lý', 'Thống kê xuất trực tiếp từ pipeline, kèm lựa chọn tham số và giới hạn.'],
      'phuong-phap': ['PHƯƠNG PHÁP · NGUỒN DỮ LIỆU', 'Dữ liệu và phương pháp', 'Nguồn ảnh, cách xử lý và kết quả đối chiếu.'],
    }[page];
    [$('page-eyebrow'), $('page-title'), $('page-description')].forEach((element, index) => { element.textContent = copy[index]; });
    // Old shared links resolve to tools inside the map, not additional tabs.
    if (requested === 'so-sanh') state.date = 'compare';
    if (state.analysis) requestAnimationFrame(() => { resetMap(); updateLayers(); });
  }
  function renderRegions() {
    let query = $('region-search').value.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().replace(/^vung\s*/, '').trim();
    const regions = state.regions.filter(region => !query || region.id.toLowerCase().includes(query) || region.id.padStart(3, '0').includes(query) || (region.feature.properties.road_names || []).some(name => name.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().includes(query)));
    regions.sort((a, b) => $('region-sort').value === 'priority' ? (a.feature.properties.review_rank ?? Infinity) - (b.feature.properties.review_rank ?? Infinity) || b.area-a.area : $('region-sort').value === 'small' ? a.area - b.area : b.area - a.area);
    const visible = regions.slice(0, state.limit);
    const fragment = document.createDocumentFragment();
    for (const region of visible) {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'region-row'; button.dataset.index = region.index;
      button.classList.toggle('selected', state.selected === region.index);
      button.setAttribute('aria-pressed', String(state.selected === region.index));
      const badge = $('region-sort').value === 'priority' && region.feature.properties.review_rank ? String(region.feature.properties.review_rank).padStart(2,'0') : region.id.padStart(3,'0');
      button.append(textElement('span', 'region-number', badge));
      const label = textElement('span', 'region-row-text', '');
      const basis = {essential_facility:'Giao cơ sở thiết yếu',population:'Có dân số mô hình',road:'Có đường giao cắt',radar_only:'Cần thêm bằng chứng'}[region.feature.properties.review_basis] || 'Cần kiểm chứng';
      label.append(textElement('strong', '', `Vùng ${region.id.padStart(3, '0')}`), textElement('small', '', basis));
      button.append(label, textElement('span', '', areaLabel(region.area)));
      fragment.append(button);
    }
    if (!regions.length) fragment.append(textElement('p', 'list-empty', state.analysis ? 'Không có vùng phù hợp.' : 'Nhập gói kết quả để xem các vùng ứng viên.'));
    $('region-list').replaceChildren(fragment);
    $('list-count').textContent = state.analysis ? `${compact(regions.length)} vùng` : 'Chưa có dữ liệu';
    $('more-regions').hidden = visible.length >= regions.length;
    $('more-regions').textContent = `Xem thêm (${compact(visible.length)} / ${compact(regions.length)})`;
  }
  function selectRegion(index, move = true) {
    const region = state.regions[index];
    if (!region) return;
    state.selected = index;
    document.querySelectorAll('#polygon-layer path').forEach(path => path.classList.toggle('selected', Number(path.dataset.index) === index));
    $('detail-title').textContent = `Vùng ${region.id.padStart(3, '0')}`;
    $('detail-area').textContent = `${areaLabel(region.area)} · ${compact(Math.round(region.area))} m²`;
    const [[south, west], [north, east]] = region.bounds;
    $('detail-coordinates').textContent = `${number((south + north) / 2, 5)}° N, ${number((west + east) / 2, 5)}° E`;
    $('detail-date').textContent = formatDate(state.analysis.manifest.dates.after);
    $('region-detail').hidden = false;
    window.dispatchEvent(new CustomEvent('sarwatch:region-selected', {detail:region.feature}));
    if (move) {
      const box = worldBounds(region.bounds);
      const minimum = state.fit.width / 25;
      const raw = { x: box.x + box.width / 2 - Math.max(box.width, minimum) / 2, y: box.y + box.height / 2 - Math.max(box.height, minimum) / 2, width: Math.max(box.width, minimum), height: Math.max(box.height, minimum) };
      state.box = fitBox(raw, 1.8); state.modified = true; updateBox();
    }
    renderRegions();
  }
  function closeRegion() {
    state.selected = null; $('region-detail').hidden = true;
    document.querySelectorAll('#polygon-layer path.selected').forEach(path => path.classList.remove('selected'));
    renderRegions();
  }
  function makeTable(target, rows, columns, chosen) {
    if (!rows || !rows.length) { $(target).replaceChildren(textElement('p', 'small-note', 'Gói dữ liệu chưa có bảng này.')); return; }
    const table = document.createElement('table');
    const header = document.createElement('thead'), headRow = document.createElement('tr');
    for (const column of columns) { const cell = textElement('th', '', column.label); cell.scope = 'col'; headRow.append(cell); }
    header.append(headRow); table.append(header);
    const body = document.createElement('tbody');
    for (const row of rows) {
      const tr = document.createElement('tr');
      if (chosen && chosen(row)) tr.className = 'chosen';
      for (const column of columns) {
        const value = row[column.key];
        tr.append(textElement('td', '', value == null ? '—' : column.format ? column.format(value) : String(value)));
      }
      body.append(tr);
    }
    table.append(body); $(target).replaceChildren(table);
  }
  function renderAnalysis() {
    const tables = state.analysis.tables;
    const screening = tables['candidate_screening_summary.csv'] || [];
    const maximum = Math.max(...screening.map(row => Number(row.area_km2) || 0), 1e-9);
    const fragment = document.createDocumentFragment();
    for (const row of screening) {
      const item = textElement('div', 'screening-row', '');
      const label = textElement('div', 'screening-row-label', '');
      label.append(textElement('span', '', row.group || 'Nhóm'), textElement('strong', '', `${number(Number(row.area_km2), 4)} km²`));
      const track = textElement('div', 'bar-track', '');
      const fill = textElement('div', 'bar-fill', '');
      fill.style.width = `${Math.max(0, Math.min(100, Number(row.area_km2) / maximum * 100))}%`;
      track.append(fill); item.append(label, track); fragment.append(item);
    }
    if (!screening.length) fragment.append(textElement('p', 'small-note', 'Gói dữ liệu chưa có bảng sàng lọc.'));
    $('screening-bars').replaceChildren(fragment);
    makeTable('slope-table', tables['terrain_threshold_sensitivity.csv'], [
      { key: 'slope_limit_deg', label: 'Ngưỡng dốc', format: value => `${value}°` },
      { key: 'water_occurrence_limit_%', label: 'Ngưỡng nước', format: value => `${value}%` },
      { key: 'remaining_candidate_area_km2', label: 'Còn lại (km²)', format: value => number(Number(value), 4) },
    ], row => Number(row.slope_limit_deg) === 5);
    makeTable('threshold-table', tables['candidate_threshold_sensitivity.csv'], [
      { key: 'setting', label: 'Phương án', format: value => ({ loose: 'Rộng', middle: 'Trung bình', strict: 'Chặt' }[value] || value) },
      { key: 'HH_change_limit_dB', label: 'ΔHH (dB)', format: value => number(Number(value), 2) },
      { key: 'HV_change_limit_dB', label: 'ΔHV (dB)', format: value => number(Number(value), 2) },
      { key: 'candidate_pixels', label: 'Pixel', format: value => compact(Number(value)) },
      { key: 'candidate_area_km2', label: 'Trước sàng lọc (km²)', format: value => number(Number(value), 4) },
    ], row => row.setting === 'middle');
    $('analysis-empty').hidden = true; $('analysis-content').hidden = false;
  }
  function applyAnalysis(data, imageSources) {
      const impact = globalThis.SARWatchImpact;
      if (impact && impact.analysis_version === data.version) {
        const properties = new Map(impact.geojson.features.map(f => [String(f.properties.id), f.properties]));
        data.geojson.features.forEach(f => { f.properties = {...f.properties,...properties.get(String(f.properties.id))}; });
      }
      state.analysis = data; state.selected = null; state.limit = 30;
      state.regions = data.geojson.features.map((feature, index) => ({ index, id: String(feature.properties.id ?? index + 1), area: Number(feature.properties.area_m2), feature, bounds: geometryBounds(feature.geometry) }));
      const fragment = document.createDocumentFragment();
      for (const region of state.regions) fragment.append(svgElement('path', { d: geometryPath(region.feature.geometry), 'data-index': region.index, 'fill-rule': 'evenodd' }));
      $('polygon-layer').replaceChildren(fragment);
      for (const date of ['before', 'after']) {
        const image = $(`radar-${date}`), box = worldBounds(data.manifest.previews[date].bounds);
        for (const [key, value] of Object.entries({ x: box.x, y: box.y, width: box.width, height: box.height, preserveAspectRatio: 'none', href: imageSources[date] })) image.setAttribute(key, value);
        image.onerror = () => toast('Ảnh radar chưa tải được. Kiểm tra gói dữ liệu và kết nối tới máy chủ trên máy.');
      }
      $('screened-area').textContent = number(data.manifest.screened_area_km2, 4);
      $('initial-area').textContent = `${number(data.manifest.initial_area_km2, 4)} km²`;
      $('region-count').textContent = compact(data.geojson.features.length);
      if ($('overview-area')) {
        $('overview-area').textContent = number(data.manifest.screened_area_km2, 2);
        $('overview-regions').textContent = compact(data.geojson.features.length);
        if ($('overview-removed')) $('overview-removed').textContent = number(Math.max(0, data.manifest.initial_area_km2 - data.manifest.screened_area_km2), 2);
        $('story-before').src = imageSources.before;
        $('story-after').src = imageSources.after;
        const largest = [...state.regions].sort((a, b) => (a.feature.properties.review_rank ?? Infinity)-(b.feature.properties.review_rank ?? Infinity) || b.area-a.area).slice(0, 3);
        const fragment = document.createDocumentFragment();
        largest.forEach((region, rank) => {
          const button = textElement('button', 'focus-row', '');
          button.type = 'button';
          button.setAttribute('aria-label', `Xem vùng ${region.id}, diện tích ${areaLabel(region.area)}`);
          const bar = textElement('span', 'focus-bar', '');
          const fill = textElement('span', '', '');
          fill.style.width = `${Math.min(100, largest[0].area ? region.area / largest[0].area * 100 : 0)}%`;
          bar.append(fill);
          button.append(textElement('span', 'focus-rank', String(rank + 1).padStart(2, '0')), textElement('strong', '', `Vùng ${region.id.padStart(3, '0')}`), bar, textElement('span', 'focus-area', areaLabel(region.area)), textElement('span', '', '↗'));
          button.addEventListener('click', () => { selectRegion(region.index); $('map-page').scrollIntoView?.({ behavior: 'smooth', block: 'start' }); });
          fragment.append(button);
        });
        $('focus-list').replaceChildren(fragment);
      }
      for (const date of ['before', 'after']) document.querySelectorAll(`.date-${date}`).forEach(element => { element.textContent = formatDate(data.manifest.dates[date]); });
      $('observation-period').textContent = `${formatDate(data.manifest.dates.before)} — ${formatDate(data.manifest.dates.after)}`;
      $('map-empty').hidden = true; $('map-viewport').classList.add('has-data');
      $('north-indicator').hidden = false; $('map-scale').hidden = false;
      $('region-detail').hidden = true;
      document.querySelectorAll('[data-date], .download-trigger, #region-search, #region-sort, #fit-map').forEach(element => { element.disabled = false; });
      renderRegions(); renderAnalysis();
      if (['ban-do', 'so-sanh'].includes(state.page)) resetMap();
      updateLayers();
      window.dispatchEvent(new CustomEvent('sarwatch:analysis', {detail:data}));
  }
  async function loadAnalysis(silent = false) {
    const embedded = globalThis.SARWatchDataset;
    if (embedded) applyAnalysis(embedded, embedded.imageSources);
    if (location.protocol === 'file:') return !!embedded;
    try {
      const response = await fetch('/api/analysis', { cache: 'no-store' });
      const data = await response.json();
      if (!response.ok) {
        if (embedded) return true;
        if (!(silent && response.status === 404)) toast(data.error || 'Chưa đọc được dữ liệu.');
        return false;
      }
      applyAnalysis(data, Object.fromEntries(['before', 'after'].map(date => [date, `/api/preview/${date}.png?v=${data.version}`])));
      return true;
    } catch (error) {
      if (embedded) return true;
      toast('Chưa kết nối được dữ liệu. Hãy mở website bằng start.bat.');
      return false;
    }
  }
  function downloadJSON(content, filename) {
    const blob = new Blob([JSON.stringify(content, null, 2)], { type: filename.endsWith('.geojson') ? 'application/geo+json' : 'application/json' });
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = filename; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  $('layers-toggle').addEventListener('click', () => { const open = $('layers-panel').hidden; $('layers-panel').hidden = !open; $('layers-toggle').setAttribute('aria-expanded', String(open)); });
  $('layers-close').addEventListener('click', () => { $('layers-panel').hidden = true; $('layers-toggle').setAttribute('aria-expanded', 'false'); });
  for (const id of ['show-radar', 'show-candidates', 'show-basemap']) $(id).addEventListener('change', updateLayers);
  $('radar-opacity').addEventListener('input', updateLayers);
  $('comparison-slider').addEventListener('input', event => { state.split = Number(event.target.value); updateSplit(); });
  document.querySelectorAll('[data-date]').forEach(button => button.addEventListener('click', () => {
    if (!state.analysis) return;
    state.date = button.dataset.date; updateLayers();
  }));
  $('zoom-in').addEventListener('click', () => zoom(1.5));
  $('zoom-out').addEventListener('click', () => zoom(1 / 1.5));
  $('fit-map').addEventListener('click', resetMap);
  $('region-search').addEventListener('input', () => { state.limit = 30; renderRegions(); });
  $('region-sort').addEventListener('change', renderRegions);
  $('more-regions').addEventListener('click', () => { state.limit += 30; renderRegions(); });
  $('region-list').addEventListener('click', event => { const row = event.target.closest('[data-index]'); if (row) selectRegion(Number(row.dataset.index)); });
  $('detail-close').addEventListener('click', closeRegion);
  $('detail-download').addEventListener('click', () => {
    if (state.selected == null) return;
    const region = state.regions[state.selected];
    downloadJSON({ type: 'FeatureCollection', features: [region.feature] }, `sarwatch_region_${region.id}_unvalidated.geojson`);
  });
  document.querySelectorAll('.download-trigger').forEach(button => button.addEventListener('click', () => {
    if (!state.analysis) return;
    if (button.dataset.download === 'candidates.geojson') downloadJSON(state.analysis.geojson, 'sarwatch_candidates_unvalidated.geojson');
    else downloadJSON({ manifest: state.analysis.manifest, tables: state.analysis.tables, status: 'unvalidated',
      impact: globalThis.SARWatchImpact?.analysis_version === state.analysis.version ? {
        summary:globalThis.SARWatchImpact.summary, sources:globalThis.SARWatchImpact.sources,
        ordering:globalThis.SARWatchImpact.ordering, limitations:globalThis.SARWatchImpact.limitations,
      } : null,
      optical_crosscheck:globalThis.SARWatchReference?.analysis_version === state.analysis.version ? {
        summary:globalThis.SARWatchReference.summary,sources:globalThis.SARWatchReference.sources,
        protocol:globalThis.SARWatchReference.protocol,limitations:globalThis.SARWatchReference.limitations,
      } : null }, 'sarwatch_analysis_report.json');
  }));
  $('map-svg').addEventListener('wheel', event => {
    if (!state.analysis) return;
    event.preventDefault();
    const rect = $('map-svg').getBoundingClientRect();
    zoom(event.deltaY < 0 ? 1.15 : 1 / 1.15, (event.clientX - rect.left) / rect.width, (event.clientY - rect.top) / rect.height);
  }, { passive: false });
  $('map-svg').addEventListener('pointerdown', event => {
    if (!state.analysis || event.button !== 0) return;
    state.dragging = { x: event.clientX, y: event.clientY, box: { ...state.box }, target: event.target.closest('[data-index]'), moved: false };
    $('map-svg').setPointerCapture(event.pointerId); $('map-svg').classList.add('dragging');
  });
  $('map-svg').addEventListener('pointermove', event => {
    if (!state.analysis || !state.box) return;
    const rect = $('map-svg').getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width, y = (event.clientY - rect.top) / rect.height;
    const [lon, lat] = unproject(state.box.x + state.box.width * x, state.box.y + state.box.height * y);
    $('map-coordinates').textContent = `${number(lat, 5)}° N  ·  ${number(lon, 5)}° E`; $('map-coordinates').hidden = false;
    if (state.dragging) {
      const d = state.dragging, dx = event.clientX - d.x, dy = event.clientY - d.y;
      if (Math.hypot(dx, dy) > 4) d.moved = true;
      if (d.moved) {
        state.box = { ...d.box, x: d.box.x - dx / rect.width * d.box.width, y: d.box.y - dy / rect.height * d.box.height };
        state.modified = true; updateBox(); $('map-tooltip').hidden = true;
      }
    } else {
      const path = event.target.closest('[data-index]');
      if (path && event.pointerType !== 'touch') {
        const region = state.regions[Number(path.dataset.index)];
        $('map-tooltip').textContent = `Vùng ${region.id.padStart(3, '0')} · ${areaLabel(region.area)}`;
        $('map-tooltip').style.left = `${Math.max(8, Math.min(rect.width - 205, event.clientX - rect.left + 12))}px`;
        $('map-tooltip').style.top = `${Math.max(8, Math.min(rect.height - 35, event.clientY - rect.top - 35))}px`;
        $('map-tooltip').hidden = false;
      } else $('map-tooltip').hidden = true;
    }
  });
  function endDrag() {
    const d = state.dragging;
    state.dragging = null; $('map-svg').classList.remove('dragging');
    if (d && !d.moved && d.target) selectRegion(Number(d.target.dataset.index), false);
  }
  $('map-svg').addEventListener('pointerup', endDrag);
  $('map-svg').addEventListener('pointercancel', () => { state.dragging = null; $('map-svg').classList.remove('dragging'); });
  $('map-svg').addEventListener('pointerleave', () => { $('map-tooltip').hidden = true; });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') { $('layers-panel').hidden = true; $('layers-toggle').setAttribute('aria-expanded', 'false'); closeRegion(); }
  });
  new ResizeObserver(() => {
    if (!state.analysis || $('map-page').hidden) return;
    if (!state.modified || !state.box) resetMap();
    else {
      const b = state.box, height = b.width * $('map-viewport').clientHeight / Math.max($('map-viewport').clientWidth, 1);
      state.box = { ...b, y: b.y + (b.height - height) / 2, height }; updateBox();
    }
  }).observe($('map-viewport'));
  window.addEventListener('hashchange', updateRoute);
  globalThis.SARWatchMap = {
    analysis: () => state.analysis,
    select: id => {
      if (state.page !== 'ban-do') { location.hash = '#ban-do'; updateRoute(); }
      const index = state.regions.findIndex(r => r.id === String(id));
      if (index >= 0) { selectRegion(index); return state.regions[index].feature; }
      return null;
    },
    compare: id => { globalThis.SARWatchMap.select(id); state.date='compare'; updateLayers(); },
    project,
  };
  updateRoute(); loadAnalysis(true);
})();
