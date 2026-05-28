import { ApiError } from "../services/api.js";

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function display(value, fallback = "-") {
  return value === undefined || value === null || value === "" ? fallback : escapeHtml(value);
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export function progressBar(value) {
  const numeric = Math.max(0, Math.min(100, Number(value || 0)));
  return `
    <div class="progress" aria-label="Kelengkapan data ${numeric}%">
      <span style="width: ${numeric}%"></span>
    </div>
  `;
}

export function statusPill(value) {
  const text = String(value || "BELUM ADA").toUpperCase();
  const tone = text.includes("AKTIF")
    ? "success"
    : text.includes("CUTI")
      ? "warning"
      : text.includes("KELUAR") || text.includes("NON")
        ? "danger"
        : "neutral";
  return `<span class="pill pill-${tone}">${escapeHtml(text)}</span>`;
}

export function renderError(error) {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return `<div class="empty-state compact">Sesi belum aktif. Masuk melalui topbar.</div>`;
    }
    if (error.status === 403) {
      return `<div class="empty-state compact">Akses ditolak untuk aksi ini.</div>`;
    }
    return `<div class="empty-state compact">${escapeHtml(error.message)}</div>`;
  }
  return `<div class="empty-state compact">Tidak dapat memuat data.</div>`;
}

export function emptyState(title, detail = "") {
  return `
    <div class="empty-state">
      <strong>${escapeHtml(title)}</strong>
      ${detail ? `<span>${escapeHtml(detail)}</span>` : ""}
    </div>
  `;
}

export function serializeForm(form, { omitEmpty = true } = {}) {
  const data = new FormData(form);
  const payload = {};

  for (const [key, rawValue] of data.entries()) {
    const value = typeof rawValue === "string" ? rawValue.trim() : rawValue;
    if (omitEmpty && value === "") {
      continue;
    }
    if (key.endsWith("_id") || key.endsWith("_count")) {
      payload[key] = value === "" ? null : Number(value);
      continue;
    }
    if (key === "is_active" || key.endsWith("_flag")) {
      payload[key] = value === "true" || value === "on";
      continue;
    }
    payload[key] = value;
  }

  for (const checkbox of form.querySelectorAll('input[type="checkbox"]')) {
    if (!Object.hasOwn(payload, checkbox.name)) {
      payload[checkbox.name] = checkbox.checked;
    }
  }

  return payload;
}

export function employeeInitials(fullName) {
  return String(fullName || "GB")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase())
    .join("");
}

export function setBusy(button, busyText = "Memproses") {
  button.dataset.originalText = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span class="spinner"></span>${busyText}`;
}

export function clearBusy(button) {
  if (button.dataset.originalText) {
    button.innerHTML = button.dataset.originalText;
  }
  button.disabled = false;
}
