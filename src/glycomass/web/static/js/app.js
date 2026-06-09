function drawSpectra(root) {
  root.querySelectorAll("[data-spectrum]").forEach((el) => {
    if (el.dataset.drawn) return;
    el.dataset.drawn = "1";
    const data = JSON.parse(el.getAttribute("data-spectrum"));
    const mz = data.mz, inten = data.intensity;
    const opts = {
      width: el.clientWidth || 600,
      height: 240,
      scales: { x: { time: false } },
      axes: [
        { stroke: "#9aa7c7", grid: { stroke: "rgba(255,255,255,0.06)" }, label: "m/z" },
        { stroke: "#9aa7c7", grid: { stroke: "rgba(255,255,255,0.06)" }, label: "rel. intensity" },
      ],
      series: [
        {},
        { stroke: "#FFD009", width: 2, fill: "rgba(255,208,9,0.15)", points: { show: true, size: 5 } },
      ],
    };
    new uPlot(opts, [mz, inten], el);
  });
}

document.addEventListener("DOMContentLoaded", () => drawSpectra(document));
document.body.addEventListener("htmx:afterSwap", (e) => drawSpectra(e.target));
