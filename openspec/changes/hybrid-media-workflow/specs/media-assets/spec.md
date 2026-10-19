# Media asset requirements

## Asset provenance

Every indexed or promoted asset SHALL identify its source type and stable
source reference, and SHALL include a content hash. Non-AI stock assets SHALL
include applicable license and attribution metadata before production use.

Prototype-generated images SHALL record the provider/model (or local tool),
prompt/settings when available, creation time, content hash, and review status.
Promotion SHALL retain this provenance rather than rewriting the asset as if it
were originally produced for the production library.

## Stock-source registry

The ingest pipeline SHALL use an explicit registry of supported sources and
their license/attribution requirements. New sources SHALL be added through the
existing ingest extension pattern and SHALL NOT bypass provenance validation.

The initial registry is based on the currently integrated YouTube, Coverr,
Mixkit, and Archive.org ingesters. Their terms vary by item and source; the
implementation must preserve the item-level usage conditions and must not
claim universal free commercial use.
