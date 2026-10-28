## Purpose

Separate prototype exploration from production episode work so that assets,
indexes and outputs cannot leak from one into the other, and so that paid
generation always happens under an explicit, one-task approval.

## ADDED Requirements

### Requirement: Prototype and production separation

The system SHALL provide distinct logical prototype and production profiles.
Each profile SHALL resolve configuration, library/index, temporary files, and
episode/output data to explicit roots.

The system SHALL NOT silently promote, index, or assemble prototype assets as
production assets. Promotion SHALL be an explicit, reviewable operation that
preserves the original asset provenance and checksum.

The profiles do not require Docker. The implementation may use separate
configuration files and directories, but must prevent accidental cross-profile
writes and make the active profile visible to the operator.

#### Scenario: Prototype asset is not indexed as production

- **WHEN** an asset created under the prototype profile is present on disk
- **THEN** the production index SHALL NOT contain a row for it until a promotion operation is performed

#### Scenario: Promotion is explicit and preserves provenance

- **WHEN** an operator promotes a prototype asset into the production library
- **THEN** the operation SHALL be an explicit, reviewable step that preserves the original provenance and checksum rather than rewriting the asset

#### Scenario: Active profile is visible

- **WHEN** an operator inspects the running system
- **THEN** the active profile SHALL be discoverable, and its configuration, index, temporary and episode/output roots SHALL resolve under that profile's explicit roots

### Requirement: Paid generation requires an explicit one-task approval

Every generation task SHALL have a provider and exact model explicitly selected
or approved by the user. That selection SHALL authorize generation for the
current task scope; a configured default SHALL NOT count as approval.

The system SHALL provide a local desktop-accessible interface for selecting a
provider/model and describing the task scope. The initial model list SHALL be
read from a local, explicitly maintained registry; opening the interface SHALL
not query provider catalogs, prices, subscription limits, or external services.
Selecting a model SHALL NOT itself submit a generation request.
The frontend source SHALL be kept in `frontend/model-approval/` as separate
HTML, CSS, and JavaScript files; the local Python process SHALL serve the UI and
its same-origin API.

The approval SHALL be represented by a persisted, one-task artifact stored
outside the repository and protected from group/other access. The artifact
SHALL bind to the provider, exact model ID, task scope, approval timestamp, and
state. It SHALL contain no price snapshot, spend cap, output-count cap, API
keys, or other credentials. It SHALL expire no later than 30 minutes after
approval and SHALL be atomically claimed before generation so it cannot be
replayed or used concurrently.

The system SHALL NOT require price research, price snapshots, output-count
caps, spend caps, or plan-limit lookups as a precondition for generation. The
user may inspect prices/plan details independently. In particular, subscription
MiniMax image generation SHALL NOT be subject to an application-imposed
per-output price calculation or credit cap.

The system SHALL NOT silently change provider/model or automatically fallback
to a different provider/model. If the selected model is unavailable or fails,
the system SHALL report the failure and wait for the user to select/approve an
alternative. It MAY retry a transient request using the same approved model
within the current task only when the retry is not a duplicate submission of
an ambiguous job; an ambiguous timeout SHALL be reported rather than silently
resubmitted.

Approval artifacts SHALL be retained as consumed/expired audit records rather
than deleted. State changes SHALL be atomic so interruption cannot make an
already-claimed artifact reusable.

The local interface SHALL bind only to loopback by default, SHALL NOT collect
provider credentials, and SHALL make it clear that approval is limited to the
displayed model and task scope.

Local generation that cannot incur charges may be used for prototypes. A
subscription-based image provider may be used after the user selects/approves
the model; this project SHALL NOT inspect or enforce the subscription's usage
limits.

#### Scenario: A configured default is not approval

- **WHEN** a generation task runs and the provider/model comes only from a configured default
- **THEN** the task SHALL be refused, because a default does not authorize spend

#### Scenario: Selecting a model submits nothing

- **WHEN** the operator selects a provider and exact model in the local interface and confirms the task scope
- **THEN** no generation request SHALL be submitted, and the interface SHALL NOT query provider catalogs, prices, subscription limits, or external services

#### Scenario: An approval authorizes one task only

- **WHEN** an approval artifact is claimed for a task
- **THEN** the claim SHALL be atomic and consume the artifact, so it cannot be replayed or used concurrently

#### Scenario: The artifact expires

- **WHEN** more than 30 minutes have passed since the approval
- **THEN** the artifact SHALL no longer satisfy the approval requirement

#### Scenario: The artifact holds no credentials

- **WHEN** an approval artifact is inspected
- **THEN** it SHALL bind the provider, exact model id, task scope, approval timestamp and state, and SHALL contain no price snapshot, spend cap, output-count cap, API keys, or other credentials

#### Scenario: The approved model fails

- **WHEN** the approved model is unavailable or fails
- **THEN** the system SHALL report the failure and wait for the user to select or approve an alternative, and SHALL NOT silently switch provider or model

#### Scenario: An ambiguous timeout is not resubmitted

- **WHEN** a generation request times out and it is unclear whether the provider accepted it
- **THEN** the system SHALL report the ambiguity rather than silently resubmitting the same job

#### Scenario: Consumed artifacts are kept

- **WHEN** an approval artifact has been claimed or has expired
- **THEN** it SHALL be retained as an audit record rather than deleted

#### Scenario: The interface binds to loopback only

- **WHEN** the local approval interface starts
- **THEN** it SHALL bind only to loopback by default, SHALL NOT collect provider credentials, and SHALL make clear that approval is limited to the displayed model and task scope

#### Scenario: Subscription image generation is not capped

- **WHEN** a subscription-based image provider is used after the user selects and approves the model
- **THEN** the system SHALL NOT inspect or enforce the subscription's usage limits, and SHALL NOT impose a per-output price calculation or credit cap

### Requirement: Production media inputs carry their conditions

The production profile SHALL support registered stock sources and reviewed
still-image assets. Stock assets SHALL retain source identifiers and
license/attribution conditions. An item being downloadable SHALL NOT by itself
make it eligible for production use.

Paid video generation SHALL be disabled in the ordinary production workflow.
An exception SHALL use the paid-generation approval requirements and be
recorded as a separately approved experiment.

#### Scenario: Downloadable does not mean usable

- **WHEN** an item is downloadable from a registered stock source
- **THEN** its production eligibility SHALL still depend on the item-level source identifier and license/attribution conditions

#### Scenario: Paid video generation in the production workflow

- **WHEN** the ordinary production workflow runs
- **THEN** paid video generation SHALL be disabled, and any exception SHALL follow the approval requirements and be recorded as a separately approved experiment
