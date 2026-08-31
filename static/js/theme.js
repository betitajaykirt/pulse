/* PULSE theme — light/dark toggle with persisted preference. */
(function () {
  var STORAGE_KEY = 'pulse-theme';

  function readStored() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      return null;
    }
  }

  function preferredTheme() {
    var stored = readStored();
    if (stored === 'dark' || stored === 'light') return stored;
    try {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    } catch (err) {
      return 'light';
    }
  }

  function persist(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (err) {
      /* private mode / blocked storage */
    }
  }

  function chartColors(theme) {
    var dark = theme === 'dark';
    return {
      tick: dark ? '#94A3B8' : '#64748B',
      grid: dark ? 'rgba(148, 163, 184, 0.14)' : 'rgba(241, 245, 249, 0.9)',
      emptyBg: dark ? 'rgba(30, 41, 59, 0.55)' : 'rgba(241, 245, 249, 0.4)',
    };
  }

  function applyChartTheme(theme) {
    if (!window.Chart) return;
    var colors = chartColors(theme);
    Chart.defaults.color = colors.tick;
    Chart.defaults.borderColor = colors.grid;
    document.querySelectorAll('canvas').forEach(function (canvas) {
      var chart = Chart.getChart(canvas);
      if (!chart || !chart.options) return;
      var scales = chart.options.scales || {};
      Object.keys(scales).forEach(function (axis) {
        var scale = scales[axis] || {};
        if (scale.ticks) scale.ticks.color = colors.tick;
        if (scale.grid && scale.grid.display !== false) {
          scale.grid.color = colors.grid;
        }
        if (scale.title) scale.title.color = colors.tick;
      });
      var legend = chart.options.plugins && chart.options.plugins.legend;
      if (legend && legend.labels) legend.labels.color = colors.tick;
      chart.update('none');
    });
  }

  function syncToggleButtons(theme) {
    var next = theme === 'dark' ? 'light' : 'dark';
    var label = 'Switch to ' + next + ' mode';
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
      btn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    });
  }

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.style.colorScheme = theme;
    syncToggleButtons(theme);
    applyChartTheme(theme);
    document.dispatchEvent(new CustomEvent('pulse-theme-change', { detail: { theme: theme } }));
  }

  function setTheme(theme) {
    var next = theme === 'dark' ? 'dark' : 'light';
    persist(next);
    apply(next);
  }

  window.PulseTheme = {
    get: preferredTheme,
    set: setTheme,
    toggle: function () {
      setTheme(preferredTheme() === 'dark' ? 'light' : 'dark');
    },
    chartColors: function () {
      return chartColors(preferredTheme());
    },
  };

  apply(preferredTheme());

  document.addEventListener('click', function (event) {
    var btn = event.target.closest('[data-theme-toggle]');
    if (!btn) return;
    event.preventDefault();
    window.PulseTheme.toggle();
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  });

  document.addEventListener('DOMContentLoaded', function () {
    apply(preferredTheme());
    window.setTimeout(function () {
      applyChartTheme(preferredTheme());
    }, 400);
  });
})();
