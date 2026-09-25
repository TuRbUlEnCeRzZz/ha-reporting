#!/usr/bin/with-contenv bashio
set -e
LOG_LEVEL="$(bashio::config 'log_level')"
bashio::log.level "${LOG_LEVEL}"
bashio::log.info "------------------------------------------------"
bashio::log.info " HA Reporting 0.1.0-alpha.2"
bashio::log.info "------------------------------------------------"
bashio::log.info "Architecture: $(uname -m)"
bashio::log.info "Catalog directory: /config/catalogs"
exec python3 /app/main.py
