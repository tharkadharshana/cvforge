import { TEMPLATES } from "../templates/registry";

// Grid of selectable templates with an ATS-safe badge vs a "Designer" warning tag.
// `value` is the selected template id; `onSelect(id)` fires on click.
export default function TemplatePicker({ value, onSelect, busy }) {
  return (
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
  );
}
