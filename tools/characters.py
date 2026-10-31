"""Draw every character variant as a flat SVG, then rasterize each to a transparent PNG with headless Edge.

Usage: python tools/characters.py [OUT_DIR]
"""
import pathlib
import subprocess
import sys

INK = "#1d1a1f"
SKIN = "#f6dcc8"
HAIR = "#26232c"
W, H = 700, 1100
CX, HEAD_Y, HEAD_R = 350, 330, 140
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def svg(body, w=W, h=H):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'


def limb(points, color, width=56):
    d = "M" + " L".join(f"{x},{y}" for x, y in points)
    common = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return (f'<path d="{d}" {common} stroke="{INK}" stroke-width="{width + 16}"/>'
            f'<path d="{d}" {common} stroke="{color}" stroke-width="{width}"/>')


def hand(x, y, r=26):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{SKIN}" stroke="{INK}" stroke-width="8"/>'


def eyes(kind, cx=CX, cy=HEAD_Y + 10, gap=52):
    out = []
    for side in (-1, 1):
        x = cx + side * gap
        if kind == "neutral":
            out.append(f'<ellipse cx="{x}" cy="{cy}" rx="11" ry="17" fill="{INK}"/>')
        elif kind == "side":
            out.append(f'<ellipse cx="{x + 10}" cy="{cy}" rx="11" ry="17" fill="{INK}"/>')
        elif kind == "happy":
            out.append(f'<path d="M{x - 18},{cy + 6} Q{x},{cy - 18} {x + 18},{cy + 6}" fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>')
        elif kind == "closed":
            out.append(f'<path d="M{x - 18},{cy - 2} Q{x},{cy + 14} {x + 18},{cy - 2}" fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>')
        elif kind == "wide":
            out.append(f'<circle cx="{x}" cy="{cy}" r="26" fill="#fff" stroke="{INK}" stroke-width="7"/><circle cx="{x}" cy="{cy}" r="7" fill="{INK}"/>')
        elif kind == "narrow":
            out.append(f'<path d="M{x - 22},{cy + 2} L{x + 22},{cy + 2}" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>'
                       f'<path d="M{x - 26},{cy - 24} L{x + 22},{cy - 14 + side * 0}" stroke="{INK}" stroke-width="11" stroke-linecap="round" transform="rotate({side * 14} {x} {cy - 18})"/>')
        elif kind == "x":
            out.append(f'<path d="M{x - 16},{cy - 16} L{x + 16},{cy + 16} M{x + 16},{cy - 16} L{x - 16},{cy + 16}" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>')
    return "".join(out)


def mouth(kind, cx=CX, cy=HEAD_Y + 72):
    if kind == "closed":
        return f'<path d="M{cx - 14},{cy} L{cx + 14},{cy}" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    if kind == "smile":
        return f'<path d="M{cx - 24},{cy - 6} Q{cx},{cy + 18} {cx + 24},{cy - 6}" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    if kind == "open":
        return f'<ellipse cx="{cx}" cy="{cy + 4}" rx="14" ry="18" fill="#7a2b2b" stroke="{INK}" stroke-width="6"/>'
    if kind == "wide":
        return f'<ellipse cx="{cx}" cy="{cy + 10}" rx="28" ry="34" fill="#7a2b2b" stroke="{INK}" stroke-width="7"/>'
    if kind == "frown":
        return f'<path d="M{cx - 24},{cy + 10} Q{cx},{cy - 12} {cx + 24},{cy + 10}" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    if kind == "grin":
        return f'<path d="M{cx - 34},{cy - 8} L{cx + 34},{cy - 8} Q{cx},{cy + 40} {cx - 34},{cy - 8} Z" fill="#7a2b2b" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>'
    if kind == "smirk":
        return f'<path d="M{cx - 20},{cy + 4} Q{cx + 6},{cy + 10} {cx + 26},{cy - 10}" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
    return ""


