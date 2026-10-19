import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveConcatProjectPaths } from "../lib/concat_paths.js";

test("draftPath lives at serials/<serial>/<ep>/rendered/draft.json", () => {
  const r = resolveConcatProjectPaths("cyber-heist", "ep-01-infiltration", {
    repoRoot: "/repo",
    home: "/home/user"
  });
  assert.equal(r.draftPath, "/repo/serials/cyber-heist/ep-01-infiltration/rendered/draft.json");
});

test("projectDir and concatJsonPath live under <home>/Desktop/Concat/<serial>-<ep>", () => {
  const r = resolveConcatProjectPaths("stalker-reznik", "ep-02-anomaly", {
    repoRoot: "/repo",
    home: "/Users/vladteresena"
  });
  assert.equal(r.projectName, "stalker-reznik-ep-02-anomaly");
  assert.equal(r.projectDir, "/Users/vladteresena/Desktop/Concat/stalker-reznik-ep-02-anomaly");
  assert.equal(
    r.concatJsonPath,
    "/Users/vladteresena/Desktop/Concat/stalker-reznik-ep-02-anomaly/concat.json"
  );
});

test("returns exactly the four documented keys", () => {
  const r = resolveConcatProjectPaths("s", "e", { repoRoot: "/r", home: "/h" });
  assert.deepEqual(Object.keys(r).sort(), ["concatJsonPath", "draftPath", "projectDir", "projectName"].sort());
});

test("rejects empty or non-string inputs", () => {
  assert.throws(() => resolveConcatProjectPaths("", "ep-1", { repoRoot: "/r", home: "/h" }), /serial/);
  assert.throws(() => resolveConcatProjectPaths("s", "", { repoRoot: "/r", home: "/h" }), /ep/);
  assert.throws(() => resolveConcatProjectPaths("s", "e", null), /repoRoot/);
  assert.throws(() => resolveConcatProjectPaths("s", "e", { repoRoot: "", home: "/h" }), /repoRoot/);
  assert.throws(() => resolveConcatProjectPaths("s", "e", { repoRoot: "/r", home: "" }), /home/);
});
