# Candidate deployment image; build/scan required before production.
FROM python:3.13-alpine3.24
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BC_ROOT=/data BC_TLS=1 XDG_CACHE_HOME=/tmp/ledger64-cache
WORKDIR /app
RUN apk upgrade --no-cache && apk add --no-cache tesseract-ocr tesseract-ocr-data-spa tesseract-ocr-data-eng pango harfbuzz font-noto font-noto-cjk font-noto-devanagari && addgroup -g 10001 bc && adduser -D -u 10001 -G bc bc && mkdir /data && chown bc:bc /data && chmod 700 /data && fc-cache -f
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && python -m pip check && python -m pip uninstall -y pip && rm -rf /usr/local/lib/python3.13/ensurepip/_bundled
COPY engine.py ingest.py flexible.py independent.py decisions.py reporting.py ocr_review.py tenant.py governance.py intelligence.py secure_app.py admin.py secure_index.html login.html ui.js account.js governance.js intelligence.js login.js i18n.py i18n.js style.css demo.csv ./
COPY procurement.py procurement_history.py procurement_ingest.py procurement_cli.py procurement_queue.py procurement_routes.py procurement.html procurement_ui.js ./
COPY locales/ ./locales/
COPY adaptive_learning/ ./adaptive_learning/
USER 10001
EXPOSE 8765
CMD ["python","-m","uvicorn","secure_app:app","--host","0.0.0.0","--port","8765","--workers","1","--limit-concurrency","20","--no-proxy-headers","--no-access-log"]
