import { navigate } from "../../app/router.js";
import { icon } from "../../components/icons.js";
import {
  clearBusy,
  display,
  employeeInitials,
  emptyState,
  escapeHtml,
  progressBar,
  renderError,
  serializeForm,
  setBusy,
  statusPill,
  today,
} from "../../components/ui.js";
import { employeeService, referenceService } from "../../services/employeeService.js";

function pageHeader({ title, subtitle, actions = "" }) {
  return `
    <section class="page-header">
      <div>
        <span class="eyebrow">HRIS & Manpower</span>
        <h1>${escapeHtml(title)}</h1>
        <p>${escapeHtml(subtitle)}</p>
      </div>
      <div class="page-actions">${actions}</div>
    </section>
  `;
}

function loading(label = "Memuat data") {
  return `<div class="loading"><span class="spinner"></span>${escapeHtml(label)}</div>`;
}

function employeeNav(employeeId, active) {
  const tabs = [
    ["detail", "Detail"],
    ["edit", "Edit"],
    ["status", "Status"],
    ["mutation", "Mutasi"],
    ["documents", "Dokumen"],
    ["history", "Riwayat"],
  ];
  return `
    <nav class="subnav" aria-label="Navigasi employee">
      ${tabs
        .map(
          ([key, label]) => `
            <a class="${active === key ? "active" : ""}" href="#/employees/${employeeId}/${key}">
              ${escapeHtml(label)}
            </a>
          `,
        )
        .join("")}
    </nav>
  `;
}

function employeeHero(detail, active) {
  const profile = detail.profile;
  return `
    <section class="employee-hero">
      <div class="avatar">${escapeHtml(employeeInitials(profile.full_name))}</div>
      <div class="employee-hero-main">
        <span>${escapeHtml(profile.employee_no)}</span>
        <h2>${escapeHtml(profile.full_name)}</h2>
        <p>
          ${display(detail.current_assignment?.division_name)}
          <span>/</span>
          ${display(detail.current_assignment?.position_name)}
        </p>
      </div>
      <div class="employee-hero-side">
        ${statusPill(detail.current_status?.status_name)}
        <small>${profile.is_active ? "Record aktif" : "Record nonaktif"}</small>
      </div>
    </section>
    ${employeeNav(profile.employee_id, active)}
  `;
}

function infoRow(label, value) {
  return `
    <div class="info-row">
      <span>${escapeHtml(label)}</span>
      <strong>${display(value)}</strong>
    </div>
  `;
}

function referenceOptions(items, selectedValue = "") {
  return items
    .map((item) => {
      const selected = String(item.id) === String(selectedValue) ? "selected" : "";
      return `<option value="${item.id}" ${selected}>${escapeHtml(item.code)} - ${escapeHtml(item.name)}</option>`;
    })
    .join("");
}

async function populateReferenceSelect(select, loader, selectedValue = "") {
  if (!select) {
    return;
  }
  try {
    const rows = await loader();
    select.insertAdjacentHTML("beforeend", referenceOptions(rows, selectedValue));
  } catch {
    select.insertAdjacentHTML("beforeend", `<option value="">Referensi belum tersedia</option>`);
  }
}

function bindDeleteButtons(container) {
  container.querySelectorAll("[data-delete-employee]").forEach((button) => {
    button.addEventListener("click", async () => {
      const employeeId = button.dataset.deleteEmployee;
      if (!confirm("Nonaktifkan employee ini?")) {
        return;
      }
      setBusy(button, "Menghapus");
      try {
        await employeeService.remove(employeeId);
        navigate("/employees");
      } catch (error) {
        alert(error.message || "Soft delete gagal.");
      } finally {
        clearBusy(button);
      }
    });
  });
}

