/* ═══════════════════════════════════════════════════════
   core.js — API · Auth · State · Router · Toast
   ═══════════════════════════════════════════════════════ */

// ── API ──────────────────────────────────────────────────
export async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const err = await res.json();
      msg = err.detail || msg;
      if (typeof msg === 'object') msg = JSON.stringify(msg);
    } catch { /* ignore */ }
    const e = new Error(msg);
    e.status = res.status;
    throw e;
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Auth ─────────────────────────────────────────────────
const AUTH_KEY = 'rtsm_auth';
const CREDS = { username: 'admin', password: 'admin' };

export const auth = {
  isLoggedIn: () => !!localStorage.getItem(AUTH_KEY),
  login(user, pass) {
    if (user === CREDS.username && pass === CREDS.password) {
      localStorage.setItem(AUTH_KEY, JSON.stringify({ user }));
      return true;
    }
    return false;
  },
  logout() {
    localStorage.removeItem(AUTH_KEY);
    location.reload();
  },
  getUser() {
    const d = localStorage.getItem(AUTH_KEY);
    return d ? JSON.parse(d).user : null;
  },
};

// ── State ─────────────────────────────────────────────────
const PORTFOLIOS_KEY = 'rtsm_portfolios';

export const state = {
  portfolios: [],
  currentId: null,
  currentView: 'dashboard',

  // localStorage'dan hızlı senkron okuma (ilk render için)
  loadPortfolios() {
    try { this.portfolios = JSON.parse(localStorage.getItem(PORTFOLIOS_KEY) || '[]'); }
    catch { this.portfolios = []; }
    return this.portfolios;
  },

  // Backend'den gerçek listeyi çeker — cache temizlense bile portföyler kaybolmaz
  async syncPortfolios() {
    try {
      const data = await api('GET', '/portfolios');
      this.portfolios = data.map(p => ({ id: p.id, name: p.name, currency: p.currency }));
      localStorage.setItem(PORTFOLIOS_KEY, JSON.stringify(this.portfolios));
    } catch {
      // backend erişilemezse localStorage'a düş
      this.loadPortfolios();
    }
    return this.portfolios;
  },

  savePortfolio(id, name, currency = 'USD') {
    this.portfolios = this.portfolios.filter(p => p.id !== id);
    this.portfolios.unshift({ id, name, currency });
    localStorage.setItem(PORTFOLIOS_KEY, JSON.stringify(this.portfolios));
  },
  removePortfolio(id) {
    this.portfolios = this.portfolios.filter(p => p.id !== id);
    localStorage.setItem(PORTFOLIOS_KEY, JSON.stringify(this.portfolios));
  },
};

// ── Toast ─────────────────────────────────────────────────
export function toast(message, type = 'success') {
  const root = document.getElementById('toast-root');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Router / Sidebar ─────────────────────────────────────
let _renderView = null;

export function initRouter(renderView) {
  _renderView = renderView;
}

export function navigate(view, portfolioId = null) {
  if (portfolioId !== null) state.currentId = portfolioId;
  state.currentView = view;
  renderSidebar();
  _renderView(view, state.currentId);
}

export async function renderSidebar() {
  const nav = document.getElementById('portfolio-nav');
  const subSection = document.getElementById('sub-nav-section');
  const subLabel = document.getElementById('sub-nav-label');
  const sbUser = document.getElementById('sb-user');
  if (sbUser) sbUser.textContent = auth.getUser() || '';

  // Önce localStorage ile hızlı çiz, sonra backend'den senkronize et
  state.loadPortfolios();
  await state.syncPortfolios();
  if (!nav) return;
  nav.innerHTML = '';
  if (!state.portfolios.length) {
    nav.innerHTML = '<div class="sb-empty">Portföy yok</div>';
  } else {
    state.portfolios.forEach(p => {
      const a = document.createElement('div');
      a.className = 'portfolio-nav-item' + (p.id === state.currentId ? ' active' : '');
      a.innerHTML = `<span class="portfolio-nav-dot"></span>${p.name}`;
      a.onclick = () => navigate('overview', p.id);
      nav.appendChild(a);
    });
  }

  // Sub-nav (when a portfolio is selected)
  if (state.currentId) {
    const p = state.portfolios.find(x => x.id === state.currentId);
    if (p && subLabel) subLabel.textContent = p.name;
    if (subSection) subSection.hidden = false;
    // Mark active sub-nav link
    document.querySelectorAll('.sb-link').forEach(el => {
      const v = el.dataset.view;
      el.classList.toggle('active', v === state.currentView);
    });
  } else {
    if (subSection) subSection.hidden = true;
  }
}
