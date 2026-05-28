import { request } from "./api.js";

export const employeeService = {
  list(params) {
    return request("/employees", { params });
  },

  detail(employeeId) {
    return request(`/employees/${employeeId}/detail`);
  },

  create(payload) {
    return request("/employees", {
      method: "POST",
      body: payload,
    });
  },

  update(employeeId, payload) {
    return request(`/employees/${employeeId}`, {
      method: "PUT",
      body: payload,
    });
  },

  changeStatus(employeeId, payload) {
    return request(`/employees/${employeeId}/status`, {
      method: "PATCH",
      body: payload,
    });
  },

  mutate(employeeId, payload) {
    return request(`/employees/${employeeId}/mutation`, {
      method: "POST",
      body: payload,
    });
  },

  addDocument(employeeId, payload) {
    return request(`/employees/${employeeId}/documents`, {
      method: "POST",
      body: payload,
    });
  },

  remove(employeeId) {
    return request(`/employees/${employeeId}`, {
      method: "DELETE",
    });
  },
};

export const referenceService = {
  religions: () => request("/references/religions"),
  educationLevels: () => request("/references/education-levels"),
  maritalStatuses: () => request("/references/marital-statuses"),
  employeeCategories: () => request("/references/employee-categories"),
  employmentStatuses: () => request("/references/employment-statuses"),
  movementTypes: () => request("/references/movement-types"),
  documentTypes: () => request("/references/document-types"),
  estates: () => request("/references/estates"),
  divisions: () => request("/references/divisions"),
  positions: () => request("/references/positions"),
};

export const dataQualityService = {
  summary(params) {
    return request("/data-quality/summary", { params });
  },

  issues(params) {
    return request("/data-quality/issues", { params });
  },

  updateIssue(issueId, payload) {
    return request(`/data-quality/issues/${issueId}`, {
      method: "PATCH",
      body: payload,
    });
  },
};
