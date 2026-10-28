## Purpose

Defines what an episode approval is bound to, when a change to the approved
content revokes it, and what the final renderer must verify before it
encodes anything.

## ADDED Requirements

### Requirement: Approval records the reviewed spec content

An episode approval SHALL record the content hash of the `spec.json` that was
reviewed. The presence of the `.approved` sentinel SHALL continue to mean
"approved"; the recorded hash SHALL identify what was approved.

The approval and its recorded hash SHALL be written atomically, so that a
crash cannot leave an approval without a hash or a hash without an approval.

#### Scenario: Approval records the current spec hash

- **WHEN** an episode is approved
- **THEN** the recorded hash equals the sha256 of the `spec.json` present at that moment

#### Scenario: Approval write is interrupted

- **WHEN** the approval write is interrupted part-way
- **THEN** the episode has neither an approval nor a recorded hash, and no partial approval remains

### Requirement: Spec rewrite revokes approval

Any operation that rewrites an episode's `spec.json` SHALL revoke the
episode's approval first, in the same operation. The revocation SHALL remove
both the `.approved` sentinel and the recorded hash.

After such a rewrite the episode SHALL be in the draft state, and a
subsequent final render SHALL refuse until the episode is approved again. A
write to `spec.json` SHALL NOT be possible while leaving a stale approval in
place.

#### Scenario: Spec is regenerated after approval

- **WHEN** `spec.json` is rewritten for an approved episode
- **THEN** the approval and the recorded hash are absent afterwards

#### Scenario: Episode state after regeneration

- **WHEN** `spec.json` has been rewritten
- **THEN** the episode is in the draft state and a final render refuses until it is approved again

### Requirement: Final render verifies the bound hash

A final render SHALL verify, before any encoding work begins, that the
recorded approval hash matches the current `spec.json`. A mismatch SHALL
abort the render with a non-zero exit and an explicit message naming both
hashes.

On a mismatch the render SHALL NOT create, replace, or modify
`rendered/final.mp4`, and SHALL NOT modify `rendered/spec.sha256`. The
existing `spec.sha256` idempotency key SHALL remain the key for "already
rendered"; the approval hash is a separate, earlier gate and the two SHALL
NOT be conflated.

#### Scenario: Approved spec matches

- **WHEN** the recorded hash matches the current `spec.json` and `final.mp4` does not exist
- **THEN** the render proceeds

#### Scenario: Spec changed after approval

- **WHEN** the recorded hash does not match the current `spec.json`
- **THEN** the render aborts with a non-zero exit, names both hashes, and leaves `final.mp4` and `spec.sha256` untouched

#### Scenario: Idempotency key stays separate

- **WHEN** a render is skipped because `final.mp4` already exists with a matching `spec.sha256`
- **THEN** the decision is made on `spec.sha256` and not on the approval hash

### Requirement: Legacy unbound approvals are refused

An approval that carries no recorded hash SHALL be reported as unbound and
SHALL NOT satisfy the approval gate for a new render. The refusal message
SHALL name the command that re-approves the episode against the current
`spec.json`.

#### Scenario: Legacy episode with an empty sentinel

- **WHEN** an episode has an `.approved` sentinel that carries no recorded hash and a render is requested
- **THEN** the render is refused and the message names the re-approval command

### Requirement: Approval is a recorded act

Approving an episode SHALL be performed by a single supported operation that
records the hash of the current `spec.json`. The operation SHALL be
idempotent, and SHALL NOT approve an episode whose `spec.json` is missing or
unreadable. A bare filesystem marker SHALL NOT be sufficient to satisfy the
gate.

#### Scenario: Approve twice

- **WHEN** the approval operation is run twice against the same unchanged `spec.json`
- **THEN** the second run is a no-op and the recorded hash is unchanged

#### Scenario: Approve without a readable spec

- **WHEN** the approval operation is run for an episode whose `spec.json` is missing or unreadable
- **THEN** the operation fails with a non-zero exit and records no approval
