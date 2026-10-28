## Purpose

Every asset that enters the index or the production library SHALL carry enough
provenance to be attributed, licensed and reproduced later.

## ADDED Requirements

### Requirement: Asset provenance is recorded and preserved

Every indexed or promoted asset SHALL identify its source type and stable
source reference, and SHALL include a content hash. Non-AI stock assets SHALL
include applicable license and attribution metadata before production use.

Prototype-generated images SHALL record the provider/model (or local tool),
prompt/settings when available, creation time, content hash, and review status.
Promotion SHALL retain this provenance rather than rewriting the asset as if it
were originally produced for the production library.

#### Scenario: An indexed asset is attributable

- **WHEN** an asset is indexed
- **THEN** its row SHALL identify the source type, a stable source reference, and a content hash

#### Scenario: A stock asset carries its license before production use

- **WHEN** a non-AI stock asset is about to be used in production
- **THEN** the applicable license and attribution metadata SHALL be present

#### Scenario: A generated image records how it was made

- **WHEN** a prototype image is generated
- **THEN** it SHALL record the provider/model (or local tool), the prompt and settings when available, the creation time, the content hash, and the review status

#### Scenario: Promotion does not rewrite history

- **WHEN** a prototype asset is promoted into the production library
- **THEN** its original provenance SHALL be retained rather than the asset being rewritten as if it had always been produced for the production library

### Requirement: Supported stock sources come from an explicit registry

The ingest pipeline SHALL use an explicit registry of supported sources and
their license/attribution requirements. New sources SHALL be added through the
existing ingest extension pattern and SHALL NOT bypass provenance validation.

The initial registry is based on the currently integrated YouTube, Coverr,
Mixkit, and Archive.org ingesters. Their terms vary by item and source; the
implementation must preserve the item-level usage conditions and must not
claim universal free commercial use.

#### Scenario: A new source joins through the extension pattern

- **WHEN** a new stock source is added to the ingest pipeline
- **THEN** it SHALL be registered with its license/attribution requirements and SHALL NOT bypass provenance validation

#### Scenario: Item-level conditions are preserved

- **WHEN** an item from a registered source is ingested
- **THEN** its item-level usage conditions SHALL be preserved, and the implementation SHALL NOT claim universal free commercial use
