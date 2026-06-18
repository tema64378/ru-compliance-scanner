"""CLI: проверка сайта на требования РФ.

  python cli.py                 # интерактивно (вводи адреса)
  python cli.py example.ru
  python cli.py example.ru --json
"""

import sys
import json
import argparse

from rich.console import Console

from rucompliance.scanner import scan
from rucompliance.report import print_report


def run_once(url, as_json, console):
    result = scan(url)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result, console)
    return result.get("ok")


def interactive(console):
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
        run_once(url, False, console)
        console.print("[dim]" + "─" * 60 + "[/]\n")


def main():
    ap = argparse.ArgumentParser(description="Проверка сайта на соответствие требованиям РФ (152-ФЗ и др.)")
    ap.add_argument("url", nargs="?", help="URL или домен (без него — интерактивный режим)")
    ap.add_argument("--json", action="store_true", help="Вывести JSON")
    args = ap.parse_args()

    console = Console()
    if args.url:
        sys.exit(0 if run_once(args.url, args.json, console) else 1)
    interactive(console)


if __name__ == "__main__":
    main()
