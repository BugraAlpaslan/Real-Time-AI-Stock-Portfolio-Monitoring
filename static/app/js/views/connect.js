import { api, toast } from '../core.js';

export async function renderConnect(container, portfolioId) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Telegram Bağlantısı</h1>
        <p class="page-sub">Sinyal bildirimleri doğrudan Telegram'ınıza gelsin</p>
      </div>
    </div>
    <div id="connect-status-area">
      <div class="loading-bar"></div>
    </div>
  `;

  await loadStatus();

  async function loadStatus() {
    const area = document.getElementById('connect-status-area');
    if (!area) return;
    try {
      const status = await api('GET', `/portfolios/${portfolioId}/telegram/status`);
      renderStatusUI(area, status.linked, status.chat_id);
    } catch {
      renderStatusUI(area, false, null);
    }
  }

  function renderStatusUI(area, linked, chatId) {
    area.innerHTML = `
      <!-- Mevcut durum -->
      <div class="card" style="margin-bottom:.75rem">
        <div class="card-title">Bağlantı Durumu</div>
        <div class="tg-status ${linked ? 'linked' : 'unlinked'}">
          ${linked
            ? `✓ Bağlı — Chat ID: <strong style="font-family:monospace;margin-left:.3rem">${chatId}</strong>`
            : '○ Henüz bağlı değil'}
        </div>
        ${linked ? `
          <div class="flex-row" style="margin-top:1rem">
            <button class="btn-danger" id="unlink-btn">Bağlantıyı Kes</button>
          </div>
        ` : ''}
      </div>

      <!-- Wizard (sadece bağlı değilse) -->
      ${!linked ? `
        <div class="card">
          <div class="card-title">Nasıl Bağlanılır?</div>
          <div class="wizard">

            <div class="wizard-step done" id="ws-1">
              <div class="step-num done">✓</div>
              <div class="step-body">
                <div class="step-title">@rtsm_notify_bot'u açın</div>
                <div class="step-desc">Telegram'da <strong>@rtsm_notify_bot</strong>'u aratın veya
                  <a href="https://t.me/rtsm_notify_bot" target="_blank" rel="noopener">bu linke tıklayın</a>.
                </div>
              </div>
            </div>

            <div class="wizard-step active" id="ws-2">
              <div class="step-num active">2</div>
              <div class="step-body">
                <div class="step-title">Bağlantı linkini oluşturun</div>
                <div class="step-desc" style="margin-bottom:.75rem">
                  Aşağıdaki butona basın, Telegram'da açılan ekranda <strong>Başlat</strong>'a tıklayın.
                  Bağlantı otomatik tamamlanır.
                </div>
                <button class="btn-primary" id="gen-link-btn">🔗 Bağlantı Linki Oluştur</button>
                <div id="link-result" style="margin-top:.75rem"></div>
              </div>
            </div>

            <div class="wizard-step" id="ws-3">
              <div class="step-num">3</div>
              <div class="step-body">
                <div class="step-title">Bitti — bildirimler aktif!</div>
                <div class="step-desc">
                  Bundan sonra sinyal skoru ±2 eşiğini aştığında Telegram'ınıza otomatik mesaj gelecek.
                </div>
              </div>
            </div>

          </div>
        </div>
      ` : `
        <!-- Bağlıyken test paneli -->
        <div class="card">
          <div class="card-title">Bildirim Önizleme</div>
          <p class="text-muted" style="font-size:.83rem;margin-bottom:1rem">
            Sinyal skoru ±2 eşiğini geçtiğinde Telegram'ınıza şu formatta mesaj gönderilir:
          </p>
          <div style="background:var(--s2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:1rem;font-size:.82rem;line-height:1.8">
            📊 <strong>AAPL — 🟢 ALIM SİNYALİ</strong><br>
            Toplam Skor: <strong>+3/4</strong> | Son Kapanış: <strong>213.70</strong><br><br>
            <strong>Tetiklenme Sebebi:</strong><br>
            🟢 RSI → ALIM sinyali (RSI değeri: 28.4)<br>
            🟢 MACD → ALIM sinyali (kesişim yukarı)<br>
            ⚪ Bollinger → Nötr<br>
            🟢 Stochastic → ALIM sinyali<br><br>
            <strong>Gemini Analizi:</strong><br>
            <em>AAPL hissesi RSI 28.4 ile aşırı satım bölgesine girmiş…</em>
          </div>
        </div>
      `}
    `;

    // Unlink
    document.getElementById('unlink-btn')?.addEventListener('click', async () => {
      if (!confirm('Telegram bağlantısını kesmek istediğinize emin misiniz?')) return;
      try {
        await api('DELETE', `/portfolios/${portfolioId}/telegram/unlink`);
        toast('Telegram bağlantısı kesildi', 'info');
        await loadStatus();
      } catch (err) {
        toast(`Hata: ${err.message}`, 'error');
      }
    });

    // Generate link
    document.getElementById('gen-link-btn')?.addEventListener('click', async () => {
      const btn = document.getElementById('gen-link-btn');
      const resultEl = document.getElementById('link-result');
      btn.disabled = true;
      btn.textContent = '⏳ Oluşturuluyor…';
      try {
        const res = await api('POST', `/portfolios/${portfolioId}/telegram/link`);
        resultEl.innerHTML = `
          <div style="background:var(--blue-d);border:1px solid rgba(59,130,246,.25);border-radius:var(--radius-sm);padding:.85rem">
            <div style="font-size:.78rem;color:var(--text-2);margin-bottom:.5rem">
              Aşağıdaki linke tıklayın → Telegram açılır → <strong>Başlat</strong>'a basın:
            </div>
            <a href="${res.telegram_url}" target="_blank" rel="noopener"
               class="btn-primary" style="display:inline-flex;margin-bottom:.6rem">
              📱 Telegram'da Aç
            </a>
            <div style="font-size:.75rem;color:var(--text-3)">
              Link tek kullanımlıktır. Bağlantı tamamlanınca bu sayfa otomatik güncellenmez —
              <button onclick="location.reload()" style="background:none;border:none;color:var(--blue);font-size:.75rem;cursor:pointer;padding:0">sayfayı yenileyin</button>.
            </div>
          </div>
        `;
        // Activate step 3 visually
        document.getElementById('ws-2')?.classList.remove('active');
        document.getElementById('ws-3')?.classList.add('active');
      } catch (err) {
        resultEl.innerHTML = `<div class="msg-error" style="margin:0">${err.message}</div>`;
      } finally {
        btn.disabled = false;
        btn.textContent = '🔗 Bağlantı Linki Oluştur';
      }
    });
  }
}
