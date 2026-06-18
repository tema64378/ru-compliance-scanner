"""CLI: проверка сайта на требования РФ.

  python cli.py                      # интерактивно (вводи адреса)
  python cli.py example.ru
  python cli.py example.ru --json
  python cli.py example.ru --html            # HTML-заключение (report_<host>.html)
  python cli.py example.ru --pdf             # PDF-заключение (через Chrome)
  python cli.py a.ru b.ru c.ru               # batch: несколько сайтов + сводка
  python cli.py --file sites.txt             # batch из файла (URL построчно)
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile

from rich.console import Console
from rich.table import Table

from rucompliance.scanner import scan
from rucompliance.report import print_report

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def _rub(n):
    return f"{n:,}".replace(",", " ") + " ₽"


def save_html(result, path=None):
    from rucompliance.html_report import to_html, default_filename
    path = path or default_filename(result)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(to_html(result))
    return path


def save_pdf(result, path=None):
    from rucompliance.html_report import to_html, default_filename
    path = path or default_filename(result).replace(".html", ".pdf")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(to_html(result))
        tmp_path = tmp.name
    if not os.path.exists(CHROME):
        return None
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={path}", f"file://{tmp_path}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.unlink(tmp_path)
    return path if os.path.exists(path) else None


def run_once(url, console, as_json=False, html=None, pdf=None, render=False):
    result = scan(url, render=render)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result, console)
    if result.get("ok") and html is not None:
        console.print(f"[green]📄 HTML сохранён:[/] {save_html(result, html or None)}")
    if result.get("ok") and pdf is not None:
        p = save_pdf(result, pdf or None)
        console.print(f"[green]📕 PDF сохранён:[/] {p}" if p else "[red]PDF не создан (нет Chrome)[/]")
    return result


def batch(urls, console, as_json, render=False):
    results = []
    for u in urls:
        console.print(f"\n[bold]══ {u} ══[/]")
        results.append(scan(u, render=render))
        if not as_json:
            print_report(results[-1], console)
    # сводная таблица
    if not as_json:
        t = Table(title="Сводка по сайтам")
        t.add_column("Сайт"); t.add_column("Нарушений"); t.add_column("Риск штрафа")
        for r in results:
            if r.get("ok"):
                t.add_row(r["url"], str(r["fail_count"]),
                          _rub(r["risk_max"]) if r["fail_count"] else "—")
            else:
                t.add_row(r.get("url", "?"), "—", "ошибка")
        console.print(t)
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))


def interactive(console, render=False):
    console.print("[bold]🇷🇺 Проверка сайта на требования РФ[/] — введи адрес (Enter — выход)\n")
    while True:
        try:
            url = input("URL → ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nПока!")
            return
        if not url:
            console.print("Пока!")
            return
        console.print()
        run_once(url, console, render=render)
        console.print("[dim]" + "─" * 60 + "[/]\n")


def main():
    ap = argparse.ArgumentParser(description="Проверка сайта на соответствие требованиям РФ (152-ФЗ и др.)")
    ap.add_argument("url", nargs="*", help="URL(ы) или домен(ы); без них — интерактивный режим")
    ap.add_argument("--json", action="store_true", help="Вывести JSON")
    ap.add_argument("--html", nargs="?", const="", default=None, metavar="ФАЙЛ", help="Сохранить HTML-заключение")
    ap.add_argument("--pdf", nargs="?", const="", default=None, metavar="ФАЙЛ", help="Сохранить PDF-заключение (Chrome)")
    ap.add_argument("--file", help="Файл со списком URL (по одному в строке) — batch")
    ap.add_argument("--render", action="store_true",
                    help="Рендерить через headless Chrome (видит JS-контент, точнее, но медленнее)")
    args = ap.parse_args()

    console = Console()
    urls = list(args.url)
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            urls += [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

    if len(urls) > 1:
        batch(urls, console, args.json, args.render)
    elif len(urls) == 1:
        ok = run_once(urls[0], console, args.json, args.html, args.pdf, args.render).get("ok")
        sys.exit(0 if ok else 1)
    else:
        interactive(console, args.render)


if __name__ == "__main__":
    main()
