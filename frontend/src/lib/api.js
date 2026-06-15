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

  importFile: async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/cv/import-file`, {
      method: "POST",
      headers: { Authorization: `Bearer ${tokenStore.get()}` },
      body: fd,
    });
    if (!res.ok) {
      let detail = `${res.status}`;
      try { detail = (await res.json()).detail || detail; } catch {}
      if (res.status === 401) tokenStore.clear();
      throw new Error(detail);
    }
    return res.json();
  },

  startGeneration: (payload) => req("/generate/start", { method: "POST", body: payload }),
  tailor: (jobId) => req(`/generate/${jobId}/tailor`, { method: "POST" }),
  cover: (jobId) => req(`/generate/${jobId}/cover`, { method: "POST" }),
  critique: (jobId) => req(`/generate/${jobId}/critique`, { method: "POST" }),
  getJob: (jobId) => req(`/generate/${jobId}`),
  listApplications: () => req("/applications"),
  getApplication: (id) => req(`/applications/${id}`),
  improveApplication: (id) => req(`/applications/${id}/improve`, { method: "POST" }),

  // billing
  billingSummary: () => req("/billing/summary"),
  billingLedger: () => req("/billing/ledger"),
  billingOverview: () => req("/billing/overview"),
  checkout: (planId) => req(`/billing/checkout?plan_id=${encodeURIComponent(planId)}`, { method: "POST" }),
  billingPortal: () => req("/billing/portal", { method: "POST" }),

  // jobs
  fetchJobUrl: (url) => req("/jobs/fetch-url", { method: "POST", body: { url } }),

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
