// Shared helpers for print/preview CV templates. Templates use inline styles so
// they render identically on a white page regardless of the app's (dark) theme,
// which is what we want for print-to-PDF and for the small live preview.

export const contactBits = (c = {}) =>
  [c.email, c.phone, c.location, c.linkedin, c.github, c.website].filter(Boolean);

// section presence helpers keep templates tidy
export const hasSkills = (cv) => cv?.skills && Object.keys(cv.skills).length > 0;

// A4-ish page frame used by every template's PrintView.
export function Page({ children, style }) {
  return (
    <div
      style={{
        width: "210mm",
        minHeight: "297mm",
        margin: "0 auto",
        background: "#fff",
        color: "#1a1a1a",
        boxSizing: "border-box",
        ...style,
      }}
    >
      {children}
    </div>
  );
}
