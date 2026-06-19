"""Сборка юридических страниц лендинга (оферта + политика) из шаблона оферты.
Перегенерить при смене домена: меняешь DOMAIN ниже и запускаешь:
  python landing/_build_legal.py
"""
import os
import re
import sys

import docx

# ⬇️ как выберешь домен — впиши сюда и перегенери
DOMAIN = "[адрес вашего сайта]"
OFERTA_DOCX = os.path.expanduser("~/Downloads/oferta_532123260012 (2).docx")
HERE = os.path.dirname(__file__)

NAME = "Яковлев Артём Сергеевич (самозанятый)"
INN = "532123260012"
EMAIL = "tema643789@gmail.com"
PHONE = "+7 911 609-63-41"

PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>body{{font-family:-apple-system,"Segoe UI",Inter,Arial,sans-serif;max-width:780px;
margin:0 auto;padding:32px 20px 60px;color:#16181b;line-height:1.6}}
a{{color:#0061CC}} h1{{font-size:26px}} h2{{font-size:18px;margin-top:26px}}
.back{{display:inline-block;margin-bottom:18px;color:#0061CC;text-decoration:none}}
.req{{background:#f6f8fb;border:1px solid #e6e9ee;border-radius:12px;padding:16px 18px;margin-top:20px}}
</style></head><body><a class="back" href="/">← на главную</a>{body}</body></html>"""


def build_oferta():
    d = docx.Document(OFERTA_DOCX)
    subs = {
        "Полное наименование:": f"Полное наименование: {NAME}",
        "ОГРН/ОГРНИП:": "ОГРН/ОГРНИП: — (самозанятым не присваивается)",
    }
    html = []
    for p in d.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        t = re.sub(r"_{3,}", DOMAIN, t)
        for k, v in subs.items():
            if t.startswith(k):
                t = v
        # короткие строки без точки на конце — это заголовки разделов
        if len(t) < 60 and not t.endswith((".", ":", ";")):
            html.append(f"<h2>{t}</h2>")
        else:
            html.append(f"<p>{t}</p>")
    return PAGE.format(title="Публичная оферта", body="<h1>Публичная оферта</h1>" + "".join(html))


def build_privacy():
    sys.path.insert(0, os.path.join(HERE, ".."))
    from rucompliance.docgen import Operator, privacy_policy
    import markdown
    op = Operator(org_type="Самозанятый", name=NAME, inn=INN, email=EMAIL, phone=PHONE,
                  site=DOMAIN,
                  data=["имя", "адрес электронной почты", "номер телефона",
                        "адрес проверяемого сайта"],
                  purposes=["оказание услуг проверки сайта на соответствие 152-ФЗ",
                            "формирование документов", "обратная связь с пользователем"],
                  uses_cookie=True, uses_analytics=True)
    body = markdown.markdown(privacy_policy(op), extensions=["extra"])
    return PAGE.format(title="Политика конфиденциальности", body=body)


for name, fn in [("oferta.html", build_oferta), ("privacy.html", build_privacy)]:
    open(os.path.join(HERE, name), "w", encoding="utf-8").write(fn())
    print("собрано:", name)
