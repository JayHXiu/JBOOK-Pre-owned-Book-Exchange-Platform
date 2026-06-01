const chartInstances = {};

function initDashboard(chartData, isAdmin, options) {
  options = options || {};
  const d = typeof chartData === 'string' ? JSON.parse(chartData) : chartData;

  bindChart('chartCategoryPie', {
    title: { text: '类目占比', left: 'center' },
    tooltip: { trigger: 'item' },
    toolbox: { feature: { saveAsImage: {} } },
    series: [{ type: 'pie', radius: '55%', data: d.category_pie,
      emphasis: { itemStyle: { shadowBlur: 10 } } }],
  });

  bindChart('chartCategoryBar', {
    title: { text: '类目在售数量' },
    tooltip: { trigger: 'axis' },
    toolbox: { feature: { saveAsImage: {} } },
    xAxis: { type: 'category', data: d.category_bar?.categories || [] },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: d.category_bar?.counts || [], itemStyle: { color: '#2563eb' } }],
  });

  bindChart('chartPriceHist', {
    title: { text: '价格分布' },
    tooltip: { trigger: 'axis' },
    toolbox: { feature: { saveAsImage: {} } },
    xAxis: { type: 'category', data: d.price_hist?.labels || [] },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: d.price_hist?.counts || [] }],
  });

  bindChart('chartTrend', {
    title: { text: '时序趋势' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['上架', '成交', '浏览'] },
    toolbox: { feature: { saveAsImage: {} } },
    xAxis: { type: 'category', data: d.trend?.labels || [] },
    yAxis: { type: 'value' },
    series: [
      { name: '上架', type: 'line', smooth: true, data: d.trend?.sells || [] },
      { name: '成交', type: 'line', smooth: true, data: d.trend?.orders || [] },
      { name: '浏览', type: 'line', smooth: true, data: d.trend?.views || [] },
    ],
  });

  if (document.getElementById('chartDualAxis')) {
    bindChart('chartDualAxis', {
      title: { text: '均价与成交量' },
      tooltip: { trigger: 'axis' },
      legend: { data: ['均价', '成交'] },
      xAxis: { type: 'category', data: d.trend?.labels || [] },
      yAxis: [{ type: 'value', name: '均价' }, { type: 'value', name: '成交' }],
      series: [
        { name: '均价', type: 'line', data: d.trend?.avg_prices || [], yAxisIndex: 0 },
        { name: '成交', type: 'bar', data: d.trend?.orders || [], yAxisIndex: 1 },
      ],
    });
  }

  bindChart('chartFunnel', {
    title: { text: '转化漏斗', left: 'center' },
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [{ type: 'funnel', data: d.funnel, label: { show: true, position: 'inside' } }],
  });

  if (isAdmin && d.heatmap && document.getElementById('chartHeatmap')) {
    bindChart('chartHeatmap', {
      title: { text: '访问热力图' },
      tooltip: { position: 'top' },
      xAxis: { type: 'category', data: Array.from({length:24}, (_,i)=>i+'时') },
      yAxis: { type: 'category', data: ['周一','周二','周三','周四','周五','周六','周日'] },
      visualMap: { min: 0, max: 20, calculable: true },
      series: [{ type: 'heatmap', data: d.heatmap }],
    });
  }

  if (d.category_orders_stack && document.getElementById('chartStack')) {
    bindChart('chartStack', {
      title: { text: '类目月度成交' },
      tooltip: { trigger: 'axis' },
      legend: { data: (d.category_orders_stack.series || []).map(s => s.name) },
      xAxis: { type: 'category', data: d.category_orders_stack.months || [] },
      yAxis: { type: 'value' },
      series: (d.category_orders_stack.series || []).map(s => ({
        name: s.name, type: 'bar', stack: 'total', data: s.data,
      })),
    });
  }

  window.addEventListener('resize', () => Object.values(chartInstances).forEach(c => c && c.resize()));

  if (options.onPieClick) {
    const c = chartInstances.chartCategoryPie;
    if (c) c.on('click', params => options.onPieClick(params.name));
  }
}

function bindChart(id, option) {
  const el = document.getElementById(id);
  if (!el) return;
  const chart = echarts.init(el);
  chart.setOption(option);
  chartInstances[id] = chart;
}

function refreshDashboard(admin) {
  const days = document.getElementById('filterDays')?.value || 30;
  const cat = document.getElementById('filterCat')?.value || '';
  const url = '/analytics/api/data/?admin=' + (admin ? '1' : '0') + '&days=' + days + '&cat_id=' + cat;
  fetch(url).then(r => r.json()).then(data => {
    initDashboard(data, admin, {
      onPieClick: name => {
        const sel = document.getElementById('filterCat');
        if (sel) {
          const opt = Array.from(sel.options).find(o => o.text === name);
          if (opt) { sel.value = opt.value; refreshDashboard(admin); }
        }
      },
    });
  });
}

function initMlDashboard(mlData) {
  const d = typeof mlData === 'string' ? JSON.parse(mlData) : mlData;
  bindChart('chartPriceError', {
    title: { text: '价格误差分布' },
    xAxis: { type: 'category', data: ['0-5','5-10','10-15','15-20','20+','30+'] },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: d.price_error_bins }],
  });
  bindChart('chartConfusion', {
    title: { text: '热度分类混淆矩阵' },
    xAxis: { type: 'category', data: ['冷门','普通','热门'] },
    yAxis: { type: 'category', data: ['冷门','普通','热门'] },
    visualMap: { min: 0, max: 6 },
    series: [{ type: 'heatmap', data: flattenMatrix(d.confusion) }],
  });
  bindChart('chartRecall', {
    title: { text: '推荐 Recall@K' },
    xAxis: { type: 'category', data: ['K=1','K=3','K=5','K=10'] },
    yAxis: { type: 'value', max: 1 },
    series: [{ type: 'line', data: d.recall_at_k, smooth: true }],
  });
}

function flattenMatrix(m) {
  const out = [];
  m.forEach((row, i) => row.forEach((v, j) => out.push([j, i, v])));
  return out;
}
