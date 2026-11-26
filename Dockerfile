# Candidate deployment image; build/scan required before production.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BC_ROOT=/data BC_TLS=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-noto-core fonts-noto-cjk && rm -rf /var/lib/apt/lists/* && useradd --uid 10001 --create-home bc && mkdir /data && chown bc:bc /data && chmod 700 /data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY engine.py ingest.py flexible.py independent.py decisions.py reporting.py ocr_review.py tenant.py governance.py intelligence.py secure_app.py admin.py secure_index.html login.html ui.js account.js governance.js intelligence.js login.js i18n.py i18n.js style.css demo.csv ./
COPY locales/ ./locales/
COPY adaptive_learning/ ./adaptive_learning/
USER 10001
EXPOSE 8765
CMD ["python","-m","uvicorn","secure_app:app","--host","0.0.0.0","--port","8765","--workers","1","--limit-concurrency","20","--no-proxy-headers","--no-access-log"]
