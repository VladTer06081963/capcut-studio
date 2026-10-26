# Change: Hybrid media workflow with isolated prototype and production profiles

## Status

Proposed; implementation has not started. No external generation or paid API
calls are authorized by this proposal.

## Context

The project needs a way to develop creative direction while preserving a path
to high-quality finished work. A previous agent selected a more expensive
video model without the user's approval. Therefore, the user must choose or
approve the exact model for each generation task; software defaults must not
make that choice. This workflow does not require price research, price
snapshots, subscription-limit checks, or spend caps.

The current code can ingest stock video, index and match assets, and assemble
video/audio/overlay tracks. The current overlay path expects a video source;
image assets and their Concat timeline behavior are not yet implemented as a
verified contract.

## Decision

Use two **logical workflow profiles** with separate configuration and data
directories; Docker isolation is not part of this change.
Treat existing implementation as exploratory history, not an assumed
architecture. Reuse it only after checking it against this approved workflow.

### Prototype / creative-development profile

- Explore stories, prompts, visual direction, and references before promotion
  to the production library.
- Prefer local ComfyUI for image experiments. Draw Things was removed from the
  machine; ComfyUI is the local image backend. Keep experiments small — local
  diffusion is slow on consumer hardware, so prototype at reduced resolution
  and fewer steps, and promote only reviewed results.
- Subscription-based MiniMax image generation is available under the user's
  subscription. Do not query subscription limits, calculate a per-image price,
  or require a spend/credit cap. The user may inspect current prices or plan
  details independently; this is not a prerequisite to using the selected
  model.
- Paid video generation is not part of the normal workflow. It is permitted
  only for a specific task after the user explicitly names or approves the
  provider and exact model.
- Prototype assets and indexes are kept separate from production until reviewed
  and explicitly promoted.

### Production / working profile

- Build the primary motion track from free-to-access stock sources already
  integrated by the project (YouTube, Coverr, Mixkit, Archive.org) and future
  sources added through the documented ingest extension point.
- “Free” does not mean unrestricted: check and preserve license, attribution,
  source ID/URL, and usage conditions for every asset.
- Use reviewed still illustrations as a separate parallel visual/overlay track
  in Concat, associated with the relevant scene/time range. Do not treat
  image-on-track support as implemented until the exporter, conversion, and
  Concat UI behavior are verified.
- No paid video generation by default. Existing generated video assets may be
  reused only when their provenance and rights/usage metadata are present.
- Promotion from prototype to production is a human-reviewed action that
  preserves provenance, model/provider, license, and content hash.

## Goals

- Prevent silent provider/model changes across CLI, MCP, batch, retries, and
  fallback paths.
- Make inexpensive creative exploration distinct from the working episode
  pipeline without requiring Docker.
- Prefer reusable, license-documented stock video and approved still images for
  working episodes.
- Support still-image overlays as a first-class timeline input after Concat
  compatibility is verified.
- Keep provider choice replaceable and record evidence before promoting a
  model/provider or changing defaults.

## Non-goals

- Choosing a permanent image/video provider or final cloud model.
- Automating provider price discovery or enforcing a usage/spend cap for the
  user's MiniMax subscription.
- Enabling unattended or nightly paid generation.
- Adding Docker, multi-user workflows, or a render farm.
- Assuming every YouTube/stock item is legally reusable merely because it can
  be downloaded.

## Acceptance criteria

- Prototype and production profiles have explicit, separate config and data
  roots and cannot silently read/write each other's working assets.
- Every generation task must have an explicitly user-selected provider and
  exact model. The user's model selection/approval is sufficient authorization
  for that specific task; a configured default is not. Do not require price
  research, a price snapshot, output-count cap, or spend/credit cap.
- Record the model approval as a short-lived, one-task artifact outside the
  repository. It binds the selected provider/model and task scope, is claimed
  atomically before generation, and is retained as a consumed/expired audit
  record. It contains no credentials.
- Do not silently switch to a different model/provider or automatically
  fallback to another model. If the selected model cannot be used, stop and let
  the user choose/approve an alternative. Do not query provider prices or plan
  limits unless the user asks.
- Production flow can ingest from registered stock sources with source and
  license/attribution metadata and does not invoke video generation.
- A still image can be represented as a time-bounded Concat visual clip on the
  parallel track, converted to the target Concat format, and verified using
  local fixtures/UI without paid generation.
- Promotion from prototype to production is explicit, reviewable, and
  provenance-preserving.
- Tests cover profile separation, model approval and no silent fallback, source
  metadata, and image timeline serialization without live generation calls.

## Open decisions before implementation

- Which image formats, aspect-ratio behavior, duration, and fit/crop policy
  Concat accepts.
- How images are described in the episode spec: explicit scene asset reference,
  generated illustration request, or both.
- Exact supported free-source registry and per-source license/attribution
  requirements; source additions remain subject to license review.
- Whether production overlays are still-image-only initially or may also
  include previously approved video overlays.

## Validation approach

- Inspect all generation entrypoints and prove submissions are blocked when
  the task lacks approval for an exact provider/model using mocked clients.
- Exercise stock ingest and image overlay serialization only against fixtures.
- Verify the converted Concat project with a local sample image/project; do not
  invoke paid generation to validate the timeline contract.
- Record model selection and any manual UI validation in the corresponding
  task/audit record; do not collect pricing/credit assumptions unless the user
  requests them.
