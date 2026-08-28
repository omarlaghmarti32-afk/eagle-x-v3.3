# EAGLE-X v3.3 – Operational Cybersecurity Monitor

**Seal**: 310-70-94  
**Version**: 3.3  
**Status**: Operational (host monitoring + real crypto + audit DB)

> نظام أمن سيبراني تشغيلي يراقب المضيف، يكتشف الشذوذ، يشفر السجلات، وينفّذ إجراءات شفاء ذاتي قابلة للتدقيق.

---

## ما هو حقيقي في هذا الإصدار

| القدرة | التنفيذ |
|--------|---------|
| سرية البيانات | **AES-256-GCM** (مكتبة `cryptography`) |
| سلامة/توقيع | **Ed25519** |
| مراقبة المضيف | **psutil** (CPU, RAM, الشبكة, العمليات, الاتصالات, القرص) |
| كشف التهديدات | IsolationForest + RandomForest على 8 ميزات |
| التخزين | SQLite: تهديدات، تدقيق، قائمة حظر، مقاييس |
| الشفاء الذاتي | حظر مؤشرات + ختم تدقيق موقّع |
| API | FastAPI + Bearer Token للعمليات الحساسة |
| النشر | Docker + docker-compose + CI |

### مسار PQC (غير مفعّل أصلياً بعد)
أسماء Kyber-768 / Dilithium-2 موثّقة كـ **roadmap**. الطبقة النشطة اليوم هي AES-256-GCM + Ed25519.

---

## التشغيل السريع

### محلياً

```bash
git clone https://github.com/omarlaghmarti32-afk/eagle-x-v3.3.git
cd eagle-x-v3.3
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export EAGLE_API_TOKEN="change-me-in-production"
export EAGLE_DATA_DIR="./data"
export EAGLE_LOG_DIR="./logs"

uvicorn api_server:app --host 0.0.0.0 --port 8080
```

افتح: http://localhost:8080

### Docker Compose

```bash
export EAGLE_API_TOKEN="change-me-in-production"
docker compose up -d --build
curl http://localhost:8080/api/health
```

### محرك CLI

```bash
python eaglex_v33.py --duration 60
```

---

## API

| Method | Path | Auth | وصف |
|--------|------|------|-----|
| GET | `/api/health` | لا | صحة الخدمة |
| GET | `/api/status` | لا | حالة النظام |
| GET | `/api/stats` | لا | إحصاءات + مقاييس المضيف |
| GET | `/api/threats` | لا | آخر التهديدات |
| POST | `/api/detect` | Bearer | تحليل متجه ميزات |
| POST | `/api/heal` | Bearer | شفاء يدوي |
| GET | `/api/blocklist` | Bearer | قائمة الحظر |
| GET/POST | `/api/config` | POST يتطلب Bearer | الإعدادات |

مثال:

```bash
curl -X POST http://localhost:8080/api/detect \
  -H "Authorization: Bearer change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"features":[90,92,2500000,3000000,420,280,75,0.9],"indicator":"10.0.0.66"}'
```

---

## الاختبارات

```bash
export EAGLE_DATA_DIR=/tmp/eagle-data EAGLE_LOG_DIR=/tmp/eagle-logs EAGLE_API_TOKEN=test-token
pytest -q
```

CI يعمل تلقائياً على كل push لـ `main`.

---

## هيكل المشروع

```
eagle-x-v3.3/
├── api_server.py          # FastAPI + مراقبة حية
├── eaglex_v33.py          # محرك CLI
├── core/
│   ├── crypto_engine.py   # AES-GCM + Ed25519
│   ├── ai_detector.py     # كشف الشذوذ
│   ├── system_monitor.py  # psutil
│   ├── threat_db.py       # SQLite
│   ├── self_healing.py
│   ├── network_monitor.py
│   └── pqc_manager.py     # واجهة هجينة
├── tests/
├── docker-compose.yml
└── Dockerfile
```

---

## الأمان للإنتاج

1. غيّر `EAGLE_API_TOKEN` فوراً.
2. لا تعرض المنفذ 8080 للعامة بدون reverse proxy + TLS.
3. احمِ مجلد `data/` (يحتوي المفاتيح وقاعدة البيانات).
4. راجع قائمة الحظر والتدقيق بانتظام.

---

## الترخيص

انظر ملف `LICENSE` (ترخيص تجاري).

**Noran Ultimate Systems · Seal 310-70-94**
