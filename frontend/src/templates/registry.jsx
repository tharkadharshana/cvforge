import SingleColumn from "./SingleColumn";
import Sidebar from "./Sidebar";

// Frontend mirror of backend cv/templates.py. Each entry knows how to render a CVData
// object for on-screen preview and print-to-PDF. `ats_safe` templates match what the
// backend renders into the downloadable ATS file; designer templates are print-only.
//
// A render entry is (cv) => JSX. Props are baked in here so callers just pass the CV.
export const TEMPLATES = {
  ats_classic: {
    name: "ATS Classic", ats_safe: true,
    render: (cv) => <SingleColumn cv={cv} accent="#1a1a1a" font="Helvetica, Arial, sans-serif" heading="rule" nameSize={26} />,
  },
  ats_modern: {
    name: "ATS Modern", ats_safe: true,
    render: (cv) => <SingleColumn cv={cv} accent="#0B6E4F" font="Helvetica, Arial, sans-serif" heading="caps" nameSize={28} />,
  },
  ats_serif: {
    name: "ATS Serif", ats_safe: true,
    render: (cv) => <SingleColumn cv={cv} accent="#1a1a1a" font="Georgia, 'Times New Roman', serif" heading="rule" nameSize={27} />,
  },
  aurora: {
    name: "Aurora (Designer)", ats_safe: false,
    render: (cv) => <Sidebar cv={cv} accent="#4F46E5" sidebarBg="#4F46E5" sidebarFg="#fff" font="Inter, system-ui, sans-serif" />,
  },
  sidebar_pro: {
    name: "Sidebar Pro (Designer)", ats_safe: false,
    render: (cv) => <Sidebar cv={cv} accent="#0F172A" sidebarBg="#0F172A" sidebarFg="#e2e8f0" font="Inter, system-ui, sans-serif" />,
  },
};

export const DEFAULT_TEMPLATE_ID = "ats_classic";

export function renderTemplate(templateId, cv) {
  const t = TEMPLATES[templateId] || TEMPLATES[DEFAULT_TEMPLATE_ID];
  return t.render(cv);
}
