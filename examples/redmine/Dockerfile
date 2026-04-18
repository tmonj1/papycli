FROM redmine:6.0

COPY docker-init.sh /docker-init.sh
RUN chmod +x /docker-init.sh \
    # Inject init script just before the final `exec "$@"` in the original entrypoint.
    # The entrypoint re-runs itself via `gosu redmine` when called as root, so the
    # injected code runs as the redmine user after DB setup and migrations are complete.
    && head -n -1 /docker-entrypoint.sh > /tmp/entrypoint_new.sh \
    && echo 'if [ -n "$isLikelyRedmine" ]; then /docker-init.sh; fi' >> /tmp/entrypoint_new.sh \
    && echo 'exec "$@"' >> /tmp/entrypoint_new.sh \
    && mv /tmp/entrypoint_new.sh /docker-entrypoint.sh \
    && chmod +x /docker-entrypoint.sh
