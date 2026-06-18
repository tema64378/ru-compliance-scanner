"""HTML-заключение о проверке (самодостаточное, открывается в браузере / печатается в PDF)."""

import html
from datetime import datetime
from urllib.parse import urlparse

from rucompliance.rules import DISCLAIMER

ST = {
    "fail": ("❌", "Нарушение", "#dc2626"),
    "ok": ("✅", "В порядке", "#16a34a"),
    "manual": ("🔍", "Проверь сам", "#ca8a04"),
    "na": ("➖", "Не требуется", "#64748b"),
}
ORDER = {"fail": 0, "manual": 1, "ok": 2, "na": 3}


def _esc(s):
    return html.escape(str(s or ""))


def _rub(n):
    return f"{n:,}".replace(",", " ") + " ₽"


def to_html(result):
    url = _esc(result.get("url"))
    if not result.get("ok"):
        return (f"<!doctype html><meta charset=utf-8><body style='font-family:sans-serif;padding:40px'>"
                f"<h2>Не удалось открыть {url}</h2><p>{_esc(result.get('error'))}</p></body>")

    fails = result["fail_count"]
    risk = _rub(result["risk_max"]) if fails else "—"
    cards = ""
    for f in sorted(result["findings"], key=lambda x: ORDER.get(x["status"], 9)):
        icon, label, col = ST[f["status"]]
        fine = (f'<div class="fine">💸 Штраф: {_esc(f["fine_note"])}</div>'
                if f["status"] == "fail" and f.get("fine_max") else "")
        fix = (f'<div class="fix">🛠 {_esc(f["fix"])}</div>'
               if f["status"] in ("fail", "manual") else "")
        ev = f'<div class="ev">{_esc(f["evidence"])}</div>' if f.get("evidence") else ""
        cards += f"""
        <div class="card" style="border-left:4px solid {col}">
          <div class="ct">{icon} {_esc(f['title'])} <span class="b" style="background:{col}">{label}</span></div>
          <div class="law">{_esc(f['law'])}</div>
          {ev}{fix}{fine}
        </div>"""

    ts = datetime.now().strftime("%d.%m.%Y %H:%M")
    risk_block = (f'<div class="risk">Потенциальный штраф для юрлица: <b>до {risk}</b></div>'
                  if fails else '<div class="okrisk">Явных нарушений не обнаружено 🎉</div>')

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Заключение о проверке — {url}</title>
<style>
  *{{box-sizing:border-box}} body{{margin:0;font-family:-apple-system,"Segoe UI",Inter,Arial,sans-serif;
    color:#16181b;background:#f6f8fb;line-height:1.55}}
  .wrap{{max-width:820px;margin:0 auto;padding:32px 20px 60px}}
  .head{{background:#0e1116;color:#fff;border-radius:16px;padding:24px 26px}}
  .flag{{font-size:13px;letter-spacing:2px;text-transform:uppercase;color:#7da7ff}}
  .url{{font-size:20px;font-weight:700;margin:4px 0;word-break:break-all}}
  .risk{{margin-top:10px;background:#2a0f12;border:1px solid #7f1d1d;color:#fca5a5;
    border-radius:10px;padding:10px 14px;font-size:16px}}
  .okrisk{{margin-top:10px;color:#4ade80;font-size:16px}}
  .warn{{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:12px;padding:12px 16px;margin-top:16px}}
  .card{{background:#fff;border:1px solid #e5e8ec;border-radius:12px;padding:14px 16px;margin-top:12px}}
  .ct{{font-weight:700;font-size:15px}}
  .b{{color:#fff;font-size:11px;font-weight:600;padding:2px 8px;border-radius:999px;margin-left:6px}}
  .law{{color:#64748b;font-size:13px;margin-top:3px}}
  .ev{{margin-top:6px;font-size:14px}} .fix{{margin-top:6px;color:#15803d;font-size:14px}}
  .fine{{margin-top:6px;color:#b91c1c;font-size:14px;font-weight:600}}
  footer{{color:#64748b;font-size:12px;margin-top:26px}}
</style></head>
<body><div class="wrap">
  <div class="head">
    <div class="flag">🇷🇺 Заключение о проверке сайта · 152-ФЗ</div>
    <div class="url">{url}</div>
    {risk_block}
  </div>
  {f'<div class="warn">Сайт ответил кодом {result.get("status")} — возможно, WAF/заглушка, результат неполный.</div>' if result.get("status",200) >= 400 else ''}
  {cards}
  <footer>{_esc(DISCLAIMER)}<br>Сгенерировано {ts} · ru-compliance-scanner</footer>
</div></body></html>"""


def default_filename(result):
    host = urlparse(result.get("url", "report")).hostname or "report"
    return f"report_{host}.html"
