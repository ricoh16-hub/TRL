import {
  renderEmployeeDetailPage,
  renderEmployeeDocumentPage,
  renderEmployeeEditPage,
  renderEmployeeHistoryPage,
  renderEmployeeListPage,
  renderEmployeeMutationPage,
  renderEmployeeStatusPage,
} from "../modules/employee/employeePages.js";
import { renderDataQualityPage } from "../modules/dataQuality/dataQualityPages.js";
import { setRouteTitle } from "./state.js";

function parseHash() {
  const hash = (location.hash || "#/employees").replace(/^#\/?/, "");
  return hash.split("/").filter(Boolean);
}

export function navigate(path) {
  location.hash = path.startsWith("#") ? path : `#${path}`;
}

export async function renderRoute() {
  const view = document.getElementById("view");
  const segments = parseHash();
  const [moduleName, id, action] = segments;

  if (moduleName === "data-quality") {
    setRouteTitle("Data Quality");
    await renderDataQualityPage(view);
    return;
  }

  if (moduleName !== "employees") {
    navigate("/employees");
    return;
  }

  if (!id) {
    setRouteTitle("Daftar Karyawan");
    await renderEmployeeListPage(view);
    return;
  }

  if (id === "new") {
    setRouteTitle("Input Karyawan");
    await renderEmployeeEditPage(view, null);
    return;
  }

  const employeeId = Number(id);
  if (!Number.isInteger(employeeId) || employeeId <= 0) {
    navigate("/employees");
    return;
  }

  if (!action || action === "detail") {
    setRouteTitle("Detail Karyawan");
    await renderEmployeeDetailPage(view, employeeId);
    return;
  }

  if (action === "edit") {
    setRouteTitle("Edit Karyawan");
    await renderEmployeeEditPage(view, employeeId);
    return;
  }

  if (action === "status") {
    setRouteTitle("Ubah Status");
    await renderEmployeeStatusPage(view, employeeId);
    return;
  }

  if (action === "mutation") {
    setRouteTitle("Mutasi");
    await renderEmployeeMutationPage(view, employeeId);
    return;
  }

  if (action === "documents") {
    setRouteTitle("Dokumen");
    await renderEmployeeDocumentPage(view, employeeId);
    return;
  }

  if (action === "history") {
    setRouteTitle("Riwayat");
    await renderEmployeeHistoryPage(view, employeeId);
    return;
  }

  navigate(`/employees/${employeeId}/detail`);
}
