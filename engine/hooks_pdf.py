import json, os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")
W, H = 1240, 1754
BG = (14, 14, 18); CARD = (26, 26, 32); ACC = (255, 92, 54); ACC2 = (255, 194, 75)
TXT = (245, 240, 232); MUT = (150, 146, 140)
_c = {}
def font(s, w="Bold"):
    k = (s, w)
    if k not in _c: _c[k] = ImageFont.truetype(os.path.join(FD, f"Tajawal-{w}.ttf"), s, layout_engine=ImageFont.Layout.RAQM)
    return _c[k]
def wrap(t, f, mw):
    out, cur = [], ""
    for w in t.split():
        c = (cur + " " + w).strip()
        if f.getlength(c) <= mw or not cur: cur = c
        else: out.append(cur); cur = w
    if cur: out.append(cur)
    return out
def page():
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.text((90, 90), "@l0__ol3", font=font(34, "Bold"), fill=MUT, anchor="la")
    return im, d
def foot(d, n, tot):
    d.text((W / 2, H - 70), f"{n} / {tot}", font=font(28, "Medium"), fill=MUT, anchor="mm")

D = json.load(open(os.path.join(HERE, "hooks50.json")))
pages = []
im, d = page()
d.text((W - 110, 560), D["title"], font=font(150, "ExtraBold"), fill=TXT, anchor="ra")
d.rounded_rectangle((W - 110 - 220, 760, W - 110, 774), 7, fill=ACC)
d.text((W - 110, 820), D["subtitle"], font=font(54, "Medium"), fill=ACC2, anchor="ra")
y = 1060
d.text((W - 110, y), "شلون تستخدم الملف", font=font(48, "Bold"), fill=TXT, anchor="ra"); y += 90
for i, s in enumerate(D["how"]):
    d.ellipse((W - 160, y + 2, W - 110, y + 52), fill=ACC)
    d.text((W - 135, y + 27), str(i + 1), font=font(32, "Bold"), fill=(255, 255, 255), anchor="mm")
    d.text((W - 190, y + 6), s, font=font(38, "Regular"), fill=TXT, anchor="ra"); y += 92
pages.append((im, d))
cats = D["cats"]; n = 0
for p in range(0, len(cats), 2):
    im, d = page(); y = 165
    for c in cats[p:p + 2]:
        d.rounded_rectangle((W - 110 - font(44, "Bold").getlength(c["name"]) - 60, y, W - 110, y + 76), 38, fill=ACC)
        d.text((W - 140, y + 38), c["name"], font=font(44, "Bold"), fill=(255, 255, 255), anchor="rm"); y += 110
        for h in c["hooks"]:
            n += 1
            f = font(40, "Medium"); ls = wrap(h, f, W - 340)
            ch = 40 + 54 * len(ls)
            d.rounded_rectangle((110, y, W - 110, y + ch), 22, fill=CARD)
            d.text((W - 150, y + 23 + 2), f"{n:02d}", font=font(36, "ExtraBold"), fill=ACC2, anchor="ra")
            for k, l in enumerate(ls):
                d.text((W - 230, y + 18 + k * 54), l, font=f, fill=TXT, anchor="ra")
            y += ch + 14
        y += 26
    pages.append((im, d))
tot = len(pages)
for i, (im, d) in enumerate(pages): foot(d, i + 1, tot)
out = sys.argv[1]
ims = [p[0] for p in pages]
ims[0].save(out, save_all=True, append_images=ims[1:], resolution=150)
for i, im in enumerate(ims): im.resize((W // 3, H // 3)).save(f"/tmp/hp{i}.jpg")
print(n, tot)
