export const DEFAULT_EXPOSURE_TOP_N = 5;

let chartInstance = null;
let currentCanvas = null;

export function prepareExposureDataset(chartState, topN = DEFAULT_EXPOSURE_TOP_N) {
  const viewBase = (chartState?.viewBase || "USD").toUpperCase();
  const rawItems = Array.isArray(chartState?.items) ? chartState.items : [];

  const items = rawItems
    .map((item) => ({
      label: item.label,
      baseValue: toNumber(item.baseValue),
      nativeValue: toNumber(item.nativeValue),
      nativeCurrency: item.nativeCurrency,
      color: item.color || "#94a3b8",
    }))
    .filter((item) => Number.isFinite(item.baseValue));

  const significant = items.filter((item) => Math.abs(item.baseValue) > 0);
  const working = significant.length ? significant : items;

  if (!working.length) {
    return emptyDataset(viewBase);
  }

  const sorted = working
    .map((item) => ({ ...item, magnitude: Math.abs(item.baseValue) }))
    .sort((a, b) => b.magnitude - a.magnitude);

  const limit = Math.max(1, Math.min(topN, sorted.length));
  const primary = sorted.slice(0, limit);
  const remainder = sorted.slice(limit);

  if (remainder.length > 0) {
    const otherBase = remainder.reduce((sum, item) => sum + item.baseValue, 0);
    const otherMagnitude = remainder.reduce((sum, item) => sum + item.magnitude, 0);
    primary.push({
      label: "OTHER",
      baseValue: otherBase,
      nativeValue: null,
      nativeCurrency: null,
      color: "#9ca3af",
      magnitude: otherMagnitude,
      constituents: remainder.map((item) => ({
        label: item.label,
        baseValue: item.baseValue,
        nativeValue: item.nativeValue,
        nativeCurrency: item.nativeCurrency,
      })),
    });
  }

  const data = {
    labels: primary.map((item) => item.label),
    datasets: [
      {
        label: `Base Equivalent (${viewBase})`,
        data: primary.map((item) => item.magnitude),
        backgroundColor: primary.map((item) => item.color || "#94a3b8"),
      },
    ],
  };

  const meta = {
    viewBase,
    segments: primary.map((item) => ({
      label: item.label,
      baseValue: item.baseValue,
      nativeValue: item.nativeValue,
      nativeCurrency: item.nativeCurrency,
      constituents: item.constituents || [],
    })),
  };

  return { data, meta };
}

export function renderExposureChart(canvas, chartState, { topN = DEFAULT_EXPOSURE_TOP_N } = {}) {
  const prepared = prepareExposureDataset(chartState, topN);
  return renderPreparedExposureChart(canvas, prepared);
}

export function renderPreparedExposureChart(canvas, prepared) {
  if (!canvas || !window.Chart) {
    return null;
  }

  if (!prepared.data.labels.length) {
    destroyExposureChart();
    return null;
  }

  if (chartInstance && currentCanvas && currentCanvas !== canvas) {
    destroyExposureChart();
  }

  if (!chartInstance) {
    chartInstance = new window.Chart(canvas.getContext("2d"), {
      type: "doughnut",
      data: prepared.data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { usePointStyle: true },
          },
          tooltip: {
            callbacks: buildTooltipCallbacks(prepared.meta),
          },
        },
      },
    });
    currentCanvas = canvas;
  } else {
    chartInstance.data = prepared.data;
    chartInstance.options.plugins.tooltip.callbacks = buildTooltipCallbacks(prepared.meta);
    chartInstance.update();
  }

  chartInstance.__meta = prepared.meta;
  return chartInstance;
}

export function destroyExposureChart() {
  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
    currentCanvas = null;
  }
}

function emptyDataset(viewBase) {
  return {
    data: {
      labels: [],
      datasets: [
        {
          label: `Base Equivalent (${viewBase})`,
          data: [],
          backgroundColor: [],
        },
      ],
    },
    meta: {
      viewBase,
      segments: [],
    },
  };
}

function buildTooltipCallbacks(meta) {
  return {
    label(context) {
      const segment = meta.segments[context.dataIndex];
      if (!segment) {
        return context.formattedValue;
      }

      const lines = [
        `Base (${meta.viewBase}): ${formatCurrency(segment.baseValue, meta.viewBase)}`,
      ];

      if (segment.nativeCurrency) {
        lines.push(
          `Native (${segment.nativeCurrency}): ${formatCurrency(segment.nativeValue, segment.nativeCurrency)}`,
        );
      }

      if (segment.constituents && segment.constituents.length > 0) {
        lines.push("Breakdown:");
        segment.constituents.slice(0, 3).forEach((item) => {
          lines.push(
            `- ${item.label}: ${formatCurrency(item.baseValue, meta.viewBase)} / Native ${formatCurrency(
              item.nativeValue,
              item.nativeCurrency,
            )}`,
          );
        });
        if (segment.constituents.length > 3) {
          lines.push("- ...");
        }
      }

      return lines;
    },
  };
}

function formatCurrency(value, currency) {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: (currency || "USD").toUpperCase(),
      maximumFractionDigits: 2,
    }).format(Number(value || 0));
  } catch {
    const numeric = Number(value || 0).toLocaleString("en-US", {
      maximumFractionDigits: 2,
    });
    return `${numeric} ${currency ?? ""}`.trim();
  }
}

function toNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}
