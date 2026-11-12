"""Cinematic reel engine: intro clip + illustrated scenes + original soundtrack -> 1080x1920 MP4.
Usage: python3 cine.py <day> [outdir]        render one day
       python3 cine.py preview <day> [outdir]  contact sheet of key frames
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from engine import font, text_block, paste, clamp, eo, back, pr, pill, ic_bookmark, ic_send, BG, CARD, ACC, ACC2, TXT, MUT, make_bg
from illos import scene_card, logo_mark, PILLAR_ILLOS, TEAL
import score

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
FPS = 30
HANDLE = "@l0__ol3"
T_INTRO, T_HOOK, T_CTA = 3.2, 3.6, 4.2

INSPIRE = [
    "كل محتوى عظيم بدأ بفكرة بسيطة", "أول خطوة أهم من أفضل خطوة", "صوتك يستاهل يوصل للعالم",
    "الاستمرارية تصنع المعجزات", "اللي تتعلمه اليوم، تحصده باجر", "موبايلك يكفي حتى تبدأ",
    "كل فيديو هو تمرين لفيديو أحسن", "الإبداع عادة، مو صدفة", "خلي محتواك يحچي عنك",
    "النجاح يحب اللي ما يوقف", "الفكرة الزينة تستاهل تتنفذ صح", "التفاصيل الصغيرة تصنع الفرق الكبير",
    "ابدأ بالي عندك، وكبّر بالطريق", "ما أكو محتوى بلا جمهور، ولا جمهور بلا صبر", "قصتك ما يحچيها أحد غيرك",
    "كل خبير كان مبتدئ يوم من الأيام", "اصنع شي تفتخر بيه", "الوضوح أقوى من الكمال",
    "خلي كل ثانية تستاهل", "انت أقرب لهدفك مما تتخيل", "الأصالة هي بصمتك",
    "العين تسبق الأذن، خليها تنبهر", "كل يوم فرصة جديدة تبني بيها", "الشغف يبدي، والنظام يكمّل",
    "صوت واضح، رسالة أوضح", "ابدأ قوي، وخليهم يكملون", "الاستمرارية أهم من الكمال",
    "النمو يجي لمن تفهم أرقامك", "أدوات بسيطة، نتائج كبيرة", "شهر كامل من التعلم، والقادم أحلى",
]


def item_dur(t, b):
    return max(3.4, min(6.0, 1.3 + (len(t) + len(b)) / 16.0))


class Bokeh:
    def __init__(self, seed, n=26, cols=(ACC, ACC2, (255, 255, 255))):
        rnd = np.random.default_rng(seed)
        self.p = []
        for i in range(n):
            s = int(rnd.uniform(16, 90))
            col = cols[i % len(cols)]
            im = Image.new("RGBA", (s * 4, s * 4), (0, 0, 0, 0))
            ImageDraw.Draw(im).ellipse([s, s, s * 3, s * 3], fill=col + (255,))
            im = im.filter(ImageFilter.GaussianBlur(s * 0.35))
            self.p.append((rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(-14, 14), rnd.uniform(-40, -10),
                           im, rnd.uniform(0.10, 0.32), rnd.uniform(0, 6.28), rnd.uniform(0.5, 1.4)))

    def draw(self, cv, t, gain=1.0):
        for x, y, vx, vy, im, a, ph, sp in self.p:
            xx = (x + vx * t) % (W + 200) - 100; yy = (y + vy * t) % (H + 200) - 100
            aa = a * gain * (0.65 + 0.35 * math.sin(t * sp + ph))
            paste(cv, im, xx, yy, aa, anchor="c")


def flare_sprite():
    w, h = 1600, 260
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = np.exp(-((yy - h / 2) / 18) ** 2) * np.exp(-((xx - w / 2) / (w * 0.32)) ** 2)
    v2 = np.exp(-((yy - h / 2) / 70) ** 2) * np.exp(-((xx - w / 2) / (w * 0.18)) ** 2) * 0.5
    a = np.clip(v + v2, 0, 1)
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., 0] = 255; arr[..., 1] = (180 + 75 * v).astype(np.uint8); arr[..., 2] = (120 + 135 * v).astype(np.uint8)
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = ((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2
    a = (np.clip(d - 0.35, 0, 1) ** 1.2 * 210).astype(np.uint8)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); im.putalpha(Image.fromarray(a, "L"))
    return im


class Cine:
    def __init__(self, day):
        self.day = day; n = day["day"]
        if day["type"] == "reel":
            self.items = [tuple(p) for p in day["points"]]
            self.hook, self.sub = day["hook"], None
        else:
            self.items = [tuple(s) for s in day["slides"]]
            self.hook, self.sub = day["cover"][0], day["cover"][1]
        names = PILLAR_ILLOS.get(day["pillar"], ["play", "bulb", "phone", "chart"])
        self.bg = make_bg(W + 240, H + 240, seed=n + 500, glow_pos=(0.85, 0.15), glow2=(0.1, 0.9))
        self.vig = vignette()
        self.bok = Bokeh(n)
        self.flare = flare_sprite()
        self.logo_big = logo_mark(260); self.logo_sm = logo_mark(76)
        self.handle = text_block(HANDLE, 34, TXT, "m", align="left")
        self.tag = pill(day["pillar"], 34, BG + (255,), ACC + (255,))
        # intro
        self.inspire_words = INSPIRE[(n - 1) % len(INSPIRE)].split()
        self.inspire = text_block(INSPIRE[(n - 1) % len(INSPIRE)], 92, TXT, "b", maxw=W - 200, align="center", lh=1.2, glow=ACC)
        self.kicker = text_block("نصيحة اليوم", 40, ACC2, "m", align="center")
        self.daynum = text_block(f"اليوم {n:02d}", 34, MUT, "m", align="center")
        # hook
        self.hook_card = scene_card(names[0], 860, 860, tone=n, seed=n * 7, r=64)
        self.hook_t = text_block(self.hook, 96 if len(self.hook) < 30 else 84, TXT, "b", maxw=W - 160, align="center", lh=1.18)
        self.sub_t = text_block(self.sub, 54, ACC2, "m", maxw=W - 180, align="center") if self.sub else None
        # items
        self.it = []
        for i, (a, b) in enumerate(self.items):
            card = scene_card(names[(i + 1) % len(names)], 640, 640, tone=n + i + 1, seed=n * 31 + i, r=54)
            ta = text_block(a, 84 if len(a) < 22 else 72, TXT, "b", maxw=W - 160, align="center", lh=1.15)
            tb = text_block(b, 50 if len(b) < 45 else 46, (210, 205, 198), "r", maxw=W - 170, align="center", lh=1.45)
            badge = Image.new("RGBA", (150, 150), (0, 0, 0, 0)); bd = ImageDraw.Draw(badge)
            bd.ellipse([6, 6, 144, 144], fill=ACC + (255,), outline=(255, 255, 255, 255), width=5)
            f = font(70, "b"); s = str(i + 1); l, tt, r, bb = bd.textbbox((0, 0), s, font=f)
            bd.text((75 - (r - l) / 2 - l, 75 - (bb - tt) / 2 - tt), s, font=f, fill=(255, 255, 255, 255))
            self.it.append((card, ta, tb, badge, item_dur(a, b)))
        # cta
        self.cta = text_block(day["cta"], 80, TXT, "b", maxw=W - 160, align="center", lh=1.2)
        self.follow = text_block("تابع الحساب، نصيحة جديدة كل يوم", 46, ACC2, "m", maxw=W - 160, align="center")
        self.handle_big = text_block(HANDLE, 54, TXT, "m", align="center")
        # timeline
        self.bounds = [0, T_INTRO, T_INTRO + T_HOOK]
        for it in self.it: self.bounds.append(self.bounds[-1] + it[4])
        self.bounds.append(self.bounds[-1] + T_CTA)
        self.dur = self.bounds[-1]

    # ---------- helpers ----------
    def base(self, t, drift=1.0):
        ox = 120 + int(math.sin(t * 0.35) * 90 * drift); oy = 120 + int(math.cos(t * 0.27) * 90 * drift)
        return self.bg.crop((ox, oy, ox + W, oy + H))

    def chrome(self, cv, t, seg):
        d = ImageDraw.Draw(cv)
        paste(cv, self.logo_sm, 80, 110, anchor="tl")
        paste(cv, self.handle, 168, 116, 0.9, anchor="tl")
        paste(cv, self.tag, W - 80, 118)
        segs = len(self.bounds) - 2; gap = 10; sw = (W - 160 - (segs - 1) * gap) / segs
        for i in range(segs):
            x1 = W - 80 - i * (sw + gap); x0 = x1 - sw
            d.rounded_rectangle([x0, 230, x1, 238], 4, fill=(255, 255, 255, 50))
            a, b = self.bounds[i + 1], self.bounds[i + 2]
            k = clamp((t - a) / (b - a))
            if k > 0: d.rounded_rectangle([x1 - sw * k, 230, x1, 238], 4, fill=ACC + (255,))

    def fade(self, cv, lt, D, out=0.28, col=(0, 0, 0)):
        a = pr(lt, D - out, out)
        if a > 0: cv.alpha_composite(Image.new("RGBA", (W, H), col + (int(255 * eo(a)),)))

    # ---------- scenes ----------
    def intro(self, t):
        cv = Image.new("RGBA", (W, H), (8, 8, 12, 255))
        g = eo(pr(t, 0, 0.8))
        bgc = self.base(t, 0.5); bgc.putalpha(int(255 * g * 0.9)); cv.alpha_composite(bgc)
        self.bok.draw(cv, t + 3, gain=1.6 * g)
        # flare sweep
        fx = -400 + (W + 800) * eo(pr(t, 0.15, 1.6))
        paste(cv, self.flare, fx, 760, 0.85 * (1 - pr(t, 1.4, 0.6)), anchor="c")
        k = back(pr(t, 0.25, 0.7))
        paste(cv, self.logo_big, W / 2, 620, eo(pr(t, 0.25, 0.4)), s=0.6 + 0.4 * k, anchor="c")
        # ring pulse
        rp = pr(t, 0.55, 0.9)
        if 0 < rp < 1:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            r = 150 + 260 * eo(rp)
            d.ellipse([W / 2 - r, 620 - r, W / 2 + r, 620 + r], outline=ACC2 + (int(200 * (1 - rp)),), width=6)
            cv.alpha_composite(lay)
        paste(cv, self.kicker, W / 2, 820, eo(pr(t, 0.6, 0.4)), anchor="c")
        ki = eo(pr(t, 0.9, 0.6))
        paste(cv, self.inspire, W / 2, 1010 + 40 * (1 - ki), ki, s=0.94 + 0.06 * ki, anchor="tc")
        paste(cv, self.daynum, W / 2, 1010 + self.inspire.height + 30, eo(pr(t, 1.3, 0.5)) * 0.9, anchor="tc")
        cv.alpha_composite(self.vig)
        # flash into hook
        fl = pr(t, T_INTRO - 0.22, 0.22)
        if fl > 0: cv.alpha_composite(Image.new("RGBA", (W, H), (255, 236, 210, int(255 * fl))))
        return cv

    def hook_scene(self, lt):
        cv = self.base(lt + 10)
        self.bok.draw(cv, lt + 10, 0.7)
        fl = 1 - pr(lt, 0, 0.35)
        k = eo(pr(lt, 0, 0.7))
        s = 1.08 - 0.08 * k + 0.025 * lt / T_HOOK
        paste(cv, self.hook_card, W / 2, 760 + 60 * (1 - k), k, s=s, anchor="c")
        kt = back(pr(lt, 0.35, 0.6))
        y = 1300
        paste(cv, self.hook_t, W / 2, y, eo(pr(lt, 0.35, 0.4)), s=0.85 + 0.15 * kt, anchor="tc")
        d = ImageDraw.Draw(cv); y2 = y + self.hook_t.height + 6
        w = 180 * eo(pr(lt, 0.8, 0.5)); d.rounded_rectangle([W / 2 - w, y2, W / 2 + w, y2 + 12], 6, fill=ACC + (255,))
        if self.sub_t: paste(cv, self.sub_t, W / 2, y2 + 40, eo(pr(lt, 1.0, 0.5)), anchor="tc")
        cv.alpha_composite(self.vig)
        self.chrome(cv, T_INTRO + lt, 1)
        if fl > 0: cv.alpha_composite(Image.new("RGBA", (W, H), (255, 236, 210, int(255 * fl))))
        self.fade(cv, lt, T_HOOK)
        return cv

    def item_scene(self, i, lt, tg):
        card, ta, tb, badge, D = self.it[i]
        cv = self.base(tg)
        self.bok.draw(cv, tg, 0.6)
        fi = 1 - pr(lt, 0, 0.3)
        k = eo(pr(lt, 0, 0.6))
        dirx = 1 if i % 2 == 0 else -1
        s = 1.0 + 0.05 * lt / D
        cx = W / 2 + dirx * 140 * (1 - k); cy = 690 + math.sin(lt * 1.3) * 6
        paste(cv, card, cx, cy, k, s=s, anchor="c")
        kb = back(pr(lt, 0.3, 0.5))
        if kb > 0.02: paste(cv, badge, cx + 270 * s, cy + 270 * s, eo(pr(lt, 0.3, 0.3)), s=max(0.05, kb), anchor="c")
        y = 1100
        k1 = eo(pr(lt, 0.35, 0.45))
        paste(cv, ta, W / 2, y + 40 * (1 - k1), k1, anchor="tc")
        y2 = y + ta.height
        d = ImageDraw.Draw(cv); w = 110 * eo(pr(lt, 0.6, 0.4))
        d.rounded_rectangle([W / 2 - w, y2, W / 2 + w, y2 + 9], 5, fill=ACC2 + (255,))
        k2 = eo(pr(lt, 0.75, 0.5))
        paste(cv, tb, W / 2, y2 + 30 + 30 * (1 - k2), k2, anchor="tc")
        cv.alpha_composite(self.vig)
        self.chrome(cv, tg, 2 + i)
        if fi > 0: cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fi))))
        self.fade(cv, lt, D)
        return cv

    def cta_scene(self, lt, tg):
        cv = self.base(tg)
        self.bok.draw(cv, tg, 1.0)
        fi = 1 - pr(lt, 0, 0.3)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ks = back(pr(lt, 0, 0.5)); ka = eo(pr(lt, 0, 0.35))
        for cx, fn in [(W / 2 + 150, ic_bookmark), (W / 2 - 150, ic_send)]:
            r = 105 * ks
            ld.ellipse([cx - r, 560 - r, cx + r, 560 + r], fill=CARD + (int(240 * ka),), outline=ACC + (int(255 * ka),), width=5)
            if ks > 0.3: fn(ld, cx, 560, 105 * ks, ACC + (int(255 * ka),), 9)
        cv.alpha_composite(lay)
        k = eo(pr(lt, 0.3, 0.5))
        paste(cv, self.cta, W / 2, 780 + 40 * (1 - k), k, anchor="tc")
        y = 780 + self.cta.height + 20
        paste(cv, self.follow, W / 2, y, eo(pr(lt, 0.7, 0.5)), anchor="tc")
        # logo outro
        kl = back(pr(lt, 1.3, 0.7))
        if kl > 0.02:
            paste(cv, self.logo_big, W / 2, 1450, eo(pr(lt, 1.3, 0.4)), s=0.45 * max(0.05, kl), anchor="c")
            paste(cv, self.handle_big, W / 2, 1560, eo(pr(lt, 1.6, 0.5)), anchor="tc")
        fx = -400 + (W + 800) * eo(pr(lt, 1.4, 1.4))
        paste(cv, self.flare, fx, 1450, 0.7 * (1 - pr(lt, 2.3, 0.5)), anchor="c")
        cv.alpha_composite(self.vig)
        if fi > 0: cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fi))))
        self.fade(cv, lt, T_CTA, 0.6)
        return cv

    def frame(self, t):
        b = self.bounds
        if t < b[1]: return self.intro(t)
        if t < b[2]: return self.hook_scene(t - b[1])
        for i in range(len(self.it)):
            if t < b[3 + i]: return self.item_scene(i, t - b[2 + i], t)
        return self.cta_scene(t - b[-2], t)


def load_day(n):
    plan = json.load(open(os.path.join(HERE, "plan.json")))
    return next(d for d in plan["days"] if d["day"] == n)


def render(day, out):
    c = Cine(day)
    base = os.path.join(out, f"day{day['day']:02d}_cine")
    wav = base + ".wav"; tmp = base + ".tmp.mp4"; fin = base + ".mp4"
    score.compose(wav, c.dur, T_INTRO, cuts=c.bounds[2:-1], seed=day["day"])
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                          "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                          "-shortest", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
    for i in range(int(round(c.dur * FPS))):
        p.stdin.write(c.frame(i / FPS).convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() != 0: raise SystemExit("ffmpeg failed")
    os.replace(tmp, fin); os.remove(wav)
    cov = base + "_cover.jpg"; c.frame(T_INTRO + 1.6).convert("RGB").save(cov, quality=92)
    return [fin, cov]


if __name__ == "__main__":
    if sys.argv[1] == "preview":
        day = load_day(int(sys.argv[2])); out = sys.argv[3] if len(sys.argv) > 3 else "/tmp"
        c = Cine(day)
        ts = [0.5, 1.6, 2.6, T_INTRO + 1.8, c.bounds[2] + 2.0, c.bounds[3] + 2.5, c.bounds[-2] + 1.2, c.bounds[-2] + 3.0]
        ims = [c.frame(t) for t in ts]
        sw = W // 3; sh = H // 3
        sheet = Image.new("RGB", (sw * 4, sh * 2))
        for k, im in enumerate(ims): sheet.paste(im.convert("RGB").resize((sw, sh)), ((k % 4) * sw, (k // 4) * sh))
        sheet.save(os.path.join(out, f"cine_day{day['day']:02d}.jpg"), quality=88)
        print(c.dur)
    else:
        n = int(sys.argv[1]); out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "out")
        os.makedirs(out, exist_ok=True)
        print("\n".join(render(load_day(n), out)))
