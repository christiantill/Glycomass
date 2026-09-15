// Resolve the colour theme before first paint. A stored choice overrides the OS preference.
(() => {
  const root = document.documentElement;
  const key = "glycomass-theme";
  const prefersLight = window.matchMedia("(prefers-color-scheme: light)");
  const stored = () => {
    try { return localStorage.getItem(key); } catch { return null; }
  };
  const syncButtons = () => {
    const next = root.dataset.theme === "light" ? "dark" : "light";
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.setAttribute("aria-label", `Switch to ${next} theme`);
      button.querySelector(".theme-toggle-text").textContent = `${next[0].toUpperCase()}${next.slice(1)} theme`;
    });
  };
  const apply = (theme) => {
    if (root.dataset.theme === theme) return;
    root.dataset.theme = theme;
    syncButtons();
    document.dispatchEvent(new CustomEvent("glycomass:themechange", { detail: { theme } }));
  };
  const choice = stored();
  root.dataset.theme = choice === "light" || choice === "dark" ? choice : (prefersLight.matches ? "light" : "dark");

  prefersLight.addEventListener("change", (event) => {
    if (!stored()) apply(event.matches ? "light" : "dark");
  });
  document.addEventListener("DOMContentLoaded", () => {
    syncButtons();
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.hidden = false;
      button.addEventListener("click", () => {
        const theme = root.dataset.theme === "light" ? "dark" : "light";
        try { localStorage.setItem(key, theme); } catch { /* choice lasts for this page only */ }
        apply(theme);
      });
    });
  });
})();
