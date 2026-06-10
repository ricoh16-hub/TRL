import { icon } from "../../components/icons.js";
import { display, emptyState, escapeHtml, progressBar, renderError } from "../../components/ui.js";
import { manpowerService } from "../../services/employeeService.js";

function pageHeader() {
  return `
    <section class="page-header">
      <div>
        <span class="eyebrow">HRIS & Manpower</span>
        <h1>Manpower</h1>
        <p>Ringkasan headcount aktif, coverage assignment, dan sebaran tenaga kerja.</p>
      </div>
      <div class="page-actions">
        <a class="button button-secondary" href="#/employees">${icon("users")}Data Karyawan</a>
      </div>
    </section>
  `;
}

function loading() {
  return `<div class="loading"><span class="spinner"></span>Memuat manpower</div>`;
}

function metric(label, value, detail = "") {
  return `
    <div class="metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      ${detail ? `<small>${escapeHtml(detail)}</small>` : ""}
    </div>
  `;
}

function breakdownTable(title, rows) {
  if (!rows?.length) {
    return `
      <section class="surface">
        <div class="section-title"><h3>${escapeHtml(title)}</h3></div>
        ${emptyState("Belum ada data")}
      </section>
    `;
  }

  return `
    <section class="surface">
      <div class="section-title"><h3>${escapeHtml(title)}</h3></div>
      <div class="table-wrap">
        <table class="data-table compact">
          <thead>
            <tr>
              <th>Dimensi</th>
              <th>Headcount</th>
              <th>Aktif</th>
              <th>Nonaktif</th>
            </tr>
          </thead>
          <tbody>
            ${rows
              .map(
                (row) => `
                  <tr>
                    <td>${display(row.label)}</td>
                    <td>${Number(row.headcount || 0).toLocaleString("id-ID")}</td>
                    <td>${Number(row.active || 0).toLocaleString("id-ID")}</td>
                    <td>${Number(row.inactive || 0).toLocaleString("id-ID")}</td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderSummary(summary) {
  const coverage = summary.coverage || {};
  const coverageValue = Number(coverage.assignment_coverage || 0);
  return `
    ${pageHeader()}
    <section class="metric-grid">
      ${metric("Total Headcount", Number(summary.total_headcount || 0).toLocaleString("id-ID"))}
      ${metric("Aktif", Number(summary.active_headcount || 0).toLocaleString("id-ID"))}
      ${metric("Nonaktif", Number(summary.inactive_headcount || 0).toLocaleString("id-ID"))}
      ${metric("Coverage Assignment", `${coverageValue.toFixed(0)}%`, `${coverage.with_assignment || 0} terisi`)}
    </section>
    <section class="surface">
      <div class="section-title"><h3>Kelengkapan Assignment</h3></div>
      ${progressBar(coverageValue)}
      <div class="coverage-row">
        <span>${Number(coverage.with_assignment || 0).toLocaleString("id-ID")} karyawan punya assignment aktif</span>
        <strong>${Number(coverage.without_assignment || 0).toLocaleString("id-ID")} belum terisi</strong>
      </div>
    </section>
    <section class="detail-grid">
      ${breakdownTable("Per Estate", summary.estate_breakdown)}
      ${breakdownTable("Per Divisi", summary.division_breakdown)}
    </section>
    <section class="detail-grid">
      ${breakdownTable("Per Kategori", summary.category_breakdown)}
      ${breakdownTable("Per Status", summary.status_breakdown)}
    </section>
  `;
}

export async function renderManpowerPage(container) {
  container.innerHTML = loading();
  try {
    const summary = await manpowerService.summary();
    container.innerHTML = renderSummary(summary);
  } catch (error) {
    container.innerHTML = `
      ${pageHeader()}
      ${renderError(error)}
    `;
  }
}
