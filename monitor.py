"""Мониторинг сайтов: перепроверка + алерт при новом нарушении (recurring-фича).

  python monitor.py add example.ru 123456789   # добавить сайт (url, telegram chat_id)
  python monitor.py                              # проверить все и разослать алерты

Состояние — в monitors.json. Ставится на cron (раз в день/неделю).
Алерты шлёт в Telegram (нужен BOT_TOKEN в окружении) либо печатает в консоль.
"""

import os
import sys
import json
import urllib.parse
import urllib.request

from rucompliance.scanner import scan

STORE = "monitors.json"


def _rub(n):
    return f"{n:,}".replace(",", " ") + " ₽"


def load():
    return json.load(open(STORE, encoding="utf-8")) if os.path.exists(STORE) else {"sites": []}


def save(d):
    json.dump(d, open(STORE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def tg(chat_id, text):
    token = os.getenv("BOT_TOKEN")
    if not (token and chat_id):
        print(text + "\n")
        return
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=10)
    except Exception as e:  # noqa: BLE001
        print("[tg] ошибка:", e)


def add(url, chat_id=""):
    d = load()
    d["sites"].append({"url": url, "chat_id": chat_id, "last_fail_ids": None})
    save(d)
    print("добавлено в мониторинг:", url)


def run():
    d = load()
    for s in d["sites"]:
        r = scan(s["url"])
        if not r.get("ok"):
            continue
        ids = sorted(f["id"] for f in r["findings"] if f["status"] == "fail")
        prev = s.get("last_fail_ids")
        if prev is not None:                       # не алертим при самой первой проверке
            new = [i for i in ids if i not in prev]
            if new:
                titles = {f["id"]: f["title"] for f in r["findings"]}
                msg = (f"⚠️ Новые нарушения на {s['url']}:\n"
                       + "\n".join("• " + titles.get(i, i) for i in new)
                       + f"\nСуммарный риск до {_rub(r['risk_max'])}")
                tg(s.get("chat_id"), msg)
        s["last_fail_ids"] = ids
    save(d)
    print("проверено сайтов:", len(d["sites"]))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "add":
        add(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    else:
        run()
