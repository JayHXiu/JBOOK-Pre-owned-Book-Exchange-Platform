/** JBOOK 模型分析模块 — 轻量 / 标准 / 专业三视图 */
const mlCharts = {};

function initModelAnalysis(rawData, viewMode, isAdmin) {
  const d = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
  bindHeader(d);
  bindDisclaimer(d.disclaimer);

  if (viewMode === 'lite') renderLite(d);
  if (viewMode === 'standard') renderStandard(d);
  if (viewMode === 'pro' && isAdmin) renderPro(d);

  document.getElementById('btnRefreshMl')?.addEventListener('click', () => {
    fetch('/analytics/api/ml/?view=' + viewMode)
      .then(r => r.json())
      .then(data => {
        Object.values(mlCharts).forEach(c => c && c.dispose());
        Object.keys(mlCharts).forEach(k => delete mlCharts[k]);
        initModelAnalysis(data, viewMode, isAdmin);
      });
  });

  document.getElementById('btnExportReport')?.addEventListener('click', () => {
    const ids = Object.keys(mlCharts).filter(id => id.includes('Std') || id.includes('Price') || id.includes('Radar'));
    ids.forEach((id, i) => {
      const c = mlCharts[id];
      if (c) {
        const url = c.getDataURL({ type: 'png', pixelRatio: 2 });
        const a = document.createElement('a');
        a.href = url;
        a.download = 'jbook-ml-' + id + '.png';
        setTimeout(() => a.click(), i * 300);
      }
    });
  });

  window.addEventListener('resize', () => Object.values(mlCharts).forEach(c => c && c.resize()));
}

function bindHeader(d) {
  const h = document.getElementById('mlHeadline');
  const s = document.getElementById('mlSubtitle');
  if (h) h.textContent = d.summary?.headline || 'JBOOK 模型分析';
  if (s) s.textContent = d.summary?.subtitle || d.meta?.data_scope || '';
}

function bindDisclaimer(text) {
  const el = document.getElementById('mlDisclaimer');
  if (el) el.textContent = text || '';
}

function renderLite(d) {
  const grade = d.summary?.grade || '—';
  const score = d.summary?.overall_score || 0;
  setText('liteGrade', grade + ' · ' + score + '分');
  setText('liteConclusion', grade);
  setText('liteSummary', d.interpretation?.summary || '');

  const bars = document.getElementById('liteDimBars');
  if (bars && d.dimensions) {
    bars.innerHTML = d.dimensions.map(dim => `
      <div class="lite-dim-row mb-2">
        <div class="d-flex justify-content-between small"><span>${dim.name}</span><span>${dim.score}分</span></div>
        <div class="progress" style="height:8px"><div class="progress-bar" style="width:${dim.score}%"></div></div>
      </div>`).join('');
  }

  bindRadar('chartRadarLite', d.charts?.radar);
  bindPriceError('chartPriceErrorLite', d.charts);
  bindConfusion('chartConfusionLite', d.charts?.confusion);
  bindRecall('chartRecallLite', d.charts);
}

function renderStandard(d) {
  setText('stdOverall', d.summary?.overall_score);
  setText('stdGrade', d.summary?.grade);
  const priceM = d.models?.find(m => m.id === 'price');
  const hotM = d.models?.find(m => m.id === 'hot');
  setText('stdMae', priceM?.metrics?.mae ?? '—');
  setText('stdAcc', hotM?.metrics?.accuracy != null ? (hotM.metrics.accuracy * 100).toFixed(1) + '%' : '—');

  renderMetaGrid(d);
  renderModelTabs(d.models || []);
  bindRadar('chartRadarStd', d.charts?.radar);
  bindPriceError('chartPriceError', d.charts);
  bindConfusion('chartConfusion', d.charts?.confusion);
  bindRecall('chartRecall', d.charts);
  bindModelCompare('chartComparePrice', d.charts?.model_compare?.price, 'mae', '定价模型 MAE 对比');
  bindModelCompare('chartCompareHot', d.charts?.model_compare?.hot, 'accuracy', '热度模型准确率对比', true);
  bindHistoryTrend('chartHistoryTrend', d.charts?.trend);

  setText('interpSummary', d.interpretation?.summary);
  fillList('interpStrengths', d.interpretation?.strengths);
  fillList('interpWeaknesses', d.interpretation?.weaknesses);
  fillList('interpRisks', d.interpretation?.risks);
  fillList('interpSuggestions', d.interpretation?.suggestions);
}

