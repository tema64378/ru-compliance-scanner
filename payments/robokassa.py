"""Интеграция с Робокассой (формирование ссылки + проверка подписи).

Ключи берутся из окружения (из личного кабинета Робокассы):
  ROBOKASSA_LOGIN  — идентификатор магазина (MerchantLogin)
  ROBOKASSA_PASS1  — Пароль #1 (для формирования платежа)
  ROBOKASSA_PASS2  — Пароль #2 (для проверки колбэка ResultURL)
  ROBOKASSA_TEST   — "1" для тестового режима

Подпись (MD5, как по умолчанию у Робокассы):
  платёж:  md5(login:OutSum:InvId:Пароль#1)
  колбэк:  md5(OutSum:InvId:Пароль#2)
"""

import os
import hashlib
from urllib.parse import urlencode

PAY_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


def _cfg():
    return {
        "login": os.getenv("ROBOKASSA_LOGIN", ""),
        "pass1": os.getenv("ROBOKASSA_PASS1", ""),
        "pass2": os.getenv("ROBOKASSA_PASS2", ""),
        "test": os.getenv("ROBOKASSA_TEST", "0") == "1",
    }


def _md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def payment_url(out_sum, inv_id, description, login=None, pass1=None, is_test=None):
    """Ссылка на оплату. out_sum — строка вида '990.00' или число."""
    c = _cfg()
    login = login or c["login"]
    pass1 = pass1 or c["pass1"]
    is_test = c["test"] if is_test is None else is_test
    out_sum = f"{float(out_sum):.2f}"
    signature = _md5(f"{login}:{out_sum}:{inv_id}:{pass1}")
    params = {
        "MerchantLogin": login,
        "OutSum": out_sum,
        "InvId": inv_id,
        "Description": description,
        "SignatureValue": signature,
    }
    if is_test:
        params["IsTest"] = 1
    return f"{PAY_URL}?{urlencode(params)}"


def verify_result(out_sum, inv_id, signature, pass2=None):
    """Проверка подписи в колбэке ResultURL от Робокассы."""
    pass2 = pass2 or _cfg()["pass2"]
    expected = _md5(f"{out_sum}:{inv_id}:{pass2}")
    return expected.lower() == (signature or "").lower()
