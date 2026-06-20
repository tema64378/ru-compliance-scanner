"""Вывод отчёта простым языком + сумма потенциального штрафа (rich)."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from rucompliance.rules import DISCLAIMER

ST = {
    "fail": ("❌", "НАРУШЕНИЕ", "bold red"),
    "ok": ("✅", "ОК", "green"),
    "manual": ("🔍", "ПРОВЕРЬ САМ", "yellow"),
    "na": ("➖", "не требуется", "dim"),
}


def _rub(n):
    return f"{n:,}".replace(",", " ") + " ₽"


def print_report(result, console=None):
    console = console or Console()
    if not result.get("ok"):
        console.print(Panel(f"[bold red]Не удалось открыть сайт:[/] {result.get('error')}",
                            title=result.get("url", "scan")))
        return

    fails = result["fail_count"]
    head = Text()
    head.append(f"  {result['url']}\n", style="bold")
    if fails:
        head.append(f"  Найдено нарушений: {fails} · потенциальный штраф ",
                    style="dim")
        head.append(f"{_rub(result['risk_min'])} – {_rub(result['risk_max'])}", style="bold red")
    else:
        head.append("  Явных нарушений не обнаружено 🎉", style="green")
    console.print(Panel(head, title="🇷🇺 Проверка сайта на требования РФ (152-ФЗ)"))

    if result.get("status", 200) >= 400:
        console.print(Panel(f"Сайт ответил кодом {result['status']} — возможно, нас завернула "
                           "защита (WAF). Результат может быть неполным.",
                           title="⚠️ Внимание", border_style="yellow"))

    console.print(f"[dim]Сбор персональных данных на странице: "
                  f"{'обнаружен (есть формы)' if result['collects_pd'] else 'не обнаружен'}[/]")
    trackers = result.get("trackers") or []
    if trackers:
        console.print(f"[dim]Трекеры/аналитика: [/]{', '.join(trackers)}")
    if result.get("cookies_set"):
        console.print(f"[dim]Ставит cookie: {len(result['cookies_set'])} шт.[/]")
    if result.get("rendered"):
        console.print("[dim]Режим: рендер через Chrome (виден JS-контент)[/]")
    if result.get("pages_scanned", 1) > 1:
        console.print(f"[dim]Просканировано страниц: {result['pages_scanned']}[/]")
    console.print()

    order = {"fail": 0, "manual": 1, "ok": 2, "na": 3}
    for f in sorted(result["findings"], key=lambda x: order.get(x["status"], 9)):
        icon, label, style = ST[f["status"]]
        console.print(f"{icon} [bold]{f['title']}[/] [{style}]({label})[/]")
        law_line = f"   [dim]Закон:[/] {f['law']}"
        if f.get("law_url"):
            law_line += f"  [blue][link={f['law_url']}]КонсультантПлюс →[/link][/blue]"
        console.print(law_line)
        if f["evidence"]:
            console.print(f"   [dim]Что нашли:[/] {f['evidence']}")
        if f["status"] in ("fail", "manual"):
            console.print(f"   [green]Как исправить:[/] {f['fix']}")
        if f["status"] == "fail" and f["fine_max"]:
            console.print(f"   [red]Штраф:[/] {f['fine_note']}")
        console.print()

    if fails:
        console.print(Panel(
            f"Если не исправить — суммарный риск штрафа для юрлица "
            f"[bold red]до {_rub(result['risk_max'])}[/]. Начни с ❌ по убыванию суммы.",
            border_style="red"))
    console.print(f"[dim]{DISCLAIMER}[/]")
