import { api, formatCurrency } from "./api.js";
import { requireAuth, initHeader } from "./auth.js";

requireAuth();

function getPortfolioId() {
  return new URLSearchParams(window.location.search).get("id");
}

function setCard(testId, value) {
  const el = document.querySelector(`[data-testid="${testId}"] .pnl-value`);
  if (el) {
    el.textContent = formatCurrency(value);
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
      <td>${parseFloat(p.quantity)}</td>
      <td>${formatCurrency(p.average_cost)}</td>
      <td>${formatCurrency(p.current_price)}</td>
      <td class="${parseFloat(p.unrealized_pnl) >= 0 ? "pnl-positive" : "pnl-negative"}">${formatCurrency(p.unrealized_pnl)}</td>
    `;
    tbody.appendChild(tr);
  }
  tbody.setAttribute("data-row-count", String(tbody.querySelectorAll("tr").length));
}

function renderReturnSection(summary) {
  const costEl = document.getElementById("total-cost-val");
  const mktEl = document.getElementById("total-market-val");
  const retEl = document.getElementById("return-pct");
  if (costEl) costEl.textContent = formatCurrency(summary.total_cost);
  if (mktEl) mktEl.textContent = formatCurrency(summary.total_market_value);
  if (!retEl) return;
  const cost = parseFloat(summary.total_cost);
  const mktVal = parseFloat(summary.total_market_value);
  if (cost <= 0) {
    retEl.textContent = "—";
    return;
  }
  const pct = ((mktVal - cost) / cost) * 100;
  const absPctStr = Math.abs(pct).toFixed(1).replace(".", ",");
  retEl.textContent = (pct >= 0 ? "+" : "-") + "%" + absPctStr;
  retEl.classList.toggle("pnl-positive", pct > 0);
  retEl.classList.toggle("pnl-negative", pct < 0);
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

function initPortfolioSelector() {
  const sel = document.getElementById("portfolio-select");
  if (!sel) return;
  const id = getPortfolioId();
  try {
    const entries = JSON.parse(localStorage.getItem("portfolioTrackerEntries") || "[]");
    entries.forEach(({ id: pid, name }) => {
      const opt = document.createElement("option");
      opt.value = pid;
      opt.textContent = name;
      if (String(pid) === String(id)) opt.selected = true;
      sel.appendChild(opt);
    });
  } catch {
    /* ignore */
  }
  sel.addEventListener("change", () => {
    window.location.href = `summary.html?id=${sel.value}`;
  });
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
  renderReturnSection(summary);
  const realized = parseFloat(summary.realized_pnl);
  const unrealized = parseFloat(summary.unrealized_pnl);
  const total = parseFloat(summary.total_pnl);
  document.getElementById("pnl-check").dataset.valid =
    Math.abs(total - (realized + unrealized)) < 0.02 ? "true" : "false";
}

document.addEventListener("DOMContentLoaded", () => {
  initHeader();
  initLinks();
  initPortfolioSelector();
  loadSummary().catch((err) => {
    document.getElementById("summary-error").textContent = err.message;
  });
});
