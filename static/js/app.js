/* Placement Cell — small interface helpers. No framework, no build step. */
document.addEventListener('DOMContentLoaded', function () {
  var css = getComputedStyle(document.documentElement);
  var ink = css.getPropertyValue('--ink').trim() || '#15233f';
  var muted = css.getPropertyValue('--muted').trim() || '#5b6476';

  // Chart.js defaults that match the interface
  if (typeof Chart !== 'undefined') {
    Chart.defaults.color = muted;
    Chart.defaults.font.family = "'Public Sans', system-ui, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.plugins.legend.labels.boxWidth = 10;
    Chart.defaults.plugins.legend.labels.boxHeight = 10;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.tooltip.backgroundColor = ink;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.elements.bar.borderRadius = 4;
    if (Chart.defaults.scale) {
      Chart.defaults.scale.grid.color = 'rgba(21,35,63,0.06)';
      Chart.defaults.scale.border = { display: false };
    }
  }

  // Mobile sidebar drawer
  var toggle = document.getElementById('sidebarToggleBtn');
  var sidebar = document.querySelector('.dashboard-sidebar');
  if (toggle && sidebar) {
    var backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop d-none';
    document.body.appendChild(backdrop);

    var close = function () {
      sidebar.classList.remove('mobile-open');
      backdrop.classList.add('d-none');
      document.body.style.overflow = '';
      toggle.setAttribute('aria-expanded', 'false');
    };
    var open = function () {
      sidebar.classList.add('mobile-open');
      backdrop.classList.remove('d-none');
      document.body.style.overflow = 'hidden';
      toggle.setAttribute('aria-expanded', 'true');
    };
    toggle.setAttribute('aria-expanded', 'false');
    toggle.addEventListener('click', function () {
      sidebar.classList.contains('mobile-open') ? close() : open();
    });
    backdrop.addEventListener('click', close);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
  }

  // Success and info messages fade on their own; errors stay until dismissed.
  document.querySelectorAll('.alert-success.alert-dismissible, .alert-info.alert-dismissible').forEach(function (el) {
    setTimeout(function () {
      if (window.bootstrap && bootstrap.Alert) bootstrap.Alert.getOrCreateInstance(el).close();
    }, 6000);
  });

  // Quick client-side filter for tables: <input data-tpms-table-search="tableId">
  document.querySelectorAll('[data-tpms-table-search]').forEach(function (input) {
    var table = document.getElementById(input.getAttribute('data-tpms-table-search'));
    if (!table) return;
    input.addEventListener('input', function () {
      var q = this.value.toLowerCase();
      table.querySelectorAll('tbody tr').forEach(function (row) {
        row.style.display = row.textContent.toLowerCase().indexOf(q) > -1 ? '' : 'none';
      });
    });
  });

  // File inputs inside .file-drop-area: show chosen file name, support drag and drop
  document.querySelectorAll('.file-drop-area').forEach(function (area) {
    var input = area.querySelector('input[type="file"]');
    var label = area.querySelector('.file-name-preview');
    if (!input) return;
    var show = function () {
      if (label && input.files && input.files.length) {
        label.textContent = input.files[0].name;
        label.classList.remove('text-muted');
        label.classList.add('fw-semibold', 'text-dark');
      }
    };
    input.addEventListener('change', show);
    ['dragenter', 'dragover'].forEach(function (ev) {
      area.addEventListener(ev, function (e) { e.preventDefault(); area.classList.add('is-dragging'); });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      area.addEventListener(ev, function (e) { e.preventDefault(); area.classList.remove('is-dragging'); });
    });
    area.addEventListener('drop', function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) { input.files = e.dataTransfer.files; show(); }
    });
  });

  // Confirm before destructive submits: <form data-confirm="Delete this?">
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!window.confirm(form.getAttribute('data-confirm'))) e.preventDefault();
    });
  });
});
