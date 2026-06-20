"""SVG-бейдж «проверено на 152-ФЗ» для встраивания на сайт клиента."""


def svg_badge(left, right, color):
    lw = 16 + len(left) * 7
    rw = 16 + len(right) * 7
    w = lw + rw
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img">
<linearGradient id="g" x2="0" y2="100%"><stop offset="0" stop-color="#fff" stop-opacity=".1"/>
<stop offset="1" stop-opacity=".1"/></linearGradient>
<rect rx="3" width="{w}" height="20" fill="#3a3f47"/>
<rect rx="3" x="{lw}" width="{rw}" height="20" fill="{color}"/>
<rect rx="3" width="{w}" height="20" fill="url(#g)"/>
<g fill="#fff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">
<text x="{lw/2:.0f}" y="14">{left}</text>
<text x="{lw + rw/2:.0f}" y="14">{right}</text>
</g></svg>'''


def badge_for(result):
    if not result.get("ok"):
        return svg_badge("152-ФЗ", "н/д", "#9f9f9f")
    fails = result.get("fail_count", 0)
    if fails == 0:
        return svg_badge("152-ФЗ", "✓ соответствует", "#16a34a")
    color = "#dc2626" if fails >= 3 else "#ca8a04"
    word = "нарушение" if fails == 1 else ("нарушения" if fails < 5 else "нарушений")
    return svg_badge("152-ФЗ", f"{fails} {word}", color)
