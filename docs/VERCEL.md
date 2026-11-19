# نشر EAGLE-X على Vercel (FastAPI)

## نقطة الدخول

يستخدم Vercel `main:app` من `pyproject.toml` ويوجّه الطلبات إلى FastAPI مباشرة؛ لذلك لا تضف إعادة كتابة شاملة مثل `/(.*) -> /api/index` في `vercel.json`. هذه القاعدة ليست مطلوبة وقد تغيّر المسار الذي يستلمه FastAPI.

المعتمد في `pyproject.toml`:

```toml
[tool.vercel]
entrypoint = "main:app"
```

ملفات بديلة مدعومة أيضاً:

- `main.py` → `app`
- `app.py` → `app`
- `api/index.py` → `app` (مع إصلاح `sys.path`)

## إصلاح شائع

إذا ظهر `ModuleNotFoundError: api_server` أو `core`، السبب أن مسار المشروع لم يُضف إلى `sys.path`. الملفات `main.py` و`api/index.py` تفعل ذلك تلقائياً الآن.

## القيود (Serverless)

| الميزة | على Vercel |
|--------|------------|
| REST API + لوحة | نعم |
| حلقات المراقبة الحية | معطّلة |
| SQLite تحت `/tmp` | مؤقت |
| حجم الحزمة (sklearn/numpy) | قد يفشل على الخطة المجانية إن تجاوز الحد |
| PQC / Docker / Caddy | استخدم VPS |

## المتغيرات

```
EAGLE_API_TOKEN=strong-secret
EAGLE_LIVE_MONITOR=0
EAGLE_HEALTH_INTERNAL=0
EAGLE_DATA_DIR=/tmp/eagle-x-data
EAGLE_LOG_DIR=/tmp/eagle-x-logs
EAGLE_GITHUB_REPO=omarlaghmarti32-afk/eagle-x-v3.3
EAGLE_GITHUB_TOKEN=
EAGLE_GITHUB_CACHE_SECONDS=60
```

Keep `EAGLE_GITHUB_TOKEN` in Vercel's server-side environment variables. Never
place it in the static dashboard; `/api/github/overview` also requires the
`EAGLE_API_TOKEN` Bearer header.

## النشر

```bash
vercel login
vercel
```

التحقق:

```bash
curl https://<project>.vercel.app/api/health
curl https://<project>.vercel.app/api/ready
```

قد تكون معاينات Vercel محمية بتسجيل الدخول. عندها قد يعيد الطلب العام صفحة أو تحويل المصادقة بدل JSON، وهذا لا يختبر استجابة FastAPI. استخدم `vercel curl <deployment-url>/api/health` من جلسة Vercel مصادق عليها للتحقق من المعاينة المحمية.

إذا فشل البناء بسبب حجم التبعيات، استخدم `requirements-vercel.txt` كمحتوى `requirements.txt` مؤقتاً أو انشر عبر Docker على خادم.
