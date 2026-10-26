---
name: episode-planning
description: Prepare or review an episode brief/spec while preserving show continuity and lifecycle artifacts.
---

# Episode planning

Use only when the user requests episode planning, brief/spec work, or
continuity review.

1. Identify the exact show and episode directory. Read the show bible,
   `episode-log.md`, episode brief, current spec, and relevant prior episode
   records before proposing edits.
2. Check continuity against the bible and chronicle: cast, character state,
   location, props, timeline, style, and prior events. State conflicts rather
   than silently rewriting canon.
3. Keep the library-first workflow. A spec may reference known assets or
   request an asset; do not invoke generation to fill a gap.
4. Preserve the episode lifecycle. Revise draft/approved episodes through the
   documented revise path; a rendered episode is changed only by creating a
   remix/new episode. Never modify `rendered/final.mp4`.
5. Persist only the specifically requested artifact. Do not create approval
   sentinels, run assembly, or claim human approval on the user's behalf.
6. Validate JSON/Markdown consistency and report unresolved continuity flags.

Model provider, exact model, and any generation must be separately selected
and approved by the user for that task. The project's current generation
entrypoints do not yet enforce the approval artifact; do not run them as if
they were protected.
