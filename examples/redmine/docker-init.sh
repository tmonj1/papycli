#!/bin/bash
set -eo pipefail

# Suppress Rails logger output so that only explicit output goes to stdout
SILENCE='Rails.logger = Logger.new(IO::NULL);'

# Enable REST API (idempotent)
echo "Enabling REST API..."
bundle exec rails runner "${SILENCE} Setting.rest_api_enabled = '1'"

# Load default data only if trackers have not been set up yet
echo "Checking default data..."
tracker_count=$(bundle exec rails runner "${SILENCE} puts Tracker.count" | grep -E '^[0-9]+$')
if [ "$tracker_count" = "0" ]; then
  echo "Loading default data..."
  REDMINE_LANG=en bundle exec rake redmine:load_default_data
else
  echo "Default data already loaded, skipping."
fi
