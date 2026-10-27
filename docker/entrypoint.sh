#!/bin/sh
set -e

# Define a secure path for the temporary cron file
CRON_FILE="/tmp/img2catalog.cron"

if [ -n "${CRON_SCHEDULE:-}" ]; then
    echo "INFO: Starting img2catalog on schedule: $CRON_SCHEDULE"
    
    # Safely write the cron schedule and arguments to the cron file
    if ! printf '%s img2catalog %s\n' "$CRON_SCHEDULE" "$*" > "$CRON_FILE"; then
        echo "ERROR: Failed to write cron schedule to $CRON_FILE" >&2
        exit 1
    fi
    
    # Restrict file permissions for security
    chmod 0600 "$CRON_FILE"
    
    echo "INFO: Launching Supercronic..."
    exec supercronic "$CRON_FILE"
else
    echo "INFO: Running img2catalog in immediate mode..."
    exec img2catalog "$@"
fi
