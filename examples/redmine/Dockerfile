FROM redmine:6.0

COPY docker-init.sh /docker-init.sh
RUN chmod +x /docker-init.sh \
    # Inject init script just before `exec "$@"` in the original entrypoint.
    # Verify the expected line exists first — if not, fail the build explicitly so
    # upstream entrypoint changes do not silently produce a broken image.
    # The entrypoint re-runs itself via `gosu redmine` when called as root, so the
    # injected code runs as the redmine user after DB setup and migrations are complete.
    && grep -qx 'exec "$@"' /docker-entrypoint.sh \
        || { echo 'ERROR: expected line `exec "$@"` not found in /docker-entrypoint.sh' >&2; exit 1; } \
    && sed '/^exec "\$@"$/i if [ -n "$isLikelyRedmine" ]; then /docker-init.sh; fi' \
        /docker-entrypoint.sh > /tmp/entrypoint_new.sh \
    && mv /tmp/entrypoint_new.sh /docker-entrypoint.sh \
    && chmod +x /docker-entrypoint.sh