def blush(cx=CX, cy=HEAD_Y + 52):
    return "".join(f'<ellipse cx="{cx + s * 88}" cy="{cy}" rx="24" ry="13" fill="#f29a9a" opacity="0.8"/>' for s in (-1, 1))


def head(face_eyes, face_mouth, extra=""):
    return (f'<circle cx="{CX}" cy="{HEAD_Y}" r="{HEAD_R}" fill="{SKIN}" stroke="{INK}" stroke-width="9"/>'
            + extra + eyes(face_eyes) + mouth(face_mouth))


def robe(color, trim, top=470, hem=1080, half_top=80, half_hem=190):
    return (f'<path d="M{CX - half_top},{top} Q{CX - half_top - 40},{top + 300} {CX - half_hem},{hem} L{CX + half_hem},{hem} '
            f'Q{CX + half_top + 40},{top + 300} {CX + half_top},{top} Z" fill="{color}" stroke="{INK}" stroke-width="9" stroke-linejoin="round"/>'
            f'<path d="M{CX - 40},{top} L{CX},{top + 90} L{CX + 40},{top}" fill="none" stroke="{trim}" stroke-width="14"/>'
            f'<rect x="{CX - half_top - 14}" y="{top + 150}" width="{2 * half_top + 28}" height="34" rx="8" fill="{trim}" stroke="{INK}" stroke-width="7"/>')


def umbrella(x, y):
    ribs = "".join(f'<path d="M{x},{y - 150} L{x + dx},{y - 40}" stroke="#8e3a2a" stroke-width="5"/>' for dx in (-150, -90, -30, 30, 90, 150))
    return (f'<path d="M{x},{y - 30} L{x},{y + 160}" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>'
            f'<path d="M{x - 200},{y - 30} Q{x},{y - 230} {x + 200},{y - 30} Q{x},{y - 70} {x - 200},{y - 30} Z" fill="#d0623f" stroke="{INK}" stroke-width="9" stroke-linejoin="round"/>'
            + ribs)


def cup(x, y):
    return f'<path d="M{x - 30},{y - 22} L{x + 30},{y - 22} L{x + 20},{y + 18} L{x - 20},{y + 18} Z" fill="#9cc7b0" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>'


ARMS = {
    "down": ([(270, 510), (235, 650), (240, 760)], [(430, 510), (465, 650), (460, 760)]),
    "reach": ([(270, 510), (235, 650), (240, 760)], [(430, 510), (520, 600), (610, 610)]),
    "umbrella": ([(270, 510), (235, 650), (240, 760)], [(430, 510), (500, 470), (470, 360)]),
    "cup": ([(270, 510), (235, 650), (240, 760)], [(430, 510), (470, 560), (400, 470)]),
    "up": ([(270, 510), (170, 400), (150, 250)], [(430, 510), (530, 400), (550, 250)]),
    "point": ([(270, 510), (235, 650), (240, 760)], [(430, 510), (520, 470), (540, 330)]),
    "fly": ([(270, 510), (150, 520), (60, 470)], [(430, 510), (550, 520), (640, 470)]),
}


def person(robe_color, trim, face_eyes, face_mouth, hair_back="", hair_front="", arms="down", prop="", rosy=False, head_extra=""):
    back, front = ARMS[arms]
    parts = [hair_back, limb(back, robe_color), hand(*back[-1]), robe(robe_color, trim)]
    parts.append(head(face_eyes, face_mouth, blush() if rosy else "") + head_extra)
    parts.append(hair_front)
    parts.append(limb(front, robe_color))
    if prop == "umbrella":
        parts.append(umbrella(front[-1][0], front[-1][1] - 10))
    parts.append(hand(*front[-1]))
    if prop == "cup":
        parts.append(cup(front[-1][0], front[-1][1] - 30))
    return svg("".join(parts))


