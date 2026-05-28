import { appState, clearSession, setApiBase, setSession } from "../app/state.js";

export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function url(path, params = {}) {
  const target = new URL(`${appState.apiBase}${path}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      target.searchParams.set(key, value);
    }
  });
  return target.toString();
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

export async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (appState.token) {
    headers.set("Authorization", `Bearer ${appState.token}`);
  }

  const response = await fetch(url(path, options.params), {
    ...options,
    headers,
    body:
      options.body && !(options.body instanceof FormData)
        ? JSON.stringify(options.body)
        : options.body,
  });

  const payload = response.status === 204 ? null : await parseResponse(response);
  if (!response.ok) {
    if (response.status === 401) {
      clearSession();
    }
    const detail = payload && typeof payload === "object" ? payload.detail : payload;
    throw new ApiError(detail || "Request gagal.", response.status, payload);
  }
  return payload;
}

export const authApi = {
  async login(username, password) {
    const result = await request("/auth/login", {
      method: "POST",
      body: { username, password },
    });
    setSession({ token: result.access_token, user: result.user });
    return result;
  },

  async me() {
    if (!appState.token) {
      return null;
    }
    const user = await request("/auth/me");
    setSession({ token: appState.token, user });
    return user;
  },

  logout() {
    clearSession();
  },
};

export const configApi = {
  setApiBase,
};
