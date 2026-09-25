#!/usr/bin/with-contenv bashio
set -e

bashio::log.level "$(bashio::config 'log_level')"
bashio::log.info "------------------------------------------------"
bashio::log.info " HA Reporting 0.1.0-alpha.13"
bashio::log.info "------------------------------------------------"
bashio::log.info "Architecture: $(uname -m)"
bashio::log.info "Ingress UI: port 8099"
bashio::log.info "Catalog management UI enabled"

exec python3 /app/main.py
