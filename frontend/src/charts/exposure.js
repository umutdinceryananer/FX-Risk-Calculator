export const DEFAULT_EXPOSURE_TOP_N = 5;

let chartInstance = null;
let currentCanvas = null;

export function renderExposureChart(canvas, chartState, { topN = DEFAULT_EXPOSURE_TOP_N } = {}) {
  if (!canvas || !window.Chart) {
    return null;
  }

  if (chartInstance && currentCanvas && currentCanvas !== canvas) {
    destroyExposureChart();
  }

  const processed = processChartData(chartState, topN);
  if (processed.data.labels.length === 0) {
    destroyExposureChart();
    return null;
  }

  if (!chartInstance) {
    chartInstance = new window.Chart(canvas.getContext("2d"), {
      type: "doughnut",
      data: processed.data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              usePointStyle: true,
            },
          },
          tooltip: {
            callbacks: buildTooltipCallbacks(processed.meta),
          },
        },
      },
    });
    currentCanvas = canvas;
  } else {
    chartInstance.data = processed.data;
    chartInstance.options.plugins.tooltip.callbacks = buildTooltipCallbacks(processed.meta);
    chartInstance.update();
  }

  return chartInstance;
}

export function destroyExposureChart() {
  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
    currentCanvas = null;
  }
}

function processChartData(chartState, topN) {
  const viewBase = (chartState?.viewBase || "USD").toUpperCase();
  const items = Array.isArray(chartState?.items)
    ? chartState.items.map((item) => ({
        label: item.label,
        baseValue: Number(item.baseValue) || 0,
        nativeValue: Number(item.nativeValue) || 0,
        nativeCurrency: item.nativeCurrency,
        color: item.color || "#94a3b8",
        magnitude: Math.abs(Number(item.baseValue) || 0),
      }))
    : [];

  const filtered = items.filter((item) => item.magnitude > 0);
  if (!filtered.length) {
    return emptyChart(viewBase);
  }

  const sorted = filtered.sort((a, b) => b.magnitude - a.magnitude);
  const limit = Math.max(1, Math.min(topN || DEFAULT_EXPOSURE_TOP_N, sorted.length));

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
      magnitude: otherMagnitude,
      color: "#9ca3af",
      constituents: remainder.map((item) => ({ ...item })),
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

function emptyChart(viewBase) {
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
          lines.push("- …");
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
