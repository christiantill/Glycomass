// Separate baseline-to-peak paths: never interpolate between isotope intensities.
function isotopeStickPaths(plot, seriesIndex, first, last) {
  const stroke = new Path2D();
  const baseline = plot.valToPos(0, "y", true);
  for (let index = first; index <= last; index++) {
    const intensity = plot.data[seriesIndex][index];
    if (intensity == null) continue;
    const x = plot.valToPos(plot.data[0][index], "x", true);
    const y = plot.valToPos(intensity, "y", true);
    stroke.moveTo(x, baseline);
    stroke.lineTo(x, y);
  }
  return { stroke, fill: null };
}

const spectrumCharts = new WeakMap();
function drawSpectra(root) {
  root.querySelectorAll("[data-spectrum]").forEach((el) => {
    if (spectrumCharts.has(el)) return;
    const data = JSON.parse(el.getAttribute("data-spectrum"));
    const peaks = data.mz.map((mz, index) => [mz, data.intensity[index]])
      .sort((a, b) => a[0] - b[0]);
    const profile = el.hasAttribute("data-profile") ? JSON.parse(el.dataset.profile) : null;
    const initial = profile || { mz: peaks.map(p => p[0]), intensity: peaks.map(p => p[1]) };
    const opts = {
      width: el.clientWidth || 600,
      height: 280,
      scales: {
        x: { time: false, range: (_, min, max) => {
          const padding = Math.max((max - min) * 0.05, 0.05);
          return [min - padding, max + padding];
        } },
        y: { range: [0, 105] },
      },
      axes: [
        { stroke: "#9aa7c7", grid: { stroke: "rgba(255,255,255,0.06)" }, label: "m/z", space: 85 },
        { stroke: "#9aa7c7", grid: { stroke: "rgba(255,255,255,0.06)" }, label: "Relative intensity (%)" },
      ],
      series: [
        { label: "m/z", value: (_, value) => value == null ? "—" : value.toFixed(4) },
        {
          label: "Intensity", stroke: "#FFD009", width: 1.5,
          paths: profile ? uPlot.paths.linear() : isotopeStickPaths, fill: null, points: { show: false },
          value: (_, value) => value == null ? "—" : value.toFixed(2) + "%",
        },
      ],
    };
    const chart = new uPlot(opts, [initial.mz, initial.intensity], el);
    const observer = new ResizeObserver(([entry]) => {
      const width = Math.floor(entry.contentRect.width);
      if (width > 0 && width !== chart.width) chart.setSize({ width, height: 280 });
    });
    observer.observe(el);
    spectrumCharts.set(el, { chart, observer, profile, peaks });
    el.dataset.drawn = "1";
  });
}

document.body.addEventListener("click", (event) => {
  const button = event.target.closest("[data-spectrum-mode]");
  if (!button) return;
  const widget = button.closest(".spectrum-widget");
  const el = widget.querySelector("[data-spectrum]");
  const entry = spectrumCharts.get(el);
  if (!entry) return;
  const profileMode = button.dataset.spectrumMode === "profile";
  if (profileMode && !entry.profile) return;
  entry.chart.series[1].paths = profileMode ? uPlot.paths.linear() : isotopeStickPaths;
  entry.chart.setData(profileMode
    ? [entry.profile.mz, entry.profile.intensity]
    : [entry.peaks.map(p => p[0]), entry.peaks.map(p => p[1])]);
  widget.querySelectorAll("[data-spectrum-mode]").forEach(control => {
    control.setAttribute("aria-pressed", String(control === button));
  });
  el.setAttribute("aria-label", "Theoretical isotope " + (profileMode ? "Gaussian profile" : "stick spectrum") +
    ". Horizontal axis: m/z. Vertical axis: relative intensity, normalized to 100 percent.");
});

// HTMX replaces result fragments; release canvas listeners and resize observers.
document.body.addEventListener("htmx:beforeCleanupElement", (event) => {
  const el = event.detail.elt;
  const charts = [...(el.querySelectorAll?.("[data-spectrum]") || [])];
  if (el.matches?.("[data-spectrum]")) charts.push(el);
  charts.forEach(node => {
    const entry = spectrumCharts.get(node);
    if (!entry) return;
    entry.observer.disconnect();
    entry.chart.destroy();
    spectrumCharts.delete(node);
  });
});

document.addEventListener("DOMContentLoaded", () => drawSpectra(document));
document.body.addEventListener("htmx:afterSwap", (e) => drawSpectra(e.target));

// Copy a permalink to the clipboard (progressive enhancement; the anchor still works).
document.body.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-copy]");
  if (!btn || !navigator.clipboard) return;
  const url = new URL(btn.getAttribute("data-copy"), location.origin).href;
  navigator.clipboard.writeText(url).then(() => {
    const prev = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = prev; }, 1500);
  });
});

// Render our HTML error fragments while retaining meaningful HTTP error statuses.
document.body.addEventListener("htmx:beforeSwap", (event) => {
  const detail = event.detail;
  if (detail.target?.id === "result" && [413, 422, 503].includes(detail.xhr.status) &&
      (detail.xhr.getResponseHeader("Content-Type") || "").startsWith("text/html")) {
    detail.shouldSwap = true;
    detail.isError = false;
  }
});
