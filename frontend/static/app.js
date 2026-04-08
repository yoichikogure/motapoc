const state = {
  regions: [],
  selectedGovernorateId: null,
  mapMetric: 'priority_score',
  leafletMap: null,
  geoJsonLayer: null,
  siteLayer: null,
  boundaryGeoJson: null,
  regionMetricsByName: {},
  configItems: [],
};

const fmt = (n) => (n === null || n === undefined || n === '') ? '-' : Number(n).toLocaleString();
const fmtScore = (n) => (n === null || n === undefined || n === '') ? '-' : Number(n).toFixed(1);
const fmtPct = (n) => (n === null || n === undefined || n === '') ? '-' : `${(Number(n) * (Number(n) <= 1.5 ? 100 : 1)).toFixed(1)}%`;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));

const metricDefinitions = {
  priority_score: { label: 'Priority score', formatter: fmtScore, color: v => v == null ? '#e5e7eb' : v >= 75 ? '#1d4ed8' : v >= 60 ? '#60a5fa' : v >= 40 ? '#93c5fd' : '#dbeafe' },
  latest_average_occupancy_rate: { label: 'Occupancy rate', formatter: fmtPct, color: v => v == null ? '#e5e7eb' : v >= 0.65 ? '#16a34a' : v >= 0.5 ? '#86efac' : v >= 0.35 ? '#bbf7d0' : '#dcfce7' },
  visitors_per_1000_beds: { label: 'Visitors per 1,000 beds', formatter: fmt, color: v => v == null ? '#e5e7eb' : v >= 15000 ? '#d97706' : v >= 10000 ? '#fbbf24' : v >= 5000 ? '#fde68a' : '#fef3c7' },
  capacity_classification: { label: 'Capacity classification', formatter: v => v || '-', color: v => !v ? '#e5e7eb' : v === 'Under-capacity' ? '#ef4444' : v === 'Balanced' ? '#10b981' : '#f59e0b' },
  next_forecast_value: { label: 'Next forecast', formatter: fmt, color: v => v == null ? '#e5e7eb' : v >= 120000 ? '#7c3aed' : v >= 80000 ? '#a78bfa' : v >= 50000 ? '#ddd6fe' : '#ede9fe' },
};

async function api(url, options = {}) {
  const res = await fetch(url, options);
  if (res.status === 401) throw new Error('AUTH_REQUIRED');
  if (!res.ok) throw new Error(await res.text());
  const ctype = res.headers.get('content-type') || '';
  return ctype.includes('application/json') ? res.json() : res.text();
}

const normalizeName = (name) => String(name || '').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '').replace(/[`']/g, '').replace(/[^a-z0-9]+/g, ' ').trim();

function setActiveTab(name) {
  document.querySelectorAll('.tab').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${name}`));
}

function renderKpis(data) {
  const items = [
    ['Latest Month', data.latest_month], ['Total Visitors', fmt(data.total_visitors)], ['Total Rooms', fmt(data.total_rooms)],
    ['Total Beds', fmt(data.total_beds)], ['Average Occupancy', fmtPct(data.average_occupancy_rate)], ['High Priority Zones', fmt(data.high_priority_zones)],
  ];
  document.getElementById('kpis').innerHTML = items.map(([label, value]) => `<div class="card"><div class="label">${label}</div><div class="value">${value}</div></div>`).join('');
}

function buildRegionOptions() {
  const select = document.getElementById('sim-governorate');
  select.innerHTML = state.regions.map(r => `<option value="${r.governorate_id}">${esc(r.governorate_name_en)}</option>`).join('');
}

function renderRegionsTable(rows) {
  state.regions = rows;
  state.regionMetricsByName = Object.fromEntries(rows.map(r => [normalizeName(r.governorate_name_en), r]));
  document.querySelector('#regions-table tbody').innerHTML = rows.map(r => `
    <tr data-id="${r.governorate_id}">
      <td>${esc(r.governorate_name_en)}</td><td>${fmt(r.latest_total_visitors)}</td><td>${fmt(r.latest_total_beds)}</td>
      <td>${fmtPct(r.latest_average_occupancy_rate)}</td><td>${fmtScore(r.priority_score)}</td><td>${esc(r.capacity_classification || '-')}</td>
      <td><a href="/api/exports/regions/${r.governorate_id}.csv" target="_blank">CSV</a></td>
    </tr>`).join('');
  document.querySelectorAll('#regions-table tbody tr').forEach(tr => tr.addEventListener('click', () => loadRegionDetail(Number(tr.dataset.id))));

  document.querySelector('#investment-table tbody').innerHTML = rows.map((r, idx) => `
    <tr><td>${idx + 1}</td><td>${esc(r.governorate_name_en)}</td><td>${fmtScore(r.priority_score)}</td><td>${esc(r.capacity_classification || '-')}</td>
    <td>${fmt(r.next_forecast_value)}</td><td>${esc(r.justification_text || '-')}</td></tr>`).join('');
  buildRegionOptions();
}

