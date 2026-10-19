#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: render_draft.py <draft.json>")
        return 1
    
    draft_path = Path(sys.argv[1])
    if not draft_path.exists():
        print("File not found")
        return 1
        
    with open(draft_path) as f:
        draft = json.load(f)
        
    clips = draft["tracks"][0]["clips"]
    out_dir = draft_path.parent
    list_file = out_dir / "ffmpeg_list.txt"
    
    with open(list_file, "w") as f:
        for c in clips:
            f.write(f"file '{c['src']}'\n")
            
    out_mp4 = out_dir / "preview.mp4"
    if out_mp4.exists():
        out_mp4.unlink()
        
    print(f"Rendering {out_mp4} with ffmpeg...")
    subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out_mp4)], check=True)
    print("Done!")

if __name__ == "__main__":
    sys.exit(main())
