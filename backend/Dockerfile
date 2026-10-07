# संस्कृति बैकएंड - Docker इमेज
# (Hindi: डेवलपमेंट/उत्पादन दोनों के लिए एक ही इमेज)

FROM python:3.12-slim

# पर्यावरण
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# निर्भरताएँ पहले इंस्टॉल करें (लेयर कैशिंग के लिए)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# एप्लीकेशन कोड कॉपी करें
COPY . .

# पोर्ट खोलें
EXPOSE 8000

# डिफ़ॉल्ट कमांड - uvicorn सर्वर
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
