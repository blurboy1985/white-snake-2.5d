# 2.5D motion short: first episode

Goal: one original 55 to 70 second vertical short in the 2.5D format (flat 2D characters in lit 3D Blender sets, one narrator, a true sourced story), made with the course's method.

## Done means

- `episode/final.mp4` passes ffprobe: 1080x1920, 30/1 fps, 55 to 70 s, audio present.
- Every on-screen or spoken claim has a line in `sources.md` that the user has checked.
- Contact sheet review shows no item left from the "banned" list in the house rules.
- Watched on a phone with sound on, the user calls it publishable.

## Environment (checked 2026-10-31)

| Tool | State |
| --- | --- |
| Blender | 5.2.1 LTS at `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, not on PATH |
| GPU | AMD RX 9070 XT. Verified: Cycles HIP renders headless at 1080x1920 (`tools/setup_check.py`, 64 samples, 4.3 s on dGPU only). EEVEE also works. iGPU excluded |
| ffmpeg / ffprobe | 8.1.1 |
| uv / node / python | 0.11.16 / 25.7.0 / 3.14.2 |
| Whisper | missing. Plan: run it under uv with Python 3.12 |

## Decisions

- Drive Blender headless with `blender.exe --background --python`. No Blender MCP server and no change to Claude Code config. Preview renders are PNGs I read back. Reason: reproducible scripts, nothing persistent to install.
- Captions and final assembly in ffmpeg (ASS subtitles). Remotion only if ffmpeg can't hit the caption spec.
- One `shotlist.json` is the source of truth. Blender cameras, caption cuts, and sound cues all read frame numbers from it.
- Scratch narration from Windows TTS for timing. The user records the final voice.

## Stages (each ends in a check)

1. Setup check. Blender part DONE. Whisper deferred to stage 9, the first stage that needs it.
2. Story. **Gate: user picks the topic** (user chose to pick it themselves).
3. Script and `sources.md`, about 160 words. **Gate: user approves script and checks sources.**
4. `shotlist.json`. 1.5 to 3 s shots, 3 to 5 sets.
5. Sets. Block, light, dress. Contact sheet after each pass.
6. Hero prop. 6-angle look sheet.
7. Characters. SVG parts plus expression sheets. **Gate: user approves the character look.**
8. Animation and acting pass. Draft render.
9. Voice. **User records narration.** Whisper word timestamps, then re-time shots.
10. Captions and sound. Cue list in frames.
11. Review loop. Critic pass on contact sheets, fix the three worst, repeat.
12. Export and ffprobe check. Phone test.

## Open

- Music and SFX source (CC0 library, needs download approval).
- Reference video breakdown is optional. Needs approval to download.
