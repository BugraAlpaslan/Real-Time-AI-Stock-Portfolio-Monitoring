import { api, state, toast } from '../core.js';

export function renderSignals(container, portfolioId) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Sinyal Analizi</h1>
        <p class="page-sub">RSI · MACD · Bollinger Bands · Stochastic</p>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Hisse Analizi</div>
      <div class="ticker-row">
        <div class="field-group">
          <label for="sig-ticker">Hisse Sembolü</label>
          <input id="sig-ticker" type="text" placeholder="AAPL, THYAO.IS, BIST:GARAN…"
            maxlength="20" style="text-transform:uppercase" />
        </div>
        <button class="btn-primary" id="sig-analyze-btn" style="height:38px;padding:0 1.25rem">
          Analiz Et
        </button>
      </div>
      <p class="text-muted" style="font-size:.78rem">
        Eşik ≥ ±${state.threshold ?? 2} olduğunda Gemini analizi ve Telegram bildirimi tetiklenir.
      </p>
    </div>

    <div id="sig-result" hidden></div>

    <div id="sig-history-section"></div>
  `;

  const tickerInput = document.getElementById('sig-ticker');
  const analyzeBtn  = document.getElementById('sig-analyze-btn');

  tickerInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') analyze();
  });
  analyzeBtn.addEventListener('click', analyze);

  // Geçmiş analizleri hemen yükle
  loadHistory();

  async function loadHistory() {
    const section = document.getElementById('sig-history-section');
    if (!section) return;
    try {
      const history = await api('GET', `/portfolios/${portfolioId}/signals/history?limit=10`);
      if (!history.length) { section.innerHTML = ''; return; }

      section.innerHTML = `
        <div class="card" style="margin-top:.5rem">
          <div class="card-header">
            <div class="card-title">Geçmiş Analizler</div>
            <span class="text-muted" style="font-size:.75rem">Son 10</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Tarih</th>
                  <th>Hisse</th>
                  <th>Skor</th>
                  <th>Durum</th>
                  <th>Telegram</th>
                  <th>Gemini Özeti</th>
                </tr>
              </thead>
              <tbody>
                ${history.map(h => {
                  const date = new Date(h.analyzed_at).toLocaleDateString('tr-TR', {
                    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                  });
                  const scoreClass = h.total_score > 0 ? 'positive' : h.total_score < 0 ? 'negative' : '';
                  const scoreLabel = h.total_score > 0 ? '🟢' : h.total_score < 0 ? '🔴' : '⚪';
                  const triggered  = h.triggered
                    ? '<span class="badge badge-blue">⚡ Tetiklendi</span>'
                    : '<span style="color:var(--text-3);font-size:.78rem">—</span>';
                  const tg = h.telegram_sent
                    ? '<span class="badge badge-buy">✓</span>'
                    : '<span style="color:var(--text-3);font-size:.78rem">—</span>';
                  // Gemini analizinin ilk cümlesini al
                  const preview = h.gemini_analysis
                    ? h.gemini_analysis.replace(/<[^>]+>/g,'').split('.')[0].slice(0, 80) + '…'
                    : '<span style="color:var(--text-3)">—</span>';
                  return `
                    <tr class="history-row" data-id="${h.id}" style="cursor:pointer">
                      <td class="text-muted" style="font-size:.78rem;white-space:nowrap">${date}</td>
                      <td><span class="text-mono">${h.ticker}</span></td>
                      <td class="${scoreClass}">${scoreLabel} ${h.total_score > 0 ? '+' : ''}${h.total_score}/4</td>
                      <td>${triggered}</td>
                      <td>${tg}</td>
                      <td style="font-size:.78rem;color:var(--text-2);max-width:260px">${preview}</td>
                    </tr>
                    <tr class="history-detail" id="detail-${h.id}" hidden>
                      <td colspan="6" style="padding:.75rem 1rem;background:var(--s2);border-radius:var(--radius-sm)">
                        ${h.gemini_analysis
                          ? `<div style="font-size:.83rem;line-height:1.7;white-space:pre-wrap">${h.gemini_analysis.replace(/<b>/g,'').replace(/<\/b>/g,'').replace(/<i>/g,'').replace(/<\/i>/g,'')}</div>`
                          : '<span style="color:var(--text-3);font-size:.82rem">Bu analiz için Gemini çıktısı yok.</span>'
                        }
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;

      // Satıra tıklayınca detayı aç/kapat
      section.querySelectorAll('.history-row').forEach(row => {
        row.addEventListener('click', () => {
          const detail = document.getElementById(`detail-${row.dataset.id}`);
          if (detail) detail.hidden = !detail.hidden;
        });
      });
    } catch { section.innerHTML = ''; }
  }

  async function analyze() {
    const ticker = tickerInput.value.trim().toUpperCase();
    if (!ticker) { tickerInput.focus(); return; }

    const resultEl = document.getElementById('sig-result');
    resultEl.hidden = false;
    resultEl.innerHTML = `
      <div class="card">
        <div class="loading-bar"></div>
        <div style="display:flex;align-items:center;gap:.6rem;margin-top:1rem;color:var(--text-2);font-size:.85rem">
          <div class="spinner"></div>
          ${ticker} analiz ediliyor — 90 günlük OHLCV indiriliyor…
        </div>
      </div>
    `;

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '⏳ Analiz...';

    try {
      const data = await api('GET', `/portfolios/${portfolioId}/signals?ticker=${encodeURIComponent(ticker)}`);
      renderResult(resultEl, data);
      loadHistory(); // geçmişi güncelle
    } catch (err) {
      resultEl.innerHTML = `
        <div class="card">
          <div class="msg-error" style="margin:0">
            Analiz başarısız: ${err.message}
          </div>
        </div>
      `;
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.textContent = 'Analiz Et';
    }
  }
}

function renderResult(container, data) {
  const { ticker, total_score, triggered, scores, indicators, trigger_reasons, gemini_analysis, telegram_sent } = data;
  const scoreClass = total_score > 0 ? 'buy' : total_score < 0 ? 'sell' : 'neutral';
  const scoreLabel = total_score > 0 ? '🟢 ALIM' : total_score < 0 ? '🔴 SATIM' : '— NÖTR';

  container.innerHTML = `
    <!-- Toplam Skor -->
    <div class="score-total">
      <div>
        <div class="score-number ${scoreClass}">${total_score > 0 ? '+' : ''}${total_score}</div>
        <div class="score-label">/ 4 indikatör · ${scoreLabel}</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:.5rem">
        <div class="score-trigger-badge ${triggered ? 'triggered' : 'not-triggered'}">
          ${triggered ? '⚡ TETİKLENDİ' : '○ BEKLEMEDE'}
        </div>
        ${triggered && telegram_sent
          ? '<div class="badge badge-blue" style="font-size:.72rem">✓ Telegram gönderildi</div>'
          : triggered && !telegram_sent
          ? '<div class="badge" style="background:var(--s3);color:var(--text-3);font-size:.72rem">Telegram bağlı değil</div>'
          : ''}
      </div>
    </div>

    <!-- Sinyal Barları -->
    <div class="card">
      <div class="card-title">İndikatör Skorları</div>
      <div class="signal-grid">
        ${renderBar('RSI', scores.rsi, indicators.rsi_value != null ? `RSI: ${indicators.rsi_value.toFixed(1)}` : null)}
        ${renderBar('MACD', scores.macd)}
        ${renderBar('Bollinger', scores.bollinger)}
        ${renderBar('Stochastic', scores.stochastic)}
      </div>
      <div class="divider"></div>
      <div style="display:flex;align-items:center;justify-content:space-between">
        <span class="text-muted" style="font-size:.78rem">
          Son Kapanış: <strong style="color:var(--text)">
            ${indicators.latest_close != null ? indicators.latest_close.toFixed(2) : '—'}
          </strong>
        </span>
        <span class="text-muted" style="font-size:.78rem">
          ${ticker}
        </span>
      </div>
    </div>

    <!-- Tetiklenme Sebebi -->
    ${trigger_reasons?.length ? `
      <div class="card">
        <div class="card-title">Tetiklenme Sebebi</div>
        <div class="trigger-reasons">
          ${trigger_reasons.map(r => `<div class="trigger-reason">${escHtml(r)}</div>`).join('')}
        </div>
      </div>
    ` : ''}

    <!-- Gemini Analizi -->
    <div id="gemini-panel">
      ${gemini_analysis
        ? `
          <div class="gemini-card">
            <div class="gemini-header">
              <div class="gemini-icon">✦</div>
              <div>
                <div class="gemini-label">Gemini Analizi</div>
              </div>
            </div>
            <div class="gemini-text">${escHtml(gemini_analysis)}</div>
          </div>
        `
        : triggered
        ? `
          <div class="gemini-card">
            <div class="gemini-header">
              <div class="gemini-icon">✦</div>
              <div class="gemini-label">Gemini Analizi</div>
            </div>
            <div class="gemini-loading">
              <div class="spinner"></div>
              Gemini API anahtarı yapılandırılmamış — analiz üretilmedi.
            </div>
          </div>
        `
        : `
          <div class="card" style="border-color:var(--border);background:var(--s1)">
            <div class="text-muted" style="font-size:.82rem">
              ⚡ Sinyal skoru ±2 eşiğini aştığında Gemini analizi burada görünecek.
            </div>
          </div>
        `}
    </div>
  `;

  // Animate bars after paint
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      animateBars(scores);
    });
  });
}

function renderBar(label, score, detail = null) {
  const cls = score > 0 ? 'buy' : score < 0 ? 'sell' : 'neutral';
  const dir = score > 0 ? 'AL' : score < 0 ? 'SAT' : '—';
  const scoreText = score > 0 ? '+1' : score < 0 ? '-1' : '0';

  return `
    <div class="signal-row" data-indicator="${label}">
      <div class="signal-label">${label}${detail ? `<br><span style="font-size:.68rem;font-weight:500;color:var(--text-3)">${detail}</span>` : ''}</div>
      <div class="signal-bar-track">
        <div class="signal-bar-fill ${cls}" data-score="${score}" style="width:0%"></div>
      </div>
      <div class="signal-score-badge ${cls}">${scoreText}</div>
      <div class="signal-direction" style="color:${cls === 'buy' ? 'var(--green)' : cls === 'sell' ? 'var(--red)' : 'var(--text-3)'}">${dir}</div>
    </div>
  `;
}

function animateBars(scores) {
  const map = { RSI: scores.rsi, MACD: scores.macd, Bollinger: scores.bollinger, Stochastic: scores.stochastic };
  document.querySelectorAll('.signal-bar-fill').forEach(fill => {
    const row = fill.closest('.signal-row');
    const label = row?.dataset.indicator;
    const score = map[label] ?? 0;
    // Width: 100% for ±1, 0% for 0
    fill.style.width = score !== 0 ? '100%' : '0%';
  });
}

function escHtml(str) {
  return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
