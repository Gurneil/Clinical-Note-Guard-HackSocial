/**
 * Set GITHUB_USER and the navbar's black button becomes a real
 * "View on GitHub" link. Until it's set the button falls back to the Docs
 * page, because a working control with an honest label beats a GitHub button
 * that 404s.
 *
 * The repo has no git remote configured, which is why this isn't already
 * filled in — `devpost_submission.md` still carries the placeholder
 * `https://github.com/<your-username>/clinical-note-guard`.
 */
export const GITHUB_USER = "";

export const REPO_URL = GITHUB_USER
  ? `https://github.com/${GITHUB_USER}/clinical-note-guard`
  : "";

export const PIPELINE_FILM = "pipeline-flow.mp4";
