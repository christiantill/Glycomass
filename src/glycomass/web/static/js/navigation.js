(() => {
  const nav = document.querySelector('.nav');
  if (!nav) return;
  const toggle = nav.querySelector('.nav-toggle');
  const panel = nav.querySelector('.nav-panel');
  const picker = nav.querySelector('.tool-switcher');
  const mobile = window.matchMedia('(max-width: 920px)');

  function closeNavigation(restoreFocus = false) {
    panel.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.querySelector('.nav-toggle-label').textContent = 'Menu';
    picker.open = false;
    if (restoreFocus && mobile.matches) toggle.focus();
  }

  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open));
    toggle.querySelector('.nav-toggle-label').textContent = open ? 'Close' : 'Menu';
    panel.classList.toggle('is-open', open);
    picker.open = open; // Make all three tools immediately discoverable on mobile.
  });
  document.addEventListener('click', (event) => {
    if (!nav.contains(event.target)) closeNavigation();
    else if (event.target.closest('.nav-panel a')) closeNavigation();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    if (mobile.matches && panel.classList.contains('is-open')) {
      closeNavigation(true);
      event.preventDefault();
    } else if (picker.open) {
      picker.open = false;
      picker.querySelector('summary').focus();
      event.preventDefault();
    }
  });
  nav.addEventListener('focusout', () => {
    requestAnimationFrame(() => {
      if (!nav.contains(document.activeElement)) closeNavigation();
    });
  });
  mobile.addEventListener('change', () => closeNavigation(panel.contains(document.activeElement)));
  toggle.hidden = false;
  nav.classList.add('nav-ready');
})();
