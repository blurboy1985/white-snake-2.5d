"""Resolve episode/shotlist.json word anchors against the narration's word timings into absolute frames.

Usage: python tools/timeline.py episode/shotlist.json episode/audio/words.json build/timeline.json
"""
import json
import re
import sys


def norm(text):
    return re.sub(r"[^a-z0-9']", "", text.lower())


def spoken(words):
    return [w for w in words if w["type"] == "word" and not w["text"].startswith("[")]


def resolve(shotlist, words):
    fps = shotlist["fps"]
    words = spoken(words)
    cursor = 0
    shots = []
    for shot in shotlist["shots"]:
        said = [norm(t) for t in shot["say"].split()]
        span = words[cursor:cursor + len(said)]
        heard = [norm(w["text"]) for w in span]
        assert heard == said, f"{shot['id']}: shot says {said} but narration has {heard}"
        shots.append({**shot, "_words": span})
        cursor += len(said)
    assert cursor == len(words), f"narration has {len(words) - cursor} words no shot covers"

    lead = shotlist["lead_frames"]
    starts = [0] + [max(0, round(s["_words"][0]["start"] * fps) - lead) for s in shots[1:]]
    end = round((words[-1]["end"] + shotlist["end_hold"]) * fps)
    starts.append(end)

    def frame_of(shot, start, event):
        if event.get("at") == "start":
            base = start
        else:
            target = norm(event["on"])
            match = next((w for w in shot["_words"] if norm(w["text"]) == target), None)
            assert match, f"{shot['id']}: no word '{event['on']}' in this shot"
            base = round(match["start"] * fps)
        return base + event.get("delay", 0)

    out = []
    for i, shot in enumerate(shots):
        start, stop = starts[i], starts[i + 1] - 1
        resolved = {k: v for k, v in shot.items() if k != "_words"}
        resolved["start"], resolved["end"] = start, stop
        if "shake" in shot["cam"]:
            resolved["cam"] = {**shot["cam"], "shake": frame_of(shot, start, {"on": shot["cam"]["shake"]})}
        for actor in resolved.get("actors", []):
            actor["keys"] = [{**k, "frame": max(start, frame_of(shot, start, k))} for k in actor["keys"]]
        resolved["fx"] = [{**fx, "frame": frame_of(shot, start, fx)} for fx in shot.get("fx", [])]
        resolved["captions"] = [{"text": w["text"], "start": w["start"], "end": w["end"]} for w in shot["_words"]]
        out.append(resolved)
    return {"fps": fps, "frame_end": end - 1, "shots": out}


if __name__ == "__main__":
    shotlist = json.load(open(sys.argv[1], encoding="utf-8"))
    words = json.load(open(sys.argv[2], encoding="utf-8"))["words"]
    timeline = resolve(shotlist, words)
    json.dump(timeline, open(sys.argv[3], "w", encoding="utf-8"), indent=1)
    for s in timeline["shots"]:
        print(f"{s['id']} {s['set']:7} {s['start']:5}-{s['end']:5} ({(s['end'] - s['start'] + 1) / timeline['fps']:.2f}s) {s['say']}")
    print("frames", timeline["frame_end"] + 1, "seconds", (timeline["frame_end"] + 1) / timeline["fps"])
