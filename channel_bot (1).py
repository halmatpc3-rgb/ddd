"""
بۆتی چەناڵی تیلیگرام
- هەواڵی تەکنەلۆجی بە کوردی (سۆرانی) + وێنە
- پۆستی بەرهەم و سیستەمەکان
- زیکر هەر 1 سەعات

دامەزراندن:
    pip install requests feedparser beautifulsoup4 deep-translator apscheduler

بەکارهێنان:
    export BOT_TOKEN="تۆکنە نوێیەکە"
    export CHAT_ID="@channel_username"   # یان -100xxxxxxxxxx
    export ANTHROPIC_API_KEY="کلیلی API"  # بۆ وەرگێڕانی AI
    python channel_bot.py
"""
import os, json, random, logging, html
import requests, feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from apscheduler.schedulers.blocking import BlockingScheduler

BOT_TOKEN = os.environ["9067863304:AAFPHJtin2RmLSiVfuRbFlGSo_nalYLAznw"]
CHAT_ID = os.environ["@r0nna1"]
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEEN_FILE = "seen.json"
logging.basicConfig(level=logging.INFO)

# ---------- سەرچاوەی هەواڵ (RSS) ----------
FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
]

# ---------- بەرهەمەکانت: خۆت دەستکاری بکە ----------
PRODUCTS = [
    {
        "title": "ناوی بەرهەم/سیستەم",
        "text": "کورتەیەک دەربارەی بەرهەمەکە و سوودەکانی.",
        "link": "https://example.com",
        "image": "",  # لینکی وێنە (ئارەزوومەندانە)
    },
]

# ---------- زیکر: خۆت زیاتری بکە ----------
ZIKR = [
    "سُبْحَانَ اللّٰهِ وَبِحَمْدِهِ، سُبْحَانَ اللّٰهِ الْعَظِيمِ",
    "لَا إِلٰهَ إِلَّا اللّٰهُ وَحْدَهُ لَا شَرِيكَ لَهُ",
    "أَسْتَغْفِرُ اللّٰهَ الْعَظِيمَ وَأَتُوبُ إِلَيْهِ",
    "لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللّٰهِ",
    "اللّٰهُمَّ صَلِّ وَسَلِّمْ عَلَىٰ نَبِيِّنَا مُحَمَّدٍ",
    "حَسْبِيَ اللّٰهُ لَا إِلٰهَ إِلَّا هُوَ عَلَيْهِ تَوَكَّلْتُ",
]


def load_seen():
    try:
        return set(json.load(open(SEEN_FILE)))
    except Exception:
        return set()


def save_seen(s):
    json.dump(list(s)[-2000:], open(SEEN_FILE, "w"))


ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-5-5")

SYSTEM_PROMPT = """تۆ ئێدیتەری هەواڵی تەکنەلۆجیایت بۆ چەناڵێکی تیلیگرامی کوردی.
هەواڵی ئینگلیزی وەردەگریت و بە کوردیی سۆرانیی ڕەوان، سروشتی و ڕاست (بە ئەلفوبێی کوردی) دەینووسیتەوە.
یاساکان:
- وەرگێڕانی وشە بە وشە مەکە؛ مانا بگوازەرەوە بە شێوازێک کە کوردێکی ئاسایی بە ئاسانی تێی بگات.
- ناوی کۆمپانیا و بەرهەم و کەسەکان (Apple، ChatGPT، iPhone...) وەک خۆیان بە ئینگلیزی بهێڵەرەوە.
- زاراوە تەکنیکییەکان بە کوردییەکی ئاسان بنووسە و ئەگەر پێویست بوو وشە ئینگلیزییەکە لە کەوانەدا بنووسە.
- هیچ زانیارییەکی نوێ زیاد مەکە و هیچ شتێک مەگۆڕە لە ڕاستییەکان، ژمارە و بەروارەکان.
- بەرهەمی کۆتایی تەنها JSON بێت بەم شێوەیە و هیچی تر:
{"title": "سەردێڕی کورت و ڕاکێش", "body": "کورتەی هەواڵەکە لە 2 بۆ 4 ڕستە"}"""


