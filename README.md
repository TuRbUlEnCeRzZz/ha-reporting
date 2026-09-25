# HA Reporting

A modular reporting engine for Home Assistant.

> **Status:** `0.1.0-alpha.1` — initial Home Assistant app/add-on bootstrap.

## Goal

HA Reporting will turn Home Assistant time-series data into reusable, period-based reports.

The architecture is designed around:

- interchangeable data providers (VictoriaMetrics first);
- reusable device catalogs;
- arbitrary reporting periods;
- deterministic statistics and comparisons;
- normalized JSON results;
- later HTML/PDF rendering, AI interpretation, and destinations such as Paperless-ngx.

The first development target is **Home Assistant OS on Raspberry Pi 4 (aarch64)**. `amd64` is also declared for future portability.

## Current milestone

`0.1.0-alpha.1` intentionally does only one thing: prove that the repository is recognized by Home Assistant, the app/add-on can be installed, and its container starts successfully.

## Planned architecture

```text
Data Providers
  ├─ VictoriaMetrics
  ├─ Home Assistant / Recorder
  ├─ InfluxDB
  └─ future providers
        ↓
Normalized internal data
        ↓
Catalogs
        ↓
Statistics engine
        ↓
Comparison engine
        ↓
Charts + AI interpretation
        ↓
Rendering
        ↓
HTML / PDF
        ↓
Destinations (Paperless-ngx, Home Assistant, ...)
```

## Installation

Add this repository to the Home Assistant app/add-on store:

```text
https://github.com/TuRbUlEnCeRzZz/ha-reporting
```

Then install **HA Reporting**.

## Security

Never commit Home Assistant tokens, API keys, passwords, private installation details, or personal catalogs containing sensitive information to this public repository.

Installation-specific settings belong in Home Assistant's app/add-on configuration and persistent storage.

## License

MIT
