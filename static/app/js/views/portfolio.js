import { api, state, toast, navigate } from '../core.js';

export async function renderPortfolio(container, portfolioId) {
  container.innerHTML = `<div class="loading-bar" style="margin-bottom:2rem"></div>`;

  let portfolio, summary;
  try {
    [portfolio, summary] = await Promise.all([
      api('GET', `/portfolios/${portfolioId}`),
      api('GET', `/portfolios/${portfolioId}/summary`).catch(() => null),
    ]);
  } catch (err) {
    container.innerHTML = `<div class="msg-error">Portföy yüklenemedi: ${err.message}</div>`;
    return;
  }

  const realized   = parseFloat(summary?.realized_pnl   ?? 0);
  const unrealized = parseFloat(summary?.unrealized_pnl ?? 0);
  const total      = parseFloat(summary?.total_pnl      ?? 0);

  const pnlClass = v => v > 0 ? 'positive' : v < 0 ? 'negative' : '';
  const fmt = v => (v >= 0 ? '+' : '') + v.toFixed(2);

  const positions = summary?.positions || portfolio.positions || [];
  const active = positions.filter(p => parseFloat(p.quantity) > 0);

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">${escHtml(portfolio.name)}</h1>
        <p class="page-sub">${portfolio.currency} · ${active.length} açık pozisyon</p>
      </div>
      <button class="btn-primary" id="open-trade-btn">+ İşlem Ekle</button>
    </div>

    <div class="metric-grid">
      <div class="metric-card ${pnlClass(realized)}">
        <div class="metric-label">Gerçekleşen P&L</div>
        <div class="metric-value ${pnlClass(realized)}">${fmt(realized)}</div>
      </div>
      <div class="metric-card ${pnlClass(unrealized)}">
        <div class="metric-label">Gerçekleşmemiş P&L</div>
        <div class="metric-value ${pnlClass(unrealized)}">${fmt(unrealized)}</div>
      </div>
      <div class="metric-card ${pnlClass(total)}">
        <div class="metric-label">Toplam P&L</div>
        <div class="metric-value ${pnlClass(total)}">${fmt(total)}</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">Pozisyonlar</div>
        <button class="btn-secondary" id="refresh-btn" style="padding:.3rem .7rem;font-size:.78rem">↻ Yenile</button>
      </div>
      <div class="table-wrap">
        ${active.length ? `
          <table>
            <thead>
              <tr>
                <th>Hisse</th>
                <th>Adet</th>
                <th>Ort. Maliyet</th>
                ${summary ? '<th>Piyasa Fiyatı</th><th>Gerc. P&L</th><th>Gerc.Memiş P&L</th>' : '<th>Gerc. P&L</th>'}
              </tr>
            </thead>
            <tbody>
              ${active.map(p => {
                const unr = parseFloat(p.unrealized_pnl ?? 0);
                const rpnl = parseFloat(p.realized_pnl ?? 0);
                return `
                  <tr>
                    <td><span class="text-mono">${escHtml(p.ticker)}</span></td>
                    <td>${parseFloat(p.quantity)}</td>
                    <td>${parseFloat(p.average_cost).toFixed(2)}</td>
                    ${summary ? `
                      <td>${parseFloat(p.current_price ?? 0).toFixed(2)}</td>
                      <td class="${pnlClass(rpnl)}">${fmt(rpnl)}</td>
                      <td class="${pnlClass(unr)}">${fmt(unr)}</td>
                    ` : `<td class="${pnlClass(rpnl)}">${fmt(rpnl)}</td>`}
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        ` : `
          <div class="empty-state" style="padding:2rem">
            <div class="empty-icon">◈</div>
            <div class="empty-title">Açık pozisyon yok</div>
            <div class="empty-sub">Yukarıdaki butonu kullanarak ilk işleminizi ekleyin</div>
          </div>
        `}
      </div>
    </div>

    <div class="card">
      <div class="card-title">Hızlı Erişim</div>
      <div class="flex-row" style="flex-wrap:wrap">
        <button class="btn-secondary" id="go-signals">⚡ Sinyal Analizi</button>
        <button class="btn-secondary" id="go-history">≡ İşlem Geçmişi</button>
        <button class="btn-secondary" id="go-connect">✦ Telegram</button>
      </div>
    </div>
  `;

  document.getElementById('open-trade-btn')?.addEventListener('click', () => openTradeModal(portfolioId, container));
  document.getElementById('refresh-btn')?.addEventListener('click', () => renderPortfolio(container, portfolioId));
  document.getElementById('go-signals')?.addEventListener('click', () => navigate('signals', portfolioId));
  document.getElementById('go-history')?.addEventListener('click', () => navigate('history', portfolioId));
  document.getElementById('go-connect')?.addEventListener('click', () => navigate('connect', portfolioId));
}

function openTradeModal(portfolioId, container) {
  const modal = document.getElementById('trade-modal');
  if (!modal) return;
  modal.hidden = false;
  document.getElementById('t-ticker').value = '';
  document.getElementById('t-qty').value = '';
  document.getElementById('t-price').value = '';
  document.getElementById('t-comm').value = '0';

  // Wire submit for this specific portfolio
  const form = document.getElementById('trade-form');
  const newForm = form.cloneNode(true);
  form.parentNode.replaceChild(newForm, form);

  // Re-wire toggle buttons
  newForm.querySelectorAll('.toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      newForm.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('t-type').value = btn.dataset.type;
    });
  });

  const errEl = newForm.querySelector('#trade-err');
  newForm.addEventListener('submit', async e => {
    e.preventDefault();
    errEl.hidden = true;
    const ticker   = document.getElementById('t-ticker').value.trim().toUpperCase();
    const tradeType = document.getElementById('t-type').value;
    const quantity = document.getElementById('t-qty').value;
    const price    = document.getElementById('t-price').value;
    const commission = document.getElementById('t-comm').value || '0';
    if (!ticker || !quantity || !price) return;
    try {
      await api('POST', `/portfolios/${portfolioId}/trades`, { ticker, trade_type: tradeType, quantity, price, commission });
      modal.hidden = true;
      toast(`${tradeType === 'BUY' ? '🟢 Alım' : '🔴 Satım'} işlemi kaydedildi: ${ticker}`);
      await renderPortfolio(container, portfolioId);
    } catch (err) {
      errEl.textContent = err.message;
      errEl.hidden = false;
    }
  });
}

function escHtml(str) {
  return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
