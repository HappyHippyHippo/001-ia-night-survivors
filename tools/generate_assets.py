#!/usr/bin/env python3
"""
Procedural asset generator for Night Survivors.

Generates every asset the game uses, with no third-party dependencies:
  - pixel-art sprites (PNG) + the Defold atlas that references them. Art is drawn at double
    detail (e.g. the player is 32x32 art pixels) and entity.go draws sprites at 0.5 scale
  - a 5x7 pixel TrueType font + the Defold .font
  - sound effects and a looping chiptune track (16-bit mono WAV)

Run from the project root:  python3 tools/generate_assets.py
"""
import math
import os
import random
import struct
import wave
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMG_DIR = os.path.join(ROOT, "main", "assets", "images")
FONT_DIR = os.path.join(ROOT, "main", "assets", "fonts")
SND_DIR = os.path.join(ROOT, "main", "assets", "sounds")
SCALE = 3  # every art pixel becomes a 3x3 block (shown at half size in game, see entity.go)

# ---------------------------------------------------------------------------
# PNG / canvas helpers
# ---------------------------------------------------------------------------

def hexc(s, a=255):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


CLEAR = (0, 0, 0, 0)
OUTLINE = hexc("140c1c")


def write_png(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(c for px in row for c in px) for row in rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[CLEAR] * w for _ in range(h)]

    def set(self, x, y, c, wrap=False):
        x, y = int(x), int(y)
        if wrap:
            x %= self.w
            y %= self.h
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return CLEAR

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, c)

    def circle(self, cx, cy, r, c):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, c)

    def ring(self, cx, cy, r0, r1, c):
        for y in range(int(cy - r1 - 1), int(cy + r1 + 2)):
            for x in range(int(cx - r1 - 1), int(cx + r1 + 2)):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if r0 * r0 <= d2 <= r1 * r1:
                    self.set(x, y, c)

    def line(self, x0, y0, x1, y1, c, thick=1):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) * 2 + 1
        for i in range(steps + 1):
            t = i / steps
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            if thick == 1:
                self.set(round(x), round(y), c)
            else:
                self.circle(x, y, thick / 2.0, c)

    def poly(self, pts, c):
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            yc = y + 0.5
            xs = []
            for i in range(len(pts)):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(math.ceil(xs[i] - 0.5)), int(math.floor(xs[i + 1] - 0.5)) + 1):
                    self.set(x, y, c)

    def outline(self, c=OUTLINE):
        add = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x][3] == 0:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        if self.get(x + dx, y + dy)[3] > 0 and self.get(x + dx, y + dy) != c:
                            add.append((x, y))
                            break
        for x, y in add:
            self.px[y][x] = c
        return self

    def blit(self, other, ox, oy):
        for y in range(other.h):
            for x in range(other.w):
                if other.px[y][x][3] > 0:
                    self.set(ox + x, oy + y, other.px[y][x])

    def save(self, name, scale=SCALE):
        rows = []
        for row in self.px:
            big = []
            for p in row:
                big.extend([p] * scale)
            for _ in range(scale):
                rows.append(big)
        write_png(os.path.join(IMG_DIR, name + ".png"), self.w * scale, self.h * scale, rows)
        return name


def mirror(rows):
    return [r + r[::-1] for r in rows]


def grid(rows, pal):
    w = len(rows[0])
    for r in rows:
        assert len(r) == w, ("bad row width", r, len(r), w)
    cv = Canvas(w, len(rows))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                cv.set(x, y, pal[ch])
    return cv


# ---------------------------------------------------------------------------
# Characters: three views (down = facing camera, up = back, side = facing right;
# the game mirrors side for left). Bodies, legs and arms are separate parts so
# walk cycles are built by offsetting them.
# ---------------------------------------------------------------------------

def paint(cv, rows, pal, ox=0, oy=0, remap=None):
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                if remap:
                    ch = remap.get(ch, ch)
                cv.set(ox + x, oy + y, pal[ch])


def pad(rows, w):
    for r in rows:
        assert len(r) <= w, ("row too wide", r, len(r), w)
    return [r.ljust(w, ".") for r in rows]


def hmirror(rows):
    return [r[::-1] for r in rows]


def save_anim(aid, canvases, fps, playback="PLAYBACK_LOOP_FORWARD"):
    names = []
    for i, cv in enumerate(canvases):
        names.append(cv.save("%s_%d" % (aid, i + 1)))
    ANIMATIONS.append((aid, names, fps, playback))


def copy_canvas(cv):
    out = Canvas(cv.w, cv.h)
    out.px = [row[:] for row in cv.px]
    return out


def glinted(cv, t, width=3):
    """A diagonal shine band at position t (0..1) across the opaque pixels."""
    out = copy_canvas(cv)
    pos = -width + t * (cv.w + cv.h + 2 * width)
    for y in range(cv.h):
        for x in range(cv.w):
            p = cv.px[y][x]
            if p[3] > 0 and p != OUTLINE and abs((x + y) - pos) <= width:
                k = 1 - abs((x + y) - pos) / (width + 1)
                out.px[y][x] = tuple(int(c + (255 - c) * 0.75 * k) for c in p[:3]) + (p[3],)
    return out


def shine(aid, cv, fps=10, rest=6):
    """Still image that catches the light every so often: rest frames, then a 3-frame shine sweep."""
    still = cv.save(aid + "_1")
    sweep = [glinted(cv, t).save("%s_%d" % (aid, i + 2)) for i, t in enumerate((0.25, 0.5, 0.75))]
    ANIMATIONS.append((aid, [still] * rest + sweep, fps, "PLAYBACK_LOOP_FORWARD"))


WALK_LIFT = ("L", None, "R", None)     # front/back walk: which leg is lifted per frame
SIDE_STRIDE = (2, 0, -2, 0)            # side walk: front leg x offset per frame (back leg mirrors it)


