"""Поток покупки документов через Робокассу.

  POST /order               — создать заказ (данные оператора) → ссылка на оплату
  GET/POST /robokassa/result — колбэк Робокассы (проверка подписи, отметка «оплачено»)
  GET /robokassa/success    — страница после оплаты со ссылками на скачивание
  GET /robokassa/fail       — оплата не прошла
  GET /download/{inv}/{name}— файл документа (только после оплаты)

В кабинете Робокассы укажи:
  Result URL  -> https://ТВОЙ_ДОМЕН/robokassa/result   (метод GET или POST)
  Success URL -> https://ТВОЙ_ДОМЕН/robokassa/success
  Fail URL    -> https://ТВОЙ_ДОМЕН/robokassa/fail
"""

import os
import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from pydantic import BaseModel

from rucompliance.docgen import Operator, generate_all

router = APIRouter()

ORDERS_DIR = "orders"
META = os.path.join(ORDERS_DIR, "_orders.json")
PRICES = {"docs": (990.0, "Пакет документов 152-ФЗ (политика, согласие, cookie)")}
TITLES = {"privacy_policy": "Политика обработки ПДн",
          "consent": "Согласие на обработку ПДн",
          "cookie_policy": "Политика cookie"}


def _load():
    os.makedirs(ORDERS_DIR, exist_ok=True)
    if os.path.exists(META):
        with open(META, encoding="utf-8") as f:
            return json.load(f)
    return {"_counter": 0, "orders": {}}


def _save(db):
    with open(META, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def _md_html(md, title):
    try:
        import markdown
        body = markdown.markdown(md, extensions=["extra"])
    except Exception:
        body = "<pre>" + md.replace("<", "&lt;") + "</pre>"
    return (f'<!doctype html><meta charset=utf-8><title>{title}</title>'
            '<body style="font-family:system-ui,Arial;max-width:760px;margin:40px auto;'
            f'padding:0 20px;line-height:1.6">{body}</body>')


class OrderIn(BaseModel):
    name: str = ""
    org_type: str = "ООО"
    inn: str = ""
    ogrn: str = ""
    address: str = ""
    email: str = ""
    phone: str = ""
    site: str = ""
    data: str = "фамилия, имя, e-mail"
    purposes: str = "обратная связь"
    uses_cookie: bool = True
    uses_analytics: bool = True
    product: str = "docs"


@router.post("/order")
def create_order(o: OrderIn):
    price, desc = PRICES.get(o.product, PRICES["docs"])
    db = _load()
    db["_counter"] += 1
    inv = db["_counter"]

    op = Operator(org_type=o.org_type, name=o.name, inn=o.inn, ogrn=o.ogrn,
                  address=o.address, email=o.email, phone=o.phone, site=o.site,
                  data=[x.strip() for x in o.data.split(",") if x.strip()],
                  purposes=[x.strip() for x in o.purposes.split(",") if x.strip()],
                  uses_cookie=o.uses_cookie, uses_analytics=o.uses_analytics)
    odir = os.path.join(ORDERS_DIR, str(inv))
    os.makedirs(odir, exist_ok=True)
    for key, md in generate_all(op).items():
        open(os.path.join(odir, key + ".md"), "w", encoding="utf-8").write(md)
        open(os.path.join(odir, key + ".html"), "w", encoding="utf-8").write(_md_html(md, TITLES[key]))

    db["orders"][str(inv)] = {"sum": price, "email": o.email, "paid": False, "product": o.product}
    _save(db)

    from payments.robokassa import payment_url
    return {"inv_id": inv, "amount": price, "payment_url": payment_url(price, inv, desc)}


async def _params(request: Request):
    p = dict(request.query_params)
    if request.method == "POST":
        form = await request.form()
        p.update({k: v for k, v in form.items()})
    return p


@router.api_route("/robokassa/result", methods=["GET", "POST"])
async def robokassa_result(request: Request):
    from payments.robokassa import verify_result
    p = await _params(request)
    out_sum, inv, sig = p.get("OutSum"), p.get("InvId"), p.get("SignatureValue")
    if not verify_result(out_sum, inv, sig):
        return PlainTextResponse("bad sign", status_code=400)
    db = _load()
    if inv in db["orders"]:
        db["orders"][inv]["paid"] = True
        _save(db)
        # отправляем документы на e-mail (если настроен SMTP)
        o = db["orders"][inv]
        if o.get("email"):
            from payments.email_send import send_email, configured
            if configured():
                files = ([os.path.join(ORDERS_DIR, inv, k + ".md") for k in TITLES]
                         + [os.path.join(ORDERS_DIR, inv, k + ".html") for k in TITLES])
                send_email(o["email"], "Ваши документы 152-ФЗ — 152чек",
                           "Спасибо за оплату! Во вложении документы под ваш сайт "
                           "(политика, согласие, cookie-политика). Проверьте и адаптируйте под себя.",
                           files)
    return PlainTextResponse(f"OK{inv}")


@router.get("/robokassa/success", response_class=HTMLResponse)
def robokassa_success(InvId: str = ""):
    db = _load()
    o = db["orders"].get(InvId)
    if not o or not o.get("paid"):
        return HTMLResponse("<h2>Оплата обрабатывается…</h2><p>Обнови страницу через минуту.</p>")
    links = "".join(
        f'<li><a href="/download/{InvId}/{k}.md">{TITLES[k]} (.md)</a> · '
        f'<a href="/download/{InvId}/{k}.html">.html</a></li>' for k in TITLES)
    return HTMLResponse(f"""<body style="font-family:system-ui;max-width:640px;margin:60px auto">
      <h2>✅ Оплата прошла. Ваши документы готовы:</h2><ul>{links}</ul>
      <p style="color:#666">⚠️ Шаблоны на основе 152-ФЗ — проверьте и адаптируйте под себя.</p></body>""")


@router.get("/robokassa/fail", response_class=HTMLResponse)
def robokassa_fail():
    return HTMLResponse("<h2>Оплата не прошла</h2><p>Попробуйте ещё раз.</p>")


@router.get("/download/{inv}/{name}")
def download(inv: str, name: str):
    db = _load()
    o = db["orders"].get(inv)
    if not o or not o.get("paid"):
        return PlainTextResponse("Доступ только после оплаты", status_code=403)
    path = os.path.join(ORDERS_DIR, inv, os.path.basename(name))
    if not os.path.exists(path):
        return PlainTextResponse("not found", status_code=404)
    return FileResponse(path)
