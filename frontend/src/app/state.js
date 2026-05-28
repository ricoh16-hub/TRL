const listeners = new Set();
const defaultApiBase =
  window.location.protocol.startsWith("http") && window.location.origin
    ? `${window.location.origin}/api`
    : "http://127.0.0.1:8000";

export const appState = {
  apiBase: localStorage.getItem("ptgbr.apiBase") || defaultApiBase,
  token: localStorage.getItem("ptgbr.accessToken") || "",
  user: null,
  routeTitle: "HRIS & Manpower",
};

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setState(patch) {
  Object.assign(appState, patch);
  for (const listener of listeners) {
    listener(appState);
  }
}

export function setApiBase(apiBase) {
  const cleanValue = apiBase.trim().replace(/\/$/, "");
  localStorage.setItem("ptgbr.apiBase", cleanValue);
  setState({ apiBase: cleanValue });
}

export function setSession({ token, user }) {
  localStorage.setItem("ptgbr.accessToken", token);
  setState({ token, user });
}

export function clearSession() {
  localStorage.removeItem("ptgbr.accessToken");
  setState({ token: "", user: null });
}

export function setRouteTitle(routeTitle) {
  setState({ routeTitle });
}
