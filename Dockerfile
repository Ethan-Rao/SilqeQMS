FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# LibreOffice for the auditor portal's high-fidelity Word/Excel -> PDF
# conversion. Writer + Calc only (no Impress/Draw/Base/Java). Liberation
# fonts cover Arial/Times/Courier substitutions; DejaVu fills in Unicode
# glyphs. xhtml2pdf stays in requirements.txt as a last-resort fallback.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-calc \
    fonts-liberation \
    fonts-dejavu \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8080

CMD ["sh", "-c", "gunicorn app.wsgi:app --preload --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60 --config scripts/gunicorn_conf.py"]

