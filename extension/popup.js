// Popup: store settings and trigger an autofill on the active tab.
const $ = (id) => document.getElementById(id);
const msg = (text, ok) => { const m = $("msg"); m.textContent = text; m.className = "msg " + (ok ? "ok" : "err"); };

async function load() {
  const s = await chrome.storage.local.get(["apiBase", "token", "appId"]);
  if (s.apiBase) $("apiBase").value = s.apiBase;
  if (s.token) $("token").value = s.token;
  if (s.appId) $("appId").value = s.appId;
}

async function save() {
  await chrome.storage.local.set({
    apiBase: $("apiBase").value.trim().replace(/\/$/, ""),
    token: $("token").value.trim(),
    appId: $("appId").value.trim(),
  });
  msg("Saved.", true);
}

async function fetchProfile() {
  const { apiBase, token, appId } = await chrome.storage.local.get(["apiBase", "token", "appId"]);
  if (!apiBase || !token || !appId) throw new Error("Set API URL, token and application ID first.");
  const res = await fetch(`${apiBase}/applications/${appId}/autofill-profile`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Couldn't load profile (${res.status}).`);
  return res.json();
}

async function fill() {
  try {
    await save();
    msg("Loading profile…", true);
    const profile = await fetchProfile();
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (p) => window.__cvforgeAutofill && window.__cvforgeAutofill(p),
      args: [profile],
    });
    msg(result ? `Filled ${result} field(s). Review and submit yourself.` : "No matching fields found on this page.", true);
  } catch (e) {
    msg(e.message, false);
  }
}

$("save").addEventListener("click", () => save().catch((e) => msg(e.message, false)));
$("fill").addEventListener("click", fill);
load();
