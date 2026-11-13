import json, sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import numpy as np

W, H = 1080, 1920
ACC = (255, 92, 54); ACC2 = (255, 194, 75); TXT = (250, 246, 240)
F = {"xb": "fonts/Tajawal-ExtraBold.ttf", "b": "fonts/Tajawal-Bold.ttf",
     "m": "fonts/Tajawal-Medium.ttf", "r": "fonts/Tajawal-Regular.ttf"}
_c = {}
def font(s, w):
    k = (s, w)
    if k not in _c: _c[k] = ImageFont.truetype(F[w], s, layout_engine=ImageFont.Layout.RAQM)
    return _c[k]

def wrap(t, f, mw):
    out, cur = [], ""
    for w in t.split():
        c = (cur + " " + w).strip()
        if f.getlength(c) <= mw or not cur: cur = c
        else: out.append(cur); cur = w
    if cur: out.append(cur)
    return out

def grade(im):
    im = ImageEnhance.Contrast(im).enhance(1.08)
    im = ImageEnhance.Color(im).enhance(1.06)
    a = np.asarray(im).astype(np.float32)
    a[..., 0] *= 1.03; a[..., 2] *= 0.97          # warm touch
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def gradient(top_a, bot_start, bot_a):
    y = np.arange(H, dtype=np.float32)[:, None]
    top = np.clip(1 - y / 380, 0, 1) * top_a
    bot = np.clip((y - bot_start) / (H - bot_start), 0, 1) ** 1.15 * bot_a
    al = np.maximum(top, bot).repeat(W, 1)
    g = np.zeros((H, W, 4), np.uint8); g[..., 3] = al.astype(np.uint8)
    return Image.fromarray(g, "RGBA")

def render(s, out):
    im = grade(Image.open(s["img"]).convert("RGB").resize((W, H)))
    cv = im.convert("RGBA")
    cv = Image.alpha_composite(cv, gradient(140, s.get("gstart", 760), 238))
    tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(tl)
    R = W - 80; maxw = W - 160
    # measure block (bottom-anchored above IG reply bar)
    fh, fb = font(84, "xb"), font(44, "m")
    hl = wrap(s["head"], fh, maxw); bl = wrap(s["body"], fb, maxw)
    hstep, bstep = 100, 64
    block = 86 + len(hl) * hstep + 34 + len(bl) * bstep
    y = 1610 - block
    # tag pill
    ft = font(38, "b"); tw = ft.getlength(s["tag"])
    d.rounded_rectangle((R - tw - 56, y, R, y + 64), 32, fill=ACC)
    d.text((R - 28, y + 32), s["tag"], font=ft, fill=(255, 255, 255), anchor="rm")
    y += 86
    # accent bar
    for i, l in enumerate(hl):
        d.text((R, y + i * hstep), l, font=fh, fill=TXT, anchor="ra",
               stroke_width=0)
    y += len(hl) * hstep + 10
    d.rounded_rectangle((R - 120, y, R, y + 8), 4, fill=ACC2)
    y += 34
    for i, l in enumerate(bl):
        d.text((R, y + i * bstep), l, font=fb, fill=(232, 228, 222), anchor="ra")
    # top brand
    fbr = font(36, "b")
    d.text((R, 150), "@l0__ol3", font=fbr, fill=(255, 255, 255), anchor="ra")
    d.text((80, 150), "نصائح صناعة المحتوى", font=font(34, "m"), fill=(255, 255, 255, 220), anchor="la")
    # bottom cta
    fc = font(36, "m")
    d.text((W / 2, 1712), s.get("cta", "تابع الحساب لنصيحة جديدة كل يوم"), font=fc,
           fill=(255, 255, 255, 210), anchor="mm")
    a = tl.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.75))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 255)); sh.putalpha(a)
    cv = Image.alpha_composite(Image.alpha_composite(cv, sh), tl)
    cv.convert("RGB").save(out, quality=92, optimize=True, progressive=True)

if __name__ == "__main__":
    S = json.load(open("stories.json"))
    for s in S: render(s, f"out/{s['id']}.jpg")
    print("ok", len(S))
