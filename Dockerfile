FROM python:3.12-slim AS img2catalog

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

ENTRYPOINT ["img2catalog"]