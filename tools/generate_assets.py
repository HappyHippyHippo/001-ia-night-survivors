#!/usr/bin/env python3
"""
Procedural asset generator for Night Survivors.

Generates every asset the game uses, with no third-party dependencies:
  - pixel-art sprites (PNG) + the Defold atlas that references them
  - a 5x7 pixel bitmap font (BMFont .fnt + PNG) + the Defold .font
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
SCALE = 3  # every native pixel becomes a 3x3 block

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
# Characters (half-width rows, mirrored horizontally)
# ---------------------------------------------------------------------------

PLAYER_PAL = {
    "k": OUTLINE, "h": hexc("5a3424"), "H": hexc("3e2218"), "s": hexc("f2c49a"),
    "w": hexc("ffffff"), "r": hexc("b02c3c"), "R": hexc("761c2c"), "b": hexc("3a5cb0"),
    "y": hexc("f0c840"), "g": hexc("6a6a7a"),
}
PLAYER_TOP = [
    "......kk",
    "....kkhh",
    "...khhhh",
    "..khhsss",
    "..khskws",
    "..khssss",
    "...kksss",
    "..krrkbb",
    ".krrrbby",
    ".krsrbbb",
    ".kkRrbbb",
    "..kRrbbb",
]
PLAYER_LEGS_A = [
    "...kkbbk",
    "....kbbk",
    "....kggk",
    "....kkkk",
]
PLAYER_LEGS_B = [
    "...kkbbk",
    "...kbbk.",
    "...kggk.",
    "...kkkk.",
]

BAT_PAL = {"k": OUTLINE, "p": hexc("6a3490"), "P": hexc("3e1a5c"), "e": hexc("ff3a3a"), "f": hexc("ffffff")}
BAT_A = [
    "........",
    "........",
    "k.......",
    "pk......",
    "ppk..k..",
    "pppk.kkk",
    "ppppkPPP",
    "pPppPPeP",
    ".pPpPPPP",
    "..pPPPPf",
    "...kPPPP",
    "....kkPP",
    "......kk",
    "........",
    "........",
    "........",
]
BAT_B = [
    "........",
    "........",
    "........",
    "........",
    "........",
    ".....k..",
    ".....kkk",
    "...kkPPP",
    "..kpPPeP",
    ".kppPPPf",
    "kpppPPPP",
    "kpp.kPPP",
    "kp....kk",
    "k.......",
    "........",
    "........",
]

ZOMBIE_PAL = {"k": OUTLINE, "z": hexc("7aa85a"), "Z": hexc("4e7038"), "c": hexc("6a5444"),
              "C": hexc("4a382c"), "e": hexc("ff4040")}
ZOMBIE_A = [
    "........",
    "....kkkk",
    "...kzzzz",
    "...kzZzz",
    "...kzezz",
    "...kzzzz",
    "....kZZZ",
    "..kkcccc",
    ".kzkcCcc",
    "kzzkcccc",
    "kzkkcCcc",
    "kk.kcccc",
    "...kccCk",
    "...kZZk.",
    "...kzzk.",
    "...kkkk.",
]
ZOMBIE_B = ZOMBIE_A[:7] + [
    ".kzkcccc",
    "kzzkcCcc",
    "kzkkcccc",
    "kk.kcCcc",
    "...kcccc",
    "...kccCk",
    "....kZZk",
    "....kzzk",
    "....kkkk",
]

SKEL_PAL = {"k": OUTLINE, "b": hexc("e8e6d4"), "B": hexc("a8a490"), "e": hexc("ff6020")}
SKEL_A = [
    "....kkkk",
    "...kbbbb",
    "..kbbbbb",
    "..kbkkbb",
    "..kbkebb",
    "..kbbbbb",
    "...kbkbk",
    "....kkbb",
    "..kbkbbb",
    ".kb.kbkB",
    ".kb.kbbb",
    ".kb.kbkB",
    "..k..kbb",
    "....kbk.",
    "....kbk.",
    "...kbbk.",
]
SKEL_B = SKEL_A[:8] + [
    ".kbbkbbb",
    "kb..kbkB",
    "k...kbbb",
    "....kbkB",
    ".....kbb",
    "...kbk..",
    "...kbk..",
    "..kbbk..",
]

GHOST_PAL = {"k": hexc("2a3a60"), "g": hexc("d4e6ff"), "G": hexc("98b0e0"), "e": hexc("1a1a38")}
GHOST_A = [
    "........",
    ".....kkk",
    "....kggg",
    "...kgggg",
    "..kggggg",
    "..kgeegg",
    "..kgeegg",
    ".kgggggg",
    ".kggggge",
    ".kgggggg",
    "kggggggg",
    "kggGgggg",
    "kgggggGg",
    "kgkggkgg",
    "kk.kk.kg",
    "........",
]
GHOST_B = GHOST_A[:12] + [
    "kggggggG",
    "kggkgggk",
    ".kk.kkk.",
    "........",
]

OGRE_PAL = {"k": OUTLINE, "o": hexc("c03a32"), "O": hexc("7a2020"), "h": hexc("ece0b0"),
            "e": hexc("ffe040"), "t": hexc("ffffff"), "a": hexc("5c5e70"), "A": hexc("8a8ca0")}
OGRE_A = [
    "..kk........",
    ".khk........",
    ".khhk...kkkk",
    "..khhkkkoooo",
    "...khooooooo",
    "....koooOooo",
    "....kooeeooo",
    "....kooookoo",
    "....kooooooo",
    ".....koktktk",
    "......kooooo",
    "..kkkkkaaaaa",
    ".kooooaaAaaa",
    "kooooaaaaaaa",
    "kookoaaaAaaa",
    "kookoaaaaaaa",
    "koo.kaaaaaaa",
    "kook.kaaAaaa",
    ".kk..kOOOOOO",
    "....kOOOk...",
    "....kooook..",
    "....kooook..",
    "...kkkkkkk..",
    "............",
]
OGRE_B = [OGRE_A[-1]] + OGRE_A[:18] + [
    "....kOOOk...",
    "...kooook...",
    "...kooook...",
    "..kkkkkkk...",
    "............",
]


def make_characters(names):
    p_a = mirror(PLAYER_TOP + PLAYER_LEGS_A)
    p_b = mirror(PLAYER_TOP + PLAYER_LEGS_B)
    grid(p_a, PLAYER_PAL).save("player_1")
    grid(p_b, PLAYER_PAL).save("player_2")
    # walk bob: frame 3 = legs together raised by one pixel
    up = mirror(PLAYER_TOP[1:] + ["..kRrbbb"] + PLAYER_LEGS_A)
    grid(up, PLAYER_PAL).save("player_3")
    for prefix, a, b, pal in (("bat", BAT_A, BAT_B, BAT_PAL), ("zombie", ZOMBIE_A, ZOMBIE_B, ZOMBIE_PAL),
                              ("skeleton", SKEL_A, SKEL_B, SKEL_PAL), ("ghost", GHOST_A, GHOST_B, GHOST_PAL),
                              ("ogre", OGRE_A, OGRE_B, OGRE_PAL)):
        grid(mirror(a), pal).save(prefix + "_1")
        grid(mirror(b), pal).save(prefix + "_2")
    names += ["player_1", "player_2", "player_3"]


# ---------------------------------------------------------------------------
# Weapons, pickups, effects
# ---------------------------------------------------------------------------

def make_gem(name, light, mid, dark):
    cv = Canvas(7, 9)
    cv.poly([(3.5, 0), (7, 4.5), (3.5, 9), (0, 4.5)], mid)
    cv.poly([(3.5, 0), (3.5, 9), (0, 4.5)], light)
    cv.poly([(3.5, 4.5), (7, 4.5), (3.5, 9)], dark)
    cv.set(2, 3, (255, 255, 255, 255))
    big = Canvas(9, 11)
    big.blit(cv, 1, 1)
    big.outline()
    big.save(name)


def make_projectiles():
    # magic bolt: glowing orb
    cv = Canvas(10, 10)
    cv.circle(4.5, 4.5, 4.4, hexc("2a6aff", 140))
    cv.circle(4.5, 4.5, 3.2, hexc("60c8ff"))
    cv.circle(4.5, 4.5, 1.8, hexc("e8ffff"))
    cv.save("bolt")

    # knife pointing right
    cv = Canvas(14, 5)
    cv.poly([(5, 1), (12, 1.5), (14, 2.5), (12, 3.5), (5, 4)], hexc("d8dce8"))
    cv.rect(5, 1, 12, 1, hexc("ffffff"))
    cv.rect(4, 0, 4, 4, hexc("c8a040"))
    cv.rect(0, 2, 3, 2, hexc("7a4a2a"))
    cv.rect(0, 1, 3, 1, hexc("9a6a3a"))
    cv.save("knife")

    # holy orb
    cv = Canvas(12, 12)
    cv.circle(5.5, 5.5, 5.4, hexc("ffd040", 120))
    cv.circle(5.5, 5.5, 4.2, hexc("ffc830"))
    cv.circle(5.5, 5.5, 3.0, hexc("ffe890"))
    cv.circle(4.5, 4.5, 1.4, hexc("ffffff"))
    cv.save("orb")

    # garlic aura ring (large, translucent)
    n = 64
    cv = Canvas(n, n)
    c = (n - 1) / 2
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - c, y - c)
            if d <= 31.5:
                if d > 29.5:
                    a = 170
                elif d > 27.5:
                    a = 110 if (x + y) % 2 == 0 else 70
                else:
                    a = 40 + int(20 * (d / 31.5))
                cv.set(x, y, (210, 240, 150, a))
    cv.save("aura")

    # lightning bolt (tall; bottom = impact point)
    random.seed(7)
    cv = Canvas(14, 90)
    pts = [(7, 0)]
    y = 0
    while y < 89:
        y = min(89, y + random.randint(5, 9))
        pts.append((max(2, min(11, 7 + random.randint(-4, 4))), y))
    pts[-1] = (7, 89)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(x0, y0, x1, y1, hexc("60c8ff"), thick=4)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(x0, y0, x1, y1, hexc("ffffff"), thick=2)
    cv.save("lightning")

    # death puff (3 frames)
    for i, (r0, r1, density) in enumerate(((0, 3.5, 1.0), (2.5, 5.5, 0.8), (5, 7.5, 0.4))):
        random.seed(100 + i)
        cv = Canvas(16, 16)
        for y in range(16):
            for x in range(16):
                d = math.hypot(x - 7.5, y - 7.5)
                if r0 <= d <= r1 and random.random() < density:
                    cv.set(x, y, hexc("e8e0f0") if d < (r0 + r1) / 2 else hexc("9a90b0"))
        cv.save("puff_%d" % (i + 1))

    # hit spark (2 frames)
    for i, r in enumerate((3, 5)):
        cv = Canvas(12, 12)
        for a in range(8):
            ang = a * math.pi / 4
            cv.line(5.5 + math.cos(ang) * (r - 2), 5.5 + math.sin(ang) * (r - 2),
                    5.5 + math.cos(ang) * r, 5.5 + math.sin(ang) * r, hexc("fff0a0"))
        cv.save("spark_%d" % (i + 1))

    # simple white pixel + soft shadow
    cv = Canvas(4, 4)
    cv.rect(0, 0, 3, 3, (255, 255, 255, 255))
    cv.save("pixel", scale=1)
    cv = Canvas(14, 5)
    for y in range(5):
        for x in range(14):
            if ((x - 6.5) / 7) ** 2 + ((y - 2) / 2.5) ** 2 <= 1:
                cv.set(x, y, (0, 0, 0, 90))
    cv.save("shadow")


def draw_chicken(cv, ox=0, oy=0):
    cv.circle(ox + 5, oy + 5, 4.2, hexc("c06a2a"))
    cv.circle(ox + 4, oy + 4, 2.2, hexc("e08a40"))
    cv.set(ox + 3, oy + 3, hexc("ffc080"))
    cv.line(ox + 8, oy + 8, ox + 11, oy + 11, hexc("f4eee0"), thick=2)
    cv.circle(ox + 12, oy + 11, 1.2, hexc("f4eee0"))
    cv.circle(ox + 11, oy + 12, 1.2, hexc("f4eee0"))


def draw_magnet(cv, ox=0, oy=0):
    cv.ring(ox + 7, oy + 6, 2.5, 5.5, hexc("d83a3a"))
    cv.rect(ox, oy, ox + 14, oy + 5, CLEAR)
    cv.rect(ox + 1, oy + 2, ox + 3, oy + 6, hexc("d83a3a"))
    cv.rect(ox + 10, oy + 2, ox + 12, oy + 6, hexc("d83a3a"))
    cv.rect(ox + 1, oy + 1, ox + 3, oy + 2, hexc("e0e4f0"))
    cv.rect(ox + 10, oy + 1, ox + 12, oy + 2, hexc("e0e4f0"))
    cv.set(ox + 4, oy + 9, hexc("ff8a8a"))


def make_pickups():
    make_gem("gem_blue", hexc("a0e0ff"), hexc("3a8cff"), hexc("1a4ab0"))
    make_gem("gem_green", hexc("b0ffb8"), hexc("3ad860"), hexc("1a8034"))
    make_gem("gem_red", hexc("ffb0b8"), hexc("ff3a50"), hexc("a01a2c"))
    cv = Canvas(15, 15)
    draw_chicken(cv, 1, 1)
    cv.outline()
    cv.save("chicken")
    cv = Canvas(15, 14)
    draw_magnet(cv, 1, 1)
    cv.outline()
    cv.save("magnet")
    # treasure chest (boss drop)
    cv = Canvas(16, 13)
    cv.rect(1, 4, 14, 12, hexc("8a5428"))
    cv.rect(1, 1, 14, 4, hexc("a8682e"))
    cv.rect(1, 5, 14, 5, hexc("5a3418"))
    cv.rect(1, 1, 1, 12, hexc("f0c840"))
    cv.rect(14, 1, 14, 12, hexc("f0c840"))
    cv.rect(6, 4, 9, 7, hexc("f0c840"))
    cv.set(7, 6, OUTLINE)
    cv.set(8, 6, OUTLINE)
    cv.outline()
    cv.save("chest")


# ---------------------------------------------------------------------------
# Upgrade icons (16x16 native + outline)
# ---------------------------------------------------------------------------

def icon(name, draw):
    cv = Canvas(18, 18)
    inner = Canvas(16, 16)
    draw(inner)
    cv.blit(inner, 1, 1)
    cv.outline()
    cv.save(name)


def make_icons():
    def wand(c):
        c.line(2, 14, 10, 6, hexc("7a4a2a"), thick=2)
        c.circle(11.5, 4.5, 3.4, hexc("60c8ff"))
        c.circle(11.5, 4.5, 1.6, hexc("ffffff"))
        c.set(5, 2, hexc("a0e8ff"))
        c.set(14, 10, hexc("a0e8ff"))

    def knife(c):
        c.poly([(5, 10), (13, 1), (14, 2), (6, 11)], hexc("d8dce8"))
        c.line(6, 10, 13, 2, hexc("ffffff"))
        c.line(3, 8, 8, 13, hexc("c8a040"), thick=2)
        c.line(2, 13, 5, 10, hexc("7a4a2a"), thick=2)

    def garlic(c):
        c.circle(7.5, 9.5, 5.5, hexc("f4f0e0"))
        c.line(7.5, 5, 7.5, 14, hexc("d0c8b0"))
        c.line(4.5, 6, 4, 13, hexc("d0c8b0"))
        c.line(10.5, 6, 11, 13, hexc("d0c8b0"))
        c.poly([(6, 4), (9, 4), (8, 0), (7, 0)], hexc("6ab04a"))

    def orbs(c):
        c.ring(7.5, 7.5, 5.5, 6.5, hexc("ffe890", 140))
        c.circle(7.5, 2.5, 2.4, hexc("ffc830"))
        c.circle(2.5, 10.5, 2.4, hexc("ffc830"))
        c.circle(12.5, 10.5, 2.4, hexc("ffc830"))
        for x, y in ((7, 2), (2, 10), (12, 10)):
            c.set(x, y, hexc("ffffff"))

    def bolt(c):
        c.poly([(9, 0), (3, 9), (7, 9), (5, 16), (13, 6), (9, 6), (12, 0)], hexc("ffe040"))
        c.line(10, 1, 6, 8, hexc("ffffff"))

    def ring(c):
        c.ring(7.5, 9.5, 3.2, 5.5, hexc("f0c840"))
        c.ring(7.5, 9.5, 4.6, 5.5, hexc("b08a20"))
        c.circle(7.5, 3.5, 2.6, hexc("e83a4a"))
        c.set(7, 2, hexc("ffb0b8"))

    def armor(c):
        c.poly([(1, 2), (5, 1), (7.5, 3), (10, 1), (14, 2), (13, 9), (7.5, 15), (2, 9)], hexc("8a8ca0"))
        c.poly([(3, 3), (5, 2.5), (7, 4), (7, 13), (3, 8.5)], hexc("b8bacb"))
        c.line(7.5, 4, 7.5, 13, hexc("5c5e70"))

    def heart(c):
        c.circle(4.5, 5.5, 3.6, hexc("e83a4a"))
        c.circle(10.5, 5.5, 3.6, hexc("e83a4a"))
        c.poly([(1, 7), (14, 7), (7.5, 14.5)], hexc("e83a4a"))
        c.circle(4, 4.5, 1.3, hexc("ffb0b8"))

    def boots(c):
        c.poly([(4, 3), (9, 3), (9, 10), (14, 11), (14, 14), (4, 14)], hexc("8a5428"))
        c.rect(4, 12, 14, 14, hexc("5a3418"))
        c.poly([(1, 4), (6, 5), (6, 8), (0, 9)], hexc("f4f4ff"))
        c.line(1, 6, 5, 6, hexc("c0c8e0"))

    def hourglass(c):
        c.rect(2, 0, 13, 1, hexc("8a5428"))
        c.rect(2, 14, 13, 15, hexc("8a5428"))
        c.poly([(3, 2), (12, 2), (8.5, 8), (12, 14), (3, 14), (6.5, 8)], hexc("c8e8ff", 200))
        c.poly([(4.5, 3), (10.5, 3), (7.5, 7)], hexc("f0c840"))
        c.poly([(7.5, 10), (11, 14), (4, 14)], hexc("f0c840"))

    def magnet(c):
        draw_magnet(c, 1, 2)

    def herb(c):
        c.line(7.5, 15, 7.5, 6, hexc("3a7a2a"), thick=2)
        c.poly([(7, 7), (1, 3), (2, 9)], hexc("6ac04a"))
        c.poly([(8, 5), (14, 1), (13, 8)], hexc("6ac04a"))
        c.poly([(7.5, 4), (5, 0), (10, 0)], hexc("8ae06a"))
        c.rect(11, 10, 15, 11, hexc("ff4a5a"))
        c.rect(12, 9, 14, 12, hexc("ff4a5a"))

    def chicken(c):
        draw_chicken(c, 1, 1)

    for name, fn in (("icon_bolt", wand), ("icon_knife", knife), ("icon_aura", garlic), ("icon_orb", orbs),
                     ("icon_lightning", bolt), ("icon_might", ring), ("icon_armor", armor),
                     ("icon_heart", heart), ("icon_speed", boots), ("icon_cooldown", hourglass),
                     ("icon_magnet", magnet), ("icon_regen", herb), ("icon_chicken", chicken)):
        icon(name, fn)


# ---------------------------------------------------------------------------
# Ground tiles (seamless, 64x64 native)
# ---------------------------------------------------------------------------

def make_ground():
    base = [hexc("24361f"), hexc("283c22"), hexc("2c4226"), hexc("213220")]
    for variant in range(1, 5):
        random.seed(1234)  # identical base noise -> seamless between variants
        cv = Canvas(64, 64)
        for y in range(64):
            for x in range(64):
                r = random.random()
                cv.set(x, y, base[0] if r < 0.55 else base[1] if r < 0.8 else base[2] if r < 0.93 else base[3])
        random.seed(variant * 77)
        # grass tufts
        for _ in range(14 if variant != 3 else 8):
            x, y = random.randint(0, 63), random.randint(0, 63)
            col = hexc("3e5a30") if random.random() < 0.7 else hexc("4a6a38")
            cv.set(x, y, col, wrap=True)
            cv.set(x - 1, y - 1, col, wrap=True)
            cv.set(x + 1, y - 1, col, wrap=True)
            cv.set(x, y - 1, col, wrap=True)
        if variant == 2:  # flowers
            for _ in range(5):
                x, y = random.randint(0, 63), random.randint(0, 63)
                col = random.choice([hexc("d8d0f0"), hexc("e8c860"), hexc("c870a0")])
                for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                    cv.set(x + dx, y + dy, col, wrap=True)
                cv.set(x, y, hexc("f0e070"), wrap=True)
        if variant == 3:  # dirt patch + stones
            cx, cy = random.randint(20, 44), random.randint(20, 44)
            for y in range(cy - 12, cy + 13):
                for x in range(cx - 14, cx + 15):
                    d = ((x - cx) / 14) ** 2 + ((y - cy) / 11) ** 2
                    if d < 1 and random.random() > d * 0.7:
                        cv.set(x, y, hexc("3a3024") if random.random() < 0.7 else hexc("443828"))
            for _ in range(4):
                x, y = random.randint(cx - 10, cx + 10), random.randint(cy - 8, cy + 8)
                cv.rect(x, y, x + 1, y + 1, hexc("6a6870"))
                cv.set(x, y, hexc("8a8890"))
        if variant == 4:  # gravestone
            gx, gy = 26, 22
            cv.rect(gx + 1, gy + 18, gx + 12, gy + 20, hexc("1a2616"))  # shadow
            cv.rect(gx + 2, gy + 3, gx + 10, gy + 18, hexc("6a6c78"))
            cv.rect(gx + 3, gy + 1, gx + 9, gy + 2, hexc("6a6c78"))
            cv.rect(gx + 3, gy + 3, gx + 4, gy + 17, hexc("8a8c98"))
            cv.rect(gx + 6, gy + 6, gx + 6, gy + 12, hexc("3a3c48"))
            cv.rect(gx + 4, gy + 8, gx + 8, gy + 8, hexc("3a3c48"))
            for x in range(gx + 1, gx + 12):
                cv.set(x, gy + 18, hexc("4a6a38"))
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
    """Builds a TrueType font from the 5x7 pixel glyphs (one square contour run per pixel row)."""
    PX = 128                       # font units per glyph pixel
    UPM = 8 * PX                   # 7 rows above the baseline + 1 below
    ASC, DESC = 7 * PX, -1 * PX
    ADV = 6 * PX

    chars = dict(GLYPHS)
    for ch, g in GLYPHS.items():   # lowercase renders as uppercase (except 'x')
        if "A" <= ch <= "Z" and ch.lower() not in chars:
            chars[ch.lower()] = g
    codes = sorted(ord(c) for c in chars)

    def glyph_data(rows):
        contours = []
        for r, row in enumerate(rows):
            y0, y1 = (6 - r) * PX, (7 - r) * PX
            x = 0
            while x < 5:
                if row[x] == "#":
                    x0 = x
                    while x < 5 and row[x] == "#":
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
                       0, 0, 0, DESC, 5 * PX, ASC, 0, 8, 2, 1, 0)
    hhea = struct.pack(">IhhhHhhhhhhhhhhhH", 0x00010000, ASC, DESC, 0, ADV, 0, PX, 5 * PX,
                       1, 0, 0, 0, 0, 0, 0, 0, n)
    maxp = struct.pack(">IHHHHHHHHHHHHHH", 0x00010000, n, max_pts, max_contours, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0)
    os2 = struct.pack(">HhHHHhhhhhhhhhhh", 4, ADV, 400, 5, 0, PX * 4, PX * 4, 0, PX, PX * 4, PX * 4, 0, PX * 3,
                      PX // 2, PX * 2, 0)
    os2 += bytes(10) + struct.pack(">IIII", 1, 0, 0, 0) + b"NSRV"
    os2 += struct.pack(">HHHhhhHHII", 0x40, codes[0], codes[-1], ASC, DESC, 0, ASC, -DESC, 1, 0)
    os2 += struct.pack(">hhHHH", 5 * PX, 7 * PX, 0, 32, 1)
    post = struct.pack(">IIhhIIIII", 0x00030000, 0, -PX, PX // 2, 1, 0, 0, 0, 0)

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
                'antialias: 0\n'
                'alpha: 1.0\n'
                'outline_alpha: 1.0\n'
                'outline_width: 3.0\n'
                'shadow_alpha: 0.0\n'
                'output_format: TYPE_BITMAP\n' % (8 * SCALE))


# ---------------------------------------------------------------------------
# Content added in the "more mechanics" update
# ---------------------------------------------------------------------------

EYE_PAL = {"k": OUTLINE, "w": hexc("f2e8e6"), "r": hexc("c83a4a"), "i": hexc("8a3ab8"),
           "p": hexc("120818"), "f": hexc("a04a6a")}
EYE_A = [
    "........",
    ".....kkk",
    "...kkwww",
    "..kwwwww",
    ".kwwrwww",
    ".kwwwwii",
    "kwwwwiip",
    "kwrwwiip",
    "kwwwwiip",
    "kwwwwwii",
    ".kwwrwww",
    ".kwwwwww",
    "..kwwwww",
    "...kkwww",
    "..kf.kkk",
    ".kf..kf.",
]
EYE_B = EYE_A[:14] + [
    "...kf.kk",
    "...kf.kf",
]

BRAZIER_PAL = {"k": OUTLINE, "s": hexc("7a7c88"), "S": hexc("4e505c"), "o": hexc("ff9a30"),
               "y": hexc("ffe060"), "r": hexc("e04020")}
BRAZIER_BASE = [
    "..kkkkkk",
    "..ksssss",
    "...kSsss",
    "....kSss",
    ".....kss",
    ".....kSs",
    ".....kss",
    "....kSss",
    "...kSSSS",
    "...kkkkk",
]
BRAZIER_A = ["........", "......r.", ".....ro.", "....rooy", "...royyy", "...royyy"] + BRAZIER_BASE
BRAZIER_B = ["........", "........", "......r.", "....rory", "...ryyyy", "...royyy"] + BRAZIER_BASE

DIGITS = {
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"], "3": ["###", "..#", ".##", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"], "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "###"],
}


def make_extras():
    grid(mirror(EYE_A), EYE_PAL).save("eye_1")
    grid(mirror(EYE_B), EYE_PAL).save("eye_2")
    grid(mirror(BRAZIER_A), BRAZIER_PAL).save("brazier_1")
    grid(mirror(BRAZIER_B), BRAZIER_PAL).save("brazier_2")

    # damage-number digits (white, tinted at runtime)
    for d, rows in DIGITS.items():
        cv = Canvas(5, 7)
        for y, r in enumerate(rows):
            for x, ch in enumerate(r):
                if ch == "#":
                    cv.set(x + 1, y + 1, (255, 255, 255, 255))
        cv.outline()
        cv.save("num_" + d)

    # enemy bullet
    cv = Canvas(9, 9)
    cv.circle(4, 4, 4.2, hexc("c040ff", 150))
    cv.circle(4, 4, 3.0, hexc("e070ff"))
    cv.circle(4, 4, 1.5, hexc("2a0838"))
    cv.save("ebullet")

    # holy water flask + pool (2 shimmer frames)
    cv = Canvas(9, 11)
    cv.rect(3, 0, 5, 2, hexc("c8a070"))
    cv.circle(4, 6.5, 3.6, hexc("70b8ff"))
    cv.circle(3, 5.5, 1.2, hexc("e8f8ff"))
    cv.outline()
    cv.save("flask")
    for i in range(2):
        random.seed(40 + i)
        cv = Canvas(32, 32)
        for y in range(32):
            for x in range(32):
                d = math.hypot(x - 15.5, y - 15.5)
                if d <= 15.5:
                    if d > 14:
                        cv.set(x, y, hexc("a8e0ff", 200))
                    elif random.random() < 0.06:
                        cv.set(x, y, hexc("e8f8ff", 210))
                    else:
                        cv.set(x, y, hexc("3a8cff", 95 + (i * 20 if (x + y) % 3 == 0 else 0)))
        cv.save("pool_%d" % (i + 1))

    # axe (rotated at runtime)
    cv = Canvas(14, 14)
    cv.line(2, 12, 10, 4, hexc("7a4a2a"), thick=2)
    cv.poly([(7, 1), (13, 4), (12, 9), (9, 5)], hexc("c8ccd8"))
    cv.line(8, 1, 13, 4, hexc("ffffff"))
    cv.outline()
    cv.save("axe")

    # cross pickup
    cv = Canvas(14, 16)
    cv.rect(5, 1, 8, 14, hexc("f0c840"))
    cv.rect(1, 4, 12, 7, hexc("f0c840"))
    cv.rect(6, 2, 6, 13, hexc("fff0a0"))
    cv.rect(2, 5, 11, 5, hexc("fff0a0"))
    cv.outline()
    cv.save("cross")

    # clock pickup
    cv = Canvas(15, 15)
    cv.circle(7, 7, 6.2, hexc("f0c840"))
    cv.circle(7, 7, 4.8, hexc("f4f4ff"))
    cv.line(7, 7, 7, 3.5, OUTLINE)
    cv.line(7, 7, 9.5, 8.5, OUTLINE)
    cv.outline()
    cv.save("clock")

    def water(c):
        c.rect(6, 0, 9, 3, hexc("c8a070"))
        c.circle(7.5, 9.5, 5.4, hexc("70b8ff"))
        c.circle(5.5, 7.5, 1.6, hexc("e8f8ff"))

    def axe(c):
        c.line(2, 14, 11, 5, hexc("7a4a2a"), thick=2)
        c.poly([(7, 1), (15, 4), (13, 11), (10, 6)], hexc("c8ccd8"))
        c.line(8, 1, 15, 4, hexc("ffffff"))

    def book(c):
        c.rect(2, 2, 13, 14, hexc("6a3aa0"))
        c.rect(3, 3, 12, 13, hexc("8a5ac8"))
        c.rect(11, 3, 13, 14, hexc("f0e8d0"))
        c.circle(7, 8, 2.5, hexc("f0c840"))

    def dup(c):
        c.rect(1, 5, 9, 13, hexc("3a8cff"))
        c.rect(6, 1, 14, 9, hexc("60c8ff"))
        c.rect(9, 4, 11, 6, hexc("ffffff"))
        c.rect(4, 8, 6, 10, hexc("ffffff"))

    def clover(c):
        for cx, cy in ((5, 5), (10, 5), (5, 10), (10, 10)):
            c.circle(cx, cy, 3.2, hexc("4ac04a"))
        c.circle(7.5, 7.5, 1.5, hexc("8ae06a"))
        c.line(9, 10, 13, 15, hexc("2a7a2a"), thick=2)

    def crown(c):
        c.poly([(1, 5), (4.5, 9), (7.5, 2), (10.5, 9), (14, 5), (13, 13), (2, 13)], hexc("f0c840"))
        c.rect(2, 11, 13, 13, hexc("c89a20"))
        c.set(7, 6, hexc("e83a4a"))
        c.set(4, 11, hexc("3a8cff"))
        c.set(11, 11, hexc("3a8cff"))

    for name, fn in (("icon_water", water), ("icon_axe", axe), ("icon_area", book), ("icon_amount", dup),
                     ("icon_luck", clover), ("icon_growth", crown)):
        icon(name, fn)


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

ANIMATIONS = [
    # id, frames, fps, playback
    ("player_idle", ["player_1"], 1, "PLAYBACK_NONE"),
    ("player_walk", ["player_1", "player_3", "player_2", "player_3"], 8, "PLAYBACK_LOOP_FORWARD"),
    ("bat", ["bat_1", "bat_2"], 8, "PLAYBACK_LOOP_FORWARD"),
    ("zombie", ["zombie_1", "zombie_2"], 3, "PLAYBACK_LOOP_FORWARD"),
    ("skeleton", ["skeleton_1", "skeleton_2"], 5, "PLAYBACK_LOOP_FORWARD"),
    ("ghost", ["ghost_1", "ghost_2"], 4, "PLAYBACK_LOOP_FORWARD"),
    ("ogre", ["ogre_1", "ogre_2"], 3, "PLAYBACK_LOOP_FORWARD"),
    ("puff", ["puff_1", "puff_2", "puff_3"], 15, "PLAYBACK_ONCE_FORWARD"),
    ("spark", ["spark_1", "spark_2"], 20, "PLAYBACK_ONCE_FORWARD"),
    ("eye", ["eye_1", "eye_2"], 4, "PLAYBACK_LOOP_FORWARD"),
    ("brazier", ["brazier_1", "brazier_2"], 6, "PLAYBACK_LOOP_FORWARD"),
    ("pool", ["pool_1", "pool_2"], 4, "PLAYBACK_LOOP_FORWARD"),
]
SINGLE_IMAGES = [
    "bolt", "knife", "orb", "aura", "lightning", "pixel", "shadow",
    "gem_blue", "gem_green", "gem_red", "chicken", "magnet", "chest",
    "ground_1", "ground_2", "ground_3", "ground_4",
    "icon_bolt", "icon_knife", "icon_aura", "icon_orb", "icon_lightning", "icon_might",
    "icon_armor", "icon_heart", "icon_speed", "icon_cooldown", "icon_magnet", "icon_regen", "icon_chicken",
    "icon_water", "icon_axe", "icon_area", "icon_amount", "icon_luck", "icon_growth",
    "ebullet", "flask", "axe", "cross", "clock",
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
    names = []
    make_characters(names)
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
