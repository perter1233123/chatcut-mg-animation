---
name: chatcut-mg-animation
description: Build and export a short motion-graphics animation (title sequence, explainer, roughly 30 seconds) in ChatCut Desktop by driving its local MCP tools from Codex. Use for ChatCut animation or motion-graphics requests, or when the user wants ChatCut Desktop edited from Codex and the ChatCut tools are not already loaded in the session.
metadata:
  short-description: Author and export ChatCut motion-graphics animations
---

# ChatCut Motion-Graphics Animation From Codex

Deliver an animation the user can watch: authored Motion Graphic assets, a composed timeline, verified frames, and an exported video file. Use the built-in `chatcut-create-motion-graphics` guidance for visual-language decisions; this skill covers the Codex-side path and the shape of a short animated piece.

## Reach the ChatCut tool surface

ChatCut Desktop serves a local MCP server. Codex usually registers it in `~/.codex/config.toml` as `chatcut_desktop`, pointing at `~/Library/Application Support/ChatCut/chatcut-mcp`.

- Prefer the native MCP tools when they are present in the session.
- When they are not loaded, drive the same server over stdio with [scripts/chatcut_mcp.py](scripts/chatcut_mcp.py). Each run is a fresh session, so every invocation must bind the project with `--project` (internally `target_project`).

```bash
python3 scripts/chatcut_mcp.py list-tools --filter motion
python3 scripts/chatcut_mcp.py call read_project --project <projectId>
python3 scripts/chatcut_mcp.py call preview_timeline --project <id> --json '{"views":["viewer"],"viewerFrames":[240]}' --save-images /tmp/frames
```

The first real call may launch the ChatCut app. `local_export` with an absolute path opens a native Save dialog that blocks the turn: pass a relative path and report the returned `~/Movies/ChatCut/...` location instead.

## Confirm the target before designing

Call `get_active_project`, then `list_projects`. Continue in the user's existing project when one is open or when the default project is empty; create a new project only when the user asks for one. Read `read_project` for canvas size, fps, track list, and asset counts before choosing layout or placement.

## Structure the piece

A short animation is a continuous background plus scene beats, not one giant graphic:

| Layer | Asset | Placement |
| --- | --- | --- |
| Continuous background | one opaque full-frame MG, duration = whole piece | V1, frame 0 to the end |
| Scene beats | one transparent full-frame MG per beat (title, list, data, end card) | V2, back-to-back |

- Give every scene its own entrance, hold, and exit inside its own duration (fade in over about 12 frames, fade out over the last about 24) so back-to-back placement reads as a dissolve without transition items.
- Create the extra video track with `edit_track` (`{"trackType":"video"}`) and place scene items with `trackId`.
- Dry-run a large placement batch once with `edit_item` `validateOnly`, then commit it.
- Keep one asset per editorial job. Reuse an asset only when the job, information structure, and visual form are the same.

## Author the assets

Create assets with `create_motion_graphic_from_code`, passing the code inline (never a file path, never staged in the repository or `/tmp`). Read [references/mg-code-contract.md](references/mg-code-contract.md) before writing JSX: it lists the injected globals, the Desktop validator rules, the failure modes that cost round trips, and a validated scene recipe.

Choose fonts with `search_fonts` and use the returned family name verbatim; `Noto Sans SC` covers Chinese plus Latin. Expose visible text, primary colors, and key numbers as editable properties.

## Verify before exporting

A successful tool call is not verification.

1. `preview_timeline` with `views:["viewer"]` and frames spread across the piece for a contact sheet.
2. Re-render single settled frames per scene at full size and inspect them for text overlap, overflow, and legibility at video scale.
3. Judge settled frames; a missing or clipped element that appears in only some frames is animation, not a defect.

## Export and report

```bash
python3 scripts/chatcut_mcp.py call local_export --project <id> \
  --json '{"format":"video","resolution":"1080p","fps":30,"outputPath":"my-animation.mp4"}'
```

The render continues in the background. When the finished file is part of the delivery, follow it with `track_progress` (`{"target":"export","action":"status","jobId":"..."}`) until `status` is `done`, then report the output path, duration, and what each scene contains.

Offer follow-ups rather than assuming them: background music, captions, a different length or aspect ratio. Generation tools such as `submit_music` or `submit_video` consume the user's credits.
