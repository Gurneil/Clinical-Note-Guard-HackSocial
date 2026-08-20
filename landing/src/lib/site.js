/**
 * The navbar's black button links here. If GITHUB_USER is ever blanked, the
 * button falls back to the Docs page rather than 404-ing.
 */
export const GITHUB_USER = "Gurneil";

export const REPO_URL = GITHUB_USER
  ? `https://github.com/${GITHUB_USER}/Clinical-Note-Guard`
  : "";

export const PIPELINE_FILM = "pipeline-flow.mp4";
