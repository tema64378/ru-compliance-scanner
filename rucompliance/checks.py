"""Эвристический детект признаков на странице (пассивно, по HTML)."""

import re
from urllib.parse import urlparse, urljoin

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
AD_RE = re.compile(r"\bреклам", re.I)
ERID_RE = re.compile(r"\berid\b", re.I)
# обязательные смысловые блоки политики обработки ПДн
POLICY_REQ_RE = re.compile(r"(цел\w+\s+обработк|оператор|субъект\w*\s+персональн|права\s+субъект)", re.I)


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

    # политика — ищем по ссылкам (текст или href), запоминаем абсолютный URL
    policy_link = None
    policy_url = None
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        hay = (a.get_text(" ", strip=True) or "") + " " + href
        if POLICY_RE.search(hay):
            policy_link = (href or a.get_text(" ", strip=True))[:120]
            if href:
                policy_url = urljoin(url, href)
            break

    checkbox = soup.find("input", attrs={"type": "checkbox"}) is not None
    consent = bool(CONSENT_RE.search(text)) and (checkbox or policy_link is not None)

    cookie_mention = bool(COOKIE_RE.search(text))
    cookie_banner = cookie_mention and bool(COOKIE_CONSENT_RE.search(text))

    return {
        "has_pd_form": has_pd_form,
        "policy_link": policy_link,
        "policy_url": policy_url,
        "consent": consent,
        "checkbox": checkbox,
        "cookie_mention": cookie_mention,
        "cookie_banner": cookie_banner,
        "https": urlparse(url).scheme == "https",
        "requisites": bool(INN_RE.search(text) or OGRN_RE.search(text)),
        "age_mark": bool(AGE_RE.search(text)),
        "ad_mention": bool(AD_RE.search(text)),
        "erid": bool(ERID_RE.search(text)),
    }


def check_http_redirect(url):
    """Проверяет, что http://host принудительно редиректит на https. -> bool|None."""
    host = urlparse(normalize_url(url)).hostname
    if not host:
        return None
    try:
        r = requests.get(f"http://{host}", headers={"User-Agent": UA},
                         timeout=TIMEOUT, allow_redirects=True)
        return r.url.lower().startswith("https://")
    except Exception:
        return None


def fetch_policy(policy_url):
    """Заходит по ссылке на политику и проверяет: открывается ли и есть ли
    обязательные смысловые блоки. -> dict."""
    try:
        r = requests.get(policy_url, headers={"User-Agent": UA},
                         timeout=TIMEOUT, allow_redirects=True)
    except Exception as e:
        return {"reachable": False, "has_required": False, "error": str(e)}
    text = BeautifulSoup(r.text or "", "html.parser").get_text(" ", strip=True)
    return {
        "reachable": r.status_code == 200 and len(text) > 200,
        "has_required": bool(POLICY_REQ_RE.search(text)),
        "status": r.status_code,
    }
