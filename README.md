# EAGLE-X v3.3 – Operational Cybersecurity Monitor

**Seal**: 310-70-94 · **Version**: 3.3

مراقبة مضيف حقيقية · AES-256-GCM + Ed25519 · **ML-KEM/ML-DSA** (liboqs مُضمَّن في صورة Docker) · TLS عبر Caddy (محلي أو **Let’s Encrypt**).

---

## تشغيل محلي (HTTPS داخلي)

```bash
cp .env.example .env
# عدّل EAGLE_API_TOKEN
docker compose up -d --build
curl -k https://localhost/api/health
```

## إنتاج مع Let’s Encrypt

المتطلبات:
1. نطاق يشير إلى عنوان الخادم (سجل A/AAAA)
2. المنافذ **80** و **443** مفتوحة للعالم
3. بريد صالح لتسجيل ACME

```bash
cp .env.example .env
# مثال:
# EAGLE_DOMAIN=eagle.example.com
# CADDY_EMAIL=ops@example.com
# EAGLE_API_TOKEN=<رمز-قوي-طويل>

chmod +x scripts/deploy-prod.sh
./scripts/deploy-prod.sh
```

أو يدوياً:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
curl https://$EAGLE_DOMAIN/api/health
```

Caddy يحصل على شهادة Let’s Encrypt تلقائياً ويجدّدها.

---

## صورة Docker مع liboqs جاهز

البناء يُجمّع **liboqs 0.12.0** داخل الصورة عند `ENABLE_PQC=1` (الافتراضي):

```bash
./scripts/build-pqc-image.sh
# أو
docker build --build-arg ENABLE_PQC=1 -t eagle-x:3.3-pqc .
```

للتحقق من PQC داخل الحاوية:

```bash
docker run --rm eagle-x:3.3-pqc python -c "from core.pqc_manager import PQCManager; print(PQCManager().get_status())"
```

مسار API:

```bash
curl -H "Authorization: Bearer $EAGLE_API_TOKEN" https://$EAGLE_DOMAIN/api/pqc/kem-demo
```

بناء أسرع بدون PQC:

```bash
docker build --build-arg ENABLE_PQC=0 -t eagle-x:3.3 .
```

CI يدفع الصورة إلى GHCR كـ `ghcr.io/<user>/eagle-x-v3.3:3.3-pqc` عند الدفع لـ `main`.

---

## الطبقات الأمنية

| الطبقة | الحالة |
|--------|--------|
| AES-256-GCM + Ed25519 | دائماً |
| ML-KEM-768 / ML-DSA-65 | في صورة PQC |
| Caddy TLS | محلي (`tls internal`) أو Let’s Encrypt |
| Bearer token | على `/api/detect` و`/heal` و`/pqc/*` و`/pcap/*` |
| SQLite audit + blocklist | مفعّل |

---

## ملفات مهمة

| ملف | دور |
|-----|-----|
| `Caddyfile` | TLS محلي |
| `Caddyfile.production` | Let’s Encrypt |
| `docker-compose.prod.yml` | طبقة الإنتاج |
| `scripts/deploy-prod.sh` | نشر إنتاج |
| `scripts/build-pqc-image.sh` | بناء صورة PQC |
| `.env.example` | نموذج المتغيرات |

---

## الاختبارات

```bash
export EAGLE_DATA_DIR=/tmp/eagle-data EAGLE_LOG_DIR=/tmp/eagle-logs EAGLE_API_TOKEN=test-token EAGLE_LIVE_MONITOR=0
pytest -q
```

**Noran Ultimate Systems · Seal 310-70-94**
