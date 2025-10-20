import { formatCurrencyAmount } from "../utils/numeral.js";

let chartInstance = null;
let currentCanvas = null;

export function renderTimelineChart(canvas, chartState) {
  if (!canvas || !window.Chart) {
    return null;
  }

  if (!chartState || !Array.isArray(chartState.labels) || chartState.labels.length === 0) {
    destroyTimelineChart();
    return null;
  }

  if (chartInstance && currentCanvas && currentCanvas !== canvas) {
    destroyTimelineChart();
  }

  const dataset = buildDataset(chartState);
  const config = buildConfig(chartState, dataset);

  if (!chartInstance) {
    chartInstance = new window.Chart(canvas.getContext("2d"), config);
    currentCanvas = canvas;
  } else {
    chartInstance.config.data = config.data;
    chartInstance.options = config.options;
    chartInstance.update();
  }

  chartInstance.__meta = {
    viewBase: chartState.viewBase,
    points: chartState.points || [],
  };

  return chartInstance;
}

export function destroyTimelineChart() {
  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
    currentCanvas = null;
  }
}

function buildDataset(chartState) {
  return {
    label: `Portfolio Value (${chartState.viewBase})`,
    data: chartState.data,
    segment: {
      borderColor: (ctx) =>
        ctx.p0.parsed.y === null || ctx.p1.parsed.y === null
          ? "rgba(37, 99, 235, 0.15)"
          : "#2563eb",
      borderDash: (ctx) =>
        ctx.p0.parsed.y === null || ctx.p1.parsed.y === null ? [6, 6] : undefined,
    },
    borderColor: "#2563eb",
    backgroundColor: "rgba(37, 99, 235, 0.18)",
    tension: 0.25,
    spanGaps: false,
    pointRadius: 0,
    pointHoverRadius: 4,
    pointHitRadius: 10,
  };
}

function buildConfig(chartState, dataset) {
  return {
    type: "line",
    data: {
      labels: chartState.labels,
      datasets: [dataset],
    },
    options: {
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: "index",
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: "index",
          callbacks: {
            title: (items) => (items.length ? formatFullDate(items[0].label) : ""),
            label: (context) => formatCurrencyAmount(context.parsed.y, chartState.viewBase),
          },
        },
      },
      elements: {
        line: { borderWidth: 2 },
        point: { radius: 0 },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            maxTicksLimit: 6,
            callback: (_, index) => formatShortDate(chartState.labels[index]),
          },
        },
        y: {
          ticks: {
            callback: (value) => formatCurrencyAmount(value, chartState.viewBase),
          },
          grid: {
            color: "rgba(148, 163, 184, 0.2)",
          },
        },
      },
    },
  };
}

function formatShortDate(iso) {
  if (!iso) {
    return "";
  }
  try {
    const date = new Date(`${iso}T00:00:00Z`);
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

function formatFullDate(iso) {
  if (!iso) {
    return "";
  }
  try {
    const date = new Date(`${iso}T00:00:00Z`);
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return iso;
  }
}
