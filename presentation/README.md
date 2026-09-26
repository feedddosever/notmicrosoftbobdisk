# Presentation materials

Drafted by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. The builder edits, records and submits.

| File | What it is | Status |
|---|---|---|
| `statements.md` | Problem & Solution Statement and IBM Bob Usage Statement (each 500 words or fewer) | Draft with `[placeholders]` |
| `video_script.md` | 2:50 narrated script, shot list and captions | Draft with `[placeholders]` |
| `slides.md` | 9-slide deck (Marp Markdown) | Draft with `[placeholders]` |
| `cover.html` | 1920×1080 cover image source | Draft with `[placeholders]` |

Placeholders are filled only from `reports/*.json`, `bob_sessions/INDEX.md` and the task screenshots.

## Render (Windows, from the repository folder)

Cover PNG (headless Chrome):

```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new --disable-gpu --hide-scrollbars --window-size=1920,1080 --virtual-time-budget=4000 --screenshot=%CD%\presentation\cover.png file:///%CD:\=/%/presentation/cover.html
```

Slides PDF (Marp CLI through npx, uses the installed Chrome):

```
npx -y @marp-team/marp-cli@4 presentation/slides.md --pdf --allow-local-files -o presentation/slides.pdf
```

Video: record with OBS at 1080p30, edit in any editor, export H.264/AAC MP4, then check it with `tools/check_video.sh demo.mp4` (Git Bash) before uploading. Keep the raw recordings out of the repository (`*.mp4` and `*.mkv` are ignored).