def bai(face_eyes="neutral", face_mouth="smile", arms="down", prop="", rosy=False):
    hair_back = (f'<path d="M{CX - 150},{HEAD_Y} Q{CX - 170},{HEAD_Y + 260} {CX - 110},{HEAD_Y + 330} L{CX + 110},{HEAD_Y + 330} '
                 f'Q{CX + 170},{HEAD_Y + 260} {CX + 150},{HEAD_Y} Z" fill="{HAIR}" stroke="{INK}" stroke-width="8"/>')
    hair_front = (f'<circle cx="{CX}" cy="{HEAD_Y - 170}" r="70" fill="{HAIR}" stroke="{INK}" stroke-width="8"/>'
                  f'<path d="M{CX - 145},{HEAD_Y - 10} Q{CX - 120},{HEAD_Y - 150} {CX},{HEAD_Y - 145} Q{CX + 120},{HEAD_Y - 150} {CX + 145},{HEAD_Y - 10} '
                  f'Q{CX + 60},{HEAD_Y - 90} {CX},{HEAD_Y - 60} Q{CX - 60},{HEAD_Y - 90} {CX - 145},{HEAD_Y - 10} Z" fill="{HAIR}" stroke="{INK}" stroke-width="8"/>'
                  f'<path d="M{CX + 30},{HEAD_Y - 200} L{CX + 140},{HEAD_Y - 240}" stroke="#d9b44a" stroke-width="10" stroke-linecap="round"/>'
                  f'<circle cx="{CX + 140}" cy="{HEAD_Y - 240}" r="14" fill="#7fc8c0" stroke="{INK}" stroke-width="6"/>')
    return person("#f5f2ea", "#6cc0b4", face_eyes, face_mouth, hair_back, hair_front, arms, prop, rosy)


def xu(face_eyes="neutral", face_mouth="smile", arms="down", prop="", rosy=False):
    hat = (f'<path d="M{CX - 120},{HEAD_Y - 70} Q{CX - 120},{HEAD_Y - 200} {CX},{HEAD_Y - 200} Q{CX + 120},{HEAD_Y - 200} {CX + 120},{HEAD_Y - 70} Z" '
           f'fill="{HAIR}" stroke="{INK}" stroke-width="8"/>'
           f'<rect x="{CX - 210}" y="{HEAD_Y - 120}" width="90" height="22" rx="10" fill="{HAIR}" stroke="{INK}" stroke-width="6"/>'
           f'<rect x="{CX + 120}" y="{HEAD_Y - 120}" width="90" height="22" rx="10" fill="{HAIR}" stroke="{INK}" stroke-width="6"/>')
    return person("#4f78b0", "#e8d9a8", face_eyes, face_mouth, "", hat, arms, prop, rosy)


def fahai(face_eyes="narrow", face_mouth="frown", arms="down"):
    marks = "".join(f'<circle cx="{CX + dx}" cy="{HEAD_Y - 95 + dy}" r="6" fill="#c9a98f"/>' for dx, dy in ((-30, 0), (0, -6), (30, 0), (-30, 26), (0, 20), (30, 26)))
    brows = (f'<path d="M{CX - 90},{HEAD_Y - 40} L{CX - 20},{HEAD_Y - 18}" stroke="{INK}" stroke-width="16" stroke-linecap="round"/>'
             f'<path d="M{CX + 90},{HEAD_Y - 40} L{CX + 20},{HEAD_Y - 18}" stroke="{INK}" stroke-width="16" stroke-linecap="round"/>')
    staff = (f'<path d="M{560},{180} L{560},{1080}" stroke="#8a5a2b" stroke-width="16" stroke-linecap="round"/>'
             f'<circle cx="560" cy="150" r="46" fill="none" stroke="#d9b44a" stroke-width="12"/>')
    kasaya = f'<path d="M{CX - 80},{470} L{CX + 140},{720} L{CX + 170},{1080} L{CX + 60},{1080} L{CX - 60},{620} Z" fill="#b8382c" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>'
    back, front = ARMS[arms]
    parts = [staff, limb(back, "#e0a238"), hand(*back[-1]), robe("#e0a238", "#b8382c"), kasaya,
             head(face_eyes, face_mouth, marks + brows), limb(front, "#e0a238"), hand(*front[-1])]
    return svg("".join(parts))


