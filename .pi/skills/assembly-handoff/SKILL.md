---
name: assembly-handoff
description: Validate an episode's assembly inputs and prepare a safe Concat handoff without rendering finals.
---

# Assembly handoff

Use only when the user requests episode assembly preparation or a Concat
handoff.

1. Confirm the exact show/episode, lifecycle state, `.approved` status, spec,
   matched assets, and source-file hashes required by the current contract.
2. Do not silently create `.approved`, substitute an asset, generate missing
   media, or switch a model/provider.
3. Treat `rendered/final.mp4` as immutable. An already-rendered episode is not
   re-rendered; use a new remix/episode for edits.
4. Keep draft/preview outputs separate from final output. Concat UI actions and
   external process launches need the user-requested scope; do not claim UI
   verification unless it was performed and checked.
5. Prefer fixture-only conversion/serialization tests. Do not launch paid
   generation to validate an assembly format.
6. Report missing approval, broken hashes, absent licenses, unsupported image
   tracks, or any other blocker explicitly; do not produce a success-shaped
   draft with silent placeholders.
