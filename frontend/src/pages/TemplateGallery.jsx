import { TEMPLATES, renderTemplate } from "../templates/registry";
import { SAMPLE_CV } from "../templates/sampleCv";
import { Banner } from "../components/ui";

// Pure client-side preview: renders every template with dummy CV data so users
// can see what each one looks like before spending any credits generating a
// real CV. No backend or LLM call involved.
export default function TemplateGallery() {
  return (
    <div className="rise space-y-5">
      <div>
        <h1 className="font-display font-extrabold text-3xl mb-1">Template gallery</h1>
        <p className="label">Preview with sample data — free, no credits used.</p>
      </div>
      <Banner kind="info">
        Designer templates look great for humans but may parse poorly in some ATS. Your ATS score
        and "Download ATS" files always use the safe layout, whichever template you pick.
      </Banner>
      <div className="grid sm:grid-cols-2 gap-6">
        {Object.entries(TEMPLATES).map(([id, t]) => (
          <div key={id} className="panel p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="font-display font-semibold text-[15px]">{t.name.replace(" (Designer)", "")}</span>
              {t.ats_safe
                ? <span className="tag border-good/40 text-good">ATS-safe</span>
                : <span className="tag border-warn/40 text-warn">Designer · may hurt ATS</span>}
            </div>
            <div className="overflow-hidden border border-line" style={{ height: 420 }}>
              <div style={{ transform: "scale(0.4)", transformOrigin: "top left", width: "210mm" }}>
                {renderTemplate(id, SAMPLE_CV)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
