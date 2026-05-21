import { isLoggedIn, login } from "./auth.js";

if (isLoggedIn()) {
  window.location.href = "/ui/index.html";
}

document.getElementById("login-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;
  const errorEl = document.getElementById("login-error");

  if (login(username, password)) {
    window.location.href = "/ui/index.html";
  } else {
    errorEl.textContent = "Kullanıcı adı veya şifre hatalı.";
    errorEl.hidden = false;
  }
});