function renderLegend(metricKey) {
  const def = metricDefinitions[metricKey];
  const el = document.getElementById('map-legend');

  const presets = {
    priority_score: [
      { label: '75 and above', color: '#1d4ed8' },
      { label: '60–74.9', color: '#60a5fa' },
      { label: '40–59.9', color: '#93c5fd' },
      { label: 'Below 40', color: '#dbeafe' },
      { label: 'No data', color: '#e5e7eb' },
    ],
    latest_average_occupancy_rate: [
      { label: '65% and above', color: '#16a34a' },
      { label: '50%–64.9%', color: '#86efac' },
      { label: '35%–49.9%', color: '#bbf7d0' },
      { label: 'Below 35%', color: '#dcfce7' },
      { label: 'No data', color: '#e5e7eb' },
    ],
    visitors_per_1000_beds: [
      { label: '15,000 and above', color: '#d97706' },
      { label: '10,000–14,999', color: '#fbbf24' },
      { label: '5,000–9,999', color: '#fde68a' },
      { label: 'Below 5,000', color: '#fef3c7' },
      { label: 'No data', color: '#e5e7eb' },
    ],
    capacity_classification: [
      { label: 'Under-capacity', color: '#ef4444' },
      { label: 'Balanced', color: '#10b981' },
      { label: 'Over-capacity', color: '#f59e0b' },
      { label: 'No data', color: '#e5e7eb' },
    ],
    next_forecast_value: [
      { label: '120,000 and above', color: '#7c3aed' },
      { label: '80,000–119,999', color: '#a78bfa' },
      { label: '50,000–79,999', color: '#ddd6fe' },
      { label: 'Below 50,000', color: '#ede9fe' },
      { label: 'No data', color: '#e5e7eb' },
    ],
  };

  const items = (presets[metricKey] || []).map(item => `
    <div class="legend-item">
      <span class="legend-swatch" style="background:${item.color}"></span>
      <span>${item.label}</span>
    </div>
  `).join('');

  el.innerHTML = `
    <div class="legend-title">${def.label}</div>
    <div class="legend-items">${items}</div>
  `;
}

function metricValue(metrics, metricKey) {
  const raw = metrics?.[metricKey];
  if (raw === null || raw === undefined || raw === '') return null;
  return metricKey === 'capacity_classification' ? raw : Number(raw);
}

function popupHtml(metrics, geoName) {
  const name = metrics?.governorate_name_en || geoName || '-';
  return `
    <div class="map-popup-title">${esc(name)}</div>
    <div class="map-popup-grid">
      <div>Visitors</div><div>${fmt(metrics?.latest_total_visitors)}</div>
      <div>Beds</div><div>${fmt(metrics?.latest_total_beds)}</div>
      <div>Occupancy</div><div>${fmtPct(metrics?.latest_average_occupancy_rate)}</div>
      <div>Priority</div><div>${fmtScore(metrics?.priority_score)}</div>
      <div>Forecast</div><div>${fmt(metrics?.next_forecast_value)}</div>
      <div>Action</div><div>${esc(metrics?.justification_text || '-')}</div>
    </div>`;
}

function layerStyle(feature, selected = false) {
  const metrics = feature.properties.joinedMetrics;
  const val = metricValue(metrics, state.mapMetric);
  return { color: selected ? '#0f172a' : '#ffffff', weight: selected ? 3.5 : 2, opacity: 1, fillColor: metricDefinitions[state.mapMetric].color(val), fillOpacity: 0.72 };
}

async function ensureMapInitialized() {
  if (state.leafletMap) return;
  state.leafletMap = L.map('map').setView([31.2, 36.4], 7);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(state.leafletMap);
}

async function loadBoundaryGeoJson() {
  if (state.boundaryGeoJson) return state.boundaryGeoJson;
  state.boundaryGeoJson = await api('/static/data/jo_admin.json');
  return state.boundaryGeoJson;
}

