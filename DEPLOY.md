# Деплой 152чек

Три части: **API** (сканер + оплата), **бот** (отдельный сервис 24/7), **лендинг** (статика).

## 🚀 Рекомендуемый путь: свой домен + RU-VPS (turnkey)

Всё на одной машине под твоим доменом (`152check.ru`), HTTPS, данные в РФ. Выглядит
как настоящий сервис, без сторонних сабдоменов.

1. Купи **`.ru` домен** (reg.ru, ~200 ₽/год) и **VPS Ubuntu** (Timeweb/aeza, ~200 ₽/мес).
2. Наведи A-запись домена на IP сервера.
3. На сервере:
   ```bash
   git clone https://github.com/tema64378/ru-compliance-scanner /var/www/152check
   cd /var/www/152check
   nano deploy/nginx.conf          # заменить ВАШ_ДОМЕН
   nano .env                       # BOT_TOKEN, ROBOKASSA_LOGIN/PASS1/PASS2
   sudo bash deploy/setup.sh       # поставит API + бота + nginx, всё на автозапуске
   sudo certbot --nginx -d 152check.ru   # HTTPS
   ```
4. `API_BASE` в `landing/index.html` оставь пустым — API на том же домене.

Готово: лендинг на `https://152check.ru`, API проксируется там же, бот крутится в фоне,
всё перезапускается само (systemd). Конфиги — в папке `deploy/`.

---

## 1. Бэкенд (API) — Railway / VPS (альтернатива)

**Railway (проще всего):**
1. railway.app → New Project → Deploy from GitHub → выбрать `ru-compliance-scanner`.
2. Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
3. Variables: `ROBOKASSA_LOGIN`, `ROBOKASSA_PASS1`, `ROBOKASSA_PASS2`, `ROBOKASSA_TEST=1`.
4. Получишь публичный URL вида `https://xxx.up.railway.app` — это адрес API.

**VPS (Timeweb/Selectel, под РФ-аудиторию):**
```bash
git clone … && cd ru-compliance-scanner
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ROBOKASSA_LOGIN=… ROBOKASSA_PASS1=… ROBOKASSA_PASS2=… ROBOKASSA_TEST=1
uvicorn api.main:app --host 0.0.0.0 --port 8000   # обернуть в systemd + nginx + HTTPS
```

## 2. Бот — отдельный сервис (worker)

На Railway добавь **второй сервис** из той же репы:
- Start command: `python bot.py`
- Variable: `BOT_TOKEN` (от @BotFather)

Бот работает на long-polling — ему не нужен публичный URL, просто крутится 24/7.
(Docker: `docker build -t svc . && docker run -e BOT_TOKEN=… svc python bot.py`)

## 3. Лендинг — Vercel / Netlify (статика, бесплатно)

1. Залей папку `landing/` (drag-n-drop на Netlify или `vercel` в папке).
2. В `landing/index.html` впиши адрес бэкенда:
   ```js
   const API_BASE = "https://xxx.up.railway.app";
   ```
3. Подключи домен `.ru` (reg.ru).

## 4. Робокасса

В кабинете магазина укажи:
- **Result URL** → `https://API_ДОМЕН/robokassa/result` (метод GET или POST)
- **Success URL** → `https://API_ДОМЕН/robokassa/success`
- **Fail URL** → `https://API_ДОМЕН/robokassa/fail`

Скопируй `Login`, `Пароль#1`, `Пароль#2` в переменные окружения API.
Тест: `ROBOKASSA_TEST=1`. Боевой режим — убрать переменную.

## 5. Приём денег

Оформи **самозанятость** («Мой налог») — чек формируется в приложении, онлайн-касса
не нужна. Робокасса работает с самозанятыми.

---

### Порядок запуска
1. Самозанятость → 2. Робокасса (ключи) → 3. Деплой API → 4. Деплой бота →
5. Деплой лендинга + `API_BASE` → 6. Robokassa URLs → 7. Тест → 8. Боевой режим.
