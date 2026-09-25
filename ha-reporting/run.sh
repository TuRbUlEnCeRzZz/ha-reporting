#!/usr/bin/with-contenv bashio
set -e

bashio::log.level "$(bashio::config 'log_level')"
bashio::log.info "------------------------------------------------"
bashio::log.info " HA Reporting 0.1.0-alpha.5"
bashio::log.info "------------------------------------------------"
bashio::log.info "Architecture: $(uname -m)"
bashio::log.info "Ingress catalog manager: port 8099"

exec python3 /app/main.py
