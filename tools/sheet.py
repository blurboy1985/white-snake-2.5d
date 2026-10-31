"""Tile images into one contact sheet. Usage: python tools/sheet.py OUT.png COLS CELL_W CELL_H IMG [IMG ...]"""
import subprocess
import sys

out, cols, cw, ch, files = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5:]
args = [a for f in files for a in ("-i", f)]
bg = "0x8a9a8a"
filt = "".join(f"color={bg}:s={cw}x{ch}:d=1[b{i}];[{i}]scale={cw}:{ch}:force_original_aspect_ratio=decrease[s{i}];"
               f"[b{i}][s{i}]overlay=(W-w)/2:(H-h)/2[v{i}];" for i in range(len(files)))
rows = []
for r in range(0, len(files), cols):
    cells = [f"[v{i}]" for i in range(r, min(r + cols, len(files)))]
    for k in range(cols - len(cells)):
        filt += f"color={bg}:s={cw}x{ch}:d=1[p{r}_{k}];"
        cells.append(f"[p{r}_{k}]")
    filt += "".join(cells) + (f"hstack={cols}" if cols > 1 else "null") + f"[r{r}];"
    rows.append(f"[r{r}]")
filt += "".join(rows) + (f"vstack={len(rows)}" if len(rows) > 1 else "null")
subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", filt, "-frames:v", "1", out], check=True)
