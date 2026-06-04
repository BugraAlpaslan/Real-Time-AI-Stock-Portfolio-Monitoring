import { api, state, toast, navigate } from '../core.js';

export async function renderDashboard(container) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Portföyler</h1>
        <p class="page-sub">Tüm portföylerinizi buradan yönetin</p>
      </div>
      <button class="btn-primary" id="dash-new-btn">+ Yeni Portföy</button>
    </div>
    <div id="dash-portfolio-grid" class="portfolio-grid">
      <div class="skeleton" style="height:88px;border-radius:12px"></div>
      <div class="skeleton" style="height:88px;border-radius:12px"></div>
      <div class="skeleton" style="height:88px;border-radius:12px"></div>
    </div>
  `;

  document.getElementById('dash-new-btn')
    ?.addEventListener('click', () => openNewPortfolioModal());

  await refreshDashboard(container);
}

async function refreshDashboard(container) {
  const grid = document.getElementById('dash-portfolio-grid');
  if (!grid) return;

  // Backend'den gerçek listeyi çek (cache'e bağlı değil)
  await state.syncPortfolios();

  // Her portföyün pozisyon detayını al
  const verified = [];
  for (const p of state.portfolios) {
    try {
      const data = await api('GET', `/portfolios/${p.id}`);
      verified.push({ id: data.id, name: data.name, currency: data.currency, positions: data.positions || [] });
    } catch { /* stale */ }
  }

  if (!verified.length) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="empty-icon">◈</div>
        <div class="empty-title">Henüz portföy yok</div>
        <div class="empty-sub">Sağ üstteki "Yeni Portföy" butonu ile başlayın</div>
      </div>
    `;
    return;
  }

  grid.innerHTML = verified.map(p => {
    const activeCount = p.positions.filter(x => parseFloat(x.quantity) > 0).length;
    return `
      <div class="portfolio-card" data-id="${p.id}">
        <div class="pc-name">${escHtml(p.name)}</div>
        <div style="margin-top:.35rem; display:flex; gap:.5rem; align-items:center;">
          <span class="pc-currency">${p.currency}</span>
          ${activeCount ? `<span class="badge badge-blue">${activeCount} pozisyon</span>` : ''}
        </div>
        <span class="pc-arrow">›</span>
      </div>
    `;
  }).join('');

  grid.querySelectorAll('.portfolio-card').forEach(card => {
    card.addEventListener('click', () => {
      navigate('overview', parseInt(card.dataset.id));
    });
  });
}

function openNewPortfolioModal() {
  const modal = document.getElementById('new-portfolio-modal');
  if (modal) modal.hidden = false;
}

function escHtml(str) {
  return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
