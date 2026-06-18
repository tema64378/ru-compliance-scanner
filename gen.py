"""Генератор документов 152-ФЗ под сайт.

  python gen.py                      # интерактивно (вопрос-ответ)
  python gen.py --scan example.ru    # предзаполнить сайт/аналитику из скана

Выдаёт готовые: политику обработки ПДн, согласие, cookie-политику — в .md, .html и .pdf.

⚠️ Шаблоны на основе типовой структуры 152-ФЗ. Проверьте и адаптируйте под себя —
это не заменяет юридическую консультацию.
"""

import os
import argparse
import subprocess
import tempfile
from urllib.parse import urlparse

from rich.console import Console
from rich.prompt import Prompt, Confirm

from rucompliance.docgen import Operator, generate_all

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
console = Console()


def md_to_html(md, title):
    try:
        import markdown
        body = markdown.markdown(md, extensions=["extra"])
    except Exception:
        body = "<pre>" + md.replace("<", "&lt;") + "</pre>"
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>{title}</title><style>
body{{font-family:-apple-system,Segoe UI,Arial,sans-serif;max-width:760px;margin:40px auto;
padding:0 20px;color:#16181b;line-height:1.6}} h1{{font-size:24px}} h2{{font-size:18px;margin-top:24px}}
code,pre{{background:#f4f5f7;border-radius:6px}} pre{{padding:12px;overflow:auto}}
a{{color:#0061CC}}</style></head><body>{body}</body></html>"""


def to_pdf(html, path):
    if not os.path.exists(CHROME):
        return None
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as t:
        t.write(html); tmp = t.name
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={path}", f"file://{tmp}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.unlink(tmp)
    return path if os.path.exists(path) else None


def ask(op, scan_url=None):
    if scan_url:
        from rucompliance.scanner import scan
        console.print(f"[dim]Сканирую {scan_url} для предзаполнения…[/]")
        r = scan(scan_url)
        if r.get("ok"):
            op.site = r["url"]
            op.uses_analytics = bool(r.get("trackers"))
            op.uses_cookie = bool(r.get("trackers") or r.get("cookies_set")) or op.uses_cookie
            if r.get("trackers"):
                console.print(f"[green]Нашёл аналитику:[/] {', '.join(r['trackers'])}")

    console.print("\n[bold]Данные оператора[/] (Enter — пропустить):")
    op.org_type = Prompt.ask("Тип", choices=["ООО", "ИП", "Самозанятый", "Физлицо"], default=op.org_type)
    op.name = Prompt.ask("Название/ФИО (напр. «ООО Ромашка» или «ИП Иванов И.И.»)", default=op.name)
    op.inn = Prompt.ask("ИНН", default=op.inn)
    op.ogrn = Prompt.ask("ОГРН/ОГРНИП", default=op.ogrn)
    op.address = Prompt.ask("Адрес", default=op.address)
    op.email = Prompt.ask("E-mail для запросов субъектов", default=op.email)
    op.phone = Prompt.ask("Телефон", default=op.phone)
    op.site = Prompt.ask("Адрес сайта", default=op.site)
    data = Prompt.ask("Какие данные собираете (через запятую)", default=", ".join(op.data))
    op.data = [x.strip() for x in data.split(",") if x.strip()]
    purp = Prompt.ask("Цели обработки (через запятую)", default=", ".join(op.purposes))
    op.purposes = [x.strip() for x in purp.split(",") if x.strip()]
    op.uses_cookie = Confirm.ask("Используете cookie?", default=op.uses_cookie)
    op.uses_analytics = Confirm.ask("Используете аналитику (Метрика/GA)?", default=op.uses_analytics)
    return op


def main():
    ap = argparse.ArgumentParser(description="Генератор документов 152-ФЗ под сайт")
    ap.add_argument("--scan", help="URL сайта для предзаполнения из скана")
    ap.add_argument("--out", default="generated", help="Папка для результата")
    args = ap.parse_args()

    op = ask(Operator(), args.scan)
    docs = generate_all(op)

    host = urlparse(op.site).hostname or (op.name or "operator").replace(" ", "_")
    outdir = os.path.join(args.out, host)
    os.makedirs(outdir, exist_ok=True)

    titles = {"privacy_policy": "Политика обработки ПДн",
              "consent": "Согласие на обработку ПДн",
              "cookie_policy": "Политика cookie"}
    console.print(f"\n[bold green]Готово![/] Документы в [bold]{outdir}/[/]:")
    for key, md in docs.items():
        with open(os.path.join(outdir, key + ".md"), "w", encoding="utf-8") as f:
            f.write(md)
        html = md_to_html(md, titles[key])
        with open(os.path.join(outdir, key + ".html"), "w", encoding="utf-8") as f:
            f.write(html)
        pdf = to_pdf(html, os.path.join(outdir, key + ".pdf"))
        console.print(f"  • {titles[key]}: {key}.md, .html"
                      + (", .pdf" if pdf else " (PDF: нет Chrome)"))

    console.print("\n[dim]⚠️ Шаблоны — проверьте и адаптируйте под себя. Это не юр.консультация.[/]")


if __name__ == "__main__":
    main()
