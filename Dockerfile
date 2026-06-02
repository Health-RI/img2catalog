FROM python:3.12-alpine3.22 AS img2catalog

COPY pyproject.toml README.md ./
COPY src/ ./src/

# Latest releases and checksums available at https://github.com/aptible/supercronic/releases
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.44/supercronic-linux-amd64 \
    SUPERCRONIC_SHA256SUM=6feff7d5eba16a89cf229b7eb644cfae2f03a32c62ca320f17654659315275b6 \
    SUPERCRONIC=supercronic-linux-amd64

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN apk update \
	&& apk upgrade \
	&& rm -rf /var/cache/apk/*\
    && pip install --no-cache-dir . \
    && apk add --no-cache curl \
    && curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA256SUM}  ${SUPERCRONIC}" | sha256sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -sf "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic \
    && apk del curl\
    && chmod +x /usr/local/bin/entrypoint.sh \
    && adduser -D app

USER app
WORKDIR /home/app

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