function renderPro(d) {
  const pipe = document.getElementById('proPipeline');
  if (pipe && d.pro?.pipeline) {
    pipe.innerHTML = d.pro.pipeline.map(p => `
      <div class="col-md-4 col-lg mb-3">
        <div class="pro-step-card p-3 h-100">
          <div class="pro-step-num">${p.step}</div>
          <strong>${p.title}</strong>
          <p class="small text-muted mb-0 mt-1">${p.desc}</p>
        </div>
      </div>`).join('');
  }
  const hp = document.getElementById('proHyperparams');
  if (hp) hp.textContent = JSON.stringify(d.pro?.hyperparams || {}, null, 2);
  fillList('proTrainingLog', d.pro?.training_log || []);
  const tbody = document.getElementById('proHistoryTable');
  if (tbody) {
    const rows = d.pro?.history || [];
    tbody.innerHTML = rows.length ? rows.slice().reverse().map(r => `
      <tr>
        <td>${r.time || '—'}</td>
        <td>${r.overall_score ?? '—'}</td>
        <td>${r.price_mae ?? '—'}</td>
        <td>${r.price_r2 ?? '—'}</td>
        <td>${r.hot_accuracy != null ? (r.hot_accuracy * 100).toFixed(1) + '%' : '—'}</td>
        <td class="small">${r.price_model || ''} / ${r.hot_model || ''}</td>
      </tr>`).join('') : '<tr><td colspan="6" class="text-muted text-center">暂无历史，运行 train_ml 后生成</td></tr>';
  }
  bindPriceError('chartPriceErrorPro', d.charts);
  bindConfusion('chartConfusionPro', d.charts?.confusion);
  bindRecall('chartRecallPro', d.charts);
}

function renderMetaGrid(d) {
  const grid = document.getElementById('modelMetaGrid');
  if (!grid) return;
  const m = d.meta || {};
  const items = [
    ['平台', m.platform], ['版本', m.version], ['更新时间', m.updated_at],
    ['适用场景', m.scope], ['数据口径', m.data_scope],
    ['样本在售', m.sample_size?.on_sale], ['样本总量', m.sample_size?.sells],
  ];
  grid.innerHTML = items.map(([k, v]) => `
    <div class="col-md-4 col-6"><span class="text-muted small">${k}</span><div class="fw-semibold">${v ?? '—'}</div></div>`).join('');
}

function renderModelTabs(models) {
  const tabs = document.getElementById('modelTabs');
  const content = document.getElementById('modelTabContent');
  if (!tabs || !content) return;
  tabs.innerHTML = models.map((m, i) => `
    <li class="nav-item">
      <button class="nav-link ${i === 0 ? 'active' : ''}" data-bs-toggle="tab" data-bs-target="#tab-${m.id}">${m.name}</button>
    </li>`).join('');
  content.innerHTML = models.map((m, i) => `
    <div class="tab-pane fade ${i === 0 ? 'show active' : ''}" id="tab-${m.id}">
      <div class="row g-3 mb-3">
        <div class="col-md-6"><span class="text-muted small">算法</span><div>${m.algorithm}</div></div>
        <div class="col-md-6"><span class="text-muted small">类型</span><div>${m.type} · ${m.scene}</div></div>
      </div>
      <table class="table table-sm table-hover">
        <thead><tr><th>指标</th><th>权重</th><th>计分规则</th></tr></thead>
        <tbody>${(m.features || []).map(f => `
          <tr><td>${f.name || f.key}</td><td>${f.weight != null ? (f.weight * 100).toFixed(0) + '%' : '—'}</td><td class="small text-muted">${f.rule || ''}</td></tr>`).join('')}
        </tbody>
      </table>
    </div>`).join('');
}

