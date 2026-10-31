# White Snake 2.5D

A one-minute vertical cartoon of the Chinese *Legend of the White Snake*, made in the 2.5D style. Flat 2D characters act inside lit 3D Blender sets, with one narrator.

Blender runs headless from Python scripts in `tools/`. Narration and music come from ElevenLabs. ffmpeg handles captions and final assembly. [PLAN.md](PLAN.md) has the stages, the decisions and the done check.

## Requirements

- Blender 5.2 or newer
- ffmpeg and ffprobe

## Check the setup

```bash
blender --background --factory-startup --python tools/setup_check.py -- CYCLES "$PWD/renders/setup/CYCLES.png"
```

This prints `SETUP_CHECK` with the render device and time, and writes a 1080x1920 test frame.
