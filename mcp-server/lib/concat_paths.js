import path from "path";

/**
 * Pure path resolver for the Concat export step of an episode.
 *
 * Returns the paths that MCP `open_in_concat` operates on. Side-effect-free so
 * the function can be unit-tested without touching the filesystem or running
 * any subprocess.
 *
 * Layout contract:
 *   draft.json      : <repoRoot>/serials/<serial>/<ep>/rendered/draft.json
 *   project dir     : <home>/Desktop/Concat/<serial>-<ep>
 *   concat.json     : <home>/Desktop/Concat/<serial>-<ep>/concat.json
 */
export function resolveConcatProjectPaths(serial, ep, { repoRoot, home }) {
  if (typeof serial !== "string" || serial.length === 0) {
    throw new TypeError("serial must be a non-empty string");
  }
  if (typeof ep !== "string" || ep.length === 0) {
    throw new TypeError("ep must be a non-empty string");
  }
  if (typeof repoRoot !== "string" || repoRoot.length === 0) {
    throw new TypeError("repoRoot must be a non-empty string");
  }
  if (typeof home !== "string" || home.length === 0) {
    throw new TypeError("home must be a non-empty string");
  }

  const draftPath = path.join(repoRoot, "serials", serial, ep, "rendered", "draft.json");
  const projectName = `${serial}-${ep}`;
  const projectDir = path.join(home, "Desktop", "Concat", projectName);
  const concatJsonPath = path.join(projectDir, "concat.json");

  return { draftPath, projectDir, concatJsonPath, projectName };
}
