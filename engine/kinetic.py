"""Kinetic-text reel in the 'UI motion graphics' style:
dark grid bg, two-line karaoke text, UI cards, progress segments, comment-keyword CTA.
Usage: python3 kinetic.py <out.mp4> [preview]"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import score

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
BG = (11, 13, 17); CARD = (22, 25, 31); LINE = (44, 48, 58)
ACC = (255, 92, 54); ACC2 = (255, 194, 75); GOOD = (72, 214, 160); BAD = (236, 84, 84)
TXT = (246, 242, 236); DIM = (96, 98, 106); MUT = (150, 150, 158)
_fc = {}
def font(s, w="Bold"):
    k = (s, w)
    if k not in _fc: _fc[k] = ImageFont.truetype(os.path.join(HERE, "fonts", f"Tajawal-{w}.ttf"), s, layout_engine=ImageFont.Layout.RAQM)
    return _fc[k]
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def eo(t): t = clamp(t); return 1 - (1 - t) ** 3
def back(t): t = clamp(t); c = 1.7; return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def mix(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

# ---------- scenes: (dur, line1, line2, key words, visual)
SC = [
 (3.0, "إذا فيديوك ينسحب", "بأول 3 ثواني", ["3"], "cards"),
 (2.2, "المشكلة مو بالمحتوى", "المشكلة بأول جملة", ["أول", "جملة"], "cards_dim"),
 (1.8, "شوف", "هالطريقة", [], "arrow"),
 (3.0, "جمعتلك 50 هوك", "جاهز بالعراقي", ["50", "هوك"], "counter"),
 (3.6, "مقسمة على 10 أنواع", "حسب فكرة فيديوك", ["10"], "grid"),
 (4.4, "تنسخ الهوك", "وتبدّل بس مجالك", ["مجالك"], "template"),
 (3.4, "وياه طريقة الاستخدام", "خطوة بخطوة", [], "checks"),
 (3.6, "علّق كلمة", "«هوك»", ["«هوك»"], "comment"),
 (3.2, "وأرسلك الملف", "عالخاص", ["عالخاص"], "dm"),
 (2.4, "", "", [], "outro"),
]
STARTS = np.cumsum([0] + [s[0] for s in SC])
DUR = float(STARTS[-1])

def make_bg():
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    for x in range(0, W, 54): d.line([(x, 0), (x, H)], fill=(17, 20, 25))
    for y in range(0, H, 54): d.line([(0, y), (W, y)], fill=(17, 20, 25))
    return im.convert("RGBA")
BGI = make_bg()
_gc = {}
def glow(cx, cy, r, col, a):
    k = (r, col, a)
    if k not in _gc:
        g = Image.new("L", (r * 2, r * 2), 0); m = r * 0.45
        ImageDraw.Draw(g).ellipse((m, m, r * 2 - m, r * 2 - m), fill=int(255 * a))
        g = g.filter(ImageFilter.GaussianBlur(r / 4))
        lay = Image.new("RGBA", (r * 2, r * 2), col + (0,)); lay.putalpha(g); _gc[k] = lay
    return _gc[k], (int(cx - r), int(cy - r))

# ---------- karaoke line (RTL, word by word)
def kline(d, text, cy, size, t, keys, base_lit=False):
    """t: 0..1 progress of word reveal. Returns nothing; draws centered RTL."""
    if not text: return
    f = font(size, "ExtraBold"); words = text.split(); sp = f.getlength(" ")
    ws = [f.getlength(w) for w in words]; tot = sum(ws) + sp * (len(words) - 1)
    x = W / 2 + tot / 2
    n = len(words)
    for i, w in enumerate(words):
        lit = 1.0 if base_lit else clamp(t * (n + 0.6) - i)
        iskey = w in keys
        if iskey and lit > 0:
            pad = 16; a = eo(lit)
            d.rounded_rectangle((x - ws[i] - pad, cy - size * 0.62, x - ws[i] + (ws[i] + 2 * pad) * a - pad, cy + size * 0.6), 14,
                                fill=mix(BG, ACC, a))
        col = mix(DIM, TXT, eo(lit)) if not iskey else mix(DIM, (255, 255, 255), eo(lit))
        d.text((x, cy), w, font=f, fill=col, anchor="rm")
        x -= ws[i] + sp

# ---------- UI pieces
def retention_card(cv, x, y, w, h, good, prog, views, alpha=1.0, label=""):
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 26, fill=CARD + (255,), outline=LINE + (255,), width=2)
    col = GOOD if good else BAD
    d.text((w - 30, 28), "مدة المشاهدة", font=font(28, "Medium"), fill=MUT, anchor="ra")
    tag = "ينتشر" if good else "يطيح"; ft = font(26, "Bold"); tw = ft.getlength(tag)
    d.rounded_rectangle((30, 22, 30 + tw + 34, 66), 22, fill=mix(CARD, col, 0.22))
    d.text((30 + 17 + tw / 2, 44), tag, font=ft, fill=col, anchor="mm")
    gx0, gx1, gy0, gy1 = 30, w - 30, 90, h - 80
    pts = []
    N = 60
    for k in range(int(N * prog) + 1):
        u = k / N
        v = 1 - 0.28 * u if good else math.exp(-4.2 * u) * 0.92 + 0.06
        pts.append((gx0 + (gx1 - gx0) * u, gy1 - (gy1 - gy0) * v))
    if len(pts) > 1:
        poly = pts + [(pts[-1][0], gy1), (pts[0][0], gy1)]
        d.polygon(poly, fill=mix(CARD, col, 0.18) + (255,))
        d.line(pts, fill=col + (255,), width=5)
    d.text((w - 30, h - 44), f"{int(views * eo(prog)):,} مشاهدة", font=font(30, "Bold"), fill=TXT, anchor="rm")
    if label: d.text((30, h - 44), label, font=font(24, "Regular"), fill=DIM, anchor="lm")
    if alpha < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    cv.alpha_composite(lay, (int(x), int(y)))

CATS = ["السؤال", "الرقم", "الخطأ الشائع", "قبل وبعد", "السر", "التحدي", "القصة", "المقارنة", "التحذير", "النتيجة أولاً"]

def visual(cv, d, kind, lt, D):
    p = lt / D
    if kind in ("cards", "cards_dim"):
        a = 1.0 if kind == "cards" else 1 - 0.45 * eo(lt / 0.6)
        if kind == "cards":
            s1 = eo(lt / 0.5); s2 = eo((lt - 0.25) / 0.5)
            retention_card(cv, 110 + (1 - s1) * 200, 640, 860, 330, True, clamp((lt - 0.2) / 1.6), 38240, s1, "مثال")
            retention_card(cv, 110 + (1 - s2) * 200, 1010, 860, 330, False, clamp((lt - 0.4) / 1.6), 1912, s2, "مثال")
        else:
            retention_card(cv, 110, 640, 860, 330, True, 1, 38240, a, "مثال")
            sh = math.sin(lt * 40) * 10 * clamp(1 - lt / 0.7)
            retention_card(cv, 110 + sh, 1010, 860, 330, False, 1, 1912, 1.0, "مثال")
    elif kind == "arrow":
        for k in range(3):
            ph = (lt * 1.6 - k * 0.25) % 1.0
            y = 760 + k * 90 + ph * 40; al = math.sin(ph * math.pi)
            c = mix(BG, ACC, al)
            d.line([(W / 2 - 60, y), (W / 2, y + 60), (W / 2 + 60, y)], fill=c, width=14, joint="curve")
    elif kind == "counter":
        s = back(lt / 0.6)
        cw, ch = int(620 * max(s, 0.01)), int(560 * max(s, 0.01))
        if s > 0.02:
            x0, y0 = W / 2 - cw / 2, 1000 - ch / 2
            d.rounded_rectangle((x0, y0, x0 + cw, y0 + ch), 36, fill=CARD, outline=LINE, width=2)
            if s > 0.9:
                n = int(50 * eo((lt - 0.4) / 1.4))
                d.text((W / 2, 960), str(n), font=font(260, "ExtraBold"), fill=ACC2, anchor="mm")
                d.text((W / 2, 1140), "هوك جاهز", font=font(56, "Bold"), fill=TXT, anchor="mm")
                ft = font(30, "Bold"); tg = "ملف مجاني"; tw = ft.getlength(tg)
                d.rounded_rectangle((W / 2 - tw / 2 - 24, y0 + 36, W / 2 + tw / 2 + 24, y0 + 86), 25, fill=ACC)
                d.text((W / 2, y0 + 61), tg, font=ft, fill=(255, 255, 255), anchor="mm")
    elif kind == "grid":
        cw, ch, gx, gy = 400, 130, 30, 26
        for i, c in enumerate(CATS):
            r, col = i // 2, i % 2
            a = back((lt - 0.15 * i) / 0.45)
            if a <= 0.01: continue
            x1 = W / 2 + gx / 2 + cw if col == 0 else W / 2 - gx / 2
            y0 = 600 + r * (ch + gy)
            w = cw * min(a, 1.08)
            d.rounded_rectangle((x1 - w, y0, x1, y0 + ch), 24, fill=CARD, outline=LINE, width=2)
            if a > 0.6:
                d.text((x1 - 28, y0 + ch / 2), c, font=font(42, "Bold"), fill=TXT, anchor="rm")
                d.text((x1 - w + 30, y0 + ch / 2), "×5", font=font(36, "ExtraBold"), fill=ACC2, anchor="lm")
    elif kind == "template":
        s = eo(lt / 0.5)
        x0, y0, x1, y1 = 90, 720, 990, 1180
        d.rounded_rectangle((x0, y0 + (1 - s) * 80, x1, y1 + (1 - s) * 80), 32, fill=CARD, outline=LINE, width=2)
        if s > 0.8:
            d.text((x1 - 40, y0 + 50), "هوك رقم 06", font=font(30, "Medium"), fill=MUT, anchor="ra")
            opts = ["[مجالك]", "الطبخ", "التصوير", "الرياضة"]
            k = min(3, int(max(0, lt - 1.0) / 0.85) + (1 if lt > 1.0 else 0)) if lt > 1.0 else 0
            word = opts[k]
            f = font(64, "ExtraBold")
            parts = [("3 أخطاء بمجال", TXT), (word, ACC2 if k == 0 else (255, 255, 255))]
            line2 = "تخسرك من أول يوم"
            sp = f.getlength(" "); ws = [f.getlength(t) for t, _ in parts]; tot = sum(ws) + sp * (len(parts) - 1)
            x = W / 2 + tot / 2; cy = y0 + 210
            for (t_, c_), w_ in zip(parts, ws):
                if t_ == word:
                    d.rounded_rectangle((x - w_ - 14, cy - 44, x + 14, cy + 44), 14, fill=ACC if k else mix(CARD, ACC2, 0.18))
                d.text((x, cy), t_, font=f, fill=c_, anchor="rm"); x -= w_ + sp
            d.text((W / 2, cy + 110), line2, font=f, fill=TXT, anchor="mm")
            # cursor blink
            if int(lt * 3) % 2 == 0: d.rectangle((W / 2 - 3, cy + 175, W / 2 + 3, cy + 215), fill=ACC)
    elif kind == "checks":
        items = ["الهوك جاهز تنسخه", "مقسّم حسب نوع الفيديو", "طريقة الاستخدام بأول صفحة"]
        for i, it in enumerate(items):
            a = eo((lt - 0.3 - i * 0.45) / 0.4)
            if a <= 0: continue
            y = 700 + i * 170; x1 = 960 + (1 - a) * 120
            d.rounded_rectangle((120 + (1 - a) * 120, y, x1, y + 130), 26, fill=CARD, outline=LINE, width=2)
            d.ellipse((x1 - 100, y + 33, x1 - 36, y + 97), fill=GOOD)
            d.line([(x1 - 86, y + 66), (x1 - 72, y + 80), (x1 - 50, y + 52)], fill=BG, width=8)
            d.text((x1 - 130, y + 65), it, font=font(44, "Bold"), fill=TXT, anchor="rm")
    elif kind == "comment":
        s = eo(lt / 0.5)
        x0, y0, x1, y1 = 110, 700 + (1 - s) * 80, 970, 1280 + (1 - s) * 80
        d.rounded_rectangle((x0, y0, x1, y1), 32, fill=CARD, outline=LINE, width=2)
        d.text((W / 2, y0 + 55), "التعليقات", font=font(36, "Bold"), fill=TXT, anchor="mm")
        d.line([(x0, y0 + 100), (x1, y0 + 100)], fill=LINE, width=2)
        rows = [("sara.creates", "مفيد جداً"), ("ali_vlogs", "هوك"), ("you", None)]
        for i, (u, c) in enumerate(rows):
            yy = y0 + 150 + i * 120
            d.ellipse((x1 - 110, yy, x1 - 40, yy + 70), fill=[(70, 90, 140), (120, 80, 60), ACC][i])
            d.text((x1 - 135, yy + 18), u if u != "you" else "أنت", font=font(28, "Medium"), fill=MUT, anchor="ra")
            if c: d.text((x1 - 135, yy + 50), c, font=font(36, "Bold"), fill=TXT, anchor="ra")
        # typing "هوك" in input
        yy = y1 - 120
        d.rounded_rectangle((x0 + 30, yy, x1 - 30, yy + 84), 42, fill=(30, 34, 42), outline=LINE, width=2)
        typed = "هوك"[:max(0, min(3, int((lt - 0.9) / 0.25)))]
        d.text((x1 - 70, yy + 42), typed if typed else "أضف تعليق...", font=font(38, "Bold" if typed else "Regular"),
               fill=TXT if typed else DIM, anchor="rm")
        if lt > 2.0:
            a = eo((lt - 2.0) / 0.3)
            d.rounded_rectangle((x0 + 50, yy + 12, x0 + 50 + 140 * a, yy + 72), 30, fill=ACC)
            if a > 0.8: d.text((x0 + 120, yy + 42), "نشر", font=font(32, "Bold"), fill=(255, 255, 255), anchor="mm")
    elif kind == "dm":
        x0, x1 = 110, 970
        d.rounded_rectangle((x0, 680, x1, 1300), 32, fill=CARD, outline=LINE, width=2)
        d.ellipse((x1 - 100, 715, x1 - 40, 775), fill=ACC)
        d.text((x1 - 120, 745), "l0__ol3", font=font(32, "Bold"), fill=TXT, anchor="rm")
        d.line([(x0, 800), (x1, 800)], fill=LINE, width=2)
        a1 = eo((lt - 0.2) / 0.35); a2 = eo((lt - 0.9) / 0.35)
        if a1 > 0:  # user bubble (left = them? keep: user's comment on right)
            d.rounded_rectangle((x1 - 40 - 200 * a1, 840, x1 - 40, 920), 36, fill=(44, 48, 58))
            if a1 > 0.8: d.text((x1 - 80, 880), "هوك", font=font(36, "Bold"), fill=TXT, anchor="rm")
        if a2 > 0:
            bw = 640 * a2
            d.rounded_rectangle((x0 + 40, 960, x0 + 40 + bw, 1200), 36, fill=ACC)
            if a2 > 0.85:
                d.text((x0 + 40 + bw - 36, 1010), "تفضل، هذا ملف 50 هوك", font=font(36, "Bold"), fill=(255, 255, 255), anchor="ra")
                d.rounded_rectangle((x0 + 76, 1060, x0 + 40 + bw - 36, 1164), 22, fill=(255, 255, 255))
                d.rounded_rectangle((x0 + 100, 1080, x0 + 160, 1144), 10, fill=ACC)
                d.text((x0 + 130, 1112), "PDF", font=font(22, "Bold"), fill=(255, 255, 255), anchor="mm")
                d.text((x0 + 40 + bw - 70, 1112), "50 هوك جاهز", font=font(34, "Bold"), fill=BG, anchor="rm")
    elif kind == "outro":
        s = back(lt / 0.6)
        r = int(120 * max(s, 0.01))
        d.rounded_rectangle((W / 2 - r, 820 - r, W / 2 + r, 820 + r), int(r * 0.32), fill=ACC)
        if s > 0.8:
            d.text((W / 2, 820), "l0", font=font(120, "ExtraBold"), fill=(255, 255, 255), anchor="mm")
            d.text((W / 2, 1030), "@l0__ol3", font=font(52, "Bold"), fill=TXT, anchor="mm", direction="ltr")
            d.text((W / 2, 1100), "نصيحة صناعة محتوى كل يوم", font=font(36, "Medium"), fill=MUT, anchor="mm")

def frame(t):
    i = int(np.searchsorted(STARTS, t, side="right") - 1); i = min(i, len(SC) - 1)
    D, l1, l2, keys, kind = SC[i]; lt = t - STARTS[i]
    cv = BGI.copy()
    gx = W * (0.75 + 0.1 * math.sin(t * 0.4)); gy = 980 + 120 * math.sin(t * 0.3)
    g, pos = glow(gx, gy, 600, ACC, 0.22); cv.alpha_composite(g, pos)
    d = ImageDraw.Draw(cv)
    # top chrome: handle left, progress segments right
    d.text((70, 120), "@l0__ol3", font=font(32, "Bold"), fill=MUT, anchor="lm", direction="ltr")
    nseg = len(SC) - 1
    for k in range(nseg):
        x1 = W - 70 - k * 34
        on = k < i or (k == i)
        c = ACC if k == i else (mix(BG, ACC, 0.45) if k < i else (34, 37, 44))
        d.rounded_rectangle((x1 - 24, 108, x1, 132), 5, fill=c)
    # text
    in1 = clamp(lt / 0.55); in2 = clamp((lt - 0.45) / 0.7)
    if kind == "arrow":
        kline(d, l1, 470, 110, in1, keys); kline(d, l2, 600, 110, in2, keys)
    else:
        kline(d, l1, 330, 80, in1, keys); kline(d, l2, 440, 80, in2, keys)
    visual(cv, d, kind, lt, D)
    # scene fade in/out
    fi = clamp(lt / 0.12); fo = clamp((D - lt) / 0.12) if i < len(SC) - 1 else clamp((D - lt) / 0.5)
    a = min(fi, fo)
    if a < 1:
        blk = Image.new("RGBA", (W, H), BG + (int(255 * (1 - a)),)); cv.alpha_composite(blk)
    return cv.convert("RGB")

def render(out):
    wav = out + ".wav"
    score.compose(wav, DUR, 0.5, cuts=list(STARTS[1:-1]), seed=3, outro=2.4)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                          "-crf", "19", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                          "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for k in range(int(round(DUR * FPS))): p.stdin.write(frame(k / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0: raise SystemExit("ffmpeg failed")
    os.remove(wav)
    frame(STARTS[3] + 2.4).save(out.replace(".mp4", "_cover.jpg"), quality=92)

if __name__ == "__main__":
    out = sys.argv[1]
    if len(sys.argv) > 2:
        ts = [0.15, 1.6, 2.9, STARTS[1] + 1.5, STARTS[2] + 1.0, STARTS[3] + 2.4, STARTS[4] + 2.8, STARTS[5] + 0.6,
              STARTS[5] + 2.0, STARTS[6] + 2.5, STARTS[7] + 2.6, STARTS[8] + 2.0, STARTS[9] + 1.2]
        sw, sh = W // 4, H // 4
        sheet = Image.new("RGB", (sw * 5, sh * 3))
        for k, tt in enumerate(ts): sheet.paste(frame(tt).resize((sw, sh)), ((k % 5) * sw, (k // 5) * sh))
        sheet.save(out, quality=88); print(DUR)
    else:
        render(out); print(out, DUR)
