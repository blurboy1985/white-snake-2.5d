# White Snake 2.5D

A 70-second vertical cartoon of the Chinese *Legend of the White Snake*, made in the 2.5D style. Flat 2D characters act inside lit 3D Blender sets, with one narrator.

The finished short is `episode/final.mp4`.

Everything is generated from scripts. You can rebuild the whole film after editing the script, shots or art:

| Step | Command | Output |
| --- | --- | --- |
| Draw characters | `python tools/characters.py build/chars` | One transparent PNG per pose and expression |
| Time the shots | `python tools/timeline.py episode/shotlist.json episode/audio/words.json build/timeline.json` | Every shot and beat resolved to a frame |
| Render | `blender --background --enable-autoexec --factory-startup --python tools/build_scene.py -- "$PWD" anim` | 2100 PNG frames in `build/frames` |
| Preview stills | `... build_scene.py -- "$PWD" stills 45,109,179 30` | Chosen frames at 30% size in `build/stills` |
| Assemble | `python tools/assemble.py .` | Captions, voice, music and sound effects mixed into `episode/final.mp4` |

`episode/shotlist.json` is the source of truth. Each shot lists the narration words it covers, its set, its camera move, and the actors with their expression changes, each anchored to a spoken word. `tools/timeline.py` refuses to run unless the shots cover the narration word for word.

The narration, word timings, music and sound effects came from ElevenLabs. The script and its sources are in `episode/script.md` and `episode/sources.md`. [PLAN.md](PLAN.md) has the decisions and review notes.

## Requirements

- Blender 5.2 or newer
- ffmpeg with libass
- Microsoft Edge (headless, for rasterizing the character SVGs)
- Python 3.10 or newer
