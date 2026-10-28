## Purpose

Allow a reviewed still image to sit on a parallel, time-bounded visual track
in the episode timeline without silently replacing the matched video clip.

## ADDED Requirements

### Requirement: Still image as a parallel visual clip

The episode timeline SHALL be able to place a reviewed still image on a
separate, time-bounded visual/overlay track associated with the relevant
episode scene, while retaining the main video track sourced from registered
stock footage where available.

An image overlay SHALL NOT silently replace a matched video clip. The
specification and serialized timeline SHALL make the image source, track,
start time, duration, and display behavior explicit.

Before implementation is considered complete, the image clip representation,
supported formats, duration, aspect-ratio/fit behavior, and target Concat
project schema SHALL be verified with a local fixture. Do not assume the
existing video-overlay exporter supports still images.

#### Scenario: Image sits alongside the video track

- **WHEN** a reviewed still image is attached to an episode scene
- **THEN** the timeline SHALL place it on a separate, time-bounded visual/overlay track, and the main video track sourced from registered stock footage SHALL be retained

#### Scenario: An image never replaces the video clip

- **WHEN** a scene has both a matched video clip and a still image
- **THEN** the still image SHALL NOT replace the video clip

#### Scenario: The overlay is fully described

- **WHEN** the timeline is serialized
- **THEN** the image source, track, start time, duration and display behavior SHALL all be explicit in the specification and in the serialized timeline

#### Scenario: Format support is verified, not assumed

- **WHEN** still-image overlay support is considered complete
- **THEN** the image clip representation, supported formats, duration, aspect-ratio/fit behavior and target Concat project schema SHALL have been verified with a local fixture, and the existing video-overlay exporter SHALL NOT be assumed to support still images
