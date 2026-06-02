const AUTH_KEY = "spt_auth";
const CREDENTIALS = { username: "admin", password: "admin" };

export function isLoggedIn() {
  return !!localStorage.getItem(AUTH_KEY);
}

export function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = "/ui/login.html";
  }
}

export function login(username, password) {
  if (username === CREDENTIALS.username && password === CREDENTIALS.password) {
    localStorage.setItem(AUTH_KEY, JSON.stringify({ user: username }));
    return true;
  }
  return false;
}

export function logout() {
  localStorage.removeItem(AUTH_KEY);
  window.location.href = "/ui/login.html";
}

export function getCurrentUser() {
  const data = localStorage.getItem(AUTH_KEY);
  return data ? JSON.parse(data).user : null;
}

export function initHeader() {
  const badge = document.getElementById("user-badge");
  const logoutBtn = document.getElementById("logout-btn");
  const user = getCurrentUser();
  if (badge && user) badge.textContent = user;
  if (logoutBtn) logoutBtn.addEventListener("click", logout);

  // Active nav link: match data-page attribute to current page filename
  const currentPage = window.location.pathname.split("/").pop().replace(".html", "") || "index";
  document.querySelectorAll(`nav a[data-page="${currentPage}"]`).forEach((a) => {
    a.classList.add("active");
  });
}
