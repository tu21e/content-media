"""
arabic.py - Arabic (Iraqi dialect first) support shared by hookscore.py,
beats.py, caption.py and swipe.py.

Everything here is a local heuristic, same spirit as the rest of the repo:
it lets the scripts count Arabic words, find concrete markers and tension
words in Arabic, and time spoken Arabic. It does not make the scores more
predictive than they were in English; it makes them stop being wrong.
"""
import re

AR_CHARS = "؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿"
AR_RE = re.compile(f"[{AR_CHARS}]")
LATIN_RE = re.compile(r"[A-Za-z]")
TASHKEEL_RE = re.compile(r"[ً-ٰٟـ]")   # harakat + tatweel
# One word: Arabic letters, Latin letters, digits (ASCII + Arabic-Indic), $ % ' -
WORD_RE = re.compile(f"[{AR_CHARS}A-Za-z0-9٠-٩۰-۹$%'’-]+")
INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# Spoken Arabic is slower in words per minute than English, because the words
# carry more (prefixes, suffixes, attached pronouns). Measured averages for
# Arabic speech sit around 120-160 wpm; reels run fast, so 150 is the default.
AR_WPM = 150


def is_arabic(text):
    a = len(AR_RE.findall(text))
    l = len(LATIN_RE.findall(text))
    return a > 0 and a >= l


def to_ascii_digits(text):
    return text.translate(INDIC)


def norm(token):
    """Lower-friction matching form: no harakat, unified alef/ya/ta-marbuta."""
    t = TASHKEEL_RE.sub("", token)
    t = re.sub("[أإآٱ]", "ا", t)
    t = t.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    t = t.replace("گ", "ك").replace("چ", "ج").replace("ڤ", "ف").replace("پ", "ب")
    return t.strip("'’-«»\"")


