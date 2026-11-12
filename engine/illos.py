"""Vector illustrations + photo-style scene cards for the cinematic engine."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from engine import font, ACC, ACC2, TXT, BG, CARD

SS = 2000  # supersampled canvas
WHITE = (255, 255, 255)
TEAL = (38, 205, 190); PURP = (124, 92, 255); BLUE = (64, 150, 255); RED = (255, 70, 90); GREEN = (70, 210, 120)
DARK = (22, 22, 30); DARK2 = (40, 40, 52)


def U(v): return v * SS / 100.0


def lingrad(size, c1, c2, angle=90):
    W, H = size
    a = math.radians(angle)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    p = (xx / W - 0.5) * math.cos(a) + (yy / H - 0.5) * math.sin(a)
    p = (p - p.min()) / (p.max() - p.min() + 1e-6)
    c1 = np.array(c1, np.float32); c2 = np.array(c2, np.float32)
    arr = c1 + (c2 - c1) * p[..., None]
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")


_G = {}
def G(c1, c2, angle=90):
    k = (c1, c2, angle)
    if k not in _G: _G[k] = lingrad((SS, SS), c1, c2, angle)
    return _G[k]


def gfill(cv, fn, c1, c2, angle=90):
    m = Image.new("L", cv.size, 0); fn(ImageDraw.Draw(m))
    g = G(c1, c2, angle).copy(); g.putalpha(m); cv.alpha_composite(g)


def sfill(cv, fn, col, a=255):
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); fn(ImageDraw.Draw(lay), col + (a,)); cv.alpha_composite(lay)


def shadow(cv, fn, blur=40, a=150, off=(0, 30)):
    m = Image.new("L", cv.size, 0); fn(ImageDraw.Draw(m))
    m = m.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * a / 255))
    sh = Image.new("RGBA", cv.size, (0, 0, 0, 0)); sh.putalpha(m)
    out = Image.new("RGBA", cv.size, (0, 0, 0, 0)); out.paste(sh, off); cv.alpha_composite(out)


def glow(cv, col, blur=50, strength=0.8):
    a = cv.getchannel("A").filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(min(255, v * strength)))
    g = Image.new("RGBA", cv.size, col + (0,)); g.putalpha(a)
    return Image.alpha_composite(g, cv)


def rr(box, r):
    return lambda d, *c: d.rounded_rectangle([U(b) for b in box], U(r), fill=(c[0] if c else 255))


def el(box):
    return lambda d, *c: d.ellipse([U(b) for b in box], fill=(c[0] if c else 255))


def poly(pts):
    return lambda d, *c: d.polygon([(U(x), U(y)) for x, y in pts], fill=(c[0] if c else 255))


def line(d, pts, col, w):
    d.line([(U(x), U(y)) for x, y in pts], fill=col, width=int(U(w)), joint="curve")


def arc(d, box, a0, a1, col, w):
    d.arc([U(b) for b in box], a0, a1, fill=col, width=int(U(w)))


def txt(cv, s, cx, cy, size, col, w="b"):
    f = font(int(U(size)), w); d = ImageDraw.Draw(cv)
    l, t, r, b = d.textbbox((0, 0), s, font=f)
    d.text((U(cx) - (r - l) / 2 - l, U(cy) - (b - t) / 2 - t), s, font=f, fill=col)


def sky_screen(cv, box, r=3, c1=(255, 140, 80), c2=(120, 70, 200)):
    """Mini 'photo' (sunset landscape) inside a rounded box."""
    x0, y0, x1, y1 = box
    W, H = int(U(x1 - x0)), int(U(y1 - y0))
    ph = lingrad((W, H), c2, c1, 90)
    d = ImageDraw.Draw(ph)
    d.ellipse([W * 0.55, H * 0.38, W * 0.8, H * 0.38 + W * 0.25], fill=(255, 226, 150, 255))
    d.polygon([(0, H * 0.75), (W * 0.3, H * 0.5), (W * 0.55, H * 0.72), (W * 0.75, H * 0.55), (W, H * 0.7), (W, H), (0, H)], fill=(40, 30, 70, 255))
    d.polygon([(0, H * 0.88), (W * 0.4, H * 0.7), (W * 0.8, H * 0.86), (W, H * 0.8), (W, H), (0, H)], fill=(22, 18, 40, 255))
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, H - 1], int(U(r)), fill=255)
    ph.putalpha(m); cv.alpha_composite(ph, (int(U(x0)), int(U(y0))))


# ---------------- illustrations ----------------
def i_phone(cv):
    body = rr((30, 8, 70, 92), 7)
    shadow(cv, body)
    gfill(cv, body, (60, 60, 74), (24, 24, 32), 60)
    sky_screen(cv, (32.5, 11, 67.5, 89), 5)
    d = ImageDraw.Draw(cv)
    for i in (1, 2):
        line(d, [(32.5 + 35 * i / 3, 11), (32.5 + 35 * i / 3, 89)], (255, 255, 255, 110), 0.35)
        line(d, [(32.5, 11 + 78 * i / 3), (67.5, 11 + 78 * i / 3)], (255, 255, 255, 110), 0.35)
    sfill(cv, el((36, 15, 39, 18)), RED)
    txt(cv, "REC", 43.5, 16.4, 2.6, WHITE + (255,), "m")
    sfill(cv, el((44, 76, 56, 88)), WHITE, 235)
    sfill(cv, el((45.5, 77.5, 54.5, 86.5)), RED)
    rr((45, 9.2, 55, 10.6), 1)(d, (10, 10, 14, 255))


def i_mic(cv):
    d = ImageDraw.Draw(cv)
    for k, a in ((1, 200), (2, 130), (3, 70)):
        arc(d, (50 - 16 - k * 8, 38 - 16 - k * 8, 50 + 16 + k * 8, 38 + 16 + k * 8), 150, 210, ACC2 + (a,), 2.2)
        arc(d, (50 - 16 - k * 8, 38 - 16 - k * 8, 50 + 16 + k * 8, 38 + 16 + k * 8), -30, 30, ACC2 + (a,), 2.2)
    cap = rr((38, 12, 62, 58), 12)
    shadow(cv, cap)
    gfill(cv, cap, ACC2, ACC, 70)
    d = ImageDraw.Draw(cv)
    for y in range(18, 54, 5):
        line(d, [(42, y), (58, y)], (255, 255, 255, 90), 0.7)
    arc(d, (31, 30, 69, 70), 0, 180, (230, 230, 240, 255), 2.6)
    line(d, [(50, 70), (50, 84)], (230, 230, 240, 255), 2.6)
    sfill(cv, rr((36, 83, 64, 88), 2.5), (230, 230, 240))


def i_bulb(cv):
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for k in range(12):
        a = k * math.pi * 2 / 12
        line(d, [(50 + math.cos(a) * 33, 40 + math.sin(a) * 33), (50 + math.cos(a) * 42, 40 + math.sin(a) * 42)], ACC2 + (230,), 2.4)
    cv.alpha_composite(lay)
    b = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    gfill(b, el((28, 16, 72, 60)), (255, 236, 160), ACC2, 90)
    gfill(b, poly([(38, 54), (62, 54), (58, 68), (42, 68)]), (255, 220, 120), ACC2, 90)
    cv.alpha_composite(glow(b, ACC2, 60, 1.2))
    d = ImageDraw.Draw(cv)
    line(d, [(45, 52), (45, 40), (50, 45), (55, 40), (55, 52)], (200, 110, 30, 255), 1.4)
    for i, y in enumerate((69, 74, 79)):
        sfill(cv, rr((40 + i, y, 60 - i, y + 4), 2), (170, 170, 185) if i % 2 == 0 else (130, 130, 145))
    sfill(cv, rr((45, 83, 55, 87), 2), (110, 110, 125))


def i_calendar(cv):
    body = rr((14, 16, 86, 88), 6)
    shadow(cv, body)
    gfill(cv, body, (52, 52, 66), (30, 30, 40), 90)
    gfill(cv, rr((14, 16, 86, 32), 6), ACC, ACC2, 0)
    sfill(cv, rr((14, 26, 86, 32), 0), ACC)
    gfill(cv, rr((14, 26, 86, 32), 0), ACC, ACC2, 0)
    for x in (30, 70):
        sfill(cv, rr((x - 2, 10, x + 2, 22), 2), (230, 230, 240))
    for r in range(4):
        for c in range(5):
            x0 = 20 + c * 13.2; y0 = 38 + r * 12.2
            done = (r * 5 + c) % 3 != 2 and r < 3
            sfill(cv, rr((x0, y0, x0 + 9.5, y0 + 8.5), 2), (TEAL if done else (70, 70, 86)), 255 if done else 255)
            if done:
                d = ImageDraw.Draw(cv); line(d, [(x0 + 2.5, y0 + 4.5), (x0 + 4.3, y0 + 6.3), (x0 + 7.3, y0 + 2.5)], WHITE + (255,), 1.0)


def i_chart(cv):
    panel = rr((10, 14, 90, 86), 6)
    shadow(cv, panel)
    gfill(cv, panel, (46, 46, 60), (26, 26, 34), 90)
    d = ImageDraw.Draw(cv)
    for y in (30, 46, 62):
        line(d, [(18, y), (82, y)], (255, 255, 255, 30), 0.4)
    hs = [18, 26, 22, 36, 46, 58]
    for i, h in enumerate(hs):
        x0 = 19 + i * 10.8
        gfill(cv, rr((x0, 78 - h, x0 + 7, 78), 2), ACC2, ACC, 90)
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    pts = [(22, 56), (33, 50), (44, 53), (55, 40), (66, 32), (78, 20)]
    line(dl, pts, TEAL + (255,), 1.8)
    for p in pts: dl.ellipse([U(p[0] - 1.6), U(p[1] - 1.6), U(p[0] + 1.6), U(p[1] + 1.6)], fill=WHITE + (255,))
    dl.polygon([(U(78), U(14)), (U(84), U(22)), (U(74), U(23))], fill=TEAL + (255,))
    cv.alpha_composite(glow(lay, TEAL, 25, 0.9))


def i_timeline(cv):
    panel = rr((8, 22, 92, 80), 5)
    shadow(cv, panel)
    gfill(cv, panel, (46, 46, 60), (26, 26, 34), 90)
    sky_screen(cv, (30, 26, 70, 48), 2)
    rows = [((12, 40, ACC), (42, 66, BLUE), (68, 88, ACC)), ((12, 30, PURP), (33, 58, TEAL), (60, 88, PURP)), ((12, 50, ACC2), (55, 88, ACC2))]
    for r, segs in enumerate(rows):
        y = 53 + r * 8.5
        for a, b, c in segs:
            sfill(cv, rr((a, y, b, y + 6), 1.5), c, 230)
    d = ImageDraw.Draw(cv)
    line(d, [(56, 50), (56, 79)], WHITE + (255,), 0.8)
    sfill(cv, poly([(53.5, 49), (58.5, 49), (56, 52)]), WHITE)
    # scissors
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    line(dl, [(64, 4), (82, 22)], (235, 235, 245, 255), 1.6); line(dl, [(82, 4), (64, 22)], (235, 235, 245, 255), 1.6)
    for cx, cy in ((63, 23), (83, 23)):
        dl.ellipse([U(cx - 4), U(cy - 4), U(cx + 4), U(cy + 4)], outline=ACC + (255,), width=int(U(1.6)))
    cv.alpha_composite(glow(lay, ACC, 20, 0.6))


def i_magnifier(cv):
    d = ImageDraw.Draw(cv)
    shadow(cv, el((18, 14, 70, 66)))
    gfill(cv, el((18, 14, 70, 66)), (70, 70, 90), (30, 30, 42), 60)
    sfill(cv, el((23, 19, 65, 61)), (120, 190, 255), 70)
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    line(dl, [(64, 60), (84, 82)], ACC + (255,), 7)
    cv.alpha_composite(lay)
    txt(cv, "#", 44, 39, 30, WHITE + (255,), "b")
    arc(d, (26, 22, 62, 58), 200, 250, (255, 255, 255, 150), 1.4)


def i_palette(cv):
    card = rr((12, 18, 88, 82), 7)
    shadow(cv, card)
    gfill(cv, card, (48, 48, 62), (28, 28, 36), 90)
    cols = [ACC, ACC2, TEAL, PURP, BLUE]
    for i, c in enumerate(cols):
        x = 20 + i * 13.5
        sfill(cv, el((x, 26, x + 10, 36)), c)
    txt(cv, "Aa", 34, 58, 20, WHITE + (255,), "b")
    d = ImageDraw.Draw(cv)
    for k, w in enumerate((26, 20, 23)):
        sfill(cv, rr((56, 48 + k * 7, 56 + w, 52 + k * 7), 2), (120, 120, 140))
    gfill(cv, rr((56, 69, 80, 75), 3), ACC, ACC2, 0)


def i_warning(cv):
    tri = poly([(50, 12), (88, 80), (12, 80)])
    shadow(cv, tri)
    b = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    gfill(b, tri, ACC2, ACC, 90)
    cv.alpha_composite(glow(b, ACC, 40, 0.8))
    sfill(cv, rr((47, 34, 53, 62), 3), DARK)
    sfill(cv, el((46.5, 66, 53.5, 73)), DARK)


def i_script(cv):
    paper = rr((20, 10, 76, 90), 4)
    shadow(cv, paper)
    gfill(cv, paper, (250, 246, 238), (226, 220, 210), 90)
    sfill(cv, rr((28, 18, 60, 24), 2), ACC)
    for k in range(7):
        w = [40, 34, 38, 28, 36, 30, 22][k]
        sfill(cv, rr((68 - w, 32 + k * 7.5, 68, 35 + k * 7.5), 1.5), (150, 145, 140))
    # pen
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    line(dl, [(86, 34), (60, 82)], ACC2 + (255,), 6)
    line(dl, [(86, 34), (82, 41.5)], (60, 60, 70, 255), 6)
    dl.polygon([(U(58.2), U(80)), (U(63.5), U(83)), (U(57.5), U(89))], fill=(60, 60, 70, 255))
    shadow(cv, lambda d, *c: d.line([(U(86), U(34)), (U(60), U(82))], fill=255, width=int(U(6))), 20, 120)
    cv.alpha_composite(lay)


def i_network(cv):
    nodes = [(50, 50), (20, 26), (80, 24), (16, 72), (84, 74), (50, 12), (50, 88)]
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    for n in nodes[1:]:
        line(dl, [nodes[0], n], (255, 255, 255, 70), 0.8)
    for a, b in ((1, 5), (2, 5), (3, 6), (4, 6), (1, 3), (2, 4)):
        line(dl, [nodes[a], nodes[b]], (255, 255, 255, 40), 0.5)
    cv.alpha_composite(lay)
    cols = [ACC, TEAL, PURP, BLUE, ACC2, TEAL, PURP]
    for i, (x, y) in enumerate(nodes[1:]):
        b = Image.new("RGBA", cv.size, (0, 0, 0, 0)); sfill(b, el((x - 6, y - 6, x + 6, y + 6)), cols[i + 1])
        cv.alpha_composite(glow(b, cols[i + 1], 18, 0.8))
    b = Image.new("RGBA", cv.size, (0, 0, 0, 0)); gfill(b, el((34, 34, 66, 66)), ACC2, ACC, 60)
    cv.alpha_composite(glow(b, ACC, 40, 1.0))
    d = ImageDraw.Draw(cv)
    pts = [(41, 49), (60, 41), (54, 60), (51, 52), (41, 49)]
    line(d, pts, WHITE + (255,), 1.6); line(d, [(51, 52), (60, 41)], WHITE + (255,), 1.6)


def i_retention(cv):
    panel = rr((10, 14, 90, 86), 6)
    shadow(cv, panel)
    gfill(cv, panel, (46, 46, 60), (26, 26, 34), 90)
    m = Image.new("L", cv.size, 0); dm = ImageDraw.Draw(m)
    pts = [(16, 26)] + [(16 + i * 2, 26 + 40 * (1 - math.exp(-i / 6.0)) + i * 0.15) for i in range(1, 34)]
    dm.polygon([(U(x), U(y)) for x, y in pts] + [(U(82), U(78)), (U(16), U(78))], fill=255)
    g = G(ACC, (40, 20, 30), 90).copy(); g.putalpha(m.point(lambda v: int(v * 0.55))); cv.alpha_composite(g)
    d = ImageDraw.Draw(cv); line(d, pts, ACC2 + (255,), 1.4)
    line(d, [(26, 18), (26, 80)], (255, 255, 255, 120), 0.5)
    sfill(cv, el((56, 20, 80, 44)), WHITE, 235)
    sfill(cv, poly([(65, 26), (74, 32), (65, 38)]), ACC)


def i_stopwatch(cv):
    shadow(cv, el((18, 20, 82, 84)))
    gfill(cv, el((18, 20, 82, 84)), (64, 64, 80), (26, 26, 34), 60)
    sfill(cv, el((23, 25, 77, 79)), (18, 18, 24))
    d = ImageDraw.Draw(cv)
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    arc(dl, (25, 27, 75, 77), -90, 200, ACC + (255,), 3.4)
    cv.alpha_composite(glow(lay, ACC, 25, 0.9))
    txt(cv, "3s", 50, 52, 22, WHITE + (255,), "b")
    sfill(cv, rr((45, 9, 55, 14), 2), (200, 200, 210)); sfill(cv, rr((48, 13, 52, 20), 1), (200, 200, 210))
    sfill(cv, rr((72, 18, 78, 22), 1.5), (200, 200, 210))


def i_fingerprint(cv):
    b = Image.new("RGBA", cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(b)
    for k in range(7):
        r = 6 + k * 5.2
        a0 = 200 + k * 7; a1 = 340 + (k % 3) * 25
        arc(d, (50 - r, 52 - r, 50 + r, 52 + r), a0, a1, ACC2 + (255,), 1.8)
        arc(d, (50 - r, 52 - r, 50 + r, 52 + r), 10 + k * 9, 150 - (k % 2) * 30, ACC + (255,), 1.8)
    cv.alpha_composite(glow(b, ACC, 30, 0.9))
    sfill(cv, el((72, 12, 88, 28)), TEAL)
    d = ImageDraw.Draw(cv); line(d, [(76, 20), (79, 23), (84.5, 16.5)], WHITE + (255,), 1.3)


def i_thumbnail(cv):
    fr = rr((10, 16, 90, 84), 5)
    shadow(cv, fr)
    gfill(cv, fr, (60, 60, 74), (30, 30, 40), 90)
    sky_screen(cv, (13, 19, 87, 81), 3, (255, 120, 90), (60, 90, 220))
    sfill(cv, rr((18, 26, 62, 38), 3), ACC2)
    sfill(cv, rr((18, 41, 50, 49), 3), WHITE, 235)
    sfill(cv, poly([(66, 62), (66, 88), (72, 82), (77, 92), (81, 90), (76, 80), (84, 80)]), WHITE)


def i_mountain(cv):
    gfill(cv, poly([(4, 86), (40, 30), (58, 54), (70, 40), (96, 86)]), (90, 80, 130), (34, 30, 50), 90)
    gfill(cv, poly([(40, 30), (47, 41), (42, 39), (37, 44), (33, 41)]), WHITE, (220, 220, 235), 90)
    d = ImageDraw.Draw(cv)
    line(d, [(12, 86), (24, 72), (20, 64), (32, 52), (30, 44), (39, 33)], ACC2 + (230,), 1.0)
    line(d, [(40, 30), (40, 10)], (235, 235, 245, 255), 1.0)
    b = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    gfill(b, poly([(40.5, 10), (56, 14), (40.5, 19)]), ACC, ACC2, 0)
    cv.alpha_composite(glow(b, ACC, 20, 0.8))
    for x, y, s in ((74, 16, 1.2), (84, 30, 0.8), (20, 20, 0.9), (64, 8, 0.7)):
        sfill(cv, el((x - s, y - s, x + s, y + s)), WHITE, 220)


def i_checklist(cv):
    card = rr((16, 10, 84, 90), 6)
    shadow(cv, card)
    gfill(cv, card, (50, 50, 64), (28, 28, 36), 90)
    for k in range(5):
        y = 20 + k * 14
        on = k < 4
        sfill(cv, rr((22, y, 32, y + 10), 2.5), TEAL if on else (80, 80, 96))
        if on:
            d = ImageDraw.Draw(cv); line(d, [(24.5, y + 5.2), (26.6, y + 7.3), (30, y + 2.8)], WHITE + (255,), 1.1)
        sfill(cv, rr((38, y + 3, 38 + [36, 30, 40, 26, 32][k], y + 7), 2), (150, 150, 168) if on else (95, 95, 110))


def i_apps(cv):
    body = rr((28, 6, 72, 94), 7)
    shadow(cv, body)
    gfill(cv, body, (60, 60, 74), (24, 24, 32), 60)
    gfill(cv, rr((30.5, 9, 69.5, 91), 5), (40, 36, 70), (16, 16, 26), 90)
    cols = [(ACC, ACC2), (TEAL, BLUE), (PURP, BLUE), (ACC2, ACC), (RED, ACC), (GREEN, TEAL), (BLUE, PURP), (ACC, PURP), (TEAL, GREEN)]
    for i, (a, b) in enumerate(cols):
        r, c = divmod(i, 3)
        x0 = 34 + c * 11.6; y0 = 18 + r * 12
        gfill(cv, rr((x0, y0, x0 + 8.4, y0 + 8.4), 2.2), a, b, 45)
    sfill(cv, poly([(37.5, 20.2), (40.6, 22.2), (37.5, 24.2)]), WHITE)
    sfill(cv, rr((34, 60, 66, 84), 3), (255, 255, 255), 25)
    for k in range(3):
        sfill(cv, rr((37, 64 + k * 6.5, 37 + [24, 18, 21][k], 67 + k * 6.5), 1.5), [ACC, TEAL, PURP][k], 220)


def i_play(cv):
    b = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    gfill(b, rr((18, 18, 82, 82), 18), ACC, ACC2, 45)
    cv.alpha_composite(glow(b, ACC, 50, 1.0))
    sfill(cv, poly([(42, 34), (66, 50), (42, 66)]), WHITE)
    sfill(cv, poly([(78, 10), (80.5, 16.5), (87, 19), (80.5, 21.5), (78, 28), (75.5, 21.5), (69, 19), (75.5, 16.5)]), ACC2)


ILLOS = {"phone": i_phone, "mic": i_mic, "bulb": i_bulb, "calendar": i_calendar, "chart": i_chart, "timeline": i_timeline,
         "magnifier": i_magnifier, "palette": i_palette, "warning": i_warning, "script": i_script, "network": i_network,
         "retention": i_retention, "stopwatch": i_stopwatch, "fingerprint": i_fingerprint, "thumbnail": i_thumbnail,
         "mountain": i_mountain, "checklist": i_checklist, "apps": i_apps, "play": i_play}

PILLAR_ILLOS = {
    "الهوك": ["stopwatch", "play", "retention", "script"],
    "التصوير": ["phone", "thumbnail", "bulb", "timeline"],
    "الاحتفاظ": ["retention", "stopwatch", "timeline", "play"],
    "الخوارزمية": ["network", "chart", "play", "retention"],
    "الكتابة": ["script", "bulb", "checklist", "phone"],
    "المونتاج": ["timeline", "apps", "phone", "play"],
    "الأفكار": ["bulb", "script", "calendar", "mountain"],
    "الصوت": ["mic", "timeline", "phone", "play"],
    "الأخطاء": ["warning", "chart", "checklist", "retention"],
    "الهوية": ["palette", "thumbnail", "fingerprint", "phone"],
    "الاستراتيجية": ["calendar", "checklist", "chart", "script"],
    "التحليل": ["chart", "retention", "magnifier", "network"],
    "الأصالة": ["fingerprint", "bulb", "mountain", "play"],
    "التصميم": ["thumbnail", "palette", "phone", "script"],
    "العقلية": ["mountain", "calendar", "chart", "bulb"],
    "البحث": ["magnifier", "network", "chart", "script"],
    "الأدوات": ["apps", "timeline", "phone", "play"],
    "الملخص": ["checklist", "bulb", "calendar", "mountain"],
}

_IC = {}
def illo(name, size):
    k = (name, size)
    if k not in _IC:
        cv = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
        ILLOS[name](cv)
        _IC[k] = cv.resize((size, size), Image.LANCZOS)
    return _IC[k]


SCENE_TONES = [((70, 30, 90), (18, 12, 30)), ((20, 60, 90), (10, 16, 30)), ((90, 40, 30), (24, 12, 14)),
               ((30, 70, 70), (10, 20, 24)), ((50, 40, 100), (14, 12, 30)), ((90, 60, 20), (26, 18, 10))]


def scene_card(name, W, H, tone=0, seed=0, r=56):
    """A photo-like card: deep gradient, bokeh, vignette, illustration with glow."""
    c1, c2 = SCENE_TONES[tone % len(SCENE_TONES)]
    bg = lingrad((W, H), c1, c2, 70)
    rnd = np.random.default_rng(seed)
    bok = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(bok)
    for _ in range(26):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H); s = rnd.uniform(14, 80)
        col = [ACC, ACC2, (255, 255, 255), TEAL][rnd.integers(0, 4)]
        d.ellipse([x - s, y - s, x + s, y + s], fill=col + (int(rnd.uniform(18, 60)),))
    bok = bok.filter(ImageFilter.GaussianBlur(10))
    bg.alpha_composite(bok)
    # light from top
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = np.clip(1 - (((xx - W * 0.5) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.75)) ** 2), 0, 1)
    arr = np.asarray(bg).astype(np.float32); arr[..., :3] *= (0.55 + 0.45 * v[..., None])
    bg = Image.fromarray(arr.astype(np.uint8), "RGBA")
    il = illo(name, int(min(W, H) * 0.78))
    bg.alpha_composite(il, ((W - il.width) // 2, (H - il.height) // 2 + int(H * 0.02)))
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, H - 1], r, fill=255)
    bg.putalpha(m)
    # thin border
    ImageDraw.Draw(bg).rounded_rectangle([1, 1, W - 2, H - 2], r, outline=(255, 255, 255, 50), width=3)
    out = Image.new("RGBA", (W + 120, H + 120), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0); ImageDraw.Draw(sh).rounded_rectangle([60, 80, 60 + W, 80 + H], r, fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(30)); s2 = Image.new("RGBA", out.size, (0, 0, 0, 0)); s2.putalpha(sh)
    out.alpha_composite(s2); out.alpha_composite(bg, (60, 60))
    return out


def logo_mark(size):
    cv = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    gfill(cv, rr((6, 6, 94, 94), 26), ACC, ACC2, 45)
    sfill(cv, poly([(38, 28), (70, 50), (38, 72)]), WHITE)
    sfill(cv, poly([(76, 14), (78.6, 21.4), (86, 24), (78.6, 26.6), (76, 34), (73.4, 26.6), (66, 24), (73.4, 21.4)]), WHITE, 240)
    return cv.resize((size, size), Image.LANCZOS)
