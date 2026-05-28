import { appState } from "../app/state.js";
import { authApi, configApi } from "../services/api.js";
import { icon } from "./icons.js";
import { escapeHtml } from "./ui.js";

export function renderTopbar() {
  const user = appState.user;
  return `
    <div class="topbar-title">
      <span>PT GBR Plantation</span>
      <strong>${escapeHtml(appState.routeTitle)}</strong>
    </div>
    <form class="api-form" id="api-form">
      <label>
        <span>API</span>
        <input name="api_base" value="${escapeHtml(appState.apiBase)}" />
      </label>
      <button class="icon-btn" type="submit" title="Simpan API">${icon("shield")}</button>
    </form>
    ${
      user
        ? `
          <div class="session-chip">
            <span>${escapeHtml(user.username)}</span>
            <button class="icon-btn" id="logout-button" type="button" title="Keluar">${icon("logout")}</button>
          </div>
        `
        : `
          <form class="login-form" id="login-form">
            <input name="username" placeholder="Username" autocomplete="username" />
            <input name="password" placeholder="Password" type="password" autocomplete="current-password" />
            <button class="button button-primary" type="submit">${icon("lock")}Masuk</button>
          </form>
        `
    }
  `;
}

export function bindTopbar(onRefresh) {
  const apiForm = document.getElementById("api-form");
  apiForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    configApi.setApiBase(new FormData(apiForm).get("api_base") || appState.apiBase);
    onRefresh();
  });

  const loginForm = document.getElementById("login-form");
  loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = document.getElementById("topbar-status");
    const formData = new FormData(loginForm);
    try {
      if (status) status.textContent = "Masuk...";
      await authApi.login(formData.get("username"), formData.get("password"));
      onRefresh();
    } catch (error) {
      if (status) status.textContent = error.message || "Login gagal";
    }
  });

  document.getElementById("logout-button")?.addEventListener("click", () => {
    authApi.logout();
    onRefresh();
  });
}
