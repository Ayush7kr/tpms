/**
 * TPMS — Frontend Interactive Helpers
 * Mobile Sidebar Drawer, Chart.js Defaults, Toast auto-dismissal, live search, drag-and-drop
 */

document.addEventListener('DOMContentLoaded', function () {
  // Clear any legacy dark-mode storage so presentation remains consistently default
  try {
    localStorage.removeItem('tpms-theme');
    document.documentElement.removeAttribute('data-theme');
  } catch (e) {}

  // Global Chart.js Configuration
  if (typeof Chart !== 'undefined') {
    Chart.defaults.color = '#64748b';
    Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    if (Chart.defaults.scale) {
      if (Chart.defaults.scale.ticks) Chart.defaults.scale.ticks.color = '#64748b';
      if (Chart.defaults.scale.grid) Chart.defaults.scale.grid.color = 'rgba(0, 0, 0, 0.06)';
    }
  }

  // Mobile Sidebar Toggle
  const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
  const sidebar = document.querySelector('.dashboard-sidebar');
  let backdrop = document.getElementById('sidebarBackdrop');

  if (sidebar && !backdrop) {
    backdrop = document.createElement('div');
    backdrop.id = 'sidebarBackdrop';
    backdrop.className = 'sidebar-backdrop d-none';
    document.body.appendChild(backdrop);
  }

  function closeMobileSidebar() {
    if (sidebar) sidebar.classList.remove('mobile-open');
    if (backdrop) backdrop.classList.add('d-none');
    document.body.style.overflow = '';
  }

  function openMobileSidebar() {
    if (sidebar) sidebar.classList.add('mobile-open');
    if (backdrop) backdrop.classList.remove('d-none');
    document.body.style.overflow = 'hidden';
  }

  if (sidebarToggleBtn && sidebar) {
    sidebarToggleBtn.addEventListener('click', function (e) {
      e.preventDefault();
      if (sidebar.classList.contains('mobile-open')) {
        closeMobileSidebar();
      } else {
        openMobileSidebar();
      }
    });
  }

  if (backdrop) {
    backdrop.addEventListener('click', closeMobileSidebar);
  }

  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        if (bsAlert) {
          bsAlert.close();
        }
      }
    }, 5000);
  });

  // Client-side quick table search
  const searchInputs = document.querySelectorAll('[data-tpms-table-search]');
  searchInputs.forEach(function (input) {
    const targetTableId = input.getAttribute('data-tpms-table-search');
    const table = document.getElementById(targetTableId);
    if (!table) return;

    input.addEventListener('keyup', function () {
      const query = this.value.toLowerCase();
      const rows = table.querySelectorAll('tbody tr');

      rows.forEach(function (row) {
        const text = row.textContent.toLowerCase();
        if (text.includes(query)) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  });

  // Drag and drop file upload preview
  const fileDropAreas = document.querySelectorAll('.file-drop-area');
  fileDropAreas.forEach(function (area) {
    const input = area.querySelector('input[type="file"]');
    const label = area.querySelector('.file-name-preview');

    if (input && label) {
      input.addEventListener('change', function () {
        if (input.files && input.files.length > 0) {
          label.textContent = input.files[0].name;
          label.classList.remove('text-muted');
          label.classList.add('text-success', 'fw-bold');
        }
      });
    }
  });
});
