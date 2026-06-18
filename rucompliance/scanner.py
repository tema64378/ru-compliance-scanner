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

    # policy
    if a["policy_link"]:
        findings.append(_finding("policy", "ok", f"ссылка: {a['policy_link']}"))
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
