#!/usr/bin/env bash
# Check the demo video against the submission rules (plan section 1, row 12).
#
# usage: tools/check_video.sh demo.mp4 [presentation/video_script.md]
#
#   - duration <= 175 s (the limit is 3:00; we target 2:50)
#   - size < 300 MB
#   - at least one audio stream, and it is AAC
#   - a 1920x1080 H.264 video stream
#   - optional: the script declares product footage of at least 100 s, on a line such as
#       Product footage: 0:26-2:16
#     (an en dash also works; the rules ask for at least 90 s of the solution in action)
# Needs ffprobe (ffmpeg) and python3. Exit 0 = all checks pass.
# Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
set -euo pipefail

video="${1:?usage: tools/check_video.sh demo.mp4 [video_script.md]}"
script="${2:-presentation/video_script.md}"
command -v ffprobe >/dev/null || { echo "ffprobe not found (install ffmpeg)"; exit 2; }
[ -f "$video" ] || { echo "no such file: $video"; exit 2; }

status=0
ffprobe -v error -show_entries format=duration,size -show_streams -of json "$video" |
python3 -c '
import json, sys
d = json.load(sys.stdin)
fmt, streams = d.get("format", {}), d.get("streams", [])
dur, size = float(fmt.get("duration", 0)), int(fmt.get("size", 0))
video = [s for s in streams if s.get("codec_type") == "video"]
audio = [s for s in streams if s.get("codec_type") == "audio"]
checks = [
    ("duration %.1f s <= 175 s" % dur, dur <= 175),
    ("size %.1f MB < 300 MB" % (size / 1e6), size < 300e6),
    ("audio streams: %d (need >= 1)" % len(audio), len(audio) >= 1),
    ("audio codec AAC", bool(audio) and all(s.get("codec_name") == "aac" for s in audio)),
    ("video codec H.264", bool(video) and video[0].get("codec_name") == "h264"),
    ("video 1920x1080 (got %sx%s)" % ((video[0].get("width"), video[0].get("height")) if video else ("?", "?")),
     bool(video) and (video[0].get("width"), video[0].get("height")) == (1920, 1080)),
]
bad = 0
for text, ok in checks:
    print(("ok    " if ok else "FAIL  ") + text)
    bad += not ok
sys.exit(1 if bad else 0)
' || status=1

if [ -f "$script" ]; then
  python3 - "$script" <<'PY' || status=1
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"Product footage:\s*(\d+):(\d{2})\s*[-–]\s*(\d+):(\d{2})", text)
if not m:
    print("FAIL  %s has no 'Product footage: M:SS-M:SS' line" % sys.argv[1]); sys.exit(1)
a, b = int(m.group(1)) * 60 + int(m.group(2)), int(m.group(3)) * 60 + int(m.group(4))
print(("ok    " if b - a >= 100 else "FAIL  ") + "product footage %d s (need >= 100 s)" % (b - a))
sys.exit(0 if b - a >= 100 else 1)
PY
else
  echo "note  $script not found; product-footage check skipped"
fi
exit $status
