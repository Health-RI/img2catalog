FROM python:3.15-rc-alpine3.23 AS img2catalog

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

RUN useradd -m app
USER app
WORKDIR /home/app

ENTRYPOINT ["img2catalog"]