def luxun(face_eyes="neutral", face_mouth="closed", arms="down"):
    hair = (f'<path d="M{CX - 130},{HEAD_Y - 50} Q{CX - 130},{HEAD_Y - 150} {CX},{HEAD_Y - 150} Q{CX + 130},{HEAD_Y - 150} {CX + 130},{HEAD_Y - 50} '
            f'L{CX + 118},{HEAD_Y - 80} L{CX - 118},{HEAD_Y - 80} Z" fill="{HAIR}" stroke="{INK}" stroke-width="8"/>')
    stache = f'<path d="M{CX - 60},{HEAD_Y + 52} Q{CX},{HEAD_Y + 30} {CX + 60},{HEAD_Y + 52} L{CX + 50},{HEAD_Y + 66} Q{CX},{HEAD_Y + 50} {CX - 50},{HEAD_Y + 66} Z" fill="{HAIR}"/>'
    back, front = ARMS[arms]
    parts = [limb(back, "#6d7076"), hand(*back[-1]), robe("#6d7076", "#4b4d52"),
             head(face_eyes, face_mouth, hair), stache, limb(front, "#6d7076"), hand(*front[-1])]
    return svg("".join(parts))


def snake_coiled(face_eyes="closed"):
    coil = "M350,600 C120,600 120,470 350,470 C580,470 580,350 350,350 C200,350 220,260 330,250"
    body = (f'<path d="{coil}" fill="none" stroke="{INK}" stroke-width="96" stroke-linecap="round"/>'
            f'<path d="{coil}" fill="none" stroke="#f7f5ef" stroke-width="78" stroke-linecap="round"/>'
            f'<path d="{coil}" fill="none" stroke="#dfe9e4" stroke-width="20" stroke-linecap="round" stroke-dasharray="6 40"/>')
    head_ = f'<ellipse cx="380" cy="230" rx="78" ry="58" fill="#f7f5ef" stroke="{INK}" stroke-width="9"/>'
    return svg(body + head_ + eyes(face_eyes, cx=385, cy=222, gap=30).replace('rx="11" ry="17"', 'rx="8" ry="12"'), 700, 700)


def snake_giant(face_eyes="wide"):
    jaw = f'<path d="M120,560 Q500,980 880,560 Q500,700 120,560 Z" fill="#f7f5ef" stroke="{INK}" stroke-width="12" stroke-linejoin="round"/>'
    mouth_ = f'<path d="M150,520 Q500,860 850,520 Q500,640 150,520 Z" fill="#8c2635" stroke="{INK}" stroke-width="10"/>'
    fangs = "".join(f'<path d="M{x},{535 + abs(x - 500) * -0.05} L{x + 22},{620} L{x + 44},{540}" fill="#fff" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>' for x in (300, 656))
    skull = f'<path d="M100,540 Q90,180 500,150 Q910,180 900,540 Q500,620 100,540 Z" fill="#f7f5ef" stroke="{INK}" stroke-width="12" stroke-linejoin="round"/>'
    scales = "".join(f'<path d="M{x - 40},{y} Q{x},{y - 30} {x + 40},{y}" fill="none" stroke="#c9d8d2" stroke-width="8"/>' for x in range(300, 760, 90) for y in (250, 320))
    e = "".join(f'<ellipse cx="{x}" cy="420" rx="62" ry="70" fill="#e8c34a" stroke="{INK}" stroke-width="10"/><ellipse cx="{x}" cy="420" rx="14" ry="56" fill="{INK}"/>' for x in (310, 690))
    return svg(mouth_ + jaw + fangs + skull + scales + e, 1000, 1000)


