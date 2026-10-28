#!/bin/sh
set -e

# Define a secure path for the temporary cron file
CRON_FILE="/tmp/img2catalog.cron"

if [ -n "${CRON_SCHEDULE:-}" ]; then
    echo "INFO: Starting img2catalog on schedule: $CRON_SCHEDULE"

    # Supercronic runs the job line through a shell, so shell-quote every
    # argument; otherwise spaces split arguments and characters such as ; or $
    # are interpreted by the shell.
    CMD="img2catalog"
    for arg in "$@"; do
        case "$arg" in
            *"
"*)
                echo "ERROR: arguments must not contain newlines in scheduled mode" >&2
                exit 1
                ;;
        esac
        CMD="$CMD '$(printf '%s' "$arg" | sed "s/'/'\\\\''/g")'"
    done

    # Safely write the cron schedule and command to the cron file
    if ! printf '%s %s\n' "$CRON_SCHEDULE" "$CMD" > "$CRON_FILE"; then
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
