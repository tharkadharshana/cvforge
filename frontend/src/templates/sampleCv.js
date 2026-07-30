// Dummy CVData used only to preview templates with realistic content, at zero
// cost -- no backend/LLM call, so users can see what a template looks like
// before spending any credits generating a real one.
export const SAMPLE_CV = {
  contact: {
    full_name: "Jordan Rivera", email: "jordan.rivera@email.com", phone: "+1 555 010 2938",
    location: "Austin, TX", linkedin: "linkedin.com/in/jordanrivera", github: "github.com/jrivera",
    website: "jordanrivera.dev",
  },
  summary: "Backend engineer with 6 years building high-throughput APIs and data pipelines. "
    + "Shipped services handling 50M+ requests/day at scale; led migration from monolith to microservices.",
  skills: {
    Languages: ["Python", "Go", "TypeScript", "SQL"],
    "Frameworks & Tools": ["FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS"],
  },
  experience: [
    {
      title: "Senior Backend Engineer", company: "Northwind Data", location: "Austin, TX",
      start: "2022", end: "Present",
      bullets: [
        "Redesigned the ingestion pipeline, cutting p99 latency from 4.2s to 380ms",
        "Led a 4-engineer team migrating a monolith to 12 microservices with zero downtime",
        "Introduced contract testing, reducing cross-service incidents by 60%",
      ],
    },
    {
      title: "Backend Engineer", company: "Fenwick Labs", location: "Remote",
      start: "2019", end: "2022",
      bullets: [
        "Built a billing service processing $2M/month in transactions",
        "Owned the on-call rotation for 3 core services, maintaining 99.95% uptime",
      ],
    },
  ],
  projects: [
    { name: "queuewatch", description: "Open-source Redis queue monitor with alerting",
      tech: ["Python", "Redis"], bullets: ["600+ GitHub stars", "Used by 3 YC startups"], link: "github.com/jrivera/queuewatch" },
  ],
  education: [
    { degree: "B.S. Computer Science", institution: "University of Texas at Austin", location: "Austin, TX",
      start: "2015", end: "2019", details: ["Dean's List, 4 semesters"] },
  ],
  certifications: ["AWS Certified Solutions Architect"],
  awards: ["Hackathon Winner, Austin Tech Week 2023"],
  languages: ["English (native)", "Spanish (fluent)"],
};