def tiny_monk(face_eyes="side", face_mouth="smirk"):
    marks = "".join(f'<circle cx="{CX + dx}" cy="{HEAD_Y - 95 + dy}" r="6" fill="#c9a98f"/>' for dx, dy in ((-30, 0), (0, -6), (30, 0)))
    brows = (f'<path d="M{CX - 90},{HEAD_Y - 40} L{CX - 20},{HEAD_Y - 18}" stroke="{INK}" stroke-width="16" stroke-linecap="round"/>'
             f'<path d="M{CX + 90},{HEAD_Y - 40} L{CX + 20},{HEAD_Y - 18}" stroke="{INK}" stroke-width="16" stroke-linecap="round"/>')
    hands = hand(CX - 120, HEAD_Y + 150, 34) + hand(CX + 120, HEAD_Y + 150, 34)
    return svg(head(face_eyes, face_mouth, marks + brows) + hands, 700, 600)


VARIANTS = {
    "bai_neutral": lambda: bai(),
    "bai_closed": lambda: bai("closed", "smile"),
    "bai_side": lambda: bai("side", "closed"),
    "bai_happy": lambda: bai("happy", "smile", rosy=True),
    "bai_reach": lambda: bai("neutral", "open", arms="reach"),
    "bai_umbrella": lambda: bai("happy", "smile", arms="umbrella", prop="umbrella", rosy=True),
    "bai_cup": lambda: bai("closed", "closed", arms="cup", prop="cup"),
    "bai_shock": lambda: bai("wide", "wide", arms="up"),
    "bai_fly": lambda: bai("narrow", "closed", arms="fly"),
    "bai_angry": lambda: bai("narrow", "wide", arms="up"),
    "bai_sad": lambda: bai("closed", "frown"),
    "xu_neutral": lambda: xu(),
    "xu_happy": lambda: xu("happy", "grin", rosy=True),
    "xu_umbrella": lambda: xu("neutral", "smile", arms="umbrella", prop="umbrella"),
    "xu_offer": lambda: xu("side", "smile", arms="reach", prop="cup"),
    "xu_shock": lambda: xu("wide", "wide", arms="up"),
    "xu_dead": lambda: xu("x", "open"),
    "xu_sad": lambda: xu("closed", "frown"),
    "fahai_stern": lambda: fahai("neutral", "frown"),
    "fahai_narrow": lambda: fahai("narrow", "frown"),
    "fahai_smirk": lambda: fahai("narrow", "smirk", arms="point"),
    "fahai_shock": lambda: fahai("wide", "wide", arms="up"),
    "luxun_neutral": lambda: luxun(),
    "luxun_cheer": lambda: luxun("happy", "grin", arms="up"),
    "luxun_point": lambda: luxun("side", "smirk", arms="point"),
    "snake_coiled": lambda: snake_coiled("closed"),
    "snake_open": lambda: snake_coiled("neutral"),
    "snake_giant": lambda: snake_giant(),
    "monk_tiny": lambda: tiny_monk("side", "smirk"),
    "monk_tiny_hide": lambda: tiny_monk("wide", "open"),
}


def rasterize(svg_path, png_path):
    text = svg_path.read_text()
    w = int(text.split('width="')[1].split('"')[0])
    h = int(text.split('height="')[1].split('"')[0])
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
                    f"--window-size={w},{h}", f"--screenshot={png_path.resolve()}", svg_path.resolve().as_uri()],
                   check=True, capture_output=True)


def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build/chars")
    out.mkdir(parents=True, exist_ok=True)
    for name, make in VARIANTS.items():
        svg_path = out / f"{name}.svg"
        svg_path.write_text(make())
        rasterize(svg_path, out / f"{name}.png")
        print("drew", name)


if __name__ == "__main__":
    main()
