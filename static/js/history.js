import { api, formatCurrency } from "./api.js";
import { requireAuth, initHeader } from "./auth.js";

requireAuth();

function getPortfolioId() {
  return new URLSearchParams(window.location.search).get("id");
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function badgeHtml(type) {
  const isBuy = type === "BUY";
  return `<span class="trade-badge ${isBuy ? "badge-buy" : "badge-sell"}">${isBuy ? "AL" : "SAT"}</span>`;
}

function renderTrades(trades) {
  const tbody = document.querySelector("#history-table tbody");
  tbody.innerHTML = "";
  if (!trades.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="7" class="muted">İşlem bulunamadı.</td>';
    tbody.appendChild(tr);
    return;
  }
  for (const t of trades) {
    const tr = document.createElement("tr");
    tr.setAttribute("data-testid", `history-row-${t.id}`);
    tr.innerHTML = `
      <td>${formatDate(t.executed_at)}</td>
      <td>${t.ticker}</td>
      <td>${badgeHtml(t.trade_type)}</td>
      <td>${parseFloat(t.quantity)}</td>
      <td>${formatCurrency(t.price)}</td>
      <td>${formatCurrency(t.commission || 0)}</td>
      <td>${t.notes || "—"}</td>
    `;
    tbody.appendChild(tr);
  }
}

async function load(ticker = null) {
  const id = getPortfolioId();
  if (!id) return;
  const params = new URLSearchParams({ limit: "500" });
  if (ticker) params.set("ticker", ticker.toUpperCase());
  const trades = await api("GET", `/portfolios/${id}/trades?${params}`);
  renderTrades(trades || []);
}

function initLinks() {
  const id = getPortfolioId();
  const portfolioLink = document.getElementById("portfolio-link");
  const summaryLink = document.getElementById("summary-link");
  const historyLink = document.getElementById("history-link");
  if (portfolioLink) portfolioLink.href = `portfolio.html?id=${id}`;
  if (summaryLink) summaryLink.href = `summary.html?id=${id}`;
  if (historyLink) historyLink.href = `history.html?id=${id}`;
}

document.addEventListener("DOMContentLoaded", () => {
  initHeader();
  initLinks();
  load();

  document.getElementById("filter-btn").addEventListener("click", () => {
    const val = document.getElementById("ticker-filter").value.trim();
    load(val || null);
  });

  document.getElementById("clear-btn").addEventListener("click", () => {
    document.getElementById("ticker-filter").value = "";
    load(null);
  });

  document.getElementById("ticker-filter").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const val = e.target.value.trim();
      load(val || null);
    }
  });
});
