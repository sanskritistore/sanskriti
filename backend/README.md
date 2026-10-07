# संस्कृति (Sanskriti) बैकएंड

भारतीय व्यापारिक विज्ञापन प्लेटफॉर्म का MVP बैकएंड —
AI विज्ञापन निर्माण, कैंपेन लॉन्च (Meta/Facebook/Instagram),
UPI वॉलेट और WhatsApp लीड कनेक्टर।

---

## तकनीक (Tech Stack)

| घटक | तकनीक |
|------|--------|
| वेब फ्रेमवर्क | FastAPI (async) |
| डेटाबेस | PostgreSQL + asyncpg |
| ORM | SQLAlchemy 2.0 (async) |
| माइग्रेशन | Alembic |
| पृष्ठभूमि कार्य | Celery + Redis |
| प्रमाणीकरण | JWT (python-jose) |
| भुगतान | UPI (Razorpay संरचना) |
| AI | OpenAI (विज्ञापन टेक्स्ट) |

---

## फ़ोल्डर संरचना (Folder Structure)

```
backend/
├── app/
│   ├── main.py                 # FastAPI एंट्री पॉइंट
│   ├── core/                   # मूल सेटअप
│   │   ├── config.py           # सेटिंग्स (.env से)
│   │   ├── database.py         # async SQLAlchemy इंजन
│   │   ├── security.py         # JWT + पासवर्ड हैशिंग
│   │   ├── tenant_context.py   # वर्तमान टेनेंट (request-scope)
│   │   └── exceptions.py       # कस्टम त्रुटियाँ
│   ├── api/
│   │   ├── deps.py             # dependencies (get_current_tenant_id)
│   │   └── v1/router.py        # सभी मॉड्यूल राउटर जुड़ते हैं
│   ├── models/                 # PostgreSQL मॉडल (हर टेबल में tenant_id!)
│   │   ├── base.py             # TenantMixin + TimestampMixin
│   │   ├── tenant.py           # व्यवसाय प्रोफ़ाइल + उपयोगकर्ता
│   │   ├── product.py          # उत्पाद + फ़ोटो
│   │   ├── campaign.py         # 2-लेयर कैंपेन (नीचे देखें)
│   │   └── payment.py          # वॉलेट लेनदेन + लीड
│   ├── modules/                # बिज़नेस मॉड्यूल (प्रत्येक में routes + service)
│   │   ├── tenant/             # व्यवसाय प्रोफ़ाइल
│   │   ├── product/            # आइटम + फ़ोटो
│   │   ├── ad_studio/          # AI विज्ञापन निर्माण
│   │   ├── runner/             # कैंपेन लॉन्च + बजट प्रबंधन
│   │   ├── adapters/           # प्लेटफॉर्म एडाप्टर (नीचे देखें)
│   │   ├── reports/            # सरल रिपोर्ट
│   │   ├── payments/           # UPI वॉलेट रिचार्ज
│   │   ├── i18n/               # भाषा/अनुवाद (hi, mr, gu, bn, ta, te)
│   │   └── whatsapp/           # WhatsApp लीड कनेक्टर
│   └── workers/                # Celery पृष्ठभूमि कार्य
├── alembic/                    # डेटाबेस माइग्रेशन
├── tests/                      # परीक्षण
├── requirements.txt            # Python निर्भरताएँ
├── .env.example                # पर्यावरण वेरिएबल नमूना
├── Dockerfile                  # कंटेनर इमेज
└── docker-compose.yml          # डेवलपमेंट सेटअप (api + db + redis + worker)
```

---

## आर्किटेक्चर नियम (Architecture Rules)

### 1. हर टेबल में `tenant_id` अनिवार्य है

संस्कृति multi-tenant प्लेटफॉर्म है — हर व्यवसाय (टेनेंट) का डेटा अलग।
इसलिए **हर मॉडल में `tenant_id` कॉलम है** (सिवाय `tenants` टेबल के,
जो स्वयं टेनेंट है)। यह `TenantMixin` से स्वतः आता है:

```python
class Product(Base, TimestampMixin, TenantMixin):  # tenant_id स्वतः
    ...
```

