"""Content engine: renders carousel slides (1080x1350 JPG) and reels (1080x1920 MP4) from plan.json.
Usage: python3 engine.py <day> [outdir]      -> renders that day's media
       python3 engine.py preview <day>       -> quick preview frames only
"""
import json, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")
FONTS = {"b": "DUBAI-BOLD.TTF", "m": "DUBAI-MEDIUM.TTF", "r": "DUBAI-REGULAR.TTF", "l": "DUBAI-LIGHT.TTF"}
BG = (14, 14, 18); CARD = (26, 26, 32)
ACC = (255, 92, 54); ACC2 = (255, 194, 75)
TXT = (245, 240, 232); MUT = (150, 146, 140)
FPS = 30
_fc = {}

def font(size, w="b"):
    k = (size, w)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(os.path.join(FD, FONTS[w]), size, layout_engine=ImageFont.Layout.RAQM)
    return _fc[k]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo(t): t = clamp(t); return 1 - (1 - t) ** 4
def back(t): t = clamp(t); c = 1.6; return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def pr(t, s, d): return clamp((t - s) / d)

# ---------- text helpers ----------
def wrap(txt, f, maxw):
    words, lines, cur = txt.split(), [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if f.getlength(cand) <= maxw or not cur: cur = cand
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def text_block(txt, size, color, w="b", maxw=900, align="right", lh=1.25, glow=None):
    """Returns RGBA sprite of wrapped RTL text."""
    f = font(size, w)
    lines = wrap(txt, f, maxw)
    asc, desc = f.getmetrics()
    step = int(size * lh)
    pad = 30
    widths = [f.getlength(l) for l in lines]
    W = int(max(widths)) + pad * 2
    H = step * (len(lines) - 1) + asc + desc + pad * 2
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        lw = widths[i]
        x = W - pad - lw if align == "right" else (W - lw) / 2 if align == "center" else pad
        d.text((x, pad + i * step), l, font=f, fill=color + (255,))
    if glow:
        g = im.copy(); g = g.filter(ImageFilter.GaussianBlur(18))
        tint = Image.new("RGBA", im.size, glow + (0,)); tint.putalpha(g.getchannel("A").point(lambda v: int(v * 0.6)))
        im = Image.alpha_composite(tint, im)
    return im

def paste(cv, sp, x, y, a=1.0, s=1.0, anchor="tr"):
    if a <= 0.01: return
    if abs(s - 1) > 0.003:
        sp = sp.resize((max(1, int(sp.width * s)), max(1, int(sp.height * s))), Image.BICUBIC)
    if a < 0.999:
        sp = sp.copy(); sp.putalpha(sp.getchannel("A").point(lambda v: int(v * a)))
    if anchor == "tr": px, py = x - sp.width, y
    elif anchor == "c": px, py = x - sp.width / 2, y - sp.height / 2
    elif anchor == "tc": px, py = x - sp.width / 2, y
    elif anchor == "r": px, py = x - sp.width, y - sp.height / 2
    else: px, py = x, y
    px, py = int(px), int(py)
    x0, y0 = max(0, px), max(0, py)
    x1, y1 = min(cv.width, px + sp.width), min(cv.height, py + sp.height)
    if x1 > x0 and y1 > y0:
        cv.alpha_composite(sp.crop((x0 - px, y0 - py, x1 - px, y1 - py)), (x0, y0))

# ---------- backgrounds ----------
def make_bg(W, H, seed=1, glow_pos=(0.85, 0.12), glow2=(0.1, 0.9)):
    rnd = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.zeros((H, W, 3), np.float32); base[:] = BG
    for (gx, gy), col, rad, st in [(glow_pos, ACC, 0.55, 0.22), (glow2, ACC2, 0.5, 0.08)]:
        dx = (xx / W - gx); dy = (yy / H - gy) * (H / W)
        m = np.exp(-(dx * dx + dy * dy) / (2 * (rad * 0.5) ** 2)) * st
        base += m[..., None] * (np.array(col, np.float32) - base)
    noise = rnd.normal(0, 5.0, (H, W, 1)).astype(np.float32)
    base = np.clip(base + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(base, "RGB").convert("RGBA")

# ---------- icons ----------
def ic_bookmark(d, cx, cy, s, col, w=8):
    d.line([(cx - s*0.35, cy - s*0.5), (cx + s*0.35, cy - s*0.5), (cx + s*0.35, cy + s*0.5),
            (cx, cy + s*0.22), (cx - s*0.35, cy + s*0.5), (cx - s*0.35, cy - s*0.5)], fill=col, width=w, joint="curve")

def ic_send(d, cx, cy, s, col, w=8):
    pts = [(cx - s*0.5, cy - s*0.05), (cx + s*0.5, cy - s*0.45), (cx + s*0.1, cy + s*0.5), (cx - s*0.05, cy + s*0.08), (cx - s*0.5, cy - s*0.05)]
    d.line(pts, fill=col, width=w, joint="curve")
    d.line([(cx - s*0.05, cy + s*0.08), (cx + s*0.5, cy - s*0.45)], fill=col, width=w)

def ic_arrow_left(d, cx, cy, s, col, w=6):
    d.line([(cx + s*0.5, cy), (cx - s*0.5, cy)], fill=col, width=w)
    d.line([(cx - s*0.5, cy), (cx - s*0.15, cy - s*0.32)], fill=col, width=w)
    d.line([(cx - s*0.5, cy), (cx - s*0.15, cy + s*0.32)], fill=col, width=w)

def pill(text, size, fg, bg, w="m", padx=28, pady=10):
    f = font(size, w); tw = f.getlength(text); asc, desc = f.getmetrics()
    W, H = int(tw + padx * 2), int(asc + desc + pady * 2)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, H - 1], H // 2, fill=bg)
    d.text((padx, pady), text, font=f, fill=fg)
    return im

def big_number(n, size, col):
    f = font(size, "b"); s = f"{n:02d}"
    l, t, r, b = f.getbbox(s)
    im = Image.new("RGBA", (r - l + 20, b - t + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - l, 10 - t), s, font=f, fill=(0, 0, 0, 0), stroke_width=4, stroke_fill=col + (255,))
    return im

# ================= CAROUSEL =================
CW, CH = 1080, 1350
M = 90  # margin

def footer(cv, idx, total):
    d = ImageDraw.Draw(cv)
    # progress dots (RTL: first on the right)
    n = total; gap = 26; x0 = CW / 2 + (n - 1) * gap / 2
    for i in range(n):
        x = x0 - i * gap; r = 7 if i == idx else 5
        d.ellipse([x - r, CH - 80 - r, x + r, CH - 80 + r], fill=(ACC if i == idx else (70, 70, 78)) + (255,))
    paste(cv, text_block("احفظ  •  شارك", 30, MUT, "m", align="left"), M - 30, CH - 108, anchor="tl")

def slide_cover(day, total):
    cv = make_bg(CW, CH, seed=day["day"])
    paste(cv, pill(day["pillar"], 32, BG + (255,), ACC + (255,)), CW - M, M + 10)
    title = text_block(day["cover"][0], 128, TXT, "b", maxw=CW - 2 * M, lh=1.15)
    paste(cv, title, CW - M + 30, 360)
    yb = 360 + title.height - 10
    d = ImageDraw.Draw(cv); d.rounded_rectangle([CW - M - 160, yb, CW - M, yb + 12], 6, fill=ACC + (255,))
    paste(cv, text_block(day["cover"][1], 58, ACC2, "m", maxw=CW - 2 * M), CW - M + 30, yb + 50)
    # swipe hint
    sw = text_block("اسحب", 40, TXT, "m")
    paste(cv, sw, M + 70, CH - 200, anchor="tl")
    ic_arrow_left(d, M + 30, CH - 200 + sw.height / 2 + 2, 60, TXT + (255,), 6)
    footer(cv, 0, total)
    return cv

def slide_content(day, i, total):
    t, body = day["slides"][i]
    cv = make_bg(CW, CH, seed=day["day"] * 10 + i, glow_pos=(0.15, 0.1), glow2=(0.9, 0.95))
    d = ImageDraw.Draw(cv)
    num = big_number(i + 1, 230, ACC)
    paste(cv, num, CW - M + 10, M - 10)
    d.rounded_rectangle([M, M + 40, M + 220, M + 92], 26, outline=(70, 70, 78, 255), width=3)
    paste(cv, text_block(f"{i + 1} / {len(day['slides'])}", 30, MUT, "m", align="center"), M + 110, M + 66, anchor="c")
    tb = text_block(t, 88, TXT, "b", maxw=CW - 2 * M, lh=1.18)
    y = 420
    paste(cv, tb, CW - M + 30, y)
    y += tb.height + 10
    d.rounded_rectangle([CW - M - 110, y, CW - M, y + 8], 4, fill=ACC2 + (255,))
    bb = text_block(body, 52, (205, 200, 192), "r", maxw=CW - 2 * M, lh=1.5)
    paste(cv, bb, CW - M + 30, y + 40)
    footer(cv, i + 1, total)
    return cv

def slide_cta(day, total):
    cv = make_bg(CW, CH, seed=day["day"] + 99, glow_pos=(0.5, 0.35), glow2=(0.5, 1.0))
    d = ImageDraw.Draw(cv)
    lay = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    for cx, fn, lab in [(CW / 2 + 170, ic_bookmark, "احفظ"), (CW / 2 - 170, ic_send, "أرسل")]:
        ld.ellipse([cx - 120, 330, cx + 120, 570], fill=CARD + (255,), outline=ACC + (255,), width=5)
        fn(ld, cx, 450, 120, ACC + (255,), 10)
    cv.alpha_composite(lay)
    for cx, lab in [(CW / 2 + 170, "احفظ"), (CW / 2 - 170, "أرسل")]:
        paste(cv, text_block(lab, 44, TXT, "m", align="center"), cx, 640, anchor="c")
    tb = text_block(day["cta"], 84, TXT, "b", maxw=CW - 2 * M, align="center", lh=1.2)
    paste(cv, tb, CW / 2, 760, anchor="tc")
    paste(cv, text_block("تابع الحساب حتى توصلك نصيحة كل يوم", 44, ACC2, "m", maxw=CW - 2 * M, align="center"), CW / 2, 790 + tb.height, anchor="tc")
    footer(cv, total - 1, total)
    return cv

def render_carousel(day, out):
    total = len(day["slides"]) + 2
    slides = [slide_cover(day, total)] + [slide_content(day, i, total) for i in range(len(day["slides"]))] + [slide_cta(day, total)]
    paths = []
    for i, s in enumerate(slides):
        p = os.path.join(out, f"day{day['day']:02d}_{i + 1:02d}.jpg")
        s.convert("RGB").save(p, quality=93, subsampling=0); paths.append(p)
    return paths

# ================= REEL =================
RW, RH = 1080, 1920
T_HOOK, T_PT, T_CTA = 3.2, 3.3, 3.2

def reel_timeline(day):
    n = len(day["points"])
    return T_HOOK + n * T_PT + T_CTA

def synth_audio(path, dur, seed=0):
    sr = 44100; n = int(sr * dur); t = np.arange(n) / sr
    bpm = 104; beat = 60 / bpm
    out = np.zeros(n, np.float32)
    # pad: Am - F - C - G
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 261.63, 329.63], [196.0, 246.94, 293.66]]
    bar = beat * 4
    for ci in range(int(dur / bar) + 1):
        s0 = int(ci * bar * sr); s1 = min(n, int((ci + 1) * bar * sr))
        if s0 >= n: break
        tt = t[s0:s1] - ci * bar
        env = np.minimum(1, tt / 0.4) * np.minimum(1, (bar - tt) / 0.4)
        for f in chords[ci % 4]:
            out[s0:s1] += 0.045 * env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2 * tt))
    # kick + hat
    k = 0
    while k * beat < dur:
        s0 = int(k * beat * sr); L = min(int(0.25 * sr), n - s0)
        if L > 0:
            tt = np.arange(L) / sr
            f = 110 * np.exp(-tt * 18) + 45
            out[s0:s0 + L] += 0.32 * np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 9)
        h0 = int((k + 0.5) * beat * sr); L = min(int(0.05 * sr), n - h0)
        if L > 0:
            rnd = np.random.default_rng(k + seed)
            out[h0:h0 + L] += 0.05 * rnd.normal(0, 1, L) * np.exp(-np.arange(L) / sr * 80)
        k += 1
    # fade in/out
    fi = int(0.3 * sr); fo = int(0.8 * sr)
    out[:fi] *= np.linspace(0, 1, fi); out[-fo:] *= np.linspace(1, 0, fo)
    out = np.tanh(out * 1.4) * 0.8
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())

