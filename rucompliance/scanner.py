"""Оркестратор: тянет страницу, прогоняет правила, считает потенциальный штраф."""

from rucompliance import checks
from rucompliance.rules import RULES


def _finding(rid, status, evidence=""):
    r = RULES[rid]
    return {
        "id": rid, "title": r["title"], "law": r["law"], "applies": r["applies"],
        "status": status,                       # fail | ok | manual | na
        "evidence": evidence,
        "fix": r["fix"], "fine_min": r["fine_min"], "fine_max": r["fine_max"],
        "fine_note": r["fine_note"],
    }


def scan(url):
    url = checks.normalize_url(url)
    try:
        resp = checks.fetch(url)
    except Exception as e:
        return {"url": url, "ok": False, "error": str(e)}

    a = checks.analyze(resp.text, resp.url)
    pd = a["has_pd_form"]
    findings = []

    # policy — умная проверка: заходим по ссылке и смотрим содержимое
    if a["policy_link"]:
        pol = checks.fetch_policy(a["policy_url"]) if a.get("policy_url") else {"reachable": True, "has_required": True}
        if not pol.get("reachable"):
            findings.append(_finding("policy", "fail", "ссылка на политику есть, но страница не открывается"))
        elif not pol.get("has_required"):
            findings.append(_finding("policy", "fail",
                                     "политика открывается, но не видно обязательных блоков "
                                     "(цели обработки, оператор, права субъекта)"))
        else:
            findings.append(_finding("policy", "ok",
                                     f"политика открывается и содержит обязательные блоки: {a['policy_link']}"))
    else:
        findings.append(_finding("policy", "fail" if pd else "na",
                                 "ссылка на политику не найдена"))

    # consent
    if not pd:
        findings.append(_finding("consent", "na", "формы сбора ПДн не обнаружены"))
    elif a["consent"]:
        findings.append(_finding("consent", "ok", "найдено упоминание согласия + чекбокс/политика"))
    else:
        findings.append(_finding("consent", "fail", "форма есть, явного согласия не видно"))

    # cookie
    if a["cookie_banner"]:
        findings.append(_finding("cookie", "ok", "похоже на cookie-баннер с кнопкой согласия"))
    elif a["cookie_mention"]:
        findings.append(_finding("cookie", "fail", "cookie упоминаются, но активного баннера не видно"))
    else:
        findings.append(_finding("cookie", "fail", "cookie-баннер не обнаружен"))

    # https
    if a["https"]:
        findings.append(_finding("https", "ok", "соединение по HTTPS"))
    else:
        findings.append(_finding("https", "fail", "сайт работает по http"))

    # http -> https редирект (только если собираем ПДн)
    if pd:
        red = checks.check_http_redirect(url)
        if red is True:
            findings.append(_finding("https_redirect", "ok", "http редиректит на https"))
        elif red is False:
            findings.append(_finding("https_redirect", "fail", "http НЕ редиректит на https"))
        else:
            findings.append(_finding("https_redirect", "manual", "редирект проверить не удалось"))
    else:
        findings.append(_finding("https_redirect", "na", "формы сбора ПДн не обнаружены"))

    # возрастная маркировка (контекстно, не считаем в риск)
    findings.append(_finding("age_mark", "ok" if a["age_mark"] else "manual",
                             "знак возрастной маркировки найден" if a["age_mark"]
                             else "знака нет — проставь, если сайт информационный/СМИ"))

    # маркировка рекламы (контекстно)
    if a["erid"]:
        findings.append(_finding("ad_marking", "ok", "найден идентификатор ERID"))
    elif a["ad_mention"]:
        findings.append(_finding("ad_marking", "manual",
                                 "есть упоминание рекламы без ERID — промаркируй, если это реклама"))
    else:
        findings.append(_finding("ad_marking", "manual", "если размещаешь интернет-рекламу — маркируй (ERID)"))

    # manual / informational
    findings.append(_finding("rkn_notify", "manual", "проверь сам в реестре РКН"))
    findings.append(_finding("requisites", "ok" if a["requisites"] else "manual",
                             "ИНН/ОГРН найдены на странице" if a["requisites"]
                             else "реквизиты не найдены (норма для некоммерческих)"))

    fails = [f for f in findings if f["status"] == "fail"]
    risk_min = sum(f["fine_min"] for f in fails)
    risk_max = sum(f["fine_max"] for f in fails)

    return {
        "url": url, "final_url": resp.url, "status": resp.status_code, "ok": True,
        "collects_pd": pd,
        "findings": findings,
        "fail_count": len(fails),
        "risk_min": risk_min, "risk_max": risk_max,
    }
