/** One definition for both the navbar dropdowns and the router. */
export const NAV = [
  { label: "Home", to: "/" },
  {
    label: "Evidence",
    to: "/evidence",
    items: [
      {
        to: "/evidence",
        title: "Results",
        blurb: "Pipeline vs. baseline on 57 scored cases",
      },
      {
        to: "/evidence/docs",
        title: "Docs",
        blurb: "Download the architecture, prompts and samples documents",
      },
      {
        to: "/evidence/cost",
        title: "Cost & caveats",
        blurb: "What it costs per note, and what the numbers don't cover",
      },
    ],
  },
  {
    label: "About",
    to: "/about",
    items: [
      {
        to: "/about",
        title: "Founder",
        blurb: "Who built this, and why",
      },
      {
        to: "/about/pipeline",
        title: "AI flowchart",
        blurb: "All nine nodes, on a scrubbable timeline",
      },
    ],
  },
];
