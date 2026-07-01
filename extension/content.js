// Content script: maps a CVForge autofill profile onto the job application form the
// user is looking at. It ONLY fills inputs — it never clicks submit. The user reviews
// every field and submits on the site itself, which keeps this compliant with each
// site's terms (same model as Simplify/JobWizard).
//
// Field matching is heuristic: for each profile value we look for inputs whose name,
// id, placeholder, aria-label or nearby <label> text contains known keywords. Works
// across generic forms and common ATS (Greenhouse, Lever, Workday, Ashby) which use
// recognizable field names.

(function () {
  // keyword -> profile key. First match wins per input.
  const MAP = [
    [["first name", "firstname", "given name", "fname"], "first_name"],
    [["last name", "lastname", "surname", "family name", "lname"], "last_name"],
    [["full name", "your name", "name"], "full_name"],
    [["email", "e-mail"], "email"],
    [["phone", "mobile", "telephone"], "phone"],
    [["linkedin"], "linkedin"],
    [["github"], "github"],
    [["website", "portfolio", "url"], "website"],
    [["location", "city", "address"], "location"],
    [["current title", "job title", "title", "position", "role"], "current_title"],
    [["current company", "employer", "company"], "current_company"],
    [["summary", "about", "bio"], "summary"],
    [["cover letter", "why", "message", "additional information"], "cover_letter"],
  ];

  function fieldText(el) {
    let t = [el.name, el.id, el.placeholder, el.getAttribute("aria-label")]
      .filter(Boolean).join(" ").toLowerCase();
    // associated <label for=id> or wrapping label
    if (el.id) {
      const lab = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (lab) t += " " + lab.textContent.toLowerCase();
    }
    const wrap = el.closest("label");
    if (wrap) t += " " + wrap.textContent.toLowerCase();
    return t;
  }

  function setValue(el, value) {
    if (value == null || value === "" || (el.value && el.value.trim())) return false;
    const proto = el.tagName === "TEXTAREA"
      ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, value);
    // fire events so React/controlled inputs pick up the change
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  window.__cvforgeAutofill = function (profile) {
    const inputs = Array.from(document.querySelectorAll(
      'input[type="text"], input[type="email"], input[type="tel"], input[type="url"], input:not([type]), textarea'
    ));
    let filled = 0;
    for (const el of inputs) {
      const text = fieldText(el);
      for (const [keywords, key] of MAP) {
        if (keywords.some((k) => text.includes(k))) {
          if (setValue(el, profile[key])) filled++;
          break;
        }
      }
    }
    return filled;
  };
})();
