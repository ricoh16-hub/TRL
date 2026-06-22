import { icon } from "./icons.js";

const items = [
  { href: "#/manpower", label: "Manpower", icon: "dashboard" },
  { href: "#/employees", label: "Daftar Karyawan", icon: "users" },
  { href: "#/employees/new", label: "Input Karyawan", icon: "plus" },
  { href: "#/data-quality", label: "Data Quality", icon: "shield" },
];

export function renderSidebar(currentHash) {
  return `
    <div class="brand">
      <div class="brand-mark">GBR</div>
      <div>
        <strong>PT GBR Plantation</strong>
        <span>HRIS & Manpower</span>
      </div>
    </div>
    <nav class="sidebar-nav" aria-label="Navigasi utama">
      ${items
        .map((item) => {
          const active =
            currentHash === item.href ||
            (item.href === "#/manpower" && currentHash.startsWith("#/manpower")) ||
            (item.href === "#/employees" && currentHash.startsWith("#/employees/")) ||
            (item.href === "#/data-quality" && currentHash.startsWith("#/data-quality"));
          return `
            <a class="${active ? "active" : ""}" href="${item.href}">
              ${icon(item.icon)}
              <span>${item.label}</span>
            </a>
          `;
        })
        .join("")}
    </nav>
    <div class="sidebar-foot">
      <span class="dot"></span>
      <span>FastAPI Backend</span>
    </div>
  `;
}
