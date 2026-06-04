import { api } from '../core.js';

export async function renderHistory(container, portfolioId) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">İşlem Geçmişi</h1>
        <p class="page-sub">Tüm alım-satım kayıtları</p>
      </div>
    </div>
    <div class="card" style="margin-bottom:.75rem">
      <div style="display:flex;gap:.6rem;align-items:flex-end">
        <div class="field-group" style="flex:1;margin:0">
          <label for="hist-filter">Hisseye Göre Filtrele</label>
          <input id="hist-filter" placeholder="AAPL" style="text-transform:uppercase" />
        </div>
        <button class="btn-primary" id="hist-search-btn" style="height:38px;padding:0 1rem">Ara</button>
        <button class="btn-ghost" id="hist-clear-btn" style="height:38px;padding:0 .85rem">Temizle</button>
      </div>
    </div>
    <div class="card">
      <div id="hist-table-wrap" class="table-wrap">
        <div class="loading-bar"></div>
      </div>
    </div>
  `;

  const filterInput = document.getElementById('hist-filter');
  document.getElementById('hist-search-btn')?.addEventListener('click', () => loadTrades(filterInput.value.trim().toUpperCase()));
  document.getElementById('hist-clear-btn')?.addEventListener('click', () => { filterInput.value = ''; loadTrades(); });
  filterInput.addEventListener('keydown', e => { if (e.key === 'Enter') loadTrades(filterInput.value.trim().toUpperCase()); });

  await loadTrades();

  async function loadTrades(ticker = '') {
    const wrap = document.getElementById('hist-table-wrap');
    if (!wrap) return;
    wrap.innerHTML = '<div class="loading-bar"></div>';
    try {
      const params = ticker ? `?ticker=${encodeURIComponent(ticker)}&limit=200` : '?limit=200';
      const trades = await api('GET', `/portfolios/${portfolioId}/trades${params}`);
      if (!trades.length) {
        wrap.innerHTML = `<div class="empty-state" style="padding:2rem">
          <div class="empty-icon">≡</div>
          <div class="empty-title">İşlem bulunamadı</div>
          <div class="empty-sub">${ticker ? `"${ticker}" için kayıt yok` : 'Henüz hiç işlem eklenmedi'}</div>
        </div>`;
        return;
      }
      wrap.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Tarih</th>
              <th>Hisse</th>
              <th>Tip</th>
              <th>Adet</th>
              <th>Fiyat</th>
              <th>Komisyon</th>
            </tr>
          </thead>
          <tbody>
            ${trades.map(t => {
              const date = new Date(t.executed_at).toLocaleDateString('tr-TR', { day:'2-digit', month:'short', year:'numeric' });
              const isBuy = t.trade_type === 'BUY';
              return `
                <tr>
                  <td class="text-muted" style="font-size:.8rem">${date}</td>
                  <td><span class="text-mono">${escHtml(t.ticker)}</span></td>
                  <td><span class="badge ${isBuy ? 'badge-buy' : 'badge-sell'}">${isBuy ? 'AL' : 'SAT'}</span></td>
                  <td>${parseFloat(t.quantity)}</td>
                  <td>${parseFloat(t.price).toFixed(2)}</td>
                  <td class="text-muted">${parseFloat(t.commission ?? 0).toFixed(2)}</td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      `;
    } catch (err) {
      wrap.innerHTML = `<div class="msg-error" style="margin:0">Yüklenemedi: ${err.message}</div>`;
    }
  }
}

function escHtml(str) {
  return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
