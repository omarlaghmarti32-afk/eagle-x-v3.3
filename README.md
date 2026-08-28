# EAGLE-X v3.3 – Operational Cybersecurity Monitor

**Seal**: 310-70-94 · **Version**: 3.3

نظام تشغيل حقيقي: مراقبة مضيف، كشف شذوذ، تشفير AES/Ed25519، PQC اختياري (ML-KEM/ML-DSA)، التقاط حزم اختياري، وTLS عبر Caddy.

---

## القدرات

| الطبقة | الحالة |
|--------|--------|
| AES-256-GCM + Ed25519 | **مفعّل دائماً** |
| ML-KEM / ML-DSA (liboqs) | **اختياري** — يُفعَّل تلقائياً إن وُجد |
| مراقبة المضيف (psutil) | **مفعّل** |
| التقاط حزم (scapy) | **اختياري** (`EAGLE_PCAP=1` + صلاحيات) |
| SQLite audit / blocklist | **مفعّل** |
| TLS reverse proxy (Caddy) | **مفعّل** في docker-compose |

---

## تشغيل سريع (مع HTTPS)

```bash
git clone https://github.com/omarlaghmarti32-afk/eagle-x-v3.3.git
cd eagle-x-v3.3
export EAGLE_API_TOKEN="غيّر-هذا"
docker compose up -d --build
```

- HTTP API داخلي: المنفذ 8080 داخل الشبكة
- الواجهة العامة: **https://localhost** (شهادة داخلية من Caddy)

```bash
curl -k https://localhost/api/health
```

### بدون Docker

```bash
pip install -r requirements.txt
# اختياري:
pip install -r requirements-optional.txt   # liboqs-python + scapy

export EAGLE_API_TOKEN=change-me
uvicorn api_server:app --host 0.0.0.0 --port 8080
```

---

## PQC الحقيقي

عند تثبيت `liboqs-python` وتوفر مكتبة liboqs الأصلية:

```bash
curl -k -H "Authorization: Bearer change-me" https://localhost/api/pqc/kem-demo
```

يعيد مفتاحاً عاماً وciphertext وhash للسر المشترك من **ML-KEM-768** (أو Kyber768).

بدون liboqs يبقى النظام على AES-256-GCM + Ed25519 دون انهيار.

---

## التقاط الحزم

```bash
export EAGLE_PCAP=1
# قد تحتاج:
# docker compose مع network_mode: host و cap_add: [NET_RAW, NET_ADMIN]
curl -H "Authorization: Bearer change-me" -X POST http://localhost:8080/api/pcap/burst
```

---

## API مختصرة

| Path | Auth |
|------|------|
| `GET /api/health` | لا |
| `GET /api/status` | لا (يعرض حالة PQC/pcap) |
| `POST /api/detect` | Bearer |
| `POST /api/heal` | Bearer |
| `GET /api/pqc/kem-demo` | Bearer |
| `POST /api/pcap/burst` | Bearer |

---

## الاختبارات

```bash
export EAGLE_DATA_DIR=/tmp/eagle-data EAGLE_LOG_DIR=/tmp/eagle-logs EAGLE_API_TOKEN=test-token EAGLE_LIVE_MONITOR=0
pytest -q
```

---

## الإنتاج

1. غيّر `EAGLE_API_TOKEN`
2. عيّن `EAGLE_DOMAIN` و`CADDY_EMAIL` لشهادات Let’s Encrypt بدل `tls internal`
3. لا تفتح 8080 للعامة — فقط 443 عبر Caddy
4. احمِ volume `eagle_data` (مفاتيح + SQLite)

**Noran Ultimate Systems · Seal 310-70-94**
