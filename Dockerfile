FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[azure]" && useradd --create-home --uid 10001 aegis \
    && mkdir -p /app/runs && chown -R aegis:aegis /app
USER 10001
ENTRYPOINT ["aegislake"]
CMD ["demo", "--output", "/app/runs"]
