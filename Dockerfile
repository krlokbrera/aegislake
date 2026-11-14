FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[azure]" && useradd --create-home --uid 10001 aegis \
    && mkdir -p /app/runs && chown -R aegis:aegis /app
USER 10001
ENTRYPOINT ["aegislake"]
CMD ["demo", "--output", "/app/runs"]
