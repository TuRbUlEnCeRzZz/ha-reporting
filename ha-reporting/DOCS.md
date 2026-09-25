# HA Reporting — Documentation

## 0.1.0-alpha.1

This is the initial bootstrap release.

### What it does

At this stage HA Reporting intentionally does not generate reports. It starts a minimal supervised container and writes startup information to the app/add-on log.

### Configuration

#### Log level

Default:

```yaml
log_level: info
```

### Persistent configuration

The app/add-on-specific configuration directory is mounted read/write at `/config` inside the container.

Future catalog import/export functionality will use this app/add-on-specific storage rather than requiring broad access to the Home Assistant configuration directory.

### Expected startup log

```text
------------------------------------------------
 HA Reporting 0.1.0-alpha.1
------------------------------------------------
Home Assistant app/add-on container started successfully.
Architecture: aarch64
Persistent app/add-on config is available at /config.
HA Reporting bootstrap is ready.
```

### Next milestone

`0.1.0-alpha.2` will introduce the first reporting-engine components, beginning with catalog loading and validation.
