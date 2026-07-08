// Minimal service worker. The extension is popup-driven; no background work needed
// beyond keeping the worker registered for the action popup.
chrome.runtime.onInstalled.addListener(() => {
  // no-op; settings live in chrome.storage.local, set from the popup.
});