PREFIXES = ("وبال", "فبال", "وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "ك")


def stems(token):
    """The token plus the token with common clitic prefixes peeled off."""
    t = norm(token)
    out = {t}
    for p in PREFIXES:
        if t.startswith(p) and len(t) - len(p) >= 2:
            out.add(t[len(p):])
    return out


def lexicon(words):
    return {norm(w) for w in words}


def hit(token, lex):
    return bool(stems(token) & lex)


# --- lexicons ---------------------------------------------------------------
SPOKEN_NUMBERS = lexicon("""
صفر اثنين ثنين اثنان ثنتين اثنتين ثلاث ثلاثه ثلث اربع اربعه خمس خمسه ست سته
سبع سبعه ثمان ثمانيه تسع تسعه عشر عشره عشرين ثلاثين اربعين خمسين ستين سبعين
ثمانين تسعين ميه مية مئه مائه ميتين الف الاف آلاف مليون ملايين مليار نص نصف
ربع ضعف ضعفين دزينه
""".split())

MONEY = lexicon("""
دولار دولارات دينار دنانير ورقه ورقات فلوس مصاري ربح ارباح راتب رواتب ايجار
خساره خسائر سعر اسعار مجاني ببلاش بلاش مبيعات دخل
""".split())

TIME_UNITS = lexicon("ثانيه ثواني دقيقه دقايق دقائق ساعه ساعات يوم ايام اسبوع اسابيع شهر شهور اشهر سنه سنين سنوات".split())

STAKES = lexicon("""
خطا اخطاء غلط غلطه اغلاط خسر خسرت تخسر يخسر تخسرك يخسرك خساره ضيع ضيعت تضيع
يضيع لا ما مو مش محد ماكو ابدا ابداً بطل بطّل وقف توقف سر اسرار حيله تحذير انتبه
احذر اسوا اسوأ مشكله مشاكل بدون قبل لحد بدل بس فقط يموت تموت يطيح طاح ينسحب
يسحب تسحب فشل فشلت فاشل خطر غلطان حقيقه كذب كذبه محظور مقفول حذفت احذف ندمت
ندم تمنيت لازم ماتعرف ماتدري محدش اكثر اقل الافضل الاسوا الوحيد اول
""".split())

WEAK_OPENERS = [norm(w) for w in """
هلو هلا هاي مرحبا اهلا السلام شباب جماعه اليوم حبيت حابب راح خلوني خليني
طيب يعني بصراحه اسمعوا شوفوا بهالفيديو بهذا بهاي هذا هاي
""".split()]

IMPERATIVES = lexicon("""
وقف بطل جرب شوف احفظ انسخ اكتب سوي ابدا ابدي خلي اسمع لاتسوي لا امسح احذف
استخدم صور صوّر ارسل دز تعلم اترك غير بدل
""".split())

SECOND_PERSON = lexicon("انت انتي انتو انتم إنت إنتي إلك الك لك مالك عندك حسابك فيديوك محتواك".split())
FIRST_PERSON = lexicon("انا احنا نحن مالي عندي جربت سويت خسرت تعلمت اكتشفت كنت صرت بديت نزلت".split())

STOPWORDS = lexicon("""
في من على الى إلى عن مع هذا هذه هاي هذي هذاك ذلك اللي الذي التي هو هي هم انت انا
احنا و او أو بس ما لا مو كل شي شيء كان يكون راح يعني حتى اذا إذا لو بعد قبل عند
""".split())


NOT_YOU = lexicon("ذلك كذلك هنالك هناك ملك بنك شبابيك تكتك سمك شوك مسك".split())


def second_person(token):
    """Iraqi second person usually rides on the word: فيديوك، حسابك، تخسرك."""
    t = norm(token)
    if t in SECOND_PERSON:
        return True
    if t in NOT_YOU:
        return False
    return len(t) >= 4 and (t.endswith("ك") or t.endswith("كم"))


def first_person(token):
    t = norm(token)
    return t in FIRST_PERSON


# Openers and preambles that spend the first second on nothing.
DEALBREAKERS = [
    (re.compile(r"^\s*(?:وقف|لا\s*تسحب|لا\s*تطوف|لا\s*تكمل\s*سكرول)"),
     "يبدي بـ «وقف» أو «لا تسحب». طلب الانتباه يثبت إنك بعدك ما كسبته."),
    (re.compile(r"(?:بهالفيديو|بهذا\s*الفيديو|بهاي\s*الفيديو|بفيديو\s*اليوم|اليوم\s*راح\s*(?:احجي|احكي|اشرح|اعلمكم)|راح\s*اشرحلكم)"),
     "مقدمة فيديو. احذفها وابدي من النتيجة."),
    (re.compile(r"^\s*(?:هلو|هلا|هاي|مرحبا|اهلا|أهلا|السلام\s*عليكم|شلونكم)"),
     "تحية. محد فتح الإنستغرام حتى ينسلم عليه."),
]

# Asks inside a caption.
ASKS = [
    (re.compile(r"(?:علّ?ق|اكتب\s*بالتعليقات?)\s*(?:كلمة|كلمه)?\s*[«\"']?\S{2,}"), "comment a keyword"),
    (re.compile(r"(?:راسلني|دزلي|ارسلي|أرسلي|كلمني)\s*(?:بالخاص|عالخاص|خاص)"), "DM me"),
    (re.compile(r"\bاحفظ"), "save this"),
    (re.compile(r"(?:ارسله|أرسله|دزه|شاركه)"), "share this"),
    (re.compile(r"\bتابع"), "follow"),
    (re.compile(r"الرابط\s*(?:بالبايو|بالبروفايل)"), "link in bio"),
    (re.compile(r"(?:اسحب|سوايب)"), "swipe or tap"),
    (re.compile(r"(?:شنو|شلون|منو|اي|أي|ليش|وين|كم|شكد)[^؟?\n]{0,60}[؟?]"), "answer a question"),
]


def concrete_markers(text):
    """Numbers (ASCII or Arabic-Indic) and spoken Arabic numbers/money/time."""
    t = to_ascii_digits(text)
    nums = re.findall(r"\$\s?\d[\d,]*|\d[\d,.]*", t)
    toks = WORD_RE.findall(text)
    spoken = [w for w in toks if hit(w, SPOKEN_NUMBERS) or hit(w, MONEY)]
    return nums + spoken
