import { auth, state, toast, initRouter, navigate, renderSidebar } from './core.js';
import { renderDashboard } from './views/dashboard.js';
import { renderPortfolio } from './views/portfolio.js';
import { renderSignals }   from './views/signals.js';
import { renderHistory }   from './views/history.js';
import { renderConnect }   from './views/connect.js';

// ── Boot ─────────────────────────────────────────────────
function boot() {
  if (!auth.isLoggedIn()) {
    showLogin();
    return;
  }
  showApp();
}

// ── Login ─────────────────────────────────────────────────
function showLogin() {
  document.getElementById('login-screen').hidden = false;
  document.getElementById('shell').hidden = true;

  document.getElementById('login-form').addEventListener('submit', e => {
    e.preventDefault();
    const user = document.getElementById('l-user').value.trim();
    const pass = document.getElementById('l-pass').value;
    const errEl = document.getElementById('login-err');
    if (auth.login(user, pass)) {
      showApp();
    } else {
      errEl.textContent = 'Kullanıcı adı veya şifre hatalı.';
      errEl.hidden = false;
    }
  });
}

// ── App shell ─────────────────────────────────────────────
async function showApp() {
  document.getElementById('login-screen').hidden = true;
  document.getElementById('shell').hidden = false;

  // Router
  initRouter(dispatchView);

  // Sidebar logout
  document.getElementById('btn-logout')?.addEventListener('click', () => auth.logout());

  // Sub-nav links
  document.querySelectorAll('.sb-link[data-view]').forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      navigate(el.dataset.view, state.currentId);
    });
  });

  // New portfolio modal
  document.getElementById('btn-new-portfolio')?.addEventListener('click', () => {
    document.getElementById('new-portfolio-modal').hidden = false;
  });
  document.getElementById('close-np-modal')?.addEventListener('click', () => {
    document.getElementById('new-portfolio-modal').hidden = true;
  });
  document.getElementById('close-trade-modal')?.addEventListener('click', () => {
    document.getElementById('trade-modal').hidden = true;
  });

  // Close modals on overlay click
  ['new-portfolio-modal', 'trade-modal'].forEach(id => {
    const el = document.getElementById(id);
    el?.addEventListener('click', e => { if (e.target === el) el.hidden = true; });
  });

  // New portfolio form
  document.getElementById('np-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const name = document.getElementById('np-name').value.trim();
    const currency = document.getElementById('np-currency').value;
    const errEl = document.getElementById('np-err');
    errEl.hidden = true;
    if (!name) return;
    try {
      const { api } = await import('./core.js');
      const p = await api('POST', '/portfolios', { name, currency });
      state.savePortfolio(p.id, p.name, p.currency);
      document.getElementById('new-portfolio-modal').hidden = true;
      document.getElementById('np-form').reset();
      toast(`"${p.name}" portföyü oluşturuldu`);
      navigate('overview', p.id);
    } catch (err) {
      errEl.textContent = err.message;
      errEl.hidden = false;
    }
  });

  // Initial render — önce backend'den portföyleri senkronize et
  state.loadPortfolios();
  await renderSidebar();
  navigate('dashboard');
}

// ── View dispatcher ───────────────────────────────────────
function dispatchView(view, portfolioId) {
  const container = document.getElementById('view');
  if (!container) return;

  // Re-trigger animation
  container.style.animation = 'none';
  container.offsetHeight; // reflow
  container.style.animation = '';

  switch (view) {
    case 'dashboard': return renderDashboard(container);
    case 'overview':  return renderPortfolio(container, portfolioId);
    case 'signals':   return renderSignals(container, portfolioId);
    case 'history':   return renderHistory(container, portfolioId);
    case 'connect':   return renderConnect(container, portfolioId);
    default:          return renderDashboard(container);
  }
}

// ── Start ─────────────────────────────────────────────────
boot();
