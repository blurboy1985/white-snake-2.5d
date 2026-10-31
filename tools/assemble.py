"""Burn word-timed captions over the rendered frames and mix voice, music and sound effects into the final short.

Usage: python tools/assemble.py ROOT
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1])
EP = ROOT / "episode"
BUILD = ROOT / "build"
TIMELINE = json.loads((BUILD / "timeline.json").read_text(encoding="utf-8"))
CUES = json.loads((EP / "cues.json").read_text(encoding="utf-8"))
FPS = TIMELINE["fps"]
DURATION = (TIMELINE["frame_end"] + 1) / FPS


def norm(text):
    return re.sub(r"[^a-z0-9']", "", text.lower())


def ass_time(t):
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def caption_groups(words):
    groups, current = [], []
    for w in words:
        current.append(w)
        ends_sentence = w["text"].rstrip(".").endswith(("?", "!", ",")) or w["text"].endswith(".")
        if len(current) == 2 or ends_sentence or norm(w["text"]) in CUES["stressed"]:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def write_captions(path):
    words = [w for s in TIMELINE["shots"] for w in s["captions"]]
    groups = caption_groups(words)
    lines = []
    for i, g in enumerate(groups):
        start = g[0]["start"]
        end = groups[i + 1][0]["start"] if i + 1 < len(groups) else min(g[-1]["end"] + 0.6, DURATION)
        end = min(end, g[-1]["end"] + 0.5)
        text = " ".join(w["text"] for w in g).replace("...", "").upper()
        pop = any(norm(w["text"]) in CUES["stressed"] for w in g)
        fx = r"{\fscx70\fscy70\t(0,90,\fscx112\fscy112)\t(90,160,\fscx100\fscy100)\c&H3FD6FF&}" if pop else ""
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Cap,,0,0,0,,{fx}{text}")
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Cap,Arial Black,92,&H00FFFFFF,&H00FFFFFF,&H00161616,&H64000000,1,0,0,0,100,100,0,0,1,7,3,2,80,80,430,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(lines) + "\n",
        encoding="utf-8")
    return len(lines)


def cue_time(cue):
    shot = next(s for s in TIMELINE["shots"] if s["id"] == cue["shot"])
    if cue.get("at") == "start":
        t = shot["start"] / FPS
    else:
        t = next(w["start"] for w in shot["captions"] if norm(w["text"]) == norm(cue["on"]))
    return max(0.0, t + cue.get("delay", 0) / FPS)


def main():
    n = write_captions(BUILD / "captions.ass")
    inputs = ["-framerate", str(FPS), "-i", str(BUILD / "frames" / "%04d.png"),
              "-i", str(EP / CUES["voice"]["file"]), "-i", str(EP / CUES["music"]["file"])]
    m = CUES["music"]
    filters = [
        "[0:v]subtitles=build/captions.ass[v]",
        f"[1:a]volume={CUES['voice']['gain']}[voice]",
        f"[2:a]atrim=start={m['skip']},asetpts=PTS-STARTPTS,volume={m['gain']},"
        f"afade=t=out:st={DURATION - m['fade_out']}:d={m['fade_out']}[music]",
    ]
    mix = ["[voice]", "[music]"]
    for i, cue in enumerate(CUES["sfx"]):
        inputs += (["-stream_loop", "-1"] if cue.get("loop") else []) + ["-i", str(EP / cue["file"])]
        ms = round(cue_time(cue) * 1000)
        trim = f"atrim=end={cue['dur']},afade=t=out:st={cue['dur'] - 0.6}:d=0.6," if "dur" in cue else ""
        filters.append(f"[{i + 3}:a]{trim}volume={cue['gain']},adelay={ms}|{ms}[s{i}]")
        mix.append(f"[s{i}]")
    filters.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.95[a]")
    out = EP / "final.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filters),
           "-map", "[v]", "-map", "[a]", "-t", f"{DURATION}", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    print(f"captions {n}, sfx {len(CUES['sfx'])}, wrote {out}")


if __name__ == "__main__":
    main()
