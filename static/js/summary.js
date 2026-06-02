import { api } from "./api.js";
import { requireAuth, initHeader } from "./auth.js";

requireAuth();

function getPortfolioId() {
  return new URLSearchParams(window.location.search).get("id");
}

function formatMoney(value) {
  const n = parseFloat(value);
  return Number.isFinite(n) ? n.toFixed(2) : "0.00";
}

function setCard(testId, value) {
  const el = document.querySelector(`[data-testid="${testId}"] .pnl-value`);
  if (el) {
    el.textContent = formatMoney(value);
    const num = parseFloat(value);
    el.classList.toggle("pnl-positive", num > 0);
    el.classList.toggle("pnl-negative", num < 0);
  }
}

function renderPositions(positions) {
  const tbody = document.querySelector("#summary-positions tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  const rows = (positions || []).filter((p) => parseFloat(p.quantity) > 0);
  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="5" class="muted">Açık pozisyon yok</td>';
    tbody.appendChild(tr);
    tbody.setAttribute("data-row-count", "0");
    return;
  }
  for (const p of rows) {
    const tr = document.createElement("tr");
    tr.setAttribute("data-testid", `summary-row-${p.ticker}`);
    tr.innerHTML = `
      <td>${p.ticker}</td>
      <td>${formatMoney(p.quantity)}</td>
      <td>${formatMoney(p.average_cost)}</td>
      <td>${formatMoney(p.current_price)}</td>
      <td class="${parseFloat(p.unrealized_pnl) >= 0 ? "pnl-positive" : "pnl-negative"}">${formatMoney(p.unrealized_pnl)}</td>
    `;
    tbody.appendChild(tr);
  }
  tbody.setAttribute("data-row-count", String(tbody.querySelectorAll("tr").length));
}

function initLinks() {
  const id = getPortfolioId();
  if (!id) return;
  const portfolioLink = document.getElementById("portfolio-link");
  const summaryLink = document.getElementById("summary-link");
  const historyLink = document.getElementById("history-link");
  if (portfolioLink) portfolioLink.href = `portfolio.html?id=${id}`;
  if (summaryLink) summaryLink.href = `summary.html?id=${id}`;
  if (historyLink) historyLink.href = `history.html?id=${id}`;
}

async function loadSummary() {
  const id = getPortfolioId();
  if (!id) {
    document.getElementById("summary-error").textContent = "Portföy ID eksik (?id=)";
    return;
  }
  const summary = await api("GET", `/portfolios/${id}/summary`);
  setCard("realized-pnl", summary.realized_pnl);
  setCard("unrealized-pnl", summary.unrealized_pnl);
  setCard("total-pnl", summary.total_pnl);
  renderPositions(summary.positions);
  const realized = parseFloat(summary.realized_pnl);
  const unrealized = parseFloat(summary.unrealized_pnl);
  const total = parseFloat(summary.total_pnl);
  document.getElementById("pnl-check").dataset.valid =
    Math.abs(total - (realized + unrealized)) < 0.02 ? "true" : "false";
}

document.addEventListener("DOMContentLoaded", () => {
  initHeader();
  initLinks();
  loadSummary().catch((err) => {
    document.getElementById("summary-error").textContent = err.message;
  });
});
