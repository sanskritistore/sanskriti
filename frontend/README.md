# संस्कृति (Sanskriti) — फ्रंटएंड

> अपने दुकान का डिजिटल विज्ञापन — आसान, सस्ता, अपनी भाषा में।

यह Sanskriti MVP का फ्रंटएंड है — **Next.js 14 (App Router)** + **Tailwind CSS** + **PWA**।
इसे छोटे दुकानदारों के लिए बनाया गया है: **हिंदी पहले**, मोबाइल-फर्स्ट, और बिल्कुल आसान UI।

---

## 🏗️ प्रोजेक्ट स्ट्रक्चर

```
frontend/
├── app/
│   ├── (auth)/              # लॉगिन — फोन + OTP
│   │   └── login/
│   ├── (dashboard)/         # मुख्य ऐप (लॉगिन के बाद)
│   │   ├── products/        # प्रोडक्ट जोड़ें / देखें
│   │   ├── ads/             # विज्ञापन बनाएं (3 स्टेप)
│   │   ├── reports/         # "₹X खर्च → Y ग्राहक"
│   │   └── settings/        # दुकान की जानकारी
│   ├── layout.js            # रूट लेआउट + PWA + Language Provider
│   ├── globals.css          # Tailwind + कस्टम कंपोनेंट्स
│   └── page.js              # एंट्री — लॉगिन/डैशबोर्ड पर भेजता है
├── components/
│   ├── forms/               # PhotoPicker वगैरह
│   ├── layout/              # AppShell, BottomNav
│   └── ui/                  # StepDots, LanguageToggle, ProductCard
├── lib/
│   ├── api.js               # बैकएंड API क्लाइंट (http://localhost:8000/api/v1)
│   ├── LanguageContext.jsx  # हिंदी/English स्विचिंग
│   ├── translations.js      # सारे अनुवाद (हिंदी डिफ़ॉल्ट)
│   └── utils.js             # ₹ फॉर्मेट, फोन/OTP वैलिडेशन
├── public/
│   ├── manifest.json        # PWA मैनिफेस्ट
│   ├── sw.js                # सर्विस वर्कर (ऑफलाइन सपोर्ट)
│   ├── offline.html         # ऑफलाइन पेज
│   └── icons/               # ऐप आइकॉन (placeholder)
├── tailwind.config.js
├── next.config.mjs
└── package.json
```

---

## 🚀 शुरू करें

```bash
# 1. डिपेंडेंसी इंस्टॉल करें
npm install

# 2. एनवायरनमेंट सेट करें
cp .env.local.example .env.local

# 3. डेव सर्वर चालू करें
npm run dev
```

ऐप यहाँ चलेगा: **http://localhost:3000**
बैकएंड ऐप यहाँ चाहिए: **http://localhost:8000/api/v1**

---

## 📐 आर्किटेक्चर नियम

1. **3-स्टेप नियम** — हर काम ज़्यादा से ज़्यादा 3 स्टेप में:
   - लॉगिन: नंबर डालें → OTP डालें → तैयार
   - प्रोडक्ट: फोटो → नाम/कीमत → सेव
   - विज्ञापन: प्रोडक्ट → बजट → पक्का करें
2. **हिंदी पहले** — डिफ़ॉल्ट भाषा हिंदी; English बटन से बदल सकते हैं
3. **मोबाइल-फर्स्ट** — नीचे नेविगेशन, बड़े बटन (48px+), एक हाथ से इस्तेमाल
4. **आसान भाषा** — कोई टेक्निकल शब्द नहीं; रिपोर्ट सिर्फ़ "₹X खर्च → Y ग्राहक"

---

## 🔌 बैकएंड API

| काम | Endpoint |
|---|---|
| OTP भेजें | `POST /auth/send-otp` |
| OTP पक्का करें | `POST /auth/verify-otp` |
| दुकान की जानकारी | `GET/PUT /business` |
| प्रोडक्ट | `GET/POST/PUT/DELETE /products` |
| विज्ञापन | `GET/POST/PUT/DELETE /ads` |
| रिपोर्ट | `GET /reports/summary` |

टोकन `localStorage` में (`sanskriti_token`) सेव होता है।

---

## 📱 PWA

- `manifest.json` — ऐप का नाम, आइकॉन, होम-स्क्रीन शॉर्टकट (प्रोडक्ट/विज्ञापन/रिपोर्ट)
- `sw.js` — ऑफलाइन सपोर्ट: स्टैटिक फाइलें कैश, API नेटवर्क-फर्स्ट
- `offline.html` — इंटरनेट न होने पर आसान हिंदी संदेश + retry बटन

---

## 🗣️ नई भाषा / टेक्स्ट जोड़ें

`lib/translations.js` में हर टेक्स्ट की हिंदी + English वैल्यू है।
कंपोनेंट में सिर्फ़ `t("key")` इस्तेमाल करें — भाषा अपने आप बदल जाएगी।

---

## 🛠️ टेक

- **Next.js 14** (App Router)
- **Tailwind CSS 3**
- **React 18**
- कोई भारी UI लाइब्रेरी नहीं — सिंपल रखें (MVP नियम)
