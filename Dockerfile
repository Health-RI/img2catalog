FROM python:3.12-alpine3.22 AS img2catalog

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN apk update \
	&& apk upgrade \
	&& rm -rf /var/cache/apk/*

RUN pip install --no-cache-dir .

RUN adduser -D app
USER app
WORKDIR /home/app

ENTRYPOINT ["img2catalog"]