function joinMetrics(raw) {
  const cloned = JSON.parse(JSON.stringify(raw));
  cloned.features = (cloned.features || []).map(f => {
    const geoName = f.properties?.name || f.properties?.NAME_1 || f.properties?.governorate_name_en || '';
    f.properties = { ...f.properties, joinedMetrics: state.regionMetricsByName[normalizeName(geoName)] || null };
    return f;
  });
  return cloned;
}

function drawSites(sites) {
  if (state.siteLayer) state.leafletMap.removeLayer(state.siteLayer);
  if (!document.getElementById('toggle-sites').checked) return;
  state.siteLayer = L.layerGroup((sites || []).filter(s => s.latitude && s.longitude).map(s => L.circleMarker([s.latitude, s.longitude], { radius: 6, color: '#7c3aed', fillColor: '#a78bfa', fillOpacity: 0.9 }).bindPopup(`<strong>${esc(s.site_name_en)}</strong><br>${esc(s.site_category || '-')}`))).addTo(state.leafletMap);
}

function renderMap(boundaries, sites) {
  ensureMapInitialized();
  renderLegend(state.mapMetric);
  const joined = joinMetrics(boundaries);
  if (state.geoJsonLayer) state.leafletMap.removeLayer(state.geoJsonLayer);
  state.geoJsonLayer = L.geoJSON(joined, {
    style: f => layerStyle(f, f.properties?.joinedMetrics?.governorate_id === state.selectedGovernorateId),
    onEachFeature: (feature, layer) => {
      const geoName = feature.properties?.name || feature.properties?.NAME_1 || feature.properties?.governorate_name_en || '';
      const metrics = feature.properties?.joinedMetrics;
      layer.bindPopup(popupHtml(metrics, geoName));
      layer.on('click', () => metrics?.governorate_id && loadRegionDetail(metrics.governorate_id));
    }
  }).addTo(state.leafletMap);
  drawSites(sites);
}

function sparkline(rows, keyA='total_visitors', keyB='priority_score') {
  const width = 520, height = 220, pad = 24;
  const x = i => pad + i * ((width - pad*2) / Math.max(rows.length - 1, 1));
  const valsA = rows.map(r => Number(r[keyA] || 0));
  const valsB = rows.map(r => Number(r[keyB] || 0));
  const maxA = Math.max(...valsA, 1), maxB = Math.max(...valsB, 1);
  const yA = v => height - pad - (v / maxA) * (height - pad*2);
  const yB = v => height - pad - (v / maxB) * (height - pad*2);
  const pathA = valsA.map((v,i) => `${i===0?'M':'L'}${x(i)},${yA(v)}`).join(' ');
  const pathB = valsB.map((v,i) => `${i===0?'M':'L'}${x(i)},${yB(v)}`).join(' ');
  const labels = [0, Math.max(0, rows.length-1)].map(i => `<text x="${x(i)}" y="${height-6}" font-size="11" text-anchor="middle" fill="#64748b">${esc(rows[i]?.month_index || '')}</text>`).join('');
  return `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><line x1="${pad}" y1="${height-pad}" x2="${width-pad}" y2="${height-pad}" class="chart-axis"/><path d="${pathA}" class="chart-line-primary"/><path d="${pathB}" class="chart-line-secondary"/>${labels}</svg>`;
}

function detailMetric(label, value) { return `<div class="metric-pill"><div class="k">${label}</div><div class="v">${value}</div></div>`; }