function bindRadar(id, radar) {
  if (!radar) return;
  mlBind(id, {
    title: { text: '综合维度雷达', left: 'center', textStyle: { fontSize: 13 } },
    tooltip: {},
    radar: { indicator: radar.indicators || [] },
    series: [{ type: 'radar', data: [{ value: radar.values || [], name: '得分' }] }],
  });
}

function bindPriceError(id, charts) {
  mlBind(id, {
    title: { text: '价格误差分布', textStyle: { fontSize: 13 } },
    tooltip: { trigger: 'axis' },
    toolbox: { feature: { saveAsImage: {} } },
    xAxis: { type: 'category', data: charts?.price_error_labels || [] },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: charts?.price_error_bins || [], itemStyle: { color: '#2563eb' } }],
  });
}

function bindConfusion(id, matrix) {
  mlBind(id, {
    title: { text: '热度混淆矩阵', textStyle: { fontSize: 13 } },
    tooltip: { position: 'top' },
    toolbox: { feature: { saveAsImage: {} } },
    xAxis: { type: 'category', data: ['冷门', '普通', '热门'] },
    yAxis: { type: 'category', data: ['冷门', '普通', '热门'] },
    visualMap: { min: 0, max: 10, calculable: true, orient: 'horizontal', left: 'center', bottom: 0 },
    series: [{ type: 'heatmap', data: flattenMatrix(matrix || []), label: { show: true } }],
  });
}

function bindRecall(id, charts) {
  mlBind(id, {
    title: { text: '推荐 Recall@K', textStyle: { fontSize: 13 } },
    tooltip: { trigger: 'axis' },
    toolbox: { feature: { saveAsImage: {} } },
    xAxis: { type: 'category', data: charts?.recall_labels || [] },
    yAxis: { type: 'value', max: 1 },
    series: [{ type: 'line', smooth: true, data: charts?.recall_at_k || [], areaStyle: { opacity: 0.15 } }],
  });
}

function bindModelCompare(id, rows, metric, title, isPct) {
  if (!rows?.length) return;
  const names = rows.map(r => r.name);
  const vals = rows.map(r => {
    const v = r[metric];
    return isPct && v != null ? +(v * 100).toFixed(1) : v;
  });
  mlBind(id, {
    title: { text: title, textStyle: { fontSize: 13 } },
    tooltip: { trigger: 'axis', formatter: isPct ? '{b}: {c}%' : undefined },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 20, fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: vals, itemStyle: { color: '#059669' } }],
  });
}

function bindHistoryTrend(id, history) {
  if (!history?.length) {
    mlBind(id, { title: { text: '训练历史趋势（暂无数据）' } });
    return;
  }
  mlBind(id, {
    title: { text: '模型版本回测趋势' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['综合分', '定价R²', '热度Acc'] },
    xAxis: { type: 'category', data: history.map(h => h.time?.slice(5, 16) || '') },
    yAxis: { type: 'value' },
    series: [
      { name: '综合分', type: 'line', data: history.map(h => h.overall_score) },
      { name: '定价R²', type: 'line', data: history.map(h => h.price_r2 != null ? +(h.price_r2 * 100).toFixed(1) : null) },
      { name: '热度Acc', type: 'line', data: history.map(h => h.hot_accuracy != null ? +(h.hot_accuracy * 100).toFixed(1) : null) },
    ],
  });
}

function flattenMatrix(m) {
  const out = [];
  m.forEach((row, i) => row.forEach((v, j) => out.push([j, i, v])));
  return out;
}

function mlBind(id, option) {
  const el = document.getElementById(id);
  if (!el || typeof echarts === 'undefined') return;
  if (mlCharts[id]) mlCharts[id].dispose();
  const chart = echarts.init(el);
  chart.setOption(option);
  mlCharts[id] = chart;
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? '—';
}

function fillList(id, items) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = (items || []).map(t => `<li>${t}</li>`).join('') || '<li class="text-muted">暂无</li>';
}

window.initModelAnalysis = initModelAnalysis;
