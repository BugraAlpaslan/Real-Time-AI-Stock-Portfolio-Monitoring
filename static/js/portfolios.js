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
    li.style.cssText = "display:flex;align-items:center;gap:0.5rem;";
    const a = document.createElement("a");
    a.href = `portfolio.html?id=${id}`;
    a.textContent = name;
    a.setAttribute("data-testid", `portfolio-link-${id}`);
    a.style.flex = "1";
    const delBtn = document.createElement("button");
    delBtn.textContent = "Sil";
    delBtn.className = "btn-sm btn-danger";
    delBtn.setAttribute("data-testid", `delete-portfolio-${id}`);
    delBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      if (!confirm(`"${name}" portföyünü silmek istediğinizden emin misiniz?`)) return;
      try {
        await api("DELETE", `/portfolios/${id}`);
        const stored = loadStoredPortfolios().filter((entry) => entry.id !== id);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
        renderPortfolioList(stored);
      } catch (err) {
        alert(err.message);
      }
    });
    li.appendChild(a);
    li.appendChild(delBtn);
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
