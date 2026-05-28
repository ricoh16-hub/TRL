import { renderRoute } from "./router.js";
import { appState, subscribe } from "./state.js";
import { renderSidebar } from "../components/sidebar.js";
import { bindTopbar, renderTopbar } from "../components/topbar.js";
import { authApi } from "../services/api.js";

function drawShell() {
  const root = document.getElementById("app");
  root.innerHTML = `
    <div class="app-shell">
      <aside class="sidebar" id="sidebar"></aside>
      <section class="workspace">
        <header class="topbar" id="topbar"></header>
        <div class="topbar-message" id="topbar-status"></div>
        <main class="content" id="view"></main>
      </section>
    </div>
  `;
}

function drawChrome() {
  document.getElementById("sidebar").innerHTML = renderSidebar(location.hash || "#/employees");
  document.getElementById("topbar").innerHTML = renderTopbar(appState);
  bindTopbar(() => {
    drawChrome();
    renderRoute();
  });
}

export async function initLayout() {
  drawShell();
  drawChrome();
  subscribe(drawChrome);

  if (appState.token) {
    try {
      await authApi.me();
    } catch {
      drawChrome();
    }
  }

  window.addEventListener("hashchange", () => {
    drawChrome();
    renderRoute();
  });

  if (!location.hash) {
    location.hash = "#/employees";
    return;
  }

  renderRoute();
}
