## Purpose

Defines how a generation entrypoint obtains and consumes the model-approval
artifact, and what it must not do when the approval is missing or the chosen
provider is unavailable.

## ADDED Requirements

### Requirement: Remote and paid generation requires a claimed approval artifact

A generation entrypoint SHALL NOT submit a job to a remote or paid provider
unless an approval artifact has been resolved and atomically claimed for that
exact provider, model, and task scope. The artifact SHALL be consumed by the
claim, so that one approval authorizes one task only.

A configured default provider or model SHALL NOT be treated as approval. The
provider and exact model used for a task SHALL be the ones named in the
claimed artifact.

Local generation that does not leave the machine SHALL NOT require an
approval artifact. The requirement exists to prevent a task from crossing
into a paid or remote route, not to gate free local work.

#### Scenario: Paid generation without an approval artifact

- **WHEN** a generation entrypoint is invoked for a remote or paid provider and no valid, unclaimed, unexpired approval artifact matches the requested provider, model, and task scope
- **THEN** the entrypoint exits non-zero and submits no job

#### Scenario: Approval artifact binds provider, model, and scope

- **WHEN** an approval artifact is claimed for one task
- **THEN** the claim is consumed atomically and the same artifact cannot be claimed for a second task

#### Scenario: Configured default is not approval

- **WHEN** a provider or model is configured as a default and the user has not named or approved it for the current task
- **THEN** the default SHALL NOT be used for that task

#### Scenario: Local generation does not require an artifact

- **WHEN** a generation entrypoint is invoked for a provider that does not leave the machine
- **THEN** the entrypoint proceeds without an approval artifact

### Requirement: No silent provider or model switch

An entrypoint SHALL NOT attempt a provider or model other than the one named
in the claimed approval artifact. On provider failure the entrypoint SHALL
stop and report the failure to the caller.

A fallback chain over alternative providers or models SHALL NOT be applied
implicitly. If a user wants an alternative provider or model, that choice
SHALL be named and approved as a separate task. A provider default SHALL NOT
be substituted for an unavailable approved provider.

#### Scenario: Approved provider fails

- **WHEN** the approved provider returns a failure
- **THEN** the entrypoint reports the failure and does not contact any other provider

#### Scenario: Another provider is available but not approved

- **WHEN** the approved provider is unavailable and a different provider is available
- **THEN** the entrypoint does not contact the unapproved provider

### Requirement: Explicit local-to-remote transition

A task scoped to a local model SHALL NOT fall through to a remote or paid
provider when the local provider is unreachable. The entrypoint SHALL stop
and report that the local provider is unavailable.

A remote provider MAY be used for a task only when the claimed approval
artifact names that remote provider and model.

#### Scenario: Local provider is unreachable

- **WHEN** a task approved for a local provider is run and the local provider is unreachable
- **THEN** the entrypoint stops, reports the local provider as unavailable, and does not contact a remote provider

### Requirement: Failure reporting

A generation entrypoint SHALL exit non-zero when any requested generation
fails, and SHALL NOT report success for a run in which every requested
generation failed.

The entrypoint SHALL distinguish, in its output, a failure to obtain
approval from a provider-side failure. Both are refusals to proceed, and the
caller SHALL be able to tell them apart without reading the source.

#### Scenario: Every generation in a run fails

- **WHEN** every requested generation in a run fails
- **THEN** the entrypoint exits non-zero

#### Scenario: Approval failure is distinguishable from provider failure

- **WHEN** the entrypoint refuses because approval could not be obtained
- **THEN** the reported reason is distinguishable from a provider-side failure

### Requirement: No unenforced spend-guard configuration

A configuration value that reads like a spend guard SHALL either be enforced
by the guard or be removed from the public configuration surface. A constant
that is defined, documented, and never consulted SHALL NOT remain in the
configuration surface.

#### Scenario: Budget constant is defined but never consulted

- **WHEN** a configuration constant is named as a budget or a spend guard
- **THEN** it is either consulted by the guard before a paid submission, or absent from the public configuration surface
