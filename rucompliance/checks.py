"""Эвристический детект признаков на странице (пассивно, по HTML)."""

import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
TIMEOUT = 12

PD_FIELD_RE = re.compile(r"(e-?mail|mail|phone|tel|почт|телефон|имя|фамил|name)", re.I)
POLICY_RE = re.compile(r"(политик\w*\s+\w*\s*персональн|обработк\w+\s+персональн|"
                       r"персональн\w+\s+данн|privacy|/policy|/privacy|polit|конфиденциальн)", re.I)
CONSENT_RE = re.compile(r"(соглас\w+\s+на\s+обработк|даю\s+соглас|обработк\w+\s+персональн\w+\s+данн)", re.I)
COOKIE_RE = re.compile(r"(cookie|куки|файл\w*\s+cookie|кук-файл)", re.I)
COOKIE_CONSENT_RE = re.compile(r"(принять|принимаю|согласен|разрешить|accept|отклонить)", re.I)
INN_RE = re.compile(r"\bинн\b", re.I)
OGRN_RE = re.compile(r"\bогрн\b", re.I)
AGE_RE = re.compile(r"\b(0|6|12|16|18)\+")


def normalize_url(url):
    url = (url or "").strip()
    if "://" not in url:
        url = "https://" + url
    return url


def fetch(url):
    return requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)


def analyze(html, url):
    """Возвращает словарь признаков, найденных на странице."""
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(" ", strip=True)

    inputs = soup.find_all("input")
    forms = soup.find_all("form")

    def looks_pd(inp):
        t = (inp.get("type") or "").lower()
        attrs = " ".join(filter(None, [inp.get("name"), inp.get("id"),
                                        inp.get("placeholder"), inp.get("type")]))
        return t in ("email", "tel") or bool(PD_FIELD_RE.search(attrs))

    has_pd_form = any(looks_pd(i) for i in inputs) or any(
        any(looks_pd(i) for i in f.find_all("input")) for f in forms)

    # политика — ищем по ссылкам (текст или href)
    policy_link = None
    for a in soup.find_all("a"):
        hay = (a.get_text(" ", strip=True) or "") + " " + (a.get("href") or "")
        if POLICY_RE.search(hay):
            policy_link = (a.get("href") or a.get_text(" ", strip=True))[:120]
            break

    checkbox = soup.find("input", attrs={"type": "checkbox"}) is not None
    consent = bool(CONSENT_RE.search(text)) and (checkbox or policy_link is not None)

    cookie_mention = bool(COOKIE_RE.search(text))
    cookie_banner = cookie_mention and bool(COOKIE_CONSENT_RE.search(text))

    return {
        "has_pd_form": has_pd_form,
        "policy_link": policy_link,
        "consent": consent,
        "checkbox": checkbox,
        "cookie_mention": cookie_mention,
        "cookie_banner": cookie_banner,
        "https": urlparse(url).scheme == "https",
        "requisites": bool(INN_RE.search(text) or OGRN_RE.search(text)),
        "age_mark": bool(AGE_RE.search(text)),
    }
