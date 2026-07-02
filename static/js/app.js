/* PULSE app.js — global UI behaviours */

document.addEventListener('DOMContentLoaded', function () {

  // ── Global navbar toggle (mobile) ──────────────────────────────
  const navbarToggle = document.getElementById('navbar-toggle');
  const navbarMenu   = document.getElementById('navbar-menu');

  if (navbarToggle && navbarMenu) {
    navbarToggle.addEventListener('click', function () {
      const isOpen = navbarMenu.classList.toggle('is-open');
      navbarToggle.classList.toggle('is-open', isOpen);
      navbarToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    navbarMenu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        if (window.innerWidth <= 900) {
          navbarMenu.classList.remove('is-open');
          navbarToggle.classList.remove('is-open');
          navbarToggle.setAttribute('aria-expanded', 'false');
        }
      });
    });

    document.addEventListener('click', function (e) {
      if (!navbarToggle.contains(e.target) && !navbarMenu.contains(e.target)) {
        navbarMenu.classList.remove('is-open');
        navbarToggle.classList.remove('is-open');
        navbarToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ── Sidebar toggle (mobile overlay) ────────────────────────────
  const toggle   = document.getElementById('sidebar-toggle');
  const sidebar  = document.querySelector('.sidebar');

  if (toggle && sidebar) {
    let backdrop = document.querySelector('.sidebar-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.className = 'sidebar-backdrop';
      document.body.appendChild(backdrop);
    }

    function openSidebar() {
      sidebar.classList.add('sidebar-open');
      backdrop.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
    function closeSidebar() {
      sidebar.classList.remove('sidebar-open');
      backdrop.classList.remove('active');
      document.body.style.overflow = '';
    }

    toggle.addEventListener('click', function () {
      sidebar.classList.contains('sidebar-open') ? closeSidebar() : openSidebar();
    });
    backdrop.addEventListener('click', closeSidebar);

    sidebar.querySelectorAll('.nav-item').forEach(function (link) {
      link.addEventListener('click', function () {
        if (window.innerWidth <= 900) closeSidebar();
      });
    });
  }

  // ── Auto-dismiss alerts ─────────────────────────────────────────
  document.querySelectorAll('[data-auto-dismiss]').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 400);
    }, 4000);
  });

  // ── Lucide icons ────────────────────────────────────────────────
  if (window.lucide) {
    lucide.createIcons();
  }

});
