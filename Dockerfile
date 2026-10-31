FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[azure]" && useradd --create-home --uid 10001 aegis \
    && mkdir -p /app/runs && chown -R aegis:aegis /app
USER 10001
ENTRYPOINT ["aegislake"]
CMD ["demo", "--output", "/app/runs"]
