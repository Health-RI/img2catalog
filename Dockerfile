FROM python:3.12-slim AS img2catalog

COPY pyproject.toml README.md /build/
COPY src/ /build/src/
RUN pip install --no-cache-dir /build && rm -rf /build

ENTRYPOINT ["img2catalog"]