class Reel:
    def __init__(self, day):
        self.day = day
        self.bg = make_bg(RW + 200, RH + 200, seed=day["day"], glow_pos=(0.8, 0.2), glow2=(0.15, 0.85))
        self.hook = text_block(day["hook"], 118, TXT, "b", maxw=RW - 180, align="center", lh=1.18)
        self.pts = []
        for i, (a, b) in enumerate(day["points"]):
            self.pts.append((big_number(i + 1, 260, ACC),
                             text_block(a, 100, TXT, "b", maxw=RW - 180, align="center", lh=1.15),
                             text_block(b, 58, (205, 200, 192), "r", maxw=RW - 200, align="center", lh=1.35)))
        self.cta = text_block(day["cta"], 88, TXT, "b", maxw=RW - 180, align="center", lh=1.2)
        self.tag = pill(day["pillar"], 36, BG + (255,), ACC + (255,))
        self.follow = text_block("تابع للمزيد", 46, ACC2, "m", align="center")
        self.dur = reel_timeline(day)

    def frame(self, t):
        ox = 100 + int(math.sin(t * 0.4) * 60); oy = 100 + int(math.cos(t * 0.3) * 60)
        cv = self.bg.crop((ox, oy, ox + RW, oy + RH))
        d = ImageDraw.Draw(cv)
        n = len(self.pts); segs = n + 2
        # progress segments at top (RTL: fill right->left)
        sw = (RW - 160 - (segs - 1) * 10) / segs
        bounds = [0, T_HOOK] + [T_HOOK + (i + 1) * T_PT for i in range(n)] + [self.dur]
        for i in range(segs):
            x1 = RW - 80 - i * (sw + 10); x0 = x1 - sw
            d.rounded_rectangle([x0, 250, x1, 258], 4, fill=(60, 60, 68, 255))
            k = clamp((t - bounds[i]) / (bounds[i + 1] - bounds[i]))
            if k > 0: d.rounded_rectangle([x1 - sw * k, 250, x1, 258], 4, fill=ACC + (255,))
        cy = 900
        if t < T_HOOK:
            lt = t
            paste(cv, self.tag, RW / 2, 420, eo(pr(lt, 0.0, 0.4)), anchor="c")
            k = back(pr(lt, 0.1, 0.55))
            paste(cv, self.hook, RW / 2, cy, eo(pr(lt, 0.1, 0.4)), s=0.8 + 0.2 * k, anchor="c")
            w = 200 * eo(pr(lt, 0.6, 0.5)); yb = cy + self.hook.height / 2 + 30
            d.rounded_rectangle([RW / 2 - w, yb, RW / 2 + w, yb + 12], 6, fill=ACC + (255,))
            a_out = 1 - pr(lt, T_HOOK - 0.25, 0.25)
            if a_out < 1: cv.alpha_composite(Image.new("RGBA", (RW, RH), BG + (int(255 * (1 - a_out)),)))
        elif t < T_HOOK + n * T_PT:
            i = int((t - T_HOOK) // T_PT); lt = (t - T_HOOK) - i * T_PT
            num, ti, sub = self.pts[i]
            paste(cv, num, RW / 2, 560, eo(pr(lt, 0, 0.35)) * 0.95, s=0.85 + 0.15 * back(pr(lt, 0, 0.5)), anchor="c")
            k1 = eo(pr(lt, 0.15, 0.45))
            paste(cv, ti, RW / 2 + 90 * (1 - k1), 880, k1, anchor="c")
            yb = 880 + ti.height / 2 + 10
            w = 120 * eo(pr(lt, 0.45, 0.4))
            d.rounded_rectangle([RW / 2 - w, yb, RW / 2 + w, yb + 9], 5, fill=ACC2 + (255,))
            k2 = eo(pr(lt, 0.55, 0.45))
            paste(cv, sub, RW / 2, yb + 50 + 30 * (1 - k2), k2, anchor="tc")
            a_out = 1 - pr(lt, T_PT - 0.22, 0.22)
            if a_out < 1: cv.alpha_composite(Image.new("RGBA", (RW, RH), BG + (int(255 * (1 - a_out)),)))
        else:
            lt = t - T_HOOK - n * T_PT
            lay = Image.new("RGBA", (RW, RH), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
            ks = back(pr(lt, 0, 0.5)); ka = eo(pr(lt, 0, 0.35))
            for cx, fn in [(RW / 2 + 150, ic_bookmark), (RW / 2 - 150, ic_send)]:
                r = 110 * ks
                ld.ellipse([cx - r, 620 - r, cx + r, 620 + r], fill=CARD + (int(255 * ka),), outline=ACC + (int(255 * ka),), width=5)
                if ks > 0.3: fn(ld, cx, 620, 110 * ks, ACC + (int(255 * ka),), 9)
            cv.alpha_composite(lay)
            k = eo(pr(lt, 0.3, 0.5))
            paste(cv, self.cta, RW / 2, 980 + 40 * (1 - k), k, anchor="c")
            paste(cv, self.follow, RW / 2, 980 + self.cta.height / 2 + 70, eo(pr(lt, 0.7, 0.5)), anchor="c")
            a_out = 1 - pr(lt, T_CTA - 0.5, 0.5)
            if a_out < 1: cv.alpha_composite(Image.new("RGBA", (RW, RH), (0, 0, 0, int(255 * (1 - a_out)))))
        return cv

def render_reel(day, out):
    r = Reel(day)
    base = os.path.join(out, f"day{day['day']:02d}_reel")
    wav = base + ".wav"; tmp = base + ".tmp.mp4"; fin = base + ".mp4"
    synth_audio(wav, r.dur, seed=day["day"])
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}",
                          "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                          "-crf", "19", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                          "-shortest", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
    for i in range(int(round(r.dur * FPS))):
        p.stdin.write(r.frame(i / FPS).convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() != 0: raise SystemExit("ffmpeg failed")
    os.replace(tmp, fin); os.remove(wav)
    # cover frame
    cov = base + "_cover.jpg"; r.frame(1.4).convert("RGB").save(cov, quality=92)
    return [fin, cov]

def load_day(n):
    plan = json.load(open(os.path.join(HERE, "plan.json")))
    return next(d for d in plan["days"] if d["day"] == n), plan

if __name__ == "__main__":
    if sys.argv[1] == "preview":
        day, _ = load_day(int(sys.argv[2])); out = sys.argv[3] if len(sys.argv) > 3 else "/tmp"
        if day["type"] == "carousel":
            total = len(day["slides"]) + 2
            ims = [slide_cover(day, total), slide_content(day, 0, total), slide_cta(day, total)]
        else:
            r = Reel(day); ims = [r.frame(t) for t in (1.5, T_HOOK + 1.8, r.dur - 1.0)]
        sheet = Image.new("RGB", (sum(i.width // 2 for i in ims), max(i.height // 2 for i in ims)))
        x = 0
        for im in ims: sheet.paste(im.convert("RGB").resize((im.width // 2, im.height // 2)), (x, 0)); x += im.width // 2
        sheet.save(os.path.join(out, f"preview_day{day['day']:02d}.jpg"), quality=85)
    else:
        n = int(sys.argv[1]); out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "out")
        os.makedirs(out, exist_ok=True)
        day, _ = load_day(n)
        paths = render_carousel(day, out) if day["type"] == "carousel" else render_reel(day, out)
        print("\n".join(paths))
