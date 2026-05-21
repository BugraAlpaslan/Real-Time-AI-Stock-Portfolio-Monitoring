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
  const rows = positions || [];
  for (const p of rows) {
    if (parseFloat(p.quantity) <= 0) continue;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${p.ticker}</td>
      <td>${formatMoney(p.quantity)}</td>
      <td>${formatMoney(p.average_cost)}</td>
      <td>${formatMoney(p.current_price)}</td>
      <td>${formatMoney(p.unrealized_pnl)}</td>
    `;
    tbody.appendChild(tr);
  }
  tbody.setAttribute("data-row-count", String(tbody.querySelectorAll("tr").length));
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
  loadSummary().catch((err) => {
    document.getElementById("summary-error").textContent = err.message;
  });
});
