# نشر EAGLE-X على Vercel (FastAPI)

## نقطة الدخول

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
```

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

إذا فشل البناء بسبب حجم التبعيات، استخدم `requirements-vercel.txt` كمحتوى `requirements.txt` مؤقتاً أو انشر عبر Docker على خادم.