def ai_news(title, summary):
    """سەردێڕ و کورتە بە AI دەنووسێتەوە. ئەگەر شکستی هێنا None دەگەڕێنێتەوە."""
    if not ANTHROPIC_KEY:
        return None
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": AI_MODEL, "max_tokens": 800, "system": SYSTEM_PROMPT,
                  "messages": [{"role": "user",
                                "content": f"Title: {title}\n\nSummary: {summary}"}]},
            timeout=60)
        r.raise_for_status()
        text = r.json()["content"][0]["text"].strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        d = json.loads(text)
        return d["title"], d["body"]
    except Exception as e:
        logging.warning("AI translate failed: %s", e)
        return None


def tr(text):
    """پلانی یەدەگ: Google Translate"""
    try:
        return GoogleTranslator(source="auto", target="ckb").translate(text[:4500])
    except Exception as e:
        logging.warning("translate failed: %s", e)
        return None


def get_image(entry):
    for m in entry.get("media_content", []) + entry.get("media_thumbnail", []):
        if m.get("url"):
            return m["url"]
    for l in entry.get("links", []):
        if l.get("type", "").startswith("image"):
            return l["href"]
    try:  # og:image وەک پلانی دووەم
        r = requests.get(entry.link, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        og = BeautifulSoup(r.text, "html.parser").find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
    except Exception:
        pass
    return None


def send(caption, image=None):
    caption = caption[:1020] if image else caption[:4000]
    if image:
        r = requests.post(f"{API}/sendPhoto", data={
            "chat_id": CHAT_ID, "photo": image,
            "caption": caption, "parse_mode": "HTML"}, timeout=30)
        if r.ok:
            return True
        logging.warning("photo failed, sending text: %s", r.text)
    r = requests.post(f"{API}/sendMessage", data={
        "chat_id": CHAT_ID, "text": caption,
        "parse_mode": "HTML", "disable_web_page_preview": False}, timeout=30)
    if not r.ok:
        logging.error(r.text)
    return r.ok


def post_news():
    seen = load_seen()
    for url in FEEDS:
        for e in feedparser.parse(url).entries[:5]:
            if e.link in seen:
                continue
            summary = BeautifulSoup(e.get("summary", ""), "html.parser").get_text()[:1200]
            result = ai_news(e.title, summary)
            if result:
                title, body = result
            else:  # پلانی یەدەگ
                title = tr(e.title)
                body = tr(summary[:600]) if summary else ""
            if not title:
                continue
            caption = (f"📰 <b>{html.escape(title)}</b>\n\n{html.escape(body or '')}\n\n"
                       f"🔗 <a href=\"{e.link}\">سەرچاوە</a>")
            if send(caption, get_image(e)):
                seen.add(e.link)
                save_seen(seen)
                return  # هەر جارێک یەک هەواڵ
    logging.info("هەواڵی نوێ نییە")


_pi = {"i": 0}


def post_product():
    p = PRODUCTS[_pi["i"] % len(PRODUCTS)]
    _pi["i"] += 1
    caption = (f"🚀 <b>{html.escape(p['title'])}</b>\n\n{html.escape(p['text'])}\n\n"
               f"🔗 {p['link']}")
    send(caption, p.get("image") or None)


def post_zikr():
    send(f"🤲 <b>زیکر</b>\n\n{random.choice(ZIKR)}")


if __name__ == "__main__":
    sch = BlockingScheduler(timezone="Asia/Baghdad")
    sch.add_job(post_zikr, "interval", hours=1)
    sch.add_job(post_news, "interval", minutes=45)
    sch.add_job(post_product, "interval", hours=6)
    post_news()
    sch.start()
