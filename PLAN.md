# White Snake 2.5D: first episode

Goal: one original vertical short of more than a minute in the 2.5D format (flat 2D characters in lit 3D Blender sets, one narrator), retelling the *Legend of the White Snake*.

## Done means

- `episode/final.mp4` passes ffprobe: 1080x1920, 30/1 fps, 60 to 75 s, audio present.
- Every spoken claim has a line in `episode/sources.md`. The user has checked them.
- Contact sheet review shows no item from the banned list in the house rules.
- Watched on a phone with sound on, the user calls it publishable.

## Environment (checked 2026-10-31)

| Tool | State |
| --- | --- |
| Blender | 5.2.1 LTS at `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, not on PATH |
| GPU | AMD RX 9070 XT. Cycles HIP and EEVEE both render headless. The episode uses EEVEE, about 0.35 to 0.6 s per frame |
| ffmpeg / ffprobe | 8.1.1, with libass for captions |
| Edge | Headless Edge rasterizes the character SVGs to transparent PNGs |
| ElevenLabs | Connector used for narration (George, eleven_v4), word timings (Scribe), music and sound effects |

## Decisions

- Blender runs headless from `tools/build_scene.py`. No Blender MCP server, so nothing changes in Claude Code config.
- Voice, word timings, music and sound effects come from ElevenLabs instead of a recorded voice and Whisper (user's call).
- `episode/shotlist.json` is the source of truth. Each shot names the words it covers, and `tools/timeline.py` checks that the shots cover the narration word for word before resolving every anchor to a frame.
- Characters are drawn as SVG in `tools/characters.py`, one PNG per expression or pose, and swapped per beat.
- Captions and the final mix are done in ffmpeg (`tools/assemble.py`). The sound cue list lives in `episode/cues.json`, anchored to words.
- Each set has its own sky dome and a sun linked only to that set's collection, so the 7 sets share one scene without lighting each other.

## Pipeline

```bash
python tools/characters.py build/chars
python tools/timeline.py episode/shotlist.json episode/audio/words.json build/timeline.json
blender --background --enable-autoexec --factory-startup --python tools/build_scene.py -- "$PWD" anim
python tools/assemble.py .
```

## Stages

1. Setup check. DONE.
2. Story. DONE. User picked the Legend of the White Snake.
3. Script and `sources.md`. DONE. **Waiting on the user's source check.**
4. Narration, word timings, music. DONE (ElevenLabs, 68.3 s narration).
5. `shotlist.json`. DONE. 27 shots, 70.0 s, 7 sets.
6. Sets, hero props (pagoda, golden bowl, herb, crab), characters. DONE.
7. Review loop. Three contact sheet passes. Fixed: invisible wall silhouette, tiny characters in wide shots, cropped two-shots, temple gate stuck open, crab close-ups too tight, Kunlun overexposure, Bai lost in the s17 flight (camera now follows her).
8. Full render, captions, sound effects, mix. DONE. `episode/final.mp4` verified by ffprobe: 1080x1920, 30/1 fps, 70.0 s, AAC audio, peak -0.1 dB.
9. Phone test by the user.

## Open

- Music generation reported "Instrumental: False" even though the prompt asked for no vocals. Listen for vocals.
- Pronunciation of Chinese names by the English voice is unchecked.