हर क्वेरी में tenant_id से फ़िल्टर अनिवार्य है — `get_current_tenant_id`
dependency रिक्वेस्ट से टेनेंट निकालकर context सेट करता है।

### 2. 2-लेयर कैंपेन पैटर्न (Two-Layer Campaign Pattern)

```
Campaign (हमारी कैंपेन - टेनेंट का व्यवसाय व्यू)
    └── PlatformCampaign (प्लेटफॉर्म की कैंपेन - Meta पर बनी)
```

**क्यों?**
- हमारी कैंपेन में बजट, उद्देश्य, रिपोर्ट — व्यवसाय का दृष्टिकोण
- प्लेटफॉर्म कैंपेन में platform_campaign_id, स्थिति, sync — तकनीकी दृष्टिकोण
- एक ही हमारी कैंपेन कई प्लेटफॉर्मों पर जा सकती है
- प्लेटफॉर्म API बदले तो व्यवसाय डेटा सुरक्षित रहता है

### 3. एडाप्टर 6-विधि अनुबंध (6-Method Adapter Contract)

हर प्लेटफॉर्म एडाप्टर को यह 6 विधियाँ लागू करनी होंगी
(`app/modules/adapters/base.py`):

1. `create_campaign(config)` — प्लेटफॉर्म पर कैंपेन बनाएँ
2. `update_campaign(id, config)` — कैंपेन अपडेट करें
3. `pause_campaign(id)` — कैंपेन रोकें
4. `resume_campaign(id)` — कैंपेन चालू करें
5. `get_campaign_status(id)` — स्थिति लाएँ
6. `get_campaign_metrics(id, dates)` — खर्च/रीच/क्लिक लाएँ

नया प्लेटफॉर्म जोड़ना हो? `BasePlatformAdapter` उत्तराधिकारी क्लास बनाकर
`adapters/__init__.py` की रजिस्ट्री में नाम जोड़ें — बस!

### 4. WhatsApp से लीड (WhatsApp Lead Pattern)

विज्ञापन CTA → ग्राहक WhatsApp पर → webhook से Lead रिकॉर्ड →
व्यवसाय को लीड दिखती है।

---

## चलाना (Getting Started)

### Docker से (अनुशंसित)

```bash
cp .env.example .env          # पर्यावरण वेरिएबल तैयार करें
docker compose up --build     # api + db + redis + worker चालू
```

- API: http://localhost:8000
- Swagger दस्तावेज़: http://localhost:8000/docs
- स्वास्थ्य जाँच: http://localhost:8000/health

### स्थानीय रूप से (Local)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

### माइग्रेशन (Migrations)

```bash
# नई माइग्रेशन बनाएँ (मॉडल बदलने के बाद)
alembic revision --autogenerate -m "विवरण"

# डेटाबेस पर लागू करें
alembic upgrade head
```

---

## API एंडपॉइंट (सारांश)

| मॉड्यूल | पथ | कार्य |
|---------|-----|------|
| tenant | `/api/v1/tenant/me` | व्यवसाय प्रोफ़ाइल |
| product | `/api/v1/products` | उत्पाद CRUD + फ़ोटो |
| ad_studio | `/api/v1/ad-studio/generate` | AI विज्ञापन बनाएँ |
| runner | `/api/v1/campaigns` | कैंपेन बनाएँ/लॉन्च/रोकें |
| reports | `/api/v1/reports/summary` | कैंपेन रिपोर्ट |
| payments | `/api/v1/payments/recharge` | UPI वॉलेट रिचार्ज |
| i18n | `/api/v1/i18n/languages` | समर्थित भाषाएँ |
| whatsapp | `/api/v1/whatsapp/leads` | WhatsApp लीड |

---

## समर्थित भाषाएँ (i18n)

`hi` (हिंदी), `en` (English), `mr` (मराठी), `gu` (ગુજરાતી),
`bn` (বাংলা), `ta` (தமிழ்), `te` (తెలుగు)

AI विज्ञापन और UI दोनों इन भाषाओं में उपलब्ध।
