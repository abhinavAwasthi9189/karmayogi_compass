// Karmayogi Compass — shared front-end behavior.
// Pure vanilla JS. Every dynamic value is read from a data-* attribute,
// which page-specific scripts (dashboard.js, passport.js, path.js, ...)
// fill in from real API responses before calling these.

document.addEventListener('DOMContentLoaded', () => {
  initGauges();
  initBars();
});

/* ---------- Circular score gauges ---------- */
function initGauges () {
  document.querySelectorAll('.gauge').forEach((el) => {
    const value = parseFloat(el.dataset.value || '0');
    const max = parseFloat(el.dataset.max || '100');
    const r = 54;
    const circumference = 2 * Math.PI * r;
    const pct = Math.max(0, Math.min(1, value / max));
    const offset = circumference * (1 - pct);
    const valueCircle = el.querySelector('.gauge-value');
    if (valueCircle) {
      valueCircle.style.strokeDasharray = `${circumference}`;
      valueCircle.style.strokeDashoffset = `${circumference}`;
      if (pct < 0.5) valueCircle.style.stroke = 'var(--red)';
      else if (pct < 0.75) valueCircle.style.stroke = 'var(--gold)';
      else valueCircle.style.stroke = 'var(--green)';
      requestAnimationFrame(() => {
        valueCircle.style.strokeDashoffset = `${offset}`;
      });
    }
  });
}

/* ---------- Competency / progress bars ---------- */
function initBars () {
  document.querySelectorAll('.bar-fill[data-target]').forEach((el) => {
    const target = el.dataset.target;
    requestAnimationFrame(() => { el.style.width = target + '%'; });
  });
}
