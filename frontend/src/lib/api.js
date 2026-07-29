const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

const TOKEN_KEY = "cvforge_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function req(path, { method = "GET", body, form, auth = true } = {}) {
  const headers = {};
  const token = tokenStore.get();
  if (auth && token) headers["Authorization"] = `Bearer ${token}`;

  let payload;
  if (form) {
    payload = new URLSearchParams(form).toString();
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE}${path}`, { method, headers, body: payload });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const j = await res.json();
      detail = j.detail || JSON.stringify(j);
    } catch {}
    if (res.status === 401) tokenStore.clear();
    const e = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    e.status = res.status;
    throw e;
  }
  if (res.status === 204) return null;
  return res.json();
}

// multipart POST: bearer header when a token exists, same error shape as req()
async function reqForm(path, fd) {
  const headers = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { method: "POST", headers, body: fd });
  if (!res.ok) {
    let detail = `${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch {}
    if (res.status === 401) tokenStore.clear();
    const e = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    e.status = res.status;
    throw e;
  }
  return res.json();
}

export const api = {
  base: BASE,
  register: (email, password, full_name) =>
    req("/auth/register", { method: "POST", auth: false, body: { email, password, full_name } }),
  login: (email, password) =>
    req("/auth/login", { method: "POST", auth: false, form: { username: email, password } }),

  getCV: () => req("/cv"),
  getStatus: () => req("/cv/status"),
  importCV: (raw_text) => req("/cv/import", { method: "POST", body: { raw_text } }),
  buildCV: (answers) => req("/cv/build", { method: "POST", body: { answers } }),
  replaceCV: (data) => req("/cv", { method: "PUT", body: data }),
  addQualification: (text) => req("/cv/qualification", { method: "POST", body: { text } }),

  importFile: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return reqForm("/cv/import-file", fd);
  },

  fitScore: (job_description, job_id) =>
    req("/generate/fit-score", { method: "POST", body: { job_description, job_id } }),
  startGeneration: (payload) => req("/generate/start", { method: "POST", body: payload }),
  tailor: (jobId) => req(`/generate/${jobId}/tailor`, { method: "POST" }),
  cover: (jobId) => req(`/generate/${jobId}/cover`, { method: "POST" }),
  critique: (jobId) => req(`/generate/${jobId}/critique`, { method: "POST" }),
  getJob: (jobId) => req(`/generate/${jobId}`),
  listApplications: (trackerStatus = "") =>
    req(`/applications${trackerStatus ? `?tracker_status=${encodeURIComponent(trackerStatus)}` : ""}`),
  applicationStats: () => req("/applications/stats"),
  getApplication: (id) => req(`/applications/${id}`),
  updateTrackerStatus: (id, tracker_status) =>
    req(`/applications/${id}/tracker`, { method: "PATCH", body: { tracker_status } }),
  improveApplication: (id, auto = false) =>
    req(`/applications/${id}/improve${auto ? "?auto=true" : ""}`, { method: "POST" }),
  // partial update: { tailored_cv?, cover_letter?, template_id?, template_overrides? }
  patchApplication: (id, patch) => req(`/applications/${id}`, { method: "PATCH", body: patch }),
  reevaluateApplication: (id) => req(`/applications/${id}/reevaluate`, { method: "POST" }),
  listTemplates: () => req("/templates"),

  // billing
  billingSummary: () => req("/billing/summary"),
  billingLedger: () => req("/billing/ledger"),
  billingOverview: () => req("/billing/overview"),
  checkout: (planId) => req(`/billing/checkout?plan_id=${encodeURIComponent(planId)}`, { method: "POST" }),
  billingPortal: () => req("/billing/portal", { method: "POST" }),

  // jobs
  fetchJobUrl: (url) => req("/jobs/fetch-url", { method: "POST", body: { url } }),
  searchJobs: (q, location = "", page = 1) =>
    req(`/jobs/search?q=${encodeURIComponent(q)}&location=${encodeURIComponent(location)}&page=${page}`),

  // public ATS checker (works logged out; token sent when present for paid detail)
  atsCheck: ({ file, rawText, jobDescription }) => {
    const fd = new FormData();
    if (file) fd.append("file", file);
    if (rawText) fd.append("raw_text", rawText);
    if (jobDescription) fd.append("job_description", jobDescription);
    return reqForm("/ats/check", fd);
  },

  downloadUrl: (id, doc, fmt) =>
    `${BASE}/applications/${id}/download?doc=${doc}&fmt=${fmt}`,
};

// authenticated file download (adds bearer header, triggers save)
export async function downloadFile(id, doc, fmt) {
  const res = await fetch(api.downloadUrl(id, doc, fmt), {
    headers: { Authorization: `Bearer ${tokenStore.get()}` },
  });
  if (!res.ok) throw new Error("download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${doc}_${id}.${fmt}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