def turned(cv, toward_viewer=True, outline=OUTLINE, strength=0.5, squeeze=0.86):
    """Fake a 3/4 turn to the right with a horizontal warp. Facing the viewer, the far (left)
    side stretches and the face slides right; seen from behind, the near (right) side stretches."""
    w, h = cv.w, cv.h
    src = Canvas(w, h)
    src.px = [row[:] for row in cv.px]
    for y in range(h):                       # drop the silhouette outline; it is redrawn after the warp
        for x in range(w):
            if cv.px[y][x] == outline and any(cv.get(x + dx, y + dy)[3] == 0
                                              for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                src.px[y][x] = CLEAR
    # bounding columns of the figure; the turned figure is a little narrower, centred on the same spot
    cols = [x for x in range(w) if any(src.px[y][x][3] for y in range(h))]
    x0, x1 = cols[0], cols[-1] + 1
    nw = (x1 - x0) * squeeze
    n0 = (x0 + x1) / 2 - nw / 2
    out = Canvas(w, h)
    for x in range(w):
        u = (x + 0.5 - n0) / nw
        if not 0 <= u < 1:
            continue
        # sine warp: shifts the middle by ~13% while capping how much the edges stretch
        s = u - strength * math.sin(math.pi * u) / math.pi
        if not toward_viewer:
            s = 1 - ((1 - u) - strength * math.sin(math.pi * (1 - u)) / math.pi)
        sx = min(x1 - 1, x0 + int(s * (x1 - x0)))
        for y in range(h):
            out.px[y][x] = src.px[y][sx]
    return out.outline(outline)


def diagonals(aid, frames_down, frames_up, fps, outline=OUTLINE):
    """down_side / up_side flipbooks derived from the front and back frames."""
    save_anim(aid.replace("{v}", "down_side"), [turned(f, True, outline) for f in frames_down], fps)
    save_anim(aid.replace("{v}", "up_side"), [turned(f, False, outline) for f in frames_up], fps)


def walk_frontal(size, body, pal, leg, lx, rx, ly, bob=True):
    """4 frames: legs alternate lifting one pixel (tucked under the body), body bobs on lift frames."""
    out = []
    for lift in WALK_LIFT:
        cv = Canvas(size, size)
        paint(cv, leg, pal, lx, ly - (1 if lift == "L" else 0))
        paint(cv, hmirror(leg), pal, rx, ly - (1 if lift == "R" else 0))
        paint(cv, body, pal, 0, -1 if (lift and bob) else 0)
        out.append(cv)
    return out


def walk_side(size, body, pal, leg, bx, fx, ly, back_remap, arm=None, ax=0, ay=0, stride=1):
    """4 frames: stride / pass / stride / pass. The far leg is drawn darker and behind the body."""
    out = []
    for i, dx in enumerate(SIDE_STRIDE):
        dx *= stride
        cv = Canvas(size, size)
        bob = -1 if dx == 0 else 0
        far, near = -dx, dx
        paint(cv, leg, pal, bx + far, ly, back_remap)
        paint(cv, body, pal, 0, bob)
        paint(cv, leg, pal, fx + near, ly)
        if arm:
            paint(cv, arm, pal, ax - dx // 2, ay + bob)
        out.append(cv)
    return out


def idle_frames(size, body, pal, legs, arm=None):
    """2 frames: breathing (body sinks one pixel)."""
    out = []
    for dy in (0, 1):
        cv = Canvas(size, size)
        for rows, x, y in legs:
            paint(cv, rows, pal, x, y)
        paint(cv, body, pal, 0, dy)
        if arm:
            paint(cv, arm[0], pal, arm[1], arm[2] + dy)
        out.append(cv)
    return out


def back_view(half, rows):
    """Back view from a front half-grid with the face rows repainted."""
    half = list(half)
    for i, r in rows.items():
        assert len(r) == len(half[i]), (r, half[i])
        half[i] = r
    return mirror(half)


# ---- player -----------------------------------------------------------------

PLAYER_PAL = {
    "k": OUTLINE, "h": hexc("6a3e28"), "H": hexc("442616"), "l": hexc("8e5a36"),
    "s": hexc("f2c49a"), "S": hexc("d49a72"), "p": hexc("ec9a8a"), "m": hexc("9a4a3a"),
    "w": hexc("ffffff"), "e": hexc("2a2440"),
    "r": hexc("b02c3c"), "R": hexc("761c2c"), "q": hexc("d4485a"),
    "b": hexc("3a5cb0"), "B": hexc("26407e"), "c": hexc("5a82d8"),
    "y": hexc("f0c840"), "Y": hexc("b08a20"),
    "g": hexc("6a6a7a"), "G": hexc("44444f"),
}
PLAYER_FRONT = mirror([
    "................",
    "..........kkkkkk",
    "........kkhhhhhh",
    ".......khhhhlllh",
    "......khhhhllhhh",
    ".....khhhhhhhhhh",
    ".....khhlhhhhhhh",
    "....khhlhhhhhhhh",
    "....khhhhhHhhhHh",
    "....khhhHHsHhhss",
    "....khhHssssHsss",
    "...kkhHsssssssss",
    "...ksshssHHsssss",
    "...ksShssewsssss",
    "...kSShsseessss s".replace(" ", ""),
    "....khSspsssssss",
    "....kHSssssssssm",
    ".....kSSssssssss",
    "......kkSSSSSSSS",
    ".....krrkqbbbbbb",
    "....krrqykbbbbbb",
    "...krrrrrkbbbbbb",
    "...krrrrRkbbbbbb",
    "..krrrrrRkbbbbbb",
    "..krrrrRkSSkbbbb",
    "..kRrrrRkssYYyyy",
    "...kRrRRkkbbbbbb",
    "....kRRk.kbbbbBb",
])
PLAYER_BACK = mirror([
    "................",
    "..........kkkkkk",
    "........kkhhhhhh",
    ".......khhhhlllh",
    "......khhhhllhhh",
    ".....khhhhhhhhhh",
    ".....khhlhhhhhhh",
    "....khhlhhhhhhhh",
    "....khhhhhhhhhhh",
    "....khhhhhhhhhhh",
    "....khhhhhhhhhhh",
    "...kkhhhhhhhhhhh",
    "...ksshhhhhhhhhh",
    "...ksShhhhhhhhhh",
    "...kSShhHhhhhhhh",
    "....khhhHhhhhhhh",
    "....kHhhhHhhhhhh",
    ".....kHHhhhhhhhh",
    "......kkHHHHHHHH",
    ".....krrkkSSSSSS",
    "....krrrrqqqqqqq",
    "...krrrrrrrrrrrr",
    "...krrrrrrrrrRrr",
    "..krrrrrrrrrrRrr",
    "..krrrrrrrrrrrRr",
    "..kRrrrrrrrrrrRr",
    "..kRrrrrrrrrrrrR",
    "...kRRRRRRRRRRRR",
])
PLAYER_SIDE = pad([
    "................................",
    "...........kkkkkkk",
    ".........kkhhhhhhhkk",
    "........khhhhlllhhhhk",
    ".......khhhhllhhhhhhhk",
    "......khhhhhhhhhhhhhhhk",
    "......khhlhhhhhhhhhhhhk",
    ".....khhlhhhhhhhhhhhhhhk",
    ".....khhhhhhhhhhhhhHhhhhk",
    ".....khhhhhhhhhhhhHsHhhHk",
    ".....khhhhhhhhhhhHsssHHssk",
    ".....khhhhhhhhhhHssssssssk",
    ".....khhhhhhhhhhSssssssssk",
    ".....kHhhhhSShhSsssssHHssk",
    ".....kHhhhSssShSssssssewsk",
    "......kHhhSssShSsssssseessk",
    "......kHhhhSShhSssspssssssk",
    ".......kHhhhhhhSsssssssmsk",
    "........kHhhhhhkSSssssssk",
    ".........kkkkkkkkSSSSSSk",
    "...........krrrrkqbbbbk",
    "..........krrrrrkybbbbbk",
    ".........krrrrrrkbbbbbbk",
    ".........krrrrrRkbbbbbbk",
    "........krrrrrRRkbbbbbbk",
    "........krrrrRRkbbbbbbbk",
    "........kRrrrRRkYyyyyyyk",
    ".........kRRRRkkbbbbbbbk",
], 32)
PLAYER_LEG = ["kbbbbk", "kBBBBk", "kgggGk", "kkkkkk"]
PLAYER_LEG_SIDE = ["kbbbk.", "kbBBk.", "kgggGk", "kkkkkk"]
PLAYER_ARM_SIDE = ["kbbk", "kbbk", "kbBk", "kBBk", "kSSk", "kkkk"]
DARK_PLAYER = {"b": "B", "g": "G", "S": "S"}


def make_player():
    views = {
        "down": (PLAYER_FRONT, PLAYER_LEG),
        "up": (PLAYER_BACK, ["kBBBBk", "kBBBBk", "kGGGGk", "kkkkkk"]),
    }
    walk, idle = {}, {}
    for view, (body, leg) in views.items():
        walk[view] = walk_frontal(32, body, PLAYER_PAL, leg, 8, 18, 28)
        idle[view] = idle_frames(32, body, PLAYER_PAL, [(leg, 8, 28), (hmirror(leg), 18, 28)])
        save_anim("player_walk_" + view, walk[view], 8)
        save_anim("player_idle_" + view, idle[view], 2)
    diagonals("player_walk_{v}", walk["down"], walk["up"], 8)
    diagonals("player_idle_{v}", idle["down"], idle["up"], 2)
    save_anim("player_walk_side", walk_side(32, PLAYER_SIDE, PLAYER_PAL, PLAYER_LEG_SIDE, 15, 17, 28, DARK_PLAYER,
                                            PLAYER_ARM_SIDE, 17, 20), 8)
    save_anim("player_idle_side", idle_frames(32, PLAYER_SIDE, PLAYER_PAL,
                                              [(PLAYER_LEG_SIDE, 15, 28), (PLAYER_LEG_SIDE, 18, 28)],
                                              (PLAYER_ARM_SIDE, 17, 20)), 2)


# ---- zombie -----------------------------------------------------------------

ZOMBIE_PAL = {"k": OUTLINE, "z": hexc("7aa85a"), "Z": hexc("4e7038"), "x": hexc("9cc87a"),
              "c": hexc("6a5444"), "C": hexc("4a382c"), "d": hexc("846a56"),
              "e": hexc("ff4040"), "E": hexc("ffd0a0"), "t": hexc("e8e0c0"), "m": hexc("2a1a1a")}
ZOMBIE_HALF = [
    "................",
    "................",
    "........kkkkkkkk",
    ".......kzzzzxzzz",
    "......kzzxzzzzzz",
    "......kzzzzzzzzz",
    "......kzzZzzzzzz",
    "......kzzZZkkzzz",
    "......kzzzkeEkzz",
    "......kzzzkeekzz",
    "......kzzzzkkzzz",
    "......kzZzzzzzzz",
    "......kzzZzzmmmm",
    ".......kzzZzmtmt",
    "........kZZZZZZZ",
    ".....kkkkcccdccc",
    "....kzzkccCcdccc",
    "...kzzzkcccCcccc",
    "..kzzzzkccdcCccc",
    "..kzzzkkcccccccc",
    "..kzzkdkcCccccdc",
    "..kZZkkkcccCcccc",
    "..kZk..kccccdccc",
    "...k...kcCcccccc",
    "......kccccccCCk",
    "......kCCCCCk.kk",
]
ZOMBIE_FRONT = mirror(ZOMBIE_HALF)
ZOMBIE_BACK = back_view(ZOMBIE_HALF, {
    7: "......kzzZZzzzzz", 8: "......kzzzzzZzzz", 9: "......kzzzzzzzzz", 10: "......kzzzZzzzzz",
    12: "......kzzZzzzzzz", 13: ".......kzzZzzzzz"})
ZOMBIE_SIDE = pad([
    "",
    "",
    "...........kkkkkkkk",
    "..........kzzzzxzzzk",
    ".........kzzxzzzzzzzk",
    ".........kzzzzzzzzzzk",
    ".........kzZzzzzzzzzk",
    ".........kzZZzzzzkkzzk",
    ".........kzzzzzzkeEkzk",
    ".........kzzZzzzkeekzk",
    ".........kzzzzzzzkkzzzk",
    ".........kzZzzzzzzzzzk",
    ".........kzzZzzzzzmmmk",
    "..........kzzZzzzzmtmk",
    "...........kZZZZZZZZk",
    "...........kkcccdcckkkkkkkkkk",
    "..........kccccCckzzzzzzzzzzzk",
    "..........kcccCcckzzZzzzzzzZzzk",
    "..........kccdcccckkkkkkkkkkkk",
    "..........kcccCccck",
    "..........kccccdcck",
    "..........kcCcccccck",
    "..........kccccCcck",
    "..........kcccccccck",
    "...........kCCCCCCk",
    "...........kCCCCCk",
], 32)
ZOMBIE_LEG = [".kZZZk", ".kzzzk", ".kzzZk", "kkzzzk", "kZZZZk", "kkkkkk"]
ZOMBIE_LEG_SIDE = ["kZZk.", "kzzk.", "kzzk.", "kzZk.", "kzzzk", "kkkkk"]


# ---- skeleton ---------------------------------------------------------------

SKEL_PAL = {"k": OUTLINE, "b": hexc("e8e6d4"), "B": hexc("a8a490"), "w": hexc("ffffff"),
            "e": hexc("ff6020"), "E": hexc("ffd060"), "d": hexc("3a3040")}
SKEL_HALF = [
    "................",
    "..........kkkkkk",
    "........kkbbbbbb",
    ".......kbbbwwbbb",
    "......kbbbwbbbbb",
    "......kbbbbbbbbb",
    "......kbbbkkkbbb",
    "......kbbkddEkbb",
    "......kbbkdeekbb",
    "......kbBbkkkbBb",
    ".......kbBbbbbkk",
    "........kbbkbkbk",
    "........kkbkbkbk",
    ".........kkkkkkb",
    "..........kbbBkb",
    ".....kkkkkbbbbbb",
    "....kbbbkbkkkkbb",
    "...kbBkk.kbbbbBb",
    "...kbk...kkkkkbb",
    "...kbk...kbbbbBb",
    "...kbk...kkkkkbb",
    "...kBk...kbbbbBb",
    "...kbbk...kkkkbb",
    "....kk....kbBBbb",
    "..........kbbbbb",
    "...........kkkkk",
]
SKEL_FRONT = mirror(SKEL_HALF)
SKEL_BACK = back_view(SKEL_HALF, {
    6: "......kbbbbbbbbb", 7: "......kbbbbbbbbb", 8: "......kbBbbbbbbb", 9: "......kbBbbbbbBb",
    10: ".......kbBbbbbbb", 11: "........kbbbbbbb", 12: "........kkbbbbbb"})
SKEL_SIDE = pad([
    "",
    "..........kkkkkkk",
    "........kkbbbbbbbk",
    ".......kbbbwwbbbbbk",
    "......kbbbwbbbbbbbbk",
    "......kbbbbbbbbbbbbk",
    "......kbbbbbbbkkkbbk",
    "......kbbbbbbkddEkbk",
    "......kBbbbbbkdeekbk",
    "......kBBbbbbbkkkbbbk",
    ".......kBbbbbbbbbbbk",
    "........kBbbbkbkbkbk",
    ".........kBbkbkbkbk",
    "..........kkkkkkkk",
    "............kbbBk",
    "..........kkbbbbbk",
    ".........kbbkkkkbbk",
    ".........kbbbbbbbbk",
    ".........kbkkkkkbbk",
    ".........kbbbbbbbbk",
    "..........kbkkkkbk",
    "...........kbbbbk",
    "............kbBk",
    "...........kbbbbk",
    "..........kbbbbbbk",
    "...........kkkkkk",
], 32)
SKEL_LEG = ["kbk", "kbk", "kBk", "kbk", "kbbk", "kkkk"]
SKEL_LEG_FRONT = ["..kbk", "..kbk", "..kBk", "..kbk", ".kbbk", ".kkkk"]
SKEL_ARM_SIDE = ["kbk", "kbk", "kBk", "kbk", "kbk", "kbbk", "kkk"]


# ---- ogre (boss, 48x48) -----------------------------------------------------

OGRE_PAL = {"k": OUTLINE, "o": hexc("c03a32"), "O": hexc("7a2020"), "x": hexc("e05a48"),
            "h": hexc("ece0b0"), "H": hexc("b0a478"), "e": hexc("ffe040"), "t": hexc("ffffff"),
            "a": hexc("5c5e70"), "A": hexc("8a8ca0"), "s": hexc("3c3e4c"), "m": hexc("2a0e10")}
OGRE_HALF = [
    "........................",
    "....kk..................",
    "...khk..................",
    "...khhk.................",
    "..khhHk.................",
    "..khhhHk................",
    "...khhhHk.......kkkkkkkk",
    "...kHhhhHk....kkoooooooo",
    "....kHhhhHkkkkoooxxooooo",
    ".....kHHhhHoooooxxoooooo",
    "......kkHHooooooooooooOo",
    "........kooooooOoooooooo",
    "........kooooooOOooooooo",
    "........kooooooooOOkkooo",
    "........koooooooookeekoo",
    "........kooooooooookkooo",
    "........kOoooooooooooooo",
    "........kOOoooooookkkkkk",
    ".........kOOooooooktmtmt",
    ".........kOOoooooookkkkk",
    "..........kkOOoooooooooo",
    "............kkOOOOOOOOOO",
    "......kkkkkkkkaaaaaaaaaa",
    "....kkoooooksAaaaaaaaaaa",
    "...koooxooksaAaaaaaAaaaa",
    "..kooooxoksaaaaaaaaaaaaa",
    "..koooxoksaaaaaaaaaaaaaa",
    ".koooooksaaaaaaaaaaaaaaa",
    ".kooooOksAssssssssssssss",
    ".koookkksaaaaaaaaaaaaaaa",
    ".kooOk.ksaaaaaaaaaaaaaaa",
    ".kooOk.ksaaaaaAaaaaaaaAa",
    ".kOoOk.kssaaaaaaaaaaaaaa",
    "..koook.ksssaaaaaaaaaaaa",
    "..kxoook.kssssssssssssss",
    "...kkkk..kOOOOOOOOOOOOOO",
    ".........kOOOOOOkkOOOOOO",
    "........kOOOOOOk..kkkkkk",
]
OGRE_FRONT = mirror(OGRE_HALF)
OGRE_BACK = back_view(OGRE_HALF, {
    13: "........kooooooooOOooooo", 14: "........kooooooooooooooo", 15: "........kooooooOoooooooo",
    17: "........kOOooooooooooooo", 18: ".........kOOooooooOooooo", 19: ".........kOOoooooooooooo"})
OGRE_SIDE = pad([
    "",
    "",
    "..............kk",
    ".............khk",
    "............khhk",
    "...........khhHk",
    "..........khhHk",
    "..........khHk..kkkkkkkkk",
    "...........kHkkkooooooooookk",
    "............kooooxxooooooooook",
    "...........kooooxxooooooooooooook",
    "...........koooooooooooOOoooooook",
    "...........kooooooooooookkoooooook",
    "...........koooOoooooookeekooooook",
    "...........kooOoooooooookkoooooooook",
    "...........koooooooooooooooooooooook",
    "...........kOooooooooooookkkkkkkkkk",
    "............kOooooooooooktmtmtmtk",
    "............kOOoooooooookkkkkkkkk",
    ".............kOOoooooooooooooook",
    "..............kkOOOOOOOOOOOOOk",
    "............kkkkaaaaaaaaaaaaakk",
    "..........kksAaaaaaaaaaaaaaaaaak",
    ".........ksaAaaaaaaaaaaaaaaaaaaak",
    ".........ksaaaaaaaaaaaaaaaaaaaaak",
    ".........ksaaaaaaAaaaaaaaaaaaaaak",
    ".........ksaaaaaaaaaaaaaaaaaaaaak",
    ".........ksssssssssssssssssssssk",
    ".........ksaaaaaaaaaaaaaaaaaaaaak",
    ".........ksaaaaaaAaaaaaaaaaaaaaak",
    ".........ksaaaaaaaaaaaaaaaaaaaaak",
    "..........ksaaaaaaaaaaaaaaaaaaak",
    "..........kssssssssssssssssssk",
    "...........kOOOOOOOOOOOOOOOOOk",
    "...........kOOOOOOOOOOOOOOOOk",
    "............kkkkkkkkkkkkkkkk",
], 48)
OGRE_LEG = [".kooooook", ".kooxoook", ".kooooook", "kkoooooOk", "kOOOOOOOk", "kkkkkkkkk"]
OGRE_LEG_SIDE = ["kooooook.", "kooooook.", "kooxoook.", "kooooook.", "kooooook.", "kOoooooOkk",
                 "kOOOOOOOOk", "kkkkkkkkkk"]
OGRE_ARM_SIDE = [".kkkk.", "koooxk", "kooxok", "koooook", "koooook", "kooOook", "kOooOok", "koooook",
                 "kxooook", "kooooook", "kkkkkkk"]


def make_walkers():
    dark = {"z": "Z", "x": "Z", "c": "C", "d": "C", "b": "B", "w": "B", "o": "O"}
    sets = (
        ("zombie", 32, ZOMBIE_PAL, ZOMBIE_FRONT, ZOMBIE_BACK, ZOMBIE_SIDE, ZOMBIE_LEG, 6, 20, 26,
         ZOMBIE_LEG_SIDE, 13, 15, 26, None, 1, 4),
        ("skeleton", 32, SKEL_PAL, SKEL_FRONT, SKEL_BACK, SKEL_SIDE, SKEL_LEG_FRONT, 9, 18, 26,
         SKEL_LEG, 12, 14, 26, (SKEL_ARM_SIDE, 13, 15), 1, 7),
        ("ogre", 48, OGRE_PAL, OGRE_FRONT, OGRE_BACK, OGRE_SIDE, OGRE_LEG, 7, 32, 38,
         OGRE_LEG_SIDE, 13, 18, 35, (OGRE_ARM_SIDE, 18, 21), 2, 4),
    )
    for (name, size, pal, front, back, side, leg, lx, rx, ly, leg_side, bx, fx, sly, arm, stride, fps) in sets:
        down = walk_frontal(size, front, pal, leg, lx, rx, ly)
        up = walk_frontal(size, back, pal, leg, lx, rx, ly)
        save_anim(name + "_down", down, fps)
        save_anim(name + "_up", up, fps)
        diagonals(name + "_{v}", down, up, fps)
        a = arm or (None, 0, 0)
        far = {k: v for k, v in dark.items() if k in pal and v in pal}
        save_anim(name + "_side", walk_side(size, side, pal, leg_side, bx, fx, sly, far, a[0], a[1], a[2], stride), fps)


# ---- bat (front/back grids, side drawn from shapes) -------------------------

BAT_PAL = {"k": OUTLINE, "p": hexc("8a4ab8"), "m": hexc("6a3490"), "P": hexc("3e1a5c"), "Q": hexc("2a1040"),
           "e": hexc("ff3a3a"), "E": hexc("ffb0a0"), "f": hexc("ffffff")}
BAT_UP = mirror([
    "................", "................", "................",
    "k...............",
    "kk..............",
    "kpk.............",
    "kmpk............",
    "kmmpk...........",
    "kmmmpk......k...",
    "kpmmmpk.....kk..",
    "kmpmmmpk....kPk.",
    "kmmpmmmpk..kPPkk",
    "kmmmpmmmpkkPPPPP",
    "kpmmmpmmmPPPPPPP",
    ".kmmmmpmPPPPEePP",
    ".kpmmmmpPPPPeePP",
    "..kmmmmmPPPPPPPP",
    "..kpmmmmPQPPPPfP",
    "...kmmmkPPQPPPfk",
    "...kmmk.kPPQPPPP",
    "....kmk..kPPPQQQ",
    "....kk....kPPPPP",
    ".....k.....kkPPP",
    "............kkkk",
    "................", "................", "................", "................",
    "................", "................", "................", "................",
])
BAT_MID = mirror([
    "................", "................", "................", "................",
    "................", "................", "................", "................",
    "............k...",
    "............kk..",
    "............kPk.",
    "...........kPPkk",
    "..........kPPPPP",
    "kkkkkkkkkkPPPPPP",
    "kpmmpmmmpPPPEePP",
    ".kmmpmmmpPPPeePP",
    "..kmmkmmmPPPPPPP",
    "...kk.kmmPQPPPfP",
    ".......kkPPQPPfk",
    ".........kPPQPPP",
    "..........kPPQQQ",
    "...........kPPPP",
    "............kkPP",
    "..............kk",
    "................", "................", "................", "................",
    "................", "................", "................", "................",
])
BAT_DOWN = mirror([
    "................", "................", "................", "................",
    "................", "................", "................",
    "............k...",
    "............kk..",
    "............kPk.",
    "...........kPPkk",
    "..........kPPPPP",
    "......kkkkPPPPPP",
    "....kkmmmPPPPEeP",
    "...kmmmmmPPPPeeP",
    "..kmmmmpmPPPPPPP",
    ".kmmmmpmmPQPPPfP",
    ".kmmmpmmmkPQPPfk",
    "kmmmpmmmk.kPQPPP",
    "kmmpmmmk...kPQQQ",
    "kmpmmmk.....kPPP",
    "kppmmk.......kkP",
    "kpk.kk........kk",
    "kk..............",
    "k...............",
    "................", "................", "................", "................",
    "................", "................", "................",
])


def bat_side(phase):
    """Side view facing right; phase: -1 wings up, 0 level, 1 down."""
    pal = BAT_PAL
    cv = Canvas(32, 32)
    t = phase * 9
    # far wing (darker, behind)
    cv.poly([(15, 14), (9, 13 + t * 0.5), (5, 12 + t), (8, 16 + t * 0.6), (12, 17)], pal["Q"])
    cv.circle(15, 17, 5.2, pal["P"])
    cv.circle(21, 14, 4.2, pal["P"])
    cv.poly([(19, 11), (21, 5), (23, 11)], pal["P"])
    cv.line(21, 7, 21, 10, pal["m"])
    cv.rect(23, 13, 24, 14, pal["e"])
    cv.set(24, 13, pal["E"])
    cv.set(24, 17, pal["f"])
    cv.set(14, 22, pal["k"])
    cv.set(17, 22, pal["k"])
    # near wing: membrane with bone struts
    tip = (3, 15 + t)
    elbow = (10, 15 + t * 0.45)
    cv.poly([(16, 15), elbow, tip, (6, 19 + t * 0.7), (10, 19 + t * 0.4), (13, 20)], pal["m"])
    cv.line(16, 15, elbow[0], elbow[1], pal["p"])
    cv.line(elbow[0], elbow[1], tip[0], tip[1], pal["p"])
    cv.line(elbow[0], elbow[1], 6, 19 + t * 0.7, pal["p"])
    cv.outline()
    return cv


def make_bat():
    frames = (BAT_UP, BAT_MID, BAT_DOWN, BAT_MID)
    save_anim("bat_down", [grid(f, BAT_PAL) for f in frames], 10)
    back = {"e": "P", "E": "P", "f": "P"}
    save_anim("bat_up", [grid(["".join(back.get(c, c) for c in r) for r in f], BAT_PAL) for f in frames], 10)
    save_anim("bat_side", [bat_side(p) for p in (-1, 0, 1, 0)], 10)
    diagonals("bat_{v}", [grid(f, BAT_PAL) for f in frames],
              [grid(["".join(back.get(c, c) for c in r) for r in f], BAT_PAL) for f in frames], 10)


# ---- ghost (drawn from shapes) ------------------------------------------------

GHOST_PAL = {"k": hexc("2a3a60"), "g": hexc("d4e6ff"), "G": hexc("98b0e0"), "w": hexc("ffffff"),
             "e": hexc("1a1a38"), "b": hexc("f0a0c0")}


def ghost_frame(view, i):
    pal = GHOST_PAL
    cv = Canvas(32, 32)
    bob = (0, -1, -2, -1)[i]
    ph = i * math.pi / 2
    cx, top = 15.5, 13 + bob
    lean = {"side": 3, "down_side": 1.5, "up_side": 1.5}.get(view, 0)
    for y in range(0, 32):
        for x in range(32):
            dy = y - top
            if dy < 0:
                inside = (x - cx) ** 2 + dy * dy <= 10.5 ** 2
            else:
                shift = lean * dy / 14.0                 # side view: tail trails behind (left)
                edge = 24 + bob + 2.2 * math.sin((x + shift) * 0.75 + ph) + (dy > 9) * 0
                inside = abs(x + shift - cx) <= 10.5 - max(0, dy - 6) * 0.15 and y <= edge
            if inside:
                cv.set(x, y, pal["g"])
    # rim shade on the left, soft highlight top-left
    for y in range(32):
        for x in range(32):
            if cv.get(x, y) == pal["g"] and cv.get(x - 1, y)[3] == 0:
                cv.set(x, y, pal["G"])
                if cv.get(x + 1, y) == pal["g"]:
                    cv.set(x + 1, y, pal["G"]) if y > top + 6 else None
    cv.rect(int(cx) - 5, int(top) - 7, int(cx) - 4, int(top) - 6, pal["w"])
    cv.set(int(cx) - 6, int(top) - 5, pal["w"])
    if not view.startswith("up"):
        # the face slides toward the direction of travel: front, 3/4, profile
        turn = {"down": 0, "down_side": 3, "side": 6}[view]
        ex = (cx - 6 + turn * 1.15, cx + 3 + turn * 0.5)
        for x0 in ex:
            cv.rect(int(x0), int(top) - 2, int(x0) + 2, int(top) + 1, pal["e"])
            cv.set(int(x0) + 1, int(top) - 2, pal["w"])
        mx = int(cx) - 1 + (turn * 5) // 6
        cv.rect(mx, int(top) + 4, mx + 2, int(top) + 5 + (i % 2), pal["e"])
        for x0 in ((ex[0] - 1, ex[1] + 2) if turn < 6 else (ex[1] + 2,)):
            cv.set(int(x0), int(top) + 3, pal["b"])
    cv.outline(pal["k"])
    return cv


def make_ghost():
    for view in ("down", "down_side", "side", "up_side", "up"):
        save_anim("ghost_" + view, [ghost_frame(view, i) for i in range(4)], 6)


# ---- eye (drawn from shapes; the iris looks where it's going) ---------------

EYE_PAL = {"k": OUTLINE, "w": hexc("f2e8e6"), "W": hexc("c8b8c0"), "h": hexc("ffffff"),
           "r": hexc("c83a4a"), "i": hexc("8a3ab8"), "I": hexc("b86ae0"), "p": hexc("120818"),
           "f": hexc("a04a6a"), "F": hexc("6a2a48")}


def eye_frame(view, i):
    pal = EYE_PAL
    cv = Canvas(32, 32)
    ph = i * math.pi / 2
    cx, cy = 15.5, 13.5
    for n, x0 in enumerate((9, 13, 18, 22)):            # tentacles
        wob = math.sin(ph + n * 1.7) * 2
        cv.line(x0, 23, x0 + wob * 0.5, 27, pal["f"], thick=2)
        cv.line(x0 + wob * 0.5, 27, x0 + wob, 30, pal["F"])
    cv.circle(cx, cy, 12.4, pal["W"])
    cv.circle(cx + 0.8, cy - 0.8, 11.4, pal["w"])
    cv.circle(cx - 4, cy - 5, 2.4, pal["h"])
    random.seed(55)
    for _ in range(6):                                     # veins from the rim inward
        a = random.random() * 2 * math.pi
        r0, r1 = 11.5, 7 + random.random() * 2
        x1, y1 = cx + math.cos(a) * r1, cy + math.sin(a) * r1
        cv.line(cx + math.cos(a) * r0, cy + math.sin(a) * r0, x1, y1, pal["r"])
        cv.line(x1, y1, x1 + random.choice((-1, 1)), y1 + random.choice((-1, 1)), pal["r"])
    ox, oy = {"down": (0, 3), "down_side": (3.5, 2.5), "side": (5, 0), "up_side": (3.5, -3), "up": (0, -4)}[view]
    ix, iy = cx + ox, cy + oy
    cv.circle(ix, iy, 5.6, pal["i"])
    cv.circle(ix - 0.5, iy - 0.5, 4.3, pal["I"])
    cv.circle(ix, iy, 2.8 + (0.6 if i == 2 else 0), pal["p"])
    cv.rect(int(ix) - 2, int(iy) - 3, int(ix) - 1, int(iy) - 2, pal["h"])
    cv.outline()
    return cv


def make_eye():
    for view in ("down", "down_side", "side", "up_side", "up"):
        save_anim("eye_" + view, [eye_frame(view, i) for i in range(4)], 6)


# ---- brazier (prop: flames drawn per frame) -----------------------------------

BRAZIER_PAL = {"k": OUTLINE, "s": hexc("7a7c88"), "S": hexc("4e505c"), "l": hexc("a0a2b0"),
               "o": hexc("ff9a30"), "y": hexc("ffe060"), "w": hexc("fff8d0"), "r": hexc("e04020"),
               "R": hexc("a02818"), "c": hexc("3a2a2a")}
BRAZIER_BASE = mirror([
    "....kccRrroooooo",
    "....kkkkkkkkkkkk",
    "...kllllllllllll",
    "...ksssssssssss s".replace(" ", ""),
    "....kSssssssssss",
    ".....kSsssssssss",
    "......kSSsssssss",
    ".......kkSSSSSSS",
    ".........kkkSsss",
    "..........kSssls",
    "..........kSssls",
    "..........kSssls",
    "..........kSssls",
    ".........kSSssls",
    "........kSSssssl",
    "......kkSSSSSsss",
    ".....kSSSSSSSSSS",
    ".....kkkkkkkkkkk",
])


def brazier_frame(i):
    pal = BRAZIER_PAL
    cv = Canvas(32, 32)
    ph = i * math.pi / 2
    base_y = 14
    for x in range(6, 26):
        env = max(0.0, 1 - ((x - 15.5) / 10.5) ** 2)
        h = env * (10 + 2.5 * math.sin(x * 0.8 + ph) + 1.5 * math.sin(x * 1.9 - ph * 2))
        for y in range(base_y, int(base_y - h) - 1, -1):
            t = (base_y - y) / max(h, 1)
            core = abs(x - 15.5) < 5 * env
            col = "r" if t > 0.82 else "o" if t > 0.55 else ("w" if core and t < 0.3 else "y")
            cv.set(x, y, pal[col])
    random.seed(90 + i)
    for _ in range(3):                                     # embers
        x, y = random.randint(9, 22), random.randint(0, 5)
        cv.set(x, y, pal["o"] if random.random() < 0.5 else pal["y"])
    paint(cv, BRAZIER_BASE, pal, 0, base_y)
    return cv


def make_brazier():
    save_anim("brazier", [brazier_frame(i) for i in range(4)], 8)


def make_characters():
    make_player()
    make_walkers()
    make_bat()
    make_ghost()
    make_eye()
    make_brazier()


# ---------------------------------------------------------------------------
# Weapons, pickups, effects
# ---------------------------------------------------------------------------

def make_gem(name, light, mid, dark):
    cv = Canvas(14, 18)
    cv.poly([(7, 0), (14, 9), (7, 18), (0, 9)], mid)
    cv.poly([(7, 0), (7, 18), (0, 9)], light)
    cv.poly([(7, 9), (14, 9), (7, 18)], dark)
    cv.poly([(7, 4), (10.5, 9), (7, 14), (3.5, 9)], mid)       # inner table facet
    cv.line(2, 8, 6, 3, (255, 255, 255, 180))
    cv.rect(4, 6, 5, 7, (255, 255, 255, 255))
    big = Canvas(18, 22)
    big.blit(cv, 2, 2)
    big.outline()
    shine(name, big, fps=12, rest=5)


def lightning_frame(seed):
    """Tall bolt with side forks; bottom centre is the impact point."""
    random.seed(seed)
    cv = Canvas(28, 180)
    pts = [(14, 0)]
    y = 0
    while y < 178:
        y = min(179, y + random.randint(10, 18))
        pts.append((max(5, min(22, 14 + random.randint(-8, 8))), y))
    pts[-1] = (14, 179)
    forks = []
    for (x0, y0) in pts[1:-2:2]:
        dx = random.choice((-1, 1)) * random.randint(4, 7)
        forks.append(((x0, y0), (max(1, min(26, x0 + dx)), y0 + random.randint(8, 14))))
    for a, b in forks:
        cv.line(a[0], a[1], b[0], b[1], hexc("60c8ff"), thick=3)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(x0, y0, x1, y1, hexc("3a8cff", 150), thick=10)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(x0, y0, x1, y1, hexc("60c8ff"), thick=7)
    for a, b in forks:
        cv.line(a[0], a[1], b[0], b[1], hexc("e8f8ff"))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(x0, y0, x1, y1, hexc("ffffff"), thick=3)
    return cv


def make_projectiles():
    # magic bolt: glowing orb with a bright core, pulsing
    frames = []
    for pulse in (0, 1, 2, 1):
        cv = Canvas(20, 20)
        cv.circle(9.5, 9.5, 8.6 + pulse * 0.35, hexc("2a6aff", 90))
        cv.circle(9.5, 9.5, 7.8, hexc("2a6aff", 160))
        cv.circle(9.5, 9.5, 6.2, hexc("60c8ff"))
        cv.circle(9.5, 9.5, 3.4 + pulse * 0.4, hexc("a8e8ff"))
        cv.circle(9.5, 9.5, 1.8 + pulse * 0.4, hexc("ffffff"))
        cv.rect(6, 6, 7, 6, hexc("ffffff"))
        frames.append(cv)
    save_anim("bolt", frames, 14)

    # knife pointing right
    cv = Canvas(28, 10)
    cv.poly([(10, 2), (24, 2.5), (28, 5), (24, 7.5), (10, 8)], hexc("b8bccb"))
    cv.poly([(10, 2), (24, 2.5), (28, 5), (10, 5)], hexc("d8dce8"))
    cv.line(10, 3, 24, 3, hexc("ffffff"))
    cv.line(11, 5, 22, 5, hexc("8a8ea0"))
    cv.rect(7, 0, 9, 9, hexc("c8a040"))
    cv.rect(9, 0, 9, 9, hexc("8a6a20"))
    cv.rect(7, 0, 7, 9, hexc("f0d070"))
    cv.rect(1, 3, 6, 6, hexc("7a4a2a"))
    cv.rect(1, 3, 6, 3, hexc("9a6a3a"))
    for x in (2, 4):
        cv.rect(x, 3, x, 6, hexc("5a321a"))
    cv.rect(0, 2, 1, 7, hexc("c8a040"))
    cv.save("knife")

    # holy orb: the glow breathes and a glint circles the surface
    frames = []
    for i in range(6):
        a = i * math.pi / 3
        cv = Canvas(24, 24)
        cv.circle(11.5, 11.5, 10.8 + 0.5 * math.sin(a), hexc("ffd040", 80))
        cv.circle(11.5, 11.5, 9.8, hexc("ffd040", 150))
        cv.circle(11.5, 11.5, 8.4, hexc("e8a020"))
        cv.circle(11, 11, 7.4, hexc("ffc830"))
        cv.circle(10.5, 10.5, 5.6, hexc("ffe890"))
        cv.circle(9, 9, 2.6, hexc("fff8e0"))
        cv.rect(8, 8, 9, 8, hexc("ffffff"))
        gx, gy = 11.5 + math.cos(a) * 6.5, 11.5 + math.sin(a) * 6.5
        cv.rect(int(gx), int(gy), int(gx) + 1, int(gy), hexc("ffffff"))
        frames.append(cv)
    save_anim("orb", frames, 12)

    # garlic aura ring (large, translucent)
    n = 128
    c = (n - 1) / 2
    frames = []
    for i in range(4):
        cv = Canvas(n, n)
        for y in range(n):
            for x in range(n):
                d = math.hypot(x - c, y - c)
                if d <= 63.5:
                    if d > 61.5:
                        a = 190
                    elif d > 59.5:
                        a = 130
                    elif d > 55.5:
                        a = 110 if (x + y + i) % 2 == 0 else 60
                    else:
                        wave = math.sin(d * 0.35 - i * math.pi / 2)   # rings drifting outward
                        a = 34 + int(26 * (d / 63.5)) + int(10 * wave)
                    cv.set(x, y, (210, 240, 150, a))
        frames.append(cv)
    save_anim("aura", frames, 6)

    # lightning bolt (tall; bottom = impact point) with side forks
    frames = []
    for seed in (7, 8, 9):
        frames.append(lightning_frame(seed))
    save_anim("lightning", frames, 18)


    # death puff (6 frames)
    frames = []
    for i in range(6):
        r1 = 6 + i * 1.9
        r0, density = max(0, r1 - 7 + i * 0.4), 1.0 - i * 0.13
        random.seed(100 + i)
        cv = Canvas(32, 32)
        for y in range(32):
            for x in range(32):
                d = math.hypot(x - 15.5, y - 15.5)
                if r0 <= d <= r1 and random.random() < density:
                    mid = (r0 + r1) / 2
                    col = hexc("ffffff") if d < mid - 2 else hexc("e8e0f0") if d < mid else hexc("9a90b0")
                    cv.set(x, y, col)
        frames.append(cv)
    save_anim("puff", frames, 20, "PLAYBACK_ONCE_FORWARD")

    # hit spark (4 frames): flash, burst, rays fly out and thin
    frames = []
    for i in range(4):
        cv = Canvas(24, 24)
        r = 5 + i * 2.2
        for k in range(8):
            ang = k * math.pi / 4 + (math.pi / 8 if i % 2 else 0) * 0.3
            ln = r if k % 2 == 0 else r - 2
            col = hexc("ffffff") if i == 0 else hexc("fff0a0") if i < 3 else hexc("e8c860", 180)
            cv.line(11.5 + math.cos(ang) * (ln - 4), 11.5 + math.sin(ang) * (ln - 4),
                    11.5 + math.cos(ang) * ln, 11.5 + math.sin(ang) * ln, col,
                    thick=2 if (k % 2 == 0 and i < 2) else 1)
        if i < 2:
            cv.circle(11.5, 11.5, 3 - i * 1.2, hexc("ffffff"))
        frames.append(cv)
    save_anim("spark", frames, 24, "PLAYBACK_ONCE_FORWARD")

    # simple white pixel + soft shadow
    cv = Canvas(8, 8)
    cv.rect(0, 0, 7, 7, (255, 255, 255, 255))
    cv.save("pixel", scale=1)
    cv = Canvas(28, 10)
    for y in range(10):
        for x in range(28):
            d = ((x - 13.5) / 14) ** 2 + ((y - 4.5) / 5) ** 2
            if d <= 1:
                cv.set(x, y, (0, 0, 0, 110 if d < 0.55 else 70))
    cv.save("shadow")


def draw_chicken(cv, ox=0, oy=0):
    cv.circle(ox + 10, oy + 10, 8.6, hexc("8a4418"))
    cv.circle(ox + 9.5, oy + 9.5, 7.8, hexc("c06a2a"))
    cv.circle(ox + 8.5, oy + 8.5, 5.2, hexc("e08a40"))
    cv.circle(ox + 7, oy + 7, 2.2, hexc("ffc080"))
    cv.set(ox + 12, oy + 7, hexc("8a4418"))
    cv.set(ox + 7, oy + 12, hexc("a85a22"))
    cv.line(ox + 16, oy + 16, ox + 22, oy + 22, hexc("d8d0c0"), thick=4)
    cv.line(ox + 16, oy + 16, ox + 22, oy + 22, hexc("f4eee0"), thick=2)
    cv.circle(ox + 24, oy + 22, 2.4, hexc("f4eee0"))
    cv.circle(ox + 22, oy + 24, 2.4, hexc("f4eee0"))
    cv.set(ox + 23, oy + 21, hexc("ffffff"))


def draw_magnet(cv, ox=0, oy=0):
    cv.ring(ox + 14, oy + 12, 5, 11, hexc("d83a3a"))
    cv.ring(ox + 14, oy + 12, 5, 7, hexc("a02828"))
    cv.ring(ox + 14, oy + 12, 9.5, 11, hexc("ff6a6a"))
    cv.rect(ox, oy, ox + 28, oy + 11, CLEAR)
    cv.rect(ox + 3, oy + 4, ox + 8, oy + 12, hexc("d83a3a"))
    cv.rect(ox + 20, oy + 4, ox + 25, oy + 12, hexc("d83a3a"))
    cv.rect(ox + 3, oy + 4, ox + 3, oy + 12, hexc("ff6a6a"))
    cv.rect(ox + 20, oy + 4, ox + 20, oy + 12, hexc("ff6a6a"))
    cv.rect(ox + 8, oy + 4, ox + 8, oy + 12, hexc("a02828"))
    cv.rect(ox + 25, oy + 4, ox + 25, oy + 12, hexc("a02828"))
    cv.rect(ox + 3, oy + 1, ox + 8, oy + 4, hexc("e0e4f0"))
    cv.rect(ox + 20, oy + 1, ox + 25, oy + 4, hexc("e0e4f0"))
    cv.rect(ox + 3, oy + 1, ox + 8, oy + 1, hexc("ffffff"))
    cv.rect(ox + 20, oy + 1, ox + 25, oy + 1, hexc("ffffff"))
    cv.rect(ox + 9, oy + 18, ox + 10, oy + 19, hexc("ffb0b0"))


def make_pickups():
    make_gem("gem_blue", hexc("a0e0ff"), hexc("3a8cff"), hexc("1a4ab0"))
    make_gem("gem_green", hexc("b0ffb8"), hexc("3ad860"), hexc("1a8034"))
    make_gem("gem_red", hexc("ffb0b8"), hexc("ff3a50"), hexc("a01a2c"))
    cv = Canvas(30, 30)
    draw_chicken(cv, 1, 1)
    cv.outline()
    shine("chicken", cv)
    cv = Canvas(30, 28)
    draw_magnet(cv, 1, 1)
    cv.outline()
    shine("magnet", cv)
    # treasure chest (boss drop): planked lid and body, gold bands, lock
    cv = Canvas(32, 26)
    cv.rect(2, 9, 29, 24, hexc("8a5428"))
    cv.rect(2, 2, 29, 8, hexc("a8682e"))
    cv.rect(3, 2, 28, 2, hexc("c8843e"))
    for y in (5, 14, 19):
        cv.rect(2, y, 29, y, hexc("6a3c1c"))
    cv.rect(2, 9, 29, 10, hexc("5a3418"))
    cv.rect(2, 24, 29, 24, hexc("5a3418"))
    for x0 in (2, 27):
        cv.rect(x0, 2, x0 + 2, 24, hexc("f0c840"))
        cv.rect(x0 + 2, 2, x0 + 2, 24, hexc("b08a20"))
    cv.rect(12, 7, 19, 15, hexc("f0c840"))
    cv.rect(12, 7, 19, 7, hexc("fff0a0"))
    cv.rect(12, 15, 19, 15, hexc("b08a20"))
    cv.rect(15, 10, 16, 13, OUTLINE)
    cv.rect(14, 10, 17, 11, OUTLINE)
    cv.outline()
    shine("chest", cv)


# ---------------------------------------------------------------------------
# Upgrade icons (32x32 native + outline)
# ---------------------------------------------------------------------------

def icon(name, draw):
    cv = Canvas(36, 36)
    inner = Canvas(32, 32)
    draw(inner)
    cv.blit(inner, 2, 2)
    cv.outline()
    cv.save(name)


def make_icons():
    def wand(c):
        c.line(4, 28, 19, 13, hexc("5a321a"), thick=4)
        c.line(4, 27, 19, 12, hexc("9a6a3a"), thick=2)
        c.rect(17, 12, 20, 15, hexc("c8a040"))
        c.circle(23, 9, 7, hexc("2a6aff", 140))
        c.circle(23, 9, 5.6, hexc("60c8ff"))
        c.circle(23, 9, 3, hexc("e8ffff"))
        c.rect(21, 7, 22, 7, hexc("ffffff"))
        for x, y in ((10, 4), (29, 20), (6, 12)):
            c.set(x, y, hexc("a0e8ff"))
            c.set(x - 1, y, hexc("60c8ff", 160))
            c.set(x + 1, y, hexc("60c8ff", 160))
            c.set(x, y - 1, hexc("60c8ff", 160))
            c.set(x, y + 1, hexc("60c8ff", 160))

    def knife(c):
        c.poly([(10, 20), (26, 2), (29, 4), (12, 22)], hexc("b8bccb"))
        c.poly([(10, 20), (26, 2), (28, 3), (11, 21)], hexc("d8dce8"))
        c.line(12, 19, 26, 4, hexc("ffffff"))
        c.line(6, 16, 16, 26, hexc("8a6a20"), thick=4)
        c.line(6, 16, 16, 26, hexc("c8a040"), thick=2)
        c.line(3, 27, 10, 20, hexc("5a321a"), thick=4)
        c.line(3, 26, 9, 20, hexc("9a6a3a"), thick=2)

    def garlic(c):
        c.circle(15.5, 19.5, 11, hexc("c8c0a8"))
        c.circle(15, 19, 10.2, hexc("f4f0e0"))
        c.circle(12, 16, 4, hexc("ffffff"))
        for x0, x1 in ((15.5, 15.5), (9.5, 8.5), (21.5, 22.5)):
            c.line(x0, 11, x1, 28, hexc("d0c8b0"))
        c.poly([(12, 9), (19, 9), (17, 1), (14, 1)], hexc("6ab04a"))
        c.line(15, 2, 15, 8, hexc("8ad06a"))
        c.rect(12, 29, 19, 30, hexc("a89a80"))

    def orbs(c):
        c.ring(15.5, 15.5, 11, 13, hexc("ffe890", 140))
        for x, y in ((15.5, 5), (5, 21), (26, 21)):
            c.circle(x, y, 5, hexc("e8a020"))
            c.circle(x - 0.5, y - 0.5, 4.2, hexc("ffc830"))
            c.circle(x - 1.5, y - 1.5, 2, hexc("ffe890"))
            c.set(int(x) - 2, int(y) - 2, hexc("ffffff"))

    def bolt(c):
        pts = [(18, 0), (6, 18), (14, 18), (10, 32), (26, 12), (18, 12), (24, 0)]
        c.poly(pts, hexc("c89a20"))
        c.poly([(18, 1), (8, 17), (15, 17), (12, 28), (24, 13), (17, 13), (22, 1)], hexc("ffe040"))
        c.line(20, 2, 12, 15, hexc("ffffff"))
        c.line(19, 2, 11, 15, hexc("fff8c0"))

    def ring(c):
        c.ring(15.5, 19.5, 6.4, 11, hexc("f0c840"))
        c.ring(15.5, 19.5, 9.2, 11, hexc("b08a20"))
        c.ring(15.5, 19.5, 6.4, 7.4, hexc("fff0a0"))
        c.circle(15.5, 7.5, 5.6, hexc("a01a2c"))
        c.circle(15, 7, 4.6, hexc("e83a4a"))
        c.rect(13, 4, 14, 5, hexc("ffb0b8"))

    def armor(c):
        c.poly([(2, 4), (10, 2), (15, 6), (20, 2), (28, 4), (26, 18), (15, 30), (4, 18)], hexc("5c5e70"))
        c.poly([(3, 5), (10, 3), (15, 7), (20, 3), (27, 5), (25, 17), (15, 28), (5, 17)], hexc("8a8ca0"))
        c.poly([(6, 6), (10, 5), (14, 8), (14, 26), (6, 17)], hexc("b8bacb"))
        c.line(15, 8, 15, 27, hexc("5c5e70"))
        for x, y in ((8, 8), (22, 8), (10, 18), (20, 18)):
            c.set(x, y, hexc("e0e2ee"))

    def heart(c):
        c.circle(9, 11, 7.4, hexc("a01a2c"))
        c.circle(21, 11, 7.4, hexc("a01a2c"))
        c.poly([(2, 14), (28, 14), (15, 29)], hexc("a01a2c"))
        c.circle(9, 10.5, 6.6, hexc("e83a4a"))
        c.circle(21, 10.5, 6.6, hexc("e83a4a"))
        c.poly([(3, 13), (27, 13), (15, 27)], hexc("e83a4a"))
        c.circle(8, 9, 2.6, hexc("ffb0b8"))
        c.rect(6, 7, 7, 7, hexc("ffffff"))

    def boots(c):
        c.poly([(8, 6), (18, 6), (18, 20), (28, 22), (28, 28), (8, 28)], hexc("5a3418"))
        c.poly([(9, 7), (17, 7), (17, 21), (27, 23), (27, 25), (9, 25)], hexc("8a5428"))
        c.rect(9, 7, 10, 24, hexc("a8682e"))
        c.rect(8, 25, 28, 28, hexc("3a2210"))
        c.rect(9, 10, 17, 11, hexc("c8a040"))
        c.poly([(1, 8), (12, 10), (12, 16), (0, 18)], hexc("c0c8e0"))
        c.poly([(2, 9), (11, 11), (11, 14), (2, 15)], hexc("f4f4ff"))
        c.line(3, 12, 10, 12, hexc("c0c8e0"))

    def hourglass(c):
        c.poly([(6, 4), (25, 4), (17, 16), (25, 28), (6, 28), (14, 16)], hexc("c8e8ff", 170))
        c.poly([(9, 6), (22, 6), (15.5, 14)], hexc("f0c840"))
        c.poly([(15.5, 20), (22, 27), (9, 27)], hexc("f0c840"))
        c.line(15.5, 14, 15.5, 26, hexc("f0c840"))
        c.line(8, 6, 13, 12, hexc("ffffff", 200))
        c.rect(3, 0, 28, 3, hexc("8a5428"))
        c.rect(3, 28, 28, 31, hexc("8a5428"))
        c.rect(3, 0, 28, 0, hexc("a8682e"))
        c.rect(3, 28, 28, 28, hexc("a8682e"))
        c.rect(4, 3, 5, 28, hexc("6a3c1c"))
        c.rect(26, 3, 27, 28, hexc("6a3c1c"))

    def magnet(c):
        draw_magnet(c, 2, 3)

    def herb(c):
        c.line(15, 31, 15, 12, hexc("2a5a1a"), thick=4)
        c.line(15, 31, 15, 12, hexc("3a7a2a"), thick=2)
        c.poly([(14, 14), (2, 6), (4, 18)], hexc("4a9a3a"))
        c.poly([(14, 14), (3, 7), (6, 14)], hexc("6ac04a"))
        c.poly([(16, 10), (28, 2), (26, 16)], hexc("4a9a3a"))
        c.poly([(16, 10), (27, 3), (22, 10)], hexc("6ac04a"))
        c.poly([(15, 8), (10, 0), (20, 0)], hexc("8ae06a"))
        c.line(15, 7, 15, 1, hexc("b0f090"))
        c.rect(21, 19, 30, 23, hexc("ff4a5a"))
        c.rect(24, 16, 27, 26, hexc("ff4a5a"))
        c.rect(24, 16, 25, 19, hexc("ffb0b8"))

    def chicken(c):
        draw_chicken(c, 1, 1)

    def water(c):
        c.rect(12, 0, 19, 6, hexc("a07a50"))
        c.rect(12, 0, 19, 1, hexc("c8a070"))
        c.rect(13, 6, 18, 8, hexc("c8e8ff", 200))
        c.circle(15.5, 19, 11, hexc("3a8cff"))
        c.circle(15, 18.5, 10, hexc("70b8ff"))
        c.circle(15, 21, 7, hexc("5aa4ff"))
        c.circle(11, 15, 3.2, hexc("e8f8ff"))
        c.set(20, 24, hexc("e8f8ff"))

    def axe(c):
        c.line(4, 28, 22, 10, hexc("5a321a"), thick=4)
        c.line(4, 27, 21, 10, hexc("9a6a3a"), thick=2)
        c.poly([(16, 8), (22, 1), (30, 5), (31, 16), (26, 23), (21, 15)], hexc("8a8ea0"))
        c.poly([(17, 8), (22, 2), (29, 6), (30, 16), (26, 21), (21, 14)], hexc("c8ccd8"))
        c.line(23, 2, 29, 5, hexc("ffffff"))
        c.line(30, 7, 30, 16, hexc("ffffff"))
        c.line(29, 17, 26, 21, hexc("ffffff"))

    def book(c):
        c.rect(4, 4, 27, 29, hexc("4a2478"))
        c.rect(5, 4, 25, 27, hexc("6a3aa0"))
        c.rect(7, 6, 23, 25, hexc("8a5ac8"))
        c.rect(23, 6, 27, 28, hexc("f0e8d0"))
        for y in (9, 13, 17, 21, 25):
            c.rect(24, y, 27, y, hexc("c8bca0"))
        c.circle(14.5, 15.5, 5, hexc("b08a20"))
        c.circle(14.5, 15.5, 4, hexc("f0c840"))
        c.circle(14.5, 15.5, 1.6, hexc("fff0a0"))
        c.rect(5, 4, 5, 27, hexc("a07ad8"))

    def dup(c):
        c.rect(2, 10, 19, 27, hexc("1a4ab0"))
        c.rect(3, 11, 18, 26, hexc("3a8cff"))
        c.rect(12, 2, 29, 19, hexc("2a6ac0"))
        c.rect(13, 3, 28, 18, hexc("60c8ff"))
        c.rect(13, 3, 28, 4, hexc("a8e8ff"))
        c.rect(19, 7, 22, 14, hexc("ffffff"))
        c.rect(17, 9, 24, 12, hexc("ffffff"))
        c.rect(9, 15, 12, 22, hexc("ffffff"))
        c.rect(7, 17, 14, 20, hexc("ffffff"))

    def clover(c):
        c.line(18, 20, 26, 30, hexc("2a7a2a"), thick=3)
        for cx, cy in ((10, 10), (20, 10), (10, 20), (20, 20)):
            c.circle(cx, cy, 6.6, hexc("2a8a2a"))
            c.circle(cx - 0.5, cy - 0.5, 5.8, hexc("4ac04a"))
            c.circle(cx - 2, cy - 2, 2, hexc("8ae06a"))
        c.circle(15, 15, 2.8, hexc("8ae06a"))
        c.line(15, 15, 6, 6, hexc("2a8a2a"))
        c.line(15, 15, 24, 6, hexc("2a8a2a"))
        c.line(15, 15, 6, 24, hexc("2a8a2a"))

    def crown(c):
        c.poly([(2, 10), (9, 18), (15, 4), (21, 18), (28, 10), (26, 27), (4, 27)], hexc("c89a20"))
        c.poly([(3, 12), (9, 19), (15, 6), (21, 19), (27, 12), (25, 24), (5, 24)], hexc("f0c840"))
        c.rect(4, 22, 26, 27, hexc("b08a20"))
        c.rect(4, 22, 26, 22, hexc("fff0a0"))
        c.circle(15, 13, 2.2, hexc("e83a4a"))
        c.circle(9, 24.5, 1.8, hexc("3a8cff"))
        c.circle(21, 24.5, 1.8, hexc("3a8cff"))
        for x, y in ((2, 9), (15, 3), (28, 9)):
            c.circle(x, y, 1.5, hexc("fff0a0"))

    for name, fn in (("icon_bolt", wand), ("icon_knife", knife), ("icon_aura", garlic), ("icon_orb", orbs),
                     ("icon_lightning", bolt), ("icon_might", ring), ("icon_armor", armor),
                     ("icon_heart", heart), ("icon_speed", boots), ("icon_cooldown", hourglass),
                     ("icon_magnet", magnet), ("icon_regen", herb), ("icon_chicken", chicken),
                     ("icon_water", water), ("icon_axe", axe), ("icon_area", book), ("icon_amount", dup),
                     ("icon_luck", clover), ("icon_growth", crown)):
        icon(name, fn)


# ---------------------------------------------------------------------------
# Ground tiles (seamless, 128x128 native)
# ---------------------------------------------------------------------------

def make_ground():
    N = 128
    base = [hexc("24361f"), hexc("283c22"), hexc("2c4226"), hexc("213220")]
    for variant in range(1, 5):
        random.seed(1234)  # identical base noise -> seamless between variants
        cv = Canvas(N, N)
        # 2x2 noise blobs with fine single-pixel variation inside
        for y in range(0, N, 2):
            for x in range(0, N, 2):
                r = random.random()
                col = base[0] if r < 0.55 else base[1] if r < 0.8 else base[2] if r < 0.93 else base[3]
                for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    cv.set(x + dx, y + dy, base[3] if random.random() < 0.08 else col)
        random.seed(variant * 77)
        # grass tufts: three blades each
        for _ in range(16 if variant != 3 else 9):
            x, y = random.randint(0, N - 1), random.randint(0, N - 1)
            dark, light = (hexc("3e5a30"), hexc("4a6a38")) if random.random() < 0.7 else (hexc("4a6a38"), hexc("5a7c44"))
            for bx, h, lean in ((-2, 3, -1), (0, 5, 0), (2, 4, 1)):
                for i in range(h):
                    cv.set(x + bx + (lean if i >= h - 2 else 0), y - i, light if i >= h - 2 else dark, wrap=True)
        if variant == 2:  # flowers: 4 petals, light centre
            for _ in range(6):
                x, y = random.randint(0, N - 1), random.randint(0, N - 1)
                col = random.choice([hexc("d8d0f0"), hexc("e8c860"), hexc("c870a0")])
                cv.set(x, y + 3, hexc("3e5a30"), wrap=True)
                cv.set(x, y + 4, hexc("3e5a30"), wrap=True)
                for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                    for ex, ey in ((0, 0), (1, 0), (0, 1), (1, 1)):
                        cv.set(x + dx + ex - (dx > 0) * 1, y + dy + ey - (dy > 0) * 1, col, wrap=True)
                cv.set(x, y, hexc("f0e070"), wrap=True)
        if variant == 3:  # dirt patch + stones
            cx, cy = random.randint(40, 88), random.randint(40, 88)
            for y in range(cy - 24, cy + 25):
                for x in range(cx - 28, cx + 29):
                    d = ((x - cx) / 28) ** 2 + ((y - cy) / 22) ** 2
                    if d < 1 and random.random() > d * 0.7:
                        cv.set(x, y, hexc("3a3024") if random.random() < 0.7 else hexc("443828"))
            for _ in range(5):
                x, y = random.randint(cx - 20, cx + 20), random.randint(cy - 16, cy + 16)
                cv.circle(x + 1.5, y + 1.5, 2.2, hexc("4a4850"))
                cv.circle(x + 1, y + 1, 1.6, hexc("6a6870"))
                cv.set(x, y, hexc("8a8890"))
        if variant == 4:  # gravestone with engraved cross and moss
            gx, gy = 52, 44
            cv.rect(gx + 1, gy + 36, gx + 25, gy + 41, hexc("1a2616"))  # shadow
            cv.rect(gx + 4, gy + 6, gx + 21, gy + 37, hexc("4a4c58"))
            cv.circle(gx + 12.5, gy + 9, 8.5, hexc("4a4c58"))
            cv.rect(gx + 5, gy + 7, gx + 20, gy + 36, hexc("6a6c78"))
            cv.circle(gx + 12.5, gy + 9, 7.5, hexc("6a6c78"))
            cv.rect(gx + 6, gy + 6, gx + 8, gy + 35, hexc("8a8c98"))
            cv.rect(gx + 12, gy + 10, gx + 13, gy + 25, hexc("3a3c48"))
            cv.rect(gx + 8, gy + 14, gx + 17, gy + 15, hexc("3a3c48"))
            cv.line(gx + 18, gy + 20, gx + 15, gy + 27, hexc("4a4c58"))
            for x, y in ((gx + 5, gy + 33), (gx + 6, gy + 34), (gx + 19, gy + 30), (gx + 20, gy + 31), (gx + 7, gy + 8)):
                cv.set(x, y, hexc("4a6a38"))
            for x in range(gx + 2, gx + 24):
                cv.set(x, gy + 37, hexc("4a6a38"))
                if x % 3 == 0:
                    cv.set(x, gy + 36, hexc("5a7c44"))
        cv.save("ground_%d" % variant)


# ---------------------------------------------------------------------------
# Bitmap font (5x7 glyphs)
# ---------------------------------------------------------------------------

GLYPHS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    ".": [".....", ".....", ".....", ".....", ".....", ".....", "..#.."],
    ",": [".....", ".....", ".....", ".....", ".....", "..#..", ".#..."],
    ":": [".....", "..#..", ".....", ".....", ".....", "..#..", "....."],
    "-": [".....", ".....", ".....", ".###.", ".....", ".....", "....."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    "/": ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
    "%": ["##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##"],
    "(": ["...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."],
    ")": [".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."],
    "'": ["..#..", "..#..", ".....", ".....", ".....", ".....", "....."],
    "x": [".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
    "#": [".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."],
    "<": ["...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."],
    ">": [".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."],
    "=": [".....", ".....", "#####", ".....", "#####", ".....", "....."],
}


def _ttf_table_checksum(data):
    data += b"\0" * (-len(data) % 4)
    return sum(struct.unpack(">%dI" % (len(data) // 4), data)) & 0xFFFFFFFF


def make_font():
    """Builds a TrueType font from the 5x7 glyphs, smoothed to 10x14 with Scale2x so diagonals and
    corners are rounded off (one square contour per run of pixels in a row)."""
    PX = 64                        # font units per smoothed glyph pixel
    UPM = 16 * PX                  # 14 rows above the baseline + 2 below
    ASC, DESC = 14 * PX, -2 * PX
    ADV = 12 * PX

    chars = {ch: scale2x(rows) for ch, rows in GLYPHS.items()}
    for ch in GLYPHS:              # lowercase renders as uppercase (except 'x')
        if "A" <= ch <= "Z" and ch.lower() not in chars:
            chars[ch.lower()] = chars[ch]
    codes = sorted(ord(c) for c in chars)

    def glyph_data(rows):
        contours = []
        h, w = len(rows), len(rows[0])
        for r, row in enumerate(rows):
            y0, y1 = (h - 1 - r) * PX, (h - r) * PX
            x = 0
            while x < w:
                if row[x] == "#":
                    x0 = x
                    while x < w and row[x] == "#":
                        x += 1
                    # clockwise outer contour
                    contours.append([(x0 * PX, y0), (x0 * PX, y1), (x * PX, y1), (x * PX, y0)])
                else:
                    x += 1
        if not contours:
            return b"", 0, 0, 0
        pts = [p for c in contours for p in c]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out = struct.pack(">hhhhh", len(contours), min(xs), min(ys), max(xs), max(ys))
        end = -1
        for c in contours:
            end += len(c)
            out += struct.pack(">H", end)
        out += struct.pack(">H", 0)                       # no instructions
        out += bytes([1] * len(pts))                      # all on-curve, long coords
        px = py = 0
        for x, y in pts:
            out += struct.pack(">h", x - px)
            px = x
        for x, y in pts:
            out += struct.pack(">h", y - py)
            py = y
        out += b"\0" * (-len(out) % 4)
        return out, len(pts), len(contours), min(xs)

    glyphs = [b""]  # .notdef (empty)
    lsbs = [0]      # left side bearing must equal each glyph's xMin
    max_pts = max_contours = 0
    for c in codes:
        data, npts, ncont, xmin = glyph_data(chars[chr(c)])
        glyphs.append(data)
        lsbs.append(xmin)
        max_pts, max_contours = max(max_pts, npts), max(max_contours, ncont)
    n = len(glyphs)

    glyf, loca = b"", []
    for g in glyphs:
        loca.append(len(glyf))
        glyf += g
    loca.append(len(glyf))
    loca_t = struct.pack(">%dI" % len(loca), *loca)
    hmtx = b"".join(struct.pack(">Hh", ADV, lsb) for lsb in lsbs)

    # cmap format 4: one segment per code + terminator
    segs = [(c, c, (i + 1 - c) & 0xFFFF) for i, c in enumerate(codes)] + [(0xFFFF, 0xFFFF, 1)]
    sc = len(segs)
    sr = 2 ** int(math.log2(sc)) * 2
    sub = struct.pack(">HHHHHHH", 4, 0, 0, sc * 2, sr, int(math.log2(sr // 2)), sc * 2 - sr)
    sub += b"".join(struct.pack(">H", e) for _, e, _ in segs) + b"\0\0"
    sub += b"".join(struct.pack(">H", st) for st, _, _ in segs)
    sub += b"".join(struct.pack(">H", d) for _, _, d in segs)
    sub += b"\0\0" * sc
    sub = sub[:2] + struct.pack(">H", len(sub)) + sub[4:]
    cmap = struct.pack(">HHHHI", 0, 1, 3, 1, 12) + sub

    head = struct.pack(">IIIIHHqqhhhhHHhhh", 0x00010000, 0x00010000, 0, 0x5F0F3CF5, 0x000B, UPM,
                       0, 0, 0, DESC, 10 * PX, ASC, 0, 8, 2, 1, 0)
    hhea = struct.pack(">IhhhHhhhhhhhhhhhH", 0x00010000, ASC, DESC, 0, ADV, 0, 2 * PX, 10 * PX,
                       1, 0, 0, 0, 0, 0, 0, 0, n)
    maxp = struct.pack(">IHHHHHHHHHHHHHH", 0x00010000, n, max_pts, max_contours, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0)
    os2 = struct.pack(">HhHHHhhhhhhhhhhh", 4, ADV, 400, 5, 0, PX * 8, PX * 8, 0, PX * 2, PX * 8, PX * 8, 0, PX * 6,
                      PX, PX * 4, 0)
    os2 += bytes(10) + struct.pack(">IIII", 1, 0, 0, 0) + b"NSRV"
    os2 += struct.pack(">HHHhhhHHII", 0x40, codes[0], codes[-1], ASC, DESC, 0, ASC, -DESC, 1, 0)
    os2 += struct.pack(">hhHHH", 10 * PX, 14 * PX, 0, 32, 1)
    post = struct.pack(">IIhhIIIII", 0x00030000, 0, -2 * PX, PX, 1, 0, 0, 0, 0)

    names = {1: "NightPixel", 2: "Regular", 3: "NightPixel Regular", 4: "NightPixel", 6: "NightPixel-Regular"}
    recs, strs = b"", b""
    for nid, txt in names.items():
        enc = txt.encode("utf-16-be")
        recs += struct.pack(">HHHHHH", 3, 1, 0x409, nid, len(enc), len(strs))
        strs += enc
    name = struct.pack(">HHH", 0, len(names), 6 + len(recs)) + recs + strs

    tables = {b"OS/2": os2, b"cmap": cmap, b"glyf": glyf, b"head": head, b"hhea": hhea,
              b"hmtx": hmtx, b"loca": loca_t, b"maxp": maxp, b"name": name, b"post": post}

    def build(tbls):
        nt = len(tbls)
        es = int(math.log2(nt))
        hdr = struct.pack(">IHHHH", 0x00010000, nt, (2 ** es) * 16, es, nt * 16 - (2 ** es) * 16)
        offset = 12 + 16 * nt
        dir_, body = b"", b""
        for tag in sorted(tbls):
            data = tbls[tag]
            dir_ += tag + struct.pack(">III", _ttf_table_checksum(data), offset + len(body), len(data))
            body += data + b"\0" * (-len(data) % 4)
        return hdr + dir_ + body

    font = build(tables)
    adj = (0xB1B0AFBA - _ttf_table_checksum(font)) & 0xFFFFFFFF
    tables[b"head"] = head[:8] + struct.pack(">I", adj) + head[12:]
    with open(os.path.join(FONT_DIR, "pixel.ttf"), "wb") as f:
        f.write(build(tables))

    for old in ("pixel.fnt", "pixel_font.png"):
        if os.path.exists(os.path.join(FONT_DIR, old)):
            os.remove(os.path.join(FONT_DIR, old))
    with open(os.path.join(FONT_DIR, "pixel.font"), "w") as f:
        f.write('font: "/main/assets/fonts/pixel.ttf"\n'
                'material: "/builtins/fonts/font.material"\n'
                'size: %d\n'
                'antialias: 1\n'
                'alpha: 1.0\n'
                'outline_alpha: 1.0\n'
                'outline_width: 2.5\n'
                'shadow_alpha: 0.0\n'
                'output_format: TYPE_BITMAP\n' % 28)   # drawn 1:1 by the HUD at 1440x810


# ---------------------------------------------------------------------------
# Content added in the "more mechanics" update
# ---------------------------------------------------------------------------

DIGITS = {
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"], "3": ["###", "..#", ".##", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"], "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "###"],
}


def scale2x(rows):
    """Scale2x/EPX on a '#'/'.' bitmap: doubles resolution and rounds off staircase corners."""
    h, w = len(rows), len(rows[0])
    at = lambda x, y: rows[y][x] if 0 <= x < w and 0 <= y < h else "."
    out = [[" "] * (w * 2) for _ in range(h * 2)]
    for y in range(h):
        for x in range(w):
            p, a, b, c, d = at(x, y), at(x, y - 1), at(x + 1, y), at(x - 1, y), at(x, y + 1)
            e0 = a if c == a and c != d and a != b else p
            e1 = b if a == b and a != c and b != d else p
            e2 = c if d == c and d != b and c != a else p
            e3 = d if b == d and b != a and d != c else p
            out[2 * y][2 * x], out[2 * y][2 * x + 1] = e0, e1
            out[2 * y + 1][2 * x], out[2 * y + 1][2 * x + 1] = e2, e3
    return ["".join(r) for r in out]


def make_extras():
    # damage-number digits (white, tinted at runtime): 3x5 glyphs smoothed to 6x10, 2px outline
    for d, rows in DIGITS.items():
        cv = Canvas(10, 14)
        for y, r in enumerate(scale2x(rows)):
            for x, ch in enumerate(r):
                if ch == "#":
                    cv.set(x + 2, y + 2, (255, 255, 255, 255))
        cv.outline()
        cv.outline()
        cv.save("num_" + d)

    # enemy bullet (pulsing)
    frames = []
    for pulse in (0, 1, 2, 1):
        cv = Canvas(18, 18)
        cv.circle(8.5, 8.5, 7.8 + pulse * 0.3, hexc("c040ff", 110))
        cv.circle(8.5, 8.5, 7, hexc("c040ff", 190))
        cv.circle(8.5, 8.5, 5.8, hexc("e070ff"))
        cv.circle(8.5, 8.5, 3.2, hexc("2a0838"))
        cv.circle(8.5, 8.5, 0.8 + pulse * 0.5, hexc("ff60a0"))
        cv.rect(5, 4, 6, 4, hexc("ffd0ff"))
        frames.append(cv)
    save_anim("ebullet", frames, 12)

    # holy water flask + pool (2 shimmer frames)
    cv = Canvas(18, 22)
    cv.rect(6, 0, 11, 4, hexc("a07a50"))
    cv.rect(6, 0, 11, 0, hexc("c8a070"))
    cv.rect(7, 4, 10, 6, hexc("c8e8ff", 200))
    cv.circle(8.5, 13.5, 7.6, hexc("3a8cff"))
    cv.circle(8, 13, 6.8, hexc("70b8ff"))
    cv.circle(8.5, 15, 4.4, hexc("5aa4ff"))
    cv.circle(6, 11, 2.2, hexc("e8f8ff"))
    cv.set(11, 17, hexc("e8f8ff"))
    cv.outline()
    shine("flask", cv)
    frames = []
    for i in range(4):
        random.seed(40 + i % 2)
        cv = Canvas(64, 64)
        for y in range(64):
            for x in range(64):
                d = math.hypot(x - 31.5, y - 31.5)
                if d <= 31.5:
                    if d > 29.5:
                        cv.set(x, y, hexc("a8e0ff", 210))
                    elif d > 27.5:
                        cv.set(x, y, hexc("70b8ff", 150))
                    elif random.random() < 0.025:
                        cv.rect(x, y, x + 1, y, hexc("e8f8ff", 210))
                    else:
                        cv.set(x, y, hexc("3a8cff", 95 + (20 if (x // 2 + y // 2 + i) % 3 == 0 else 0)))
        for k in range(3):  # ripples drifting outward
            r = 6 + k * 7 + i * 1.75
            cv.ring(31.5, 31.5, r, r + 0.8, hexc("a8e0ff", 110 - k * 20))
        frames.append(cv)
    save_anim("pool", frames, 6)

    # axe (rotated at runtime)
    cv = Canvas(28, 28)
    cv.line(4, 24, 19, 9, hexc("5a321a"), thick=4)
    cv.line(4, 23, 18, 9, hexc("9a6a3a"), thick=2)
    cv.poly([(14, 7), (19, 1), (26, 4), (27, 14), (23, 20), (18, 13)], hexc("8a8ea0"))
    cv.poly([(15, 7), (19, 2), (25, 5), (26, 14), (23, 18), (18, 12)], hexc("c8ccd8"))
    cv.line(20, 2, 25, 4, hexc("ffffff"))
    cv.line(26, 6, 26, 14, hexc("ffffff"))
    cv.line(25, 15, 23, 18, hexc("ffffff"))
    cv.rect(16, 9, 18, 11, hexc("6a6c78"))
    cv.outline()
    cv.save("axe")

    # cross pickup
    cv = Canvas(28, 32)
    cv.rect(10, 2, 17, 29, hexc("c89a20"))
    cv.rect(2, 8, 25, 15, hexc("c89a20"))
    cv.rect(10, 2, 16, 28, hexc("f0c840"))
    cv.rect(2, 8, 24, 14, hexc("f0c840"))
    cv.rect(12, 3, 13, 27, hexc("fff0a0"))
    cv.rect(3, 10, 23, 11, hexc("fff0a0"))
    cv.circle(13, 11, 2.2, hexc("ffffff"))
    cv.outline()
    shine("cross", cv)

    # clock pickup
    cv = Canvas(30, 30)
    cv.circle(14.5, 15, 13, hexc("b08a20"))
    cv.circle(14.5, 14.5, 12.4, hexc("f0c840"))
    cv.circle(14.5, 15, 9.8, hexc("c8c8d8"))
    cv.circle(14.5, 14.5, 9.4, hexc("f4f4ff"))
    for a in range(12):
        ang = a * math.pi / 6
        cv.set(round(14.5 + math.cos(ang) * 7.6), round(14.5 + math.sin(ang) * 7.6), hexc("8a8ca0"))
    cv.rect(12, 0, 17, 2, hexc("f0c840"))
    cv.line(14.5, 14.5, 14.5, 7, OUTLINE, thick=2)
    cv.line(14.5, 14.5, 19.5, 17.5, OUTLINE, thick=2)
    cv.circle(14.5, 14.5, 1.4, hexc("e83a4a"))
    cv.outline()
    shine("clock", cv)


def make_extra_sounds():
    write_wav("evolve", mix(seq(*[tone(0.06, note_freq(n), None, "pulse", 0.3, curve=0.3)
                                  for n in (60, 64, 67, 71, 72, 76, 79, 83, 84, 88)], tone(0.6, note_freq(96), None, "tri", 0.3)),
                            noise(1.2, 0.05, 1, 0.2, 31)))
    write_wav("freeze", seq(*[tone(0.05, note_freq(n), None, "tri", 0.3, curve=0.5) for n in (96, 91, 88, 84, 79, 76, 72)]))
    write_wav("eshot", tone(0.12, 300, 520, "pulse", 0.18, curve=1.5))
    write_wav("nuke", mix(noise(1.0, 0.7, 2.0, 0.6, 41), tone(0.8, 120, 30, "square", 0.3)))
    write_wav("splash", mix(noise(0.25, 0.35, 2, 0.5, 43), tone(0.2, 600, 200, "sine", 0.2)))
    write_wav("break", mix(noise(0.2, 0.5, 2, 0.3, 47), tone(0.15, 900, 300, "square", 0.15)))


# ---------------------------------------------------------------------------
# Atlas
# ---------------------------------------------------------------------------

ANIMATIONS = []  # (id, frames, fps, playback), registered by save_anim while drawing
SINGLE_IMAGES = [
    "knife", "pixel", "shadow", "axe",
    "ground_1", "ground_2", "ground_3", "ground_4",
    "icon_bolt", "icon_knife", "icon_aura", "icon_orb", "icon_lightning", "icon_might",
    "icon_armor", "icon_heart", "icon_speed", "icon_cooldown", "icon_magnet", "icon_regen", "icon_chicken",
    "icon_water", "icon_axe", "icon_area", "icon_amount", "icon_luck", "icon_growth",
] + ["num_%d" % i for i in range(10)]


def write_atlas():
    p = lambda n: "/main/assets/images/%s.png" % n
    out = []
    for n in SINGLE_IMAGES:
        out.append('images {\n  image: "%s"\n}\n' % p(n))
    for aid, frames, fps, playback in ANIMATIONS:
        out.append("animations {\n  id: \"%s\"\n" % aid)
        for fr in frames:
            out.append('  images {\n    image: "%s"\n  }\n' % p(fr))
        out.append("  playback: %s\n  fps: %d\n  flip_horizontal: 0\n  flip_vertical: 0\n}\n" % (playback, fps))
    out.append("margin: 0\nextrude_borders: 2\ninner_padding: 0\n")
    with open(os.path.join(ROOT, "main", "assets", "game.atlas"), "w") as f:
        f.write("".join(out))


# ---------------------------------------------------------------------------
# Audio synthesis
# ---------------------------------------------------------------------------

RATE = 22050


def write_wav(name, samples):
    path = os.path.join(SND_DIR, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000)) for s in samples))


def osc(kind, phase):
    ph = phase % 1.0
    if kind == "square":
        return 1.0 if ph < 0.5 else -1.0
    if kind == "pulse":
        return 1.0 if ph < 0.25 else -1.0
    if kind == "tri":
        return 4 * ph - 1 if ph < 0.5 else 3 - 4 * ph
    if kind == "saw":
        return 2 * ph - 1
    return math.sin(2 * math.pi * ph)


def tone(dur, f0, f1=None, kind="square", vol=0.5, attack=0.005, curve=1.0):
    f1 = f0 if f1 is None else f1
    n = int(dur * RATE)
    out, phase = [], 0.0
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * t
        phase += f / RATE
        env = min(1.0, i / (attack * RATE + 1)) * (1 - t) ** curve
        out.append(osc(kind, phase) * env * vol)
    return out


def noise(dur, vol=0.5, curve=1.5, lowpass=0.0, seed=1):
    rnd = random.Random(seed)
    n = int(dur * RATE)
    out, prev = [], 0.0
    for i in range(n):
        t = i / n
        v = rnd.uniform(-1, 1)
        prev = prev * lowpass + v * (1 - lowpass)
        out.append(prev * vol * (1 - t) ** curve)
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for tr in tracks:
        for i, v in enumerate(tr):
            out[i] += v
    return out


def seq(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def note_freq(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def make_sounds():
    write_wav("shoot", tone(0.12, 1200, 500, "square", 0.25, curve=2))
    write_wav("knife", mix(noise(0.09, 0.35, 2, 0.3, 3), tone(0.09, 2200, 1400, "tri", 0.15)))
    write_wav("hit", mix(noise(0.07, 0.45, 2, 0.6, 5), tone(0.07, 220, 110, "square", 0.2)))
    write_wav("enemy_die", mix(noise(0.18, 0.4, 2, 0.75, 9), tone(0.18, 400, 80, "square", 0.25, curve=1.5)))
    write_wav("gem", seq(tone(0.04, 1568, None, "pulse", 0.18, curve=0.5), tone(0.07, 2093, None, "pulse", 0.18)))
    write_wav("hurt", mix(tone(0.22, 180, 90, "saw", 0.4), noise(0.22, 0.25, 1, 0.8, 11)))
    write_wav("thunder", mix(noise(0.6, 0.6, 2.5, 0.85, 13), noise(0.12, 0.5, 1, 0.1, 17), tone(0.5, 90, 40, "square", 0.25)))
    write_wav("heal", seq(*[tone(0.08, note_freq(n), None, "tri", 0.35, curve=0.6) for n in (72, 76, 79, 84)]))
    write_wav("select", tone(0.06, 880, 1320, "pulse", 0.25, curve=0.8))
    write_wav("pickup", seq(tone(0.06, 660, None, "square", 0.25), tone(0.1, 990, None, "square", 0.25)))
    arp = [60, 64, 67, 72, 76, 79, 84]
    write_wav("levelup", seq(*[tone(0.07, note_freq(n), None, "pulse", 0.3, curve=0.4) for n in arp],
                             tone(0.35, note_freq(84), None, "square", 0.3)))
    write_wav("gameover", seq(*[tone(d, note_freq(n), None, "square", 0.3, curve=0.7)
                                for n, d in ((67, 0.25), (63, 0.25), (60, 0.25), (55, 0.9))]))
    write_wav("victory", seq(*[tone(d, note_freq(n), None, "pulse", 0.3, curve=0.5)
                               for n, d in ((60, 0.12), (64, 0.12), (67, 0.12), (72, 0.3), (67, 0.12), (72, 0.8))]))
    write_wav("boss", mix(seq(*[tone(0.3, note_freq(n), None, "saw", 0.35, curve=0.3) for n in (40, 41, 40, 41)]),
                          noise(1.2, 0.15, 1, 0.9, 21)))
    make_music()


def make_music():
    """Loopable minor-key chiptune: bass + arpeggio + lead + drums (16 bars @ 120bpm)."""
    bpm = 120
    step = 60.0 / bpm / 4  # 16th note
    steps_per_bar = 16
    chords = [(57, [57, 60, 64]), (53, [53, 57, 60]), (55, [55, 59, 62]), (52, [52, 56, 59])]  # Am F G E
    bars = 16
    total = int(bars * steps_per_bar * step * RATE)
    out = [0.0] * total
    melody_a = [76, None, 74, None, 72, None, 71, 72, None, None, 69, None, 71, None, 72, None]
    melody_b = [72, None, 71, None, 69, None, 67, 69, None, None, 64, None, 65, None, 67, None]
    melody_c = [77, None, 76, None, 74, None, 72, 74, None, 76, None, 77, 76, None, None, None]
    melody_d = [71, None, 68, None, 71, None, 74, 76, None, None, 75, None, 76, None, None, None]

    def add(start, samples):
        for i, v in enumerate(samples):
            j = start + i
            if j < total:
                out[j] += v

    for bar in range(bars):
        root, triad = chords[bar % 4]
        section = bar // 4
        for s in range(steps_per_bar):
            t0 = int(((bar * steps_per_bar) + s) * step * RATE)
            # bass: eighth notes, root/octave
            if s % 2 == 0:
                n = root - 12 + (12 if s % 8 == 6 else 0)
                add(t0, tone(step * 1.8, note_freq(n), None, "tri", 0.32, curve=0.6))
            # arpeggio
            if section >= 1:
                n = triad[s % 3] + 12
                add(t0, tone(step * 0.9, note_freq(n), None, "pulse", 0.07, curve=1.2))
            # drums
            if section >= 1 or bar % 4 == 3:
                if s % 8 == 0:
                    add(t0, tone(0.12, 140, 45, "sine", 0.55, curve=1.5))
                if s % 8 == 4:
                    add(t0, noise(0.1, 0.22, 2, 0.4, bar * 31 + s))
                if s % 2 == 1:
                    add(t0, noise(0.03, 0.06, 3, 0.0, bar * 17 + s))
            # lead
            if section >= 2:
                mel = (melody_a, melody_b, melody_c, melody_d)[bar % 4]
                n = mel[s]
                if n is not None:
                    length = 1
                    while s + length < 16 and mel[s + length] is None and length < 3:
                        length += 1
                    add(t0, tone(step * length * 0.95, note_freq(n), None, "square", 0.11, curve=0.4))
    peak = max(abs(v) for v in out) or 1
    write_wav("music", [v / peak * 0.8 for v in out])


# ---------------------------------------------------------------------------

def main():
    for d in (IMG_DIR, FONT_DIR, SND_DIR):
        os.makedirs(d, exist_ok=True)
    for f in os.listdir(IMG_DIR):  # every image is generated; drop frames that no longer exist
        if f.endswith(".png"):
            os.remove(os.path.join(IMG_DIR, f))
    make_characters()
    make_projectiles()
    make_pickups()
    make_icons()
    make_ground()
    make_extras()
    write_atlas()
    make_font()
    make_sounds()
    make_extra_sounds()
    print("assets generated in", os.path.join(ROOT, "main", "assets"))


if __name__ == "__main__":
    main()