function renderRegionDetail(data) {
  const rows = data.time_series || [];
  const latest12 = rows.slice(-12).map(r => `<tr><td>${esc(r.month_index)}</td><td>${fmt(r.total_visitors)}</td><td>${fmt(r.total_beds)}</td><td>${fmtPct(r.average_occupancy_rate)}</td><td>${fmtScore(r.priority_score)}</td></tr>`).join('');
  document.getElementById('detail-content').innerHTML = `
    <div class="detail-head"><div><h3>${esc(data.governorate_name_en || '')}</h3><div class="detail-subtitle">Regional deep dive with forecast, score components, and tourism sites.</div></div></div>
    <div class="metric-grid">
      ${detailMetric('Priority score', fmtScore(data.priority_score))}
      ${detailMetric('Capacity status', esc(data.capacity_classification || '-'))}
      ${detailMetric('Visitors per 1,000 beds', fmt(data.visitors_per_1000_beds))}
      ${detailMetric('Next forecast', `${fmt(data.next_forecast_value)} <span class="small-text muted">(${fmt(data.next_forecast_lower)}–${fmt(data.next_forecast_upper)})</span>`)}
      ${detailMetric('Forecast reliability', esc(data.reliability_label || '-'))}
      ${detailMetric('MAPE', fmtScore(data.mape))}
    </div>
    <div class="score-breakdown">
      <div><strong>Score breakdown:</strong> Occupancy ${fmtScore(data.occupancy_component)} · Growth ${fmtScore(data.growth_component)} · Beds ${fmtScore(data.visitor_bed_component)} · Forecast ${fmtScore(data.forecast_component)}</div>
    </div>
    <div class="detail-chart-wrap"><div class="detail-chart-title">Visitors vs Priority trend</div><div id="detail-chart">${rows.length ? sparkline(rows) : '<div class="muted">No time series.</div>'}</div></div>
    <div class="help-box">${esc(data.justification_text || 'No justification text available.')}</div>
    <div class="help-box"><strong>Tourism sites in region:</strong> ${(data.sites || []).map(s => `${esc(s.site_name_en)} (${esc(s.site_category || '-')})`).join(', ') || 'No site points configured.'}</div>
    <table class="small-table"><thead><tr><th>Month</th><th>Visitors</th><th>Beds</th><th>Occupancy</th><th>Priority</th></tr></thead><tbody>${latest12}</tbody></table>`;
}

async function loadRegionDetail(governorateId) {
  state.selectedGovernorateId = governorateId;
  const data = await api(`/api/overview/regions/${governorateId}`);
  renderRegionDetail(data);
  if (state.geoJsonLayer) state.geoJsonLayer.eachLayer(layer => layer.setStyle(layerStyle(layer.feature, layer.feature?.properties?.joinedMetrics?.governorate_id === governorateId)));
}

async function loadForecastRuns() {
  const runs = await api('/api/forecasts/runs');
  document.getElementById('forecast-runs').innerHTML = !runs.length ? '<div class="muted">No forecast runs yet.</div>' : `<table class="small-table"><thead><tr><th>Run ID</th><th>Model</th><th>Horizon</th><th>Created</th><th></th></tr></thead><tbody>${runs.map(r => `<tr><td>${r.model_run_id}</td><td>${esc(r.model_name)}</td><td>${r.horizon_months}</td><td>${esc(r.created_at)}</td><td><button class="ghost btn-forecast-detail" data-id="${r.model_run_id}">View</button></td></tr>`).join('')}</tbody></table>`;
  document.querySelectorAll('.btn-forecast-detail').forEach(btn => btn.addEventListener('click', () => loadForecastDetail(Number(btn.dataset.id))));
}

async function loadForecastDetail(modelRunId) {
  const data = await api(`/api/forecasts/runs/${modelRunId}`);
  const grouped = {};
  (data.rows || []).forEach(r => { grouped[r.governorate_name_en] ||= []; grouped[r.governorate_name_en].push(r); });
  const blocks = Object.entries(grouped).slice(0, 4).map(([name, rows]) => {
    const first = rows[0];
    return `<div class="forecast-card"><h4>${esc(name)}</h4><div class="small-text muted">MAPE ${fmtScore(first.mape)} · Reliability ${esc(first.reliability_label || '-')}</div><table class="small-table"><thead><tr><th>Month</th><th>Forecast</th><th>Band</th></tr></thead><tbody>${rows.slice(0,4).map(r => `<tr><td>${esc(r.forecast_month)}</td><td>${fmt(r.forecast_value)}</td><td>${fmt(r.lower_bound)}–${fmt(r.upper_bound)}</td></tr>`).join('')}</tbody></table></div>`;
  }).join('');
  document.getElementById('forecast-detail').innerHTML = `<div class="help-box">Run ${data.run?.model_run_id || ''} · ${esc(data.run?.model_name || '')} · horizon ${data.run?.horizon_months || ''} month(s)</div>${blocks || '<div class="muted">No detail rows.</div>'}`;
}

