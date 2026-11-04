FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    LPIC3_HOST=0.0.0.0 LPIC3_PORT=8000 LPIC3_DATA_DIR=/var/lib/lpic3-trainer
RUN useradd --system --uid 10001 --home-dir /var/lib/lpic3-trainer --shell /usr/sbin/nologin lpic3 \
    && mkdir -p /var/lib/lpic3-trainer && chown lpic3:lpic3 /var/lib/lpic3-trainer
WORKDIR /opt/lpic3-trainer/app
COPY pyproject.toml README.md LICENSE alembic.ini ./
COPY app ./app
COPY content ./content
COPY migrations ./migrations
RUN pip install --no-cache-dir . 
USER lpic3
VOLUME ["/var/lib/lpic3-trainer"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"
CMD ["lpic3ctl", "serve"]
