import { api } from "./api.js";
import { requireAuth, initHeader } from "./auth.js";

requireAuth();

const STORAGE_KEY = "portfolioTrackerEntries";

export function loadStoredPortfolios() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

export function savePortfolioEntry(id, name) {
  const entries = loadStoredPortfolios().filter((e) => e.id !== id);
  entries.unshift({ id, name });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export async function createPortfolio(name, currency) {
  return api("POST", "/portfolios", { name, currency });
}

export async function fetchPortfolio(id) {
  return api("GET", `/portfolios/${id}`);
}

function showToast(message) {
  const toast = document.querySelector('[data-testid="success-toast"]');
  if (!toast) return;
  toast.textContent = message;
  toast.hidden = false;
  setTimeout(() => {
    toast.hidden = true;
  }, 3000);
}

function renderPortfolioList(entries) {
  const list = document.getElementById("portfolio-list");
  if (!list) return;
  list.innerHTML = "";
  if (!entries.length) {
    const li = document.createElement("li");
    li.className = "muted";
    li.textContent = "Henüz portföy yok. Yukarıdan oluşturun.";
    list.appendChild(li);
    return;
  }
  for (const { id, name } of entries) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `portfolio.html?id=${id}`;
    a.textContent = name;
    a.setAttribute("data-testid", `portfolio-link-${id}`);
    li.appendChild(a);
    list.appendChild(li);
  }
}

async function refreshList() {
  const entries = loadStoredPortfolios();
  const verified = [];
  for (const entry of entries) {
    try {
      const p = await fetchPortfolio(entry.id);
      verified.push({ id: p.id, name: p.name });
    } catch {
      /* drop stale entries */
    }
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(verified));
  renderPortfolioList(verified);
}

function bindCreateForm() {
  const form = document.getElementById("create-portfolio-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("portfolio-name").value.trim();
    const currency = document.getElementById("portfolio-currency").value;
    if (!name) return;
    try {
      const created = await createPortfolio(name, currency);
      savePortfolioEntry(created.id, created.name);
      form.reset();
      showToast(`Portföy oluşturuldu: ${created.name}`);
      await refreshList();
    } catch (err) {
      alert(err.message);
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initHeader();
  bindCreateForm();
  refreshList();
});
