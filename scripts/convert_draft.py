import json
import sys


def _fps_to_rate(fps):
    """Best-effort conversion of a project fps to (rateNum, rateDen).

    Falls back to (30, 1) when fps is missing, non-numeric, zero, or negative.

    Note: this currently rounds to the nearest integer and uses a denominator
    of 1. NTSC-style non-integer fps (e.g. 23.976, 29.97) collapse to the
    nearest integer here; extend if/when the project needs that fidelity.
    """
    try:
        f = float(fps)
    except (TypeError, ValueError):
        return 30, 1
    if not (f > 0):
        return 30, 1
    return int(round(f)), 1


def convert(draft_path, out_path):
    with open(draft_path, "r") as f:
        draft = json.load(f)

    rate_num, rate_den = _fps_to_rate(
        draft.get("project", {}).get("fps")
    )

    media = []
    clips = []

    m_idx = 1
    c_idx = 1

    for track in draft.get("tracks", []):
        for c in track.get("clips", []):
            if c.get("src"):
                media_id = f"m{m_idx}"
                m_idx += 1
                media.append({
                    "id": media_id,
                    "path": c["src"]
                })

                clips.append({
                    "duration": float(c["duration_sec"]),
                    "fadeIn": 0.0,
                    "fadeOut": 0.0,
                    "filters": [],
                    "id": f"c{c_idx}",
                    "kind": "video",
                    "mediaId": media_id,
                    "name": f"Clip {c_idx}",
                    "offsetX": 0.0,
                    "offsetY": 0.0,
                    "opacity": 1.0,
                    "preservePitch": True,
                    "rotation": 0.0,
                    "scale": 1.0,
                    "sourceStart": 0.0,
                    "speed": 1.0,
                    "start": float(c["start_sec"]),
                    "trackId": "T1",
                    "videoEffects": [],
                    "volume": 1.0
                })
                c_idx += 1

    out = {
        "activeTimelineId": "TL1",
        "clips": clips,
        "concat": "0.1.0",
        "fonts": [],
        "media": media,
        "name": draft.get("project", {}).get("name", "cyber-heist-ep-01-infiltration"),
        "timelines": [
            {
                "clips": clips,
                "id": "TL1",
                "name": "Timeline 1",
                "tracks": [{ "id": "T1", "muted": False, "visible": True }],
                "video": { "width": 1920, "height": 1080, "rateNum": rate_num, "rateDen": rate_den }
            }
        ],
        "tracks": [{ "id": "T1", "muted": False, "visible": True }],
        "version": 1,
        "video": { "width": 1920, "height": 1080, "rateNum": rate_num, "rateDen": rate_den }
    }

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
