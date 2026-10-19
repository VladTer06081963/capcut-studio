# Workflow profile requirements

## Prototype and production separation

The system SHALL provide distinct logical prototype and production profiles.
Each profile SHALL resolve configuration, library/index, temporary files, and
episode/output data to explicit roots.

The system SHALL NOT silently promote, index, or assemble prototype assets as
production assets. Promotion SHALL be an explicit, reviewable operation that
preserves the original asset provenance and checksum.

The profiles do not require Docker. The implementation may use separate
configuration files and directories, but must prevent accidental cross-profile
writes and make the active profile visible to the operator.

## Paid generation approval

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

## Production media inputs

The production profile SHALL support registered stock sources and reviewed
still-image assets. Stock assets SHALL retain source identifiers and
license/attribution conditions. An item being downloadable SHALL NOT by itself
make it eligible for production use.

Paid video generation SHALL be disabled in the ordinary production workflow.
An exception SHALL use the paid-generation approval requirements and be
recorded as a separately approved experiment.
