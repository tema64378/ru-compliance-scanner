"""Telegram-бот: кидаешь ссылку на сайт → бот проверяет на требования РФ и
присылает нарушения со штрафами.

Запуск:
  export BOT_TOKEN=...        # токен от @BotFather
  python bot.py
"""

import os

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters,
)

from rucompliance.scanner import scan


def _rub(n):
    return f"{n:,}".replace(",", " ") + " ₽"


def format_result(r):
    if not r.get("ok"):
        return f"⚠️ Не удалось открыть {r.get('url')}: {r.get('error')}"
    lines = [f"🇷🇺 <b>{r['url']}</b>"]
    if r["fail_count"]:
        lines.append(f"❗ Нарушений: <b>{r['fail_count']}</b> · потенциальный штраф до "
                     f"<b>{_rub(r['risk_max'])}</b>")
    else:
        lines.append("✅ Явных нарушений не обнаружено")
    lines.append("")
    for f in r["findings"]:
        if f["status"] == "fail":
            lines.append(f"❌ <b>{f['title']}</b>\n   💸 {f['fine_note']}\n   🛠 {f['fix']}")
    lines.append("\nℹ️ Информационно, не юридическая консультация.")
    text = "\n".join(lines)
    return text[:4000]


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🇷🇺 Кинь ссылку на сайт — проверю его на требования РФ "
        "(152-ФЗ: политика, согласия, cookie, HTTPS) и покажу, какие штрафы грозят.")


async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()
    msg = await update.message.reply_text("Проверяю… ⏳")
    r = scan(url)
    await msg.edit_text(format_result(r), parse_mode="HTML",
                        disable_web_page_preview=True)


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("Задай переменную BOT_TOKEN (токен от @BotFather)")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("[*] Бот запущен. Ctrl-C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()
