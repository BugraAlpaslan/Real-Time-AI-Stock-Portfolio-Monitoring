import { api } from "./api.js";
import { fetchPortfolio } from "./portfolios.js";
import { requireAuth, initHeader } from "./auth.js";

requireAuth();

function getPortfolioId() {
  return new URLSearchParams(window.location.search).get("id");
}

function showError(message) {
  const banner = document.querySelector('[data-testid="error-banner"]');
  if (!banner) return;
  banner.textContent = message;
  banner.hidden = false;
}

function hideError() {
  const banner = document.querySelector('[data-testid="error-banner"]');
  if (banner) banner.hidden = true;
}

function renderPositions(positions) {
  const tbody = document.querySelector("#positions-table tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  const active = (positions || []).filter((p) => parseFloat(p.quantity) > 0);
  if (!active.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="4" class="muted">Pozisyon yok</td>';
    tbody.appendChild(tr);
    return;
  }
  for (const p of active) {
    const tr = document.createElement("tr");
    tr.setAttribute("data-testid", `position-row-${p.ticker}`);
    tr.innerHTML = `
      <td>${p.ticker}</td>
      <td data-testid="position-qty-${p.ticker}">${parseFloat(p.quantity)}</td>
      <td data-testid="position-avg-${p.ticker}">${parseFloat(p.average_cost)}</td>
      <td>${parseFloat(p.realized_pnl || 0).toFixed(2)}</td>
    `;
    tbody.appendChild(tr);
  }
}

async function loadPortfolioDetail() {
  const id = getPortfolioId();
  if (!id) {
    showError("Portföy ID eksik (?id=)");
    return;
  }
  hideError();
  const portfolio = await fetchPortfolio(id);
  document.getElementById("portfolio-title").textContent = portfolio.name;
  document.getElementById("portfolio-meta").textContent =
    `${portfolio.currency} · ID ${portfolio.id}`;
  renderPositions(portfolio.positions);
  const portfolioLink = document.getElementById("portfolio-link");
  if (portfolioLink) portfolioLink.href = `portfolio.html?id=${id}`;
  const summaryLink = document.getElementById("summary-link");
  if (summaryLink) summaryLink.href = `summary.html?id=${id}`;
  const historyLink = document.getElementById("history-link");
  if (historyLink) historyLink.href = `history.html?id=${id}`;
}

async function submitTrade(e) {
  e.preventDefault();
  hideError();
  const id = getPortfolioId();
  const ticker = document.getElementById("trade-ticker").value.trim().toUpperCase();
  const trade_type = document.getElementById("trade-type").value;
  const quantity = document.getElementById("trade-quantity").value;
  const price = document.getElementById("trade-price").value;
  const commission = document.getElementById("trade-commission").value || "0";
  try {
    await api("POST", `/portfolios/${id}/trades`, {
      ticker,
      trade_type,
      quantity,
      price,
      commission,
    });
    document.getElementById("trade-form").reset();
    await loadPortfolioDetail();
  } catch (err) {
    showError(err.message);
  }
}

async function handleExport() {
  const id = getPortfolioId();
  const resultEl = document.getElementById("export-result");
  const btn = document.getElementById("export-btn");
  if (!id || !resultEl) return;
  try {
    btn.disabled = true;
    btn.textContent = "Aktarılıyor…";
    const res = await api("POST", `/portfolios/${id}/export`);
    resultEl.textContent = `✓ Aktarıldı: ${res.s3_uri} (${res.trade_count} işlem, ${res.size_bytes} bayt)`;
    resultEl.style.color = "var(--success)";
  } catch (err) {
    resultEl.textContent = `Hata: ${err.message}`;
    resultEl.style.color = "var(--error)";
  } finally {
    btn.disabled = false;
    btn.textContent = "S3'e Aktar";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initHeader();
  const form = document.getElementById("trade-form");
  if (form) form.addEventListener("submit", submitTrade);
  const exportBtn = document.getElementById("export-btn");
  if (exportBtn) exportBtn.addEventListener("click", handleExport);
  loadPortfolioDetail().catch((err) => showError(err.message));
});
