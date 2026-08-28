# نشر EAGLE-X على Vercel (FastAPI)

## نقطة الدخول

Vercel يتوقع كائن FastAPI باسم `app` في أحد الملفات المدعومة:

- `api/index.py` ← **المُستخدم هنا** (`from api_server import app`)
- أو `main.py` / `app.py`

في `pyproject.toml`:

```toml
[tool.vercel]
entrypoint = "api.index:app"
```

## القيود (Serverless)

| الميزة | على Vercel |
|--------|------------|
| REST API + لوحة | نعم |
| `/api/health` و `/api/detect` | نعم |
| حلقات المراقبة الحية | **معطّلة** (لا عملية طويلة الأمد) |
| SQLite تحت `/tmp` | مؤقت — يُمسح بين الحالات الباردة |
| liboqs / scapy | غير مناسب عادةً لحجم الدالة |
| Docker / Caddy | استخدم VPS أو Railway بدل Vercel |

للمراقبة المستمرة وPQC الكامل استخدم `docker compose` على خادم.

## المتغيرات

في Vercel → Project → Settings → Environment Variables:

```
EAGLE_API_TOKEN=strong-secret
EAGLE_LIVE_MONITOR=0
EAGLE_HEALTH_INTERNAL=0
EAGLE_DATA_DIR=/tmp/eagle-x-data
EAGLE_LOG_DIR=/tmp/eagle-x-logs
```

## النشر

```bash
npm i -g vercel
vercel login
vercel
# أو ربط GitHub بالمستودع من لوحة Vercel
```

تأكد أن Root Directory هو جذر المستودع، وRuntime = Python.

## التحقق

```bash
curl https://<project>.vercel.app/api/health
curl https://<project>.vercel.app/api/status
```

مسارات محمية:

```bash
curl -X POST https://<project>.vercel.app/api/detect \
  -H "Authorization: Bearer $EAGLE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"features":[90,90,2e6,2e6,400,300,80,0.9]}'
```