async function loadSimulationRuns() {
  const runs = await api('/api/simulations/runs');
  document.getElementById('simulation-runs').innerHTML = !runs.length ? '<div class="muted">No scenario runs yet.</div>' : `<table class="small-table"><thead><tr><th>Run ID</th><th>Governorate ID</th><th>Target Month</th><th>Created</th><th></th></tr></thead><tbody>${runs.map(r => `<tr><td>${r.scenario_run_id}</td><td>${r.governorate_id}</td><td>${esc(r.target_month)}</td><td>${esc(r.created_at)}</td><td><button class="ghost btn-sim-detail" data-id="${r.scenario_run_id}">View</button></td></tr>`).join('')}</tbody></table>`;
  document.querySelectorAll('.btn-sim-detail').forEach(btn => btn.addEventListener('click', () => loadSimulationDetail(Number(btn.dataset.id))));
}

async function loadSimulationDetail(runId) {
  const data = await api(`/api/simulations/runs/${runId}`); const r = data.result;
  if (!r) return document.getElementById('simulation-result').innerHTML = '<div class="muted">No result found.</div>';
  document.getElementById('simulation-result').innerHTML = `<div class="metric-grid">
    ${detailMetric('Governorate', esc(r.governorate_name_en))}${detailMetric('Target month', esc(r.target_month))}
    ${detailMetric('Baseline demand', fmt(r.baseline_demand))}${detailMetric('Scenario demand', fmt(r.scenario_demand))}
    ${detailMetric('Baseline beds', fmt(r.baseline_beds))}${detailMetric('Scenario beds', fmt(r.scenario_beds))}
    ${detailMetric('Priority before', fmtScore(r.priority_score_before))}${detailMetric('Priority after', fmtScore(r.priority_score_after))}
    ${detailMetric('Visitors / 1,000 beds before', fmt(r.visitors_per_1000_beds_before))}${detailMetric('Visitors / 1,000 beds after', fmt(r.visitors_per_1000_beds_after))}
  </div><div class="help-box">${esc(r.recommendation_text || '-')}</div>`;
}

async function loadImportJobs() {
  const jobs = await api('/api/imports');
  document.getElementById('import-jobs').innerHTML = !jobs.length ? '<div class="muted">No import jobs yet.</div>' : `<table class="small-table"><thead><tr><th>Job ID</th><th>Dataset</th><th>Status</th><th>Rows</th><th>Validation</th><th></th></tr></thead><tbody>${jobs.map(j => {
    const s = j.validation_summary_json || {};
    return `<tr><td>${j.import_job_id}</td><td>${esc(j.dataset_type)}</td><td>${esc(j.status)}</td><td>${j.success_rows}/${j.processed_rows}</td><td>dup ${s.duplicates_in_file || 0}, null ${s.null_like_values || 0}, month ${s.invalid_months || 0}, neg ${s.negative_values || 0}</td><td>${j.error_rows > 0 ? `<button class="ghost btn-import-errors" data-id="${j.import_job_id}">Errors</button>` : ''}</td></tr>`;
  }).join('')}</tbody></table>`;
  document.querySelectorAll('.btn-import-errors').forEach(btn => btn.addEventListener('click', () => loadImportErrors(Number(btn.dataset.id))));
}

async function loadImportErrors(jobId) {
  const rows = await api(`/api/imports/${jobId}/errors`);
  document.getElementById('import-errors').innerHTML = !rows.length ? '<div class="muted">No errors.</div>' : `<table class="small-table"><thead><tr><th>Row</th><th>Error</th><th>Raw Row</th></tr></thead><tbody>${rows.map(r => `<tr><td>${r.row_number}</td><td>${esc(r.error_message)}</td><td><code>${esc(JSON.stringify(r.raw_row_json || {}))}</code></td></tr>`).join('')}</tbody></table>`;
}

