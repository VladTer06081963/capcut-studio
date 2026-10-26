---
name: asset-library
description: Inspect and document stock or prototype assets without weakening provenance, license, or approval rules.
---

# Asset library

Use only when the user requests asset discovery, ingest, indexing, or
provenance work.

1. Establish the exact source, target directory, and intended profile before
   downloading, writing, or indexing anything.
2. For stock assets, preserve source name, source ID/URL, license, attribution,
   and usage conditions. Downloadable does not mean production-eligible.
3. Keep prototype/generated assets separate from production assets until the
   user explicitly reviews and promotes them. Preserve model/provider,
   prompt/settings when available, and content hash.
4. The shared library index is additive. Never delete/replace rows or perform
   garbage collection without explicit scope and approval.
5. Do not generate media or call paid model APIs as an implicit fallback.
   Require the user's exact provider/model selection for a specific task.
6. Do not access `.env`, credentials, external disks, or large media unless
   required by the task. Prefer metadata and fixtures.
7. Verify the resulting metadata and report license/provenance gaps.
