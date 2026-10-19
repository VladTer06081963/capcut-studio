# Concat still-image track requirements

## Still image as a parallel visual clip

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