async function loadConfig() {
  state.configItems = await api('/api/config');
  document.getElementById('config-editor').innerHTML = `<div class="stack-form">${state.configItems.map(item => `<label>${esc(item.parameter_key)}<input data-key="${esc(item.parameter_key)}" value="${esc(item.parameter_value)}" /></label><div class="small-text muted">${esc(item.description || '')}</div>`).join('')}<button id="btn-save-config">Save configuration</button></div>`;
  document.getElementById('config-help').innerHTML = state.configItems.map(i => `<div><strong>${esc(i.parameter_key)}</strong>: ${esc(i.description || '')}</div>`).join('');
  document.getElementById('btn-save-config').addEventListener('click', async () => {
    const items = state.configItems.map(i => ({ parameter_key: i.parameter_key, parameter_value: document.querySelector(`[data-key="${i.parameter_key}"]`).value, value_type: i.value_type, description: i.description }));
    await api('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items }) });
    alert('Configuration saved. Recompute indicators to apply it.');
  });
}

async function loadMethodology() {
  const data = await api('/api/config/methodology');
  document.getElementById('methodology-content').innerHTML = `<div class="help-box"><strong>Forecast models</strong><ul>${data.forecast_models.map(m => `<li><strong>${esc(m.label)}</strong>: ${esc(m.description)}</li>`).join('')}</ul></div><div class="help-box">${esc(data.priority_score)}</div><div class="help-box">${esc(data.simulation)}</div>`;
  document.getElementById('limitations-content').innerHTML = `<div class="help-box"><ul>${(data.limitations || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>`;
}

async function refreshOverview() {
  const [kpis, regions, boundaries, sites] = await Promise.all([api('/api/overview/kpis'), api('/api/overview/regions'), loadBoundaryGeoJson(), api('/api/overview/sites')]);
  renderKpis(kpis); renderRegionsTable(regions); renderMap(boundaries, sites);
  const targetId = state.selectedGovernorateId || regions[0]?.governorate_id; if (targetId) await loadRegionDetail(targetId);
}

async function bootAfterLogin() {
  document.getElementById('login-screen').classList.add('hidden');
  await refreshOverview();
  await Promise.all([loadForecastRuns(), loadSimulationRuns(), loadImportJobs(), loadConfig(), loadMethodology()]);
}

async function trySession() {
  try { const me = await api('/api/auth/me'); document.getElementById('current-user').textContent = `${me.user.full_name || me.user.username} (${me.user.role_name})`; await bootAfterLogin(); }
  catch { document.getElementById('login-screen').classList.remove('hidden'); }
}

document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault(); document.getElementById('login-error').textContent = '';
  try {
    const res = await api('/api/auth/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ username: document.getElementById('login-username').value, password: document.getElementById('login-password').value }) });
    document.getElementById('current-user').textContent = `${res.user.full_name || res.user.username} (${res.user.role_name})`;
    await bootAfterLogin();
  } catch { document.getElementById('login-error').textContent = 'Login failed.'; }
});

document.getElementById('btn-logout').addEventListener('click', async () => { await api('/api/auth/logout', { method: 'POST' }); location.reload(); });
document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => setActiveTab(btn.dataset.tab)));
document.getElementById('map-metric').addEventListener('change', async e => { state.mapMetric = e.target.value; await refreshOverview(); });
document.getElementById('toggle-sites').addEventListener('change', async () => refreshOverview());
document.getElementById('btn-recompute').addEventListener('click', async () => { await api('/api/analytics/recompute', { method: 'POST' }); await refreshOverview(); alert('Indicators recomputed.'); });
document.getElementById('btn-forecast').addEventListener('click', async () => { await api('/api/forecasts/run', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ model_name: document.getElementById('forecast-model').value, horizon_months: 12 }) }); await loadForecastRuns(); await refreshOverview(); alert('Forecast run completed.'); });
document.getElementById('btn-refresh-overview').addEventListener('click', refreshOverview);
document.getElementById('simulation-form').addEventListener('submit', async (e) => {
  e.preventDefault(); const latest = await api('/api/forecasts/latest');
  const result = await api('/api/simulations/run', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
    governorate_id: Number(document.getElementById('sim-governorate').value), target_month: document.getElementById('sim-target-month').value,
    additional_beds: Number(document.getElementById('sim-additional-beds').value || 0), additional_rooms: Number(document.getElementById('sim-additional-rooms').value || 0),
    induced_demand_ratio: Number(document.getElementById('sim-induced-demand').value || 0), based_on_model_run_id: latest?.model_run_id || null,
  })});
  await loadSimulationRuns(); await loadSimulationDetail(result.scenario_run_id);
});
document.getElementById('import-form').addEventListener('submit', async (e) => {
  e.preventDefault(); const datasetType = document.getElementById('import-dataset-type').value; const file = document.getElementById('import-file').files[0]; if (!file) return;
  const formData = new FormData(); formData.append('file', file);
  await api(`/api/imports/${datasetType}`, { method: 'POST', body: formData }); await loadImportJobs(); alert('Import completed. Recompute indicators afterward if needed.');
});
document.getElementById('btn-export-overview').addEventListener('click', () => window.open('/api/exports/overview.csv', '_blank'));
document.getElementById('btn-export-summary').addEventListener('click', () => window.open('/api/exports/executive-summary.html', '_blank'));

trySession();
