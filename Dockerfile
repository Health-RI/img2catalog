# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.12-alpine3.24 AS builder

WORKDIR /app

# Install build essentials and curl (needed for downloading Supercronic)
RUN apk add --no-cache curl gcc musl-dev libffi-dev

# Copy uv binary from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv

# Latest releases and checksums available at https://github.com/aptible/supercronic/releases
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.51/supercronic-linux-amd64 \
    SUPERCRONIC_SHA256SUM=cc232108374e8e2b537045f2d5eaa1229f619db314c3ba6a14d38b35dc0aa123 \
    SUPERCRONIC=supercronic-linux-amd64

# Download and verify Supercronic
RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA256SUM}  ${SUPERCRONIC}" | sha256sum -c \
    && chmod +x "$SUPERCRONIC"

# Copy project metadata, README, and lockfile
COPY pyproject.toml README.md uv.lock ./
COPY src/ ./src/

# Export the lockfile and install dependencies & project globally into system python
RUN uv export --frozen --no-dev -o requirements.txt \
    && uv pip install --no-cache-dir --system -r requirements.txt \
    && uv pip install --no-cache-dir --system --no-deps .


# ==========================================
# Stage 2: Runtime
# ==========================================
FROM python:3.12-alpine3.24 AS img2catalog

# Create a non-root user for security (before WORKDIR, so /home/app is created
# by adduser and owned by app)
RUN adduser -D app

WORKDIR /home/app

# Copy installed global python packages/binaries from builder stage
COPY --from=builder /usr/local /usr/local

# pip is not needed at runtime. Removing it drops its CVEs and its vendored
# libraries (msgpack, urllib3, setuptools) from the image; the explicit rm also
# clears the stale pip dist-info that COPY merges in from the base image.
RUN rm -rf /usr/local/lib/python3.12/site-packages/pip \
           /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
           /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.12

# Copy Supercronic binary from builder stage and create symlink
COPY --from=builder /app/supercronic-linux-amd64 /usr/local/bin/supercronic-linux-amd64
RUN ln -sf /usr/local/bin/supercronic-linux-amd64 /usr/local/bin/supercronic

# Copy entrypoint script and set permissions
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Switch to the non-root user
USER app

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