function renderEmployeeTable(employees) {
  if (!employees.length) {
    return emptyState("Data karyawan belum ada", "Gunakan tombol tambah untuk membuat record pertama.");
  }

  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Karyawan</th>
            <th>Divisi</th>
            <th>Jabatan</th>
            <th>Kategori</th>
            <th>Status</th>
            <th>BPJS</th>
            <th>Kelengkapan</th>
            <th class="table-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          ${employees
            .map(
              (employee) => `
                <tr>
                  <td>
                    <a class="employee-link" href="#/employees/${employee.employee_id}/detail">
                      <span class="mini-avatar">${escapeHtml(employeeInitials(employee.full_name))}</span>
                      <span>
                        <strong>${escapeHtml(employee.full_name)}</strong>
                        <small>${escapeHtml(employee.employee_no)}</small>
                      </span>
                    </a>
                  </td>
                  <td>${display(employee.current_division)}</td>
                  <td>${display(employee.current_position)}</td>
                  <td>${display(employee.category)}</td>
                  <td>${statusPill(employee.status)}</td>
                  <td>${statusPill(employee.bpjs_status)}</td>
                  <td>
                    ${progressBar(employee.data_completeness)}
                    <small>${Number(employee.data_completeness || 0).toFixed(0)}%</small>
                  </td>
                  <td class="table-actions">
                    <a class="icon-btn" title="Detail" href="#/employees/${employee.employee_id}/detail">${icon("chevron")}</a>
                    <a class="icon-btn" title="Edit" href="#/employees/${employee.employee_id}/edit">${icon("edit")}</a>
                    <button class="icon-btn danger" title="Soft delete" data-delete-employee="${employee.employee_id}">${icon("trash")}</button>
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

export async function renderEmployeeListPage(container) {
  container.innerHTML = `
    ${pageHeader({
      title: "Daftar Karyawan",
      subtitle: "Kontrol data induk, status, BPJS, dan kelengkapan administrasi karyawan.",
      actions: `<a class="button button-primary" href="#/employees/new">${icon("plus")}Tambah</a>`,
    })}
    <section class="toolbar-panel">
      <form id="employee-filter" class="filter-grid">
        <label>
          <span>Cari</span>
          <input name="search" placeholder="Nama atau nomor karyawan" />
        </label>
        <label>
          <span>Kategori</span>
          <select name="category_id" id="category-filter">
            <option value="">Semua kategori</option>
          </select>
        </label>
        <label>
          <span>Status</span>
          <select name="status_id" id="status-filter">
            <option value="">Semua status</option>
          </select>
        </label>
        <label>
          <span>Divisi</span>
          <select name="division_id" id="division-filter">
            <option value="">Semua divisi</option>
          </select>
        </label>
        <input type="hidden" name="page" value="1" />
        <input type="hidden" name="limit" value="50" />
        <button class="button button-secondary" type="submit">${icon("search")}Filter</button>
      </form>
    </section>
    <section class="surface" id="employee-list-content">${loading()}</section>
  `;

  const form = container.querySelector("#employee-filter");
  const content = container.querySelector("#employee-list-content");

  await Promise.allSettled([
    populateReferenceSelect(container.querySelector("#category-filter"), referenceService.employeeCategories),
    populateReferenceSelect(container.querySelector("#status-filter"), referenceService.employmentStatuses),
    populateReferenceSelect(container.querySelector("#division-filter"), referenceService.divisions),
  ]);

  const loadRows = async () => {
    content.innerHTML = loading();
    try {
      const employees = await employeeService.list(serializeForm(form));
      content.innerHTML = renderEmployeeTable(employees);
      bindDeleteButtons(content);
    } catch (error) {
      content.innerHTML = renderError(error);
    }
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    loadRows();
  });

  await loadRows();
}

export async function renderEmployeeDetailPage(container, employeeId) {
  container.innerHTML = loading();
  try {
    const detail = await employeeService.detail(employeeId);
    const profile = detail.profile;
    container.innerHTML = `
      ${employeeHero(detail, "detail")}
      <section class="metric-grid">
        <div class="metric"><span>Status</span><strong>${display(detail.current_status?.status_name)}</strong></div>
        <div class="metric"><span>BPJS</span><strong>${detail.bpjs?.length || 0} record</strong></div>
        <div class="metric"><span>Dokumen</span><strong>${detail.documents?.length || 0} file</strong></div>
        <div class="metric"><span>Keluarga</span><strong>${detail.family_members?.length || 0} orang</strong></div>
      </section>
      <section class="detail-grid">
        <div class="surface">
          <div class="section-title"><h3>Profil</h3></div>
          ${infoRow("Nomor", profile.employee_no)}
          ${infoRow("Nama", profile.full_name)}
          ${infoRow("Gender", profile.gender)}
          ${infoRow("Tempat/Tanggal Lahir", `${profile.birth_place || "-"} / ${profile.birth_date || "-"}`)}
          ${infoRow("Agama", profile.religion)}
          ${infoRow("Pendidikan", profile.education)}
          ${infoRow("Status Kawin", profile.marital_status)}
          ${infoRow("Telepon", profile.mobile_phone)}
          ${infoRow("Email", profile.email)}
        </div>
        <div class="surface">
          <div class="section-title"><h3>Penempatan Aktif</h3></div>
          ${infoRow("Estate", detail.current_assignment?.estate_name)}
          ${infoRow("Divisi", detail.current_assignment?.division_name)}
          ${infoRow("Jabatan", detail.current_assignment?.position_name)}
          ${infoRow("Kategori", detail.current_assignment?.category_name)}
          ${infoRow("Mulai", detail.current_assignment?.start_date)}
          ${infoRow("Kontrak", detail.current_contract?.contract_no)}
          ${infoRow("Tipe kerja", detail.current_contract?.employment_type_name)}
        </div>
      </section>
      <section class="surface">
        <div class="section-title">
          <h3>Identitas</h3>
          <a class="button button-secondary" href="#/employees/${employeeId}/documents">${icon("document")}Dokumen</a>
        </div>
        ${
          detail.identities?.length
            ? `
              <div class="compact-list">
                ${detail.identities
                  .map(
                    (item) => `
                      <div>
                        <strong>${escapeHtml(item.identity_type)}</strong>
                        <span>${escapeHtml(item.identity_number)}</span>
                        <small>${item.is_primary ? "Utama" : "Tambahan"}</small>
                      </div>
                    `,
                  )
                  .join("")}
              </div>
            `
            : emptyState("Identitas belum tersedia")
        }
      </section>
    `;
  } catch (error) {
    container.innerHTML = renderError(error);
  }
}

function employeeForm(detail) {
  const profile = detail?.profile || {};
  const isCreate = !profile.employee_id;
  return `
    <form id="employee-form" class="form-grid">
      <label>
        <span>Nomor Karyawan</span>
        <input name="employee_no" value="${display(profile.employee_no, "")}" ${isCreate ? "required" : ""} />
      </label>
      <label class="span-2">
        <span>Nama Lengkap</span>
        <input name="full_name" value="${display(profile.full_name, "")}" ${isCreate ? "required" : ""} />
      </label>
      <label>
        <span>Gender</span>
        <select name="gender">
          <option value="">Pilih</option>
          <option value="L" ${profile.gender === "L" ? "selected" : ""}>Laki-laki</option>
          <option value="P" ${profile.gender === "P" ? "selected" : ""}>Perempuan</option>
        </select>
      </label>
      <label>
        <span>Tempat Lahir</span>
        <input name="birth_place" value="${display(profile.birth_place, "")}" />
      </label>
      <label>
        <span>Tanggal Lahir</span>
        <input name="birth_date" type="date" value="${display(profile.birth_date, "")}" />
      </label>
      <label>
        <span>Agama</span>
        <select name="religion_id" id="religion-select">
          <option value="">Tidak diubah</option>
        </select>
      </label>
      <label>
        <span>Pendidikan</span>
        <select name="education_id" id="education-select">
          <option value="">Tidak diubah</option>
        </select>
      </label>
      <label>
        <span>Status Kawin</span>
        <select name="marital_status_id" id="marital-status-select">
          <option value="">Tidak diubah</option>
        </select>
      </label>
      <label>
        <span>Golongan Darah</span>
        <input name="blood_type" value="${display(profile.blood_type, "")}" />
      </label>
      <label>
        <span>Telepon</span>
        <input name="mobile_phone" value="${display(profile.mobile_phone, "")}" />
      </label>
      <label>
        <span>Email</span>
        <input name="email" type="email" value="${display(profile.email, "")}" />
      </label>
      <label class="span-2">
        <span>Path Foto</span>
        <input name="photo_path" value="${display(profile.photo_path, "")}" />
      </label>
      ${
        isCreate
          ? `
            <label>
              <span>Tipe Identitas</span>
              <input name="identity_type" placeholder="KTP" />
            </label>
            <label>
              <span>Nomor Identitas</span>
              <input name="identity_number" />
            </label>
            <label>
              <span>Tanggal Status</span>
              <input name="status_effective_date" type="date" value="${today()}" />
            </label>
          `
          : ""
      }
      <label class="toggle-row">
        <input name="is_active" type="checkbox" ${profile.is_active ?? true ? "checked" : ""} />
        <span>Aktif</span>
      </label>
      <div class="form-actions span-3">
        <a class="button button-secondary" href="${isCreate ? "#/employees" : `#/employees/${profile.employee_id}/detail`}">Batal</a>
        <button class="button button-primary" type="submit">${icon("shield")}Simpan</button>
      </div>
    </form>
  `;
}

export async function renderEmployeeEditPage(container, employeeId) {
  container.innerHTML = loading();
  let detail = null;
  if (employeeId) {
    try {
      detail = await employeeService.detail(employeeId);
    } catch (error) {
      container.innerHTML = renderError(error);
      return;
    }
  }

  container.innerHTML = `
    ${employeeId ? employeeHero(detail, "edit") : pageHeader({
      title: "Input Karyawan",
      subtitle: "Data induk karyawan disimpan terpisah dari jabatan, divisi, status kerja, BPJS, dan payroll.",
    })}
    <section class="surface">
      <div class="section-title"><h3>${employeeId ? "Edit Data Induk" : "Data Induk Baru"}</h3></div>
      ${employeeForm(detail)}
      <div id="form-message"></div>
    </section>
  `;

  const form = container.querySelector("#employee-form");
  await Promise.allSettled([
    populateReferenceSelect(container.querySelector("#religion-select"), referenceService.religions),
    populateReferenceSelect(container.querySelector("#education-select"), referenceService.educationLevels),
    populateReferenceSelect(container.querySelector("#marital-status-select"), referenceService.maritalStatuses),
  ]);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    const message = container.querySelector("#form-message");
    setBusy(button, "Menyimpan");
    try {
      const payload = serializeForm(form);
      if (payload.identity_type || payload.identity_number) {
        payload.identities = [
          {
            identity_type: payload.identity_type,
            identity_number: payload.identity_number,
            is_primary: true,
          },
        ];
      }
      delete payload.identity_type;
      delete payload.identity_number;

      const saved = employeeId
        ? await employeeService.update(employeeId, payload)
        : await employeeService.create(payload);
      navigate(`/employees/${saved.profile.employee_id}/detail`);
    } catch (error) {
      message.innerHTML = renderError(error);
    } finally {
      clearBusy(button);
    }
  });
}

export async function renderEmployeeStatusPage(container, employeeId) {
  container.innerHTML = loading();
  try {
    const detail = await employeeService.detail(employeeId);
    container.innerHTML = `
      ${employeeHero(detail, "status")}
      <section class="surface narrow">
        <div class="section-title"><h3>Ubah Status Kerja</h3></div>
        <form id="status-form" class="form-grid single">
          <label>
            <span>Status Kerja</span>
            <select name="employment_status_id" id="employment-status-select" required>
              <option value="">Pilih status</option>
            </select>
          </label>
          <label>
            <span>Tanggal Efektif</span>
            <input name="effective_date" type="date" value="${today()}" required />
          </label>
          <label>
            <span>Disetujui Oleh</span>
            <input name="approved_by" />
          </label>
          <label>
            <span>Catatan</span>
            <textarea name="notes" rows="4"></textarea>
          </label>
          <div class="form-actions">
            <a class="button button-secondary" href="#/employees/${employeeId}/detail">Batal</a>
            <button class="button button-primary" type="submit">${icon("shield")}Simpan Status</button>
          </div>
        </form>
        <div id="status-message"></div>
      </section>
    `;

    const form = container.querySelector("#status-form");
    await populateReferenceSelect(
      container.querySelector("#employment-status-select"),
      referenceService.employmentStatuses,
    );
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      setBusy(button, "Menyimpan");
      try {
        await employeeService.changeStatus(employeeId, serializeForm(form));
        navigate(`/employees/${employeeId}/detail`);
      } catch (error) {
        container.querySelector("#status-message").innerHTML = renderError(error);
      } finally {
        clearBusy(button);
      }
    });
  } catch (error) {
    container.innerHTML = renderError(error);
  }
}

export async function renderEmployeeMutationPage(container, employeeId) {
  container.innerHTML = loading();
  try {
    const detail = await employeeService.detail(employeeId);
    const current = detail.current_assignment || {};
    container.innerHTML = `
      ${employeeHero(detail, "mutation")}
      <section class="detail-grid">
        <div class="surface">
          <div class="section-title"><h3>Assignment Saat Ini</h3></div>
          ${infoRow("Estate", current.estate_name)}
          ${infoRow("Divisi", current.division_name)}
          ${infoRow("Jabatan", current.position_name)}
          ${infoRow("Mulai", current.start_date)}
        </div>
        <div class="surface">
          <div class="section-title"><h3>Form Mutasi</h3></div>
          <form id="mutation-form" class="form-grid">
            <label>
              <span>Tipe Mutasi</span>
              <select name="movement_type_id" id="movement-type-select" required>
                <option value="">Pilih tipe</option>
              </select>
            </label>
            <label>
              <span>Tanggal Mutasi</span>
              <input name="movement_date" type="date" value="${today()}" required />
            </label>
            <label>
              <span>Estate Tujuan</span>
              <select name="to_estate_id" id="to-estate-select">
                <option value="">Tetap</option>
              </select>
            </label>
            <label>
              <span>Divisi Tujuan</span>
              <select name="to_division_id" id="to-division-select">
                <option value="">Tetap</option>
              </select>
            </label>
            <label>
              <span>Jabatan Tujuan</span>
              <select name="to_position_id" id="to-position-select">
                <option value="">Tetap</option>
              </select>
            </label>
            <label>
              <span>Disetujui Oleh</span>
              <input name="approved_by" />
            </label>
            <label class="span-2">
              <span>Catatan</span>
              <textarea name="notes" rows="4"></textarea>
            </label>
            <div class="form-actions span-2">
              <a class="button button-secondary" href="#/employees/${employeeId}/detail">Batal</a>
              <button class="button button-primary" type="submit">${icon("transfer")}Proses Mutasi</button>
            </div>
          </form>
          <div id="mutation-message"></div>
        </div>
      </section>
    `;

    const form = container.querySelector("#mutation-form");
    await Promise.allSettled([
      populateReferenceSelect(container.querySelector("#movement-type-select"), referenceService.movementTypes),
      populateReferenceSelect(container.querySelector("#to-estate-select"), referenceService.estates, current.estate_id),
      populateReferenceSelect(container.querySelector("#to-division-select"), referenceService.divisions, current.division_id),
      populateReferenceSelect(container.querySelector("#to-position-select"), referenceService.positions, current.position_id),
    ]);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      setBusy(button, "Memutasi");
      try {
        await employeeService.mutate(employeeId, serializeForm(form));
        navigate(`/employees/${employeeId}/detail`);
      } catch (error) {
        container.querySelector("#mutation-message").innerHTML = renderError(error);
      } finally {
        clearBusy(button);
      }
    });
  } catch (error) {
    container.innerHTML = renderError(error);
  }
}

export async function renderEmployeeDocumentPage(container, employeeId) {
  container.innerHTML = loading();
  try {
    const detail = await employeeService.detail(employeeId);
    container.innerHTML = `
      ${employeeHero(detail, "documents")}
      <section class="detail-grid">
        <div class="surface">
          <div class="section-title"><h3>Dokumen Tersimpan</h3></div>
          ${
            detail.documents?.length
              ? `
                <div class="compact-list">
                  ${detail.documents
                    .map(
                      (document) => `
                        <div>
                          <strong>${escapeHtml(document.file_name)}</strong>
                          <span>${display(document.document_type_name)}</span>
                          <small>${display(document.uploaded_at)}</small>
                        </div>
                      `,
                    )
                    .join("")}
                </div>
              `
              : emptyState("Dokumen belum tersedia")
          }
        </div>
        <div class="surface">
          <div class="section-title"><h3>Upload Dokumen</h3></div>
          <form id="document-form" class="form-grid single">
            <label>
              <span>Tipe Dokumen</span>
              <select name="document_type_id" id="document-type-select" required>
                <option value="">Pilih dokumen</option>
              </select>
            </label>
            <label>
              <span>Nama File</span>
              <input name="file_name" required />
            </label>
            <label>
              <span>Path File</span>
              <input name="file_path" required />
            </label>
            <label>
              <span>Uploaded By</span>
              <input name="uploaded_by" />
            </label>
            <label>
              <span>Catatan</span>
              <textarea name="notes" rows="4"></textarea>
            </label>
            <div class="form-actions">
              <button class="button button-primary" type="submit">${icon("document")}Simpan Dokumen</button>
            </div>
          </form>
          <div id="document-message"></div>
        </div>
      </section>
    `;

    const form = container.querySelector("#document-form");
    await populateReferenceSelect(
      container.querySelector("#document-type-select"),
      referenceService.documentTypes,
    );
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      setBusy(button, "Menyimpan");
      try {
        await employeeService.addDocument(employeeId, serializeForm(form));
        await renderEmployeeDocumentPage(container, employeeId);
      } catch (error) {
        container.querySelector("#document-message").innerHTML = renderError(error);
      } finally {
        clearBusy(button);
      }
    });
  } catch (error) {
    container.innerHTML = renderError(error);
  }
}

export async function renderEmployeeHistoryPage(container, employeeId) {
  container.innerHTML = loading();
  try {
    const detail = await employeeService.detail(employeeId);
    const events = [
      ...(detail.movements || []).map((item) => ({
        date: item.movement_date,
        title: item.movement_type_name || `Movement ${item.movement_type_id}`,
        detail: item.notes || "Perubahan assignment",
      })),
      ...(detail.documents || []).map((item) => ({
        date: item.uploaded_at,
        title: `Dokumen ${item.document_type_name || item.document_type_id}`,
        detail: item.file_name,
      })),
      detail.current_status
        ? {
            date: detail.current_status.effective_date,
            title: `Status ${detail.current_status.status_name || detail.current_status.employment_status_id}`,
            detail: detail.current_status.notes || "Status efektif",
          }
        : null,
    ]
      .filter(Boolean)
      .sort((a, b) => String(b.date).localeCompare(String(a.date)));

    container.innerHTML = `
      ${employeeHero(detail, "history")}
      <section class="surface">
        <div class="section-title"><h3>Riwayat Karyawan</h3></div>
        ${
          events.length
            ? `
              <ol class="timeline">
                ${events
                  .map(
                    (event) => `
                      <li>
                        <time>${display(event.date)}</time>
                        <strong>${escapeHtml(event.title)}</strong>
                        <span>${display(event.detail)}</span>
                      </li>
                    `,
                  )
                  .join("")}
              </ol>
            `
            : emptyState("Riwayat belum tersedia")
        }
      </section>
    `;
  } catch (error) {
    container.innerHTML = renderError(error);
  }
}
