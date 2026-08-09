import { Link } from "react-router-dom";
import { TEMPLATES, renderTemplate } from "../templates/registry";
import { SAMPLE_CV } from "../templates/sampleCv";

// Grid of selectable templates, each with a small live thumbnail (rendered
// against sample data, same as the full preview gallery) so the choice isn't
// blind before spending credits generating a real CV.
// `value` is the selected template id; `onSelect(id)` fires on click.
export default function TemplatePicker({ value, onSelect, busy }) {
  return (
    <div>
      <div className="flex justify-end mb-2">
        <Link to="/templates" target="_blank" rel="noreferrer" className="label text-accent">
          Preview with sample data ↗
        </Link>
      </div>
      <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">
      {Object.entries(TEMPLATES).map(([id, t]) => {
        const active = id === value;
        return (
          <button
            key={id}
            type="button"
            disabled={busy}
            onClick={() => onSelect(id)}
            className={`text-left border p-3 transition-colors ${active ? "border-accent" : "border-line hover:border-line2"} disabled:opacity-50`}
          >
            <div className="overflow-hidden border border-line2 mb-2" style={{ height: 110 }}>
              <div style={{ transform: "scale(0.19)", transformOrigin: "top left", width: "210mm" }}>
                {renderTemplate(id, SAMPLE_CV)}
              </div>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="font-display font-semibold text-[14px]">{t.name.replace(" (Designer)", "")}</span>
              {active && <span className="text-accent text-[11px]">● selected</span>}
            </div>
            <div className="mt-1">
              {t.ats_safe
                ? <span className="tag border-good/40 text-good">ATS-safe</span>
                : <span className="tag border-warn/40 text-warn">Designer · may hurt ATS</span>}
            </div>
          </button>
        );
      })}
      </div>
    </div>
  );
}
