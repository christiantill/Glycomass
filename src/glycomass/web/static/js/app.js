// Label visible maxima, prioritizing stronger peaks and rejecting overlapping boxes.
function spectrumLabelLayout(plot, samples) {
  const ratio = window.devicePixelRatio || 1;
  const ctx = plot.ctx;
  ctx.font = `${11 * ratio}px sans-serif`;
  const boxes = [];
  for (const [mz, intensity] of [...samples].sort((a,b) => b[1]-a[1])) {
    if (intensity < 1 || mz < plot.scales.x.min || mz > plot.scales.x.max) continue;
    const text = mz.toFixed(4);
    const width = ctx.measureText(text).width + 8 * ratio;
    const height = 17 * ratio;
    const x = plot.valToPos(mz, "x", true) - width/2;
    const y = plot.valToPos(intensity, "y", true) - height - 4 * ratio;
    if (x < plot.bbox.left || x+width > plot.bbox.left+plot.bbox.width || y < plot.bbox.top) continue;
    if (boxes.some(b => x < b.x+b.width+4*ratio && x+width+4*ratio > b.x && y < b.y+b.height+3*ratio && y+height+3*ratio > b.y)) continue;
    boxes.push({x,y,width,height,text,mz,intensity});
  }
  return boxes;
}

function profileMaxima(profile) {
  return profile.mz.flatMap((mz,i) => i > 0 && i < profile.mz.length-1 &&
    profile.intensity[i] > profile.intensity[i-1] && profile.intensity[i] >= profile.intensity[i+1]
    ? [[mz,profile.intensity[i]]] : []);
}

function peakTableText(peaks, separator = "\t") {
  return [["Peak", "m/z", "Relative intensity (%)"],
    ...peaks.map(([mz,intensity],i) => [i+1,mz.toFixed(4),intensity.toFixed(2)])]
    .map(row => row.join(separator)).join("\r\n") + "\r\n";
}

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
    const state = {labels: true, mode: profile ? "profile" : "peaks", maxima: profile ? profileMaxima(profile) : peaks, labelBoxes: []};
    const opts = {
      width: el.clientWidth || 600,
      height: 280,
      scales: {
        x: { time: false, range: (_, min, max) => {
          const padding = Math.max((max - min) * 0.05, 0.05);
          return [min - padding, max + padding];
        } },
        y: { range: [0, 120] },
      },
      hooks: {draw: [(plot) => {
        plot.ctx.save();
        state.labelBoxes = state.labels ? spectrumLabelLayout(plot, state.mode === "profile" ? state.maxima : peaks) : [];
        plot.ctx.textAlign = "center";
        plot.ctx.textBaseline = "middle";
        for (const box of state.labelBoxes) {
          plot.ctx.fillStyle = "#08142d";
          plot.ctx.fillRect(box.x,box.y,box.width,box.height);
          plot.ctx.fillStyle = "#dce5f7";
          plot.ctx.fillText(box.text,box.x+box.width/2,box.y+box.height/2);
        }
        plot.ctx.restore();
      }]},
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
    spectrumCharts.set(el, { chart, observer, profile, peaks, state });
    const widget = el.closest(".spectrum-widget");
    widget.querySelectorAll("[data-spectrum-action]").forEach(button => { button.hidden = false; });
    widget.querySelectorAll("[data-minor-peak]").forEach(row => { row.hidden = true; });
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
  entry.state.mode = profileMode ? "profile" : "peaks";
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

// Acknowledge submission immediately, including while the response is downloading.
document.body.addEventListener("htmx:beforeRequest", (event) => {
  const form = event.detail.elt;
  if (!form.matches?.(".calc-form")) return;
  form.setAttribute("aria-busy", "true");
  form.querySelector(".calculation-status").textContent = "Calculating…";
});
document.body.addEventListener("htmx:afterRequest", (event) => {
  const form = event.detail.elt;
  if (!form.matches?.(".calc-form")) return;
  form.setAttribute("aria-busy", "false");
  form.querySelector(".calculation-status").textContent = event.detail.successful
    ? "Calculation complete." : "Calculation failed. Check your inputs or connection and try again.";
});

document.body.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-spectrum-action]");
  if (!button) return;
  const widget = button.closest(".spectrum-widget");
  const entry = spectrumCharts.get(widget.querySelector("[data-spectrum]"));
  if (!entry) return;
  const status = widget.querySelector(".peak-export-status");
  switch (button.dataset.spectrumAction) {
    case "labels":
      entry.state.labels = !entry.state.labels;
      button.setAttribute("aria-pressed", String(entry.state.labels));
      // Labels are an overlay: rebuilding paths re-applies x-range padding.
      entry.chart.redraw(false);
      break;
    case "reset":
      entry.chart.setData(entry.chart.data);
      break;
    case "all": {
      const show = button.getAttribute("aria-expanded") !== "true";
      widget.querySelectorAll("[data-minor-peak]").forEach(row => { row.hidden = !show; });
      button.setAttribute("aria-expanded", String(show));
      button.textContent = show ? "Hide peaks below 1%" : "Show all peaks";
      break;
    }
    case "copy":
      try {
        await navigator.clipboard.writeText(peakTableText(entry.peaks));
        status.textContent = "Copied all isotope peaks.";
      } catch {
        status.textContent = "Copy unavailable. Download CSV or select the table to copy.";
      }
      break;
    case "csv": {
      const url = URL.createObjectURL(new Blob([peakTableText(entry.peaks, ",")], {type:"text/csv;charset=utf-8"}));
      const link = document.createElement("a");
      link.href = url;
      link.download = "glycomass-isotope-peaks.csv";
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status.textContent = "CSV includes all isotope peaks.";
      break;
    }
  }
});
