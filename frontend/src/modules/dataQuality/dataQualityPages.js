import { icon } from "../../components/icons.js";
import {
  clearBusy,
  display,
  emptyState,
  escapeHtml,
  renderError,
  serializeForm,
  setBusy,
} from "../../components/ui.js";
import { dataQualityService } from "../../services/employeeService.js";

function pageHeader({ title, subtitle }) {
  return `
    <section class="page-header">
      <div>
        <span class="eyebrow">Data Governance</span>
        <h1>${escapeHtml(title)}</h1>
        <p>${escapeHtml(subtitle)}</p>
      </div>
    </section>
  `;
}

function loading(label = "Memuat data quality") {
  return `<div class="loading"><span class="spinner"></span>${escapeHtml(label)}</div>`;
}

function issuePill(value) {
  const text = String(value || "OPEN").toUpperCase();
  const tone =
    text === "RESOLVED" ? "success" : text === "IGNORED" ? "neutral" : "warning";
  return `<span class="pill pill-${tone}">${escapeHtml(text)}</span>`;
}

function severityPill(value) {
  const text = String(value || "INFO").toUpperCase();
  const tone = text === "BLOCKING" ? "danger" : text === "REVIEW" ? "warning" : "neutral";
  return `<span class="pill pill-${tone}">${escapeHtml(text)}</span>`;
}

function metric(label, value) {
  return `
    <div class="metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function renderSummary(summary) {
  const statusText = summary.status ? String(summary.status).toUpperCase() : "";
  const totalLabel = statusText === "OPEN" ? "Open" : statusText || "Total";
  const totalValue = summary.total ?? summary.open_total ?? 0;
  const reviewCount = summary.by_severity?.REVIEW ?? summary.watch_total ?? 0;
  const infoCount = summary.by_severity?.INFO ?? 0;
  const periodLabel = summary.source_period ? `Periode ${summary.source_period}` : "Semua periode";
  return `
    <div class="section-caption">${escapeHtml(periodLabel)}</div>
    <section class="metric-grid">
      ${metric(totalLabel, totalValue)}
      ${metric("Perlu Review", reviewCount)}
      ${metric("Info", infoCount)}
      ${metric("Kode Issue", Object.keys(summary.by_code || {}).length)}
    </section>
  `;
}

function renderIssueRows(issues) {
  if (!issues.length) {
    return emptyState("Tidak ada issue", "Ubah filter untuk melihat status atau severity lain.");
  }

  return `
    <div class="table-wrap">
      <table class="data-table data-quality-table">
        <thead>
          <tr>
            <th>Issue</th>
            <th>Karyawan</th>
            <th>Periode</th>
            <th>Observasi</th>
            <th>Rekomendasi</th>
            <th class="table-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          ${issues
            .map(
              (issue) => `
                <tr>
                  <td>
                    <div class="issue-cell">
                      <strong>${escapeHtml(issue.issue_code)}</strong>
                      <span>${severityPill(issue.severity)} ${issuePill(issue.status)}</span>
                    </div>
                  </td>
                  <td>
                    <strong>${display(issue.full_name)}</strong>
                    <small>${display(issue.employee_no)}</small>
                  </td>
                  <td>${display(issue.source_period)}</td>
                  <td>${display(issue.observed_value)}</td>
                  <td>${display(issue.recommendation)}</td>
                  <td class="table-actions">
                    <button class="icon-btn" title="Resolve" data-issue-action="RESOLVED" data-issue-id="${issue.issue_id}">${icon("shield")}</button>
                    <button class="icon-btn" title="Ignore" data-issue-action="IGNORED" data-issue-id="${issue.issue_id}">${icon("trash")}</button>
                  </td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function bindIssueActions(container, onUpdated) {
  container.querySelectorAll("[data-issue-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const issueId = button.dataset.issueId;
      const status = button.dataset.issueAction;
      const recommendation = prompt("Catatan review", "");
      if (recommendation === null) {
        return;
      }

      setBusy(button, "");
      try {
        await dataQualityService.updateIssue(issueId, {
          status,
          recommendation: recommendation.trim() || undefined,
        });
        await onUpdated();
      } catch (error) {
        alert(error.message || "Update issue gagal.");
      } finally {
        clearBusy(button);
      }
    });
  });
}

function summaryParamsFromFilters(form) {
  const params = serializeForm(form);
  delete params.page;
  delete params.limit;
  return params;
}

export async function renderDataQualityPage(container) {
  container.innerHTML = `
    ${pageHeader({
      title: "Data Quality",
      subtitle: "Pantau issue import HRIS, review anomali, lalu resolve atau ignore dengan audit log.",
    })}
    <section id="data-quality-summary">${loading("Memuat summary")}</section>
    <section class="toolbar-panel">
      <form id="data-quality-filter" class="filter-grid">
        <label>
          <span>Status</span>
          <select name="status">
            <option value="OPEN">Open</option>
            <option value="RESOLVED">Resolved</option>
            <option value="IGNORED">Ignored</option>
            <option value="">Semua</option>
          </select>
        </label>
        <label>
          <span>Severity</span>
          <select name="severity">
            <option value="">Semua severity</option>
            <option value="REVIEW">Review</option>
            <option value="INFO">Info</option>
            <option value="BLOCKING">Blocking</option>
          </select>
        </label>
        <label>
          <span>Kode</span>
          <input name="issue_code" placeholder="AGE_REVIEW" />
        </label>
        <label>
          <span>Periode</span>
          <input name="source_period" placeholder="Maret 2026" />
        </label>
        <input type="hidden" name="page" value="1" />
        <input type="hidden" name="limit" value="100" />
        <button class="button button-secondary" type="submit">${icon("search")}Filter</button>
      </form>
    </section>
    <section class="surface" id="data-quality-content">${loading()}</section>
  `;

  const form = container.querySelector("#data-quality-filter");
  const summaryTarget = container.querySelector("#data-quality-summary");
  const content = container.querySelector("#data-quality-content");

  const loadSummary = async () => {
    try {
      const summary = await dataQualityService.summary(summaryParamsFromFilters(form));
      summaryTarget.innerHTML = renderSummary(summary);
    } catch (error) {
      summaryTarget.innerHTML = renderError(error);
    }
  };

  const loadIssues = async () => {
    content.innerHTML = loading();
    try {
      const params = serializeForm(form);
      const issues = await dataQualityService.issues(params);
      content.innerHTML = renderIssueRows(issues);
      bindIssueActions(content, async () => {
        await Promise.all([loadSummary(), loadIssues()]);
      });
    } catch (error) {
      content.innerHTML = renderError(error);
    }
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await Promise.all([loadSummary(), loadIssues()]);
  });

  await Promise.all([loadSummary(), loadIssues()]);
}
