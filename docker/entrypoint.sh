#!/bin/sh
set -e

if [ -n "$CRON_SCHEDULE" ]; then
    echo "Starting img2catalog on schedule: $CRON_SCHEDULE"
    printf '%s img2catalog %s\n' "$CRON_SCHEDULE" "$*" > /tmp/img2catalog.cron
    exec supercronic /tmp/img2catalog.cron
else
    exec img2catalog "$@"
fi