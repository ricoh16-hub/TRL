import { icon } from "./icons.js";

const items = [
  { href: "#/employees", label: "Daftar Karyawan", icon: "users" },
  { href: "#/employees/new", label: "Input Karyawan", icon: "plus" },
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
            (item.href === "#/employees" && currentHash.startsWith("#/employees/"));
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
