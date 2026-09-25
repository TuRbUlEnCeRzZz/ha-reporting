#!/usr/bin/with-contenv bashio

set -e

LOG_LEVEL="$(bashio::config 'log_level')"
bashio::log.level "${LOG_LEVEL}"

bashio::log.info "------------------------------------------------"
bashio::log.info " HA Reporting 0.1.0-alpha.1"
bashio::log.info "------------------------------------------------"
bashio::log.info "Home Assistant app/add-on container started successfully."
bashio::log.info "Architecture: $(uname -m)"
bashio::log.info "Persistent app/add-on config is available at /config."
bashio::log.info "HA Reporting bootstrap is ready."

# Keep the bootstrap running so Home Assistant can supervise it.
while true; do
    sleep 3600
done
