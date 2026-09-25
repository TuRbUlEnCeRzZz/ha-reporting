# HA Reporting — 0.1.0-alpha.12

Reliability + non-destructive device source editing.

## Existing device sensor editor
Use **Capteurs** on an existing device to add, remove or reclassify sources without recreating the device or catalog. Existing source keys and the device ID remain stable.

## Duplicate catalog names
A catalog ID is deterministic from the name. If that ID already exists, HA Reporting refuses creation:
- no overwrite;
- no implicit `vinotheque2`;
- explicit error.

## Runtime reliability
Runtime is physically bounded by wall-clock time. Alpha.12 ignores impossible positive jumps, reconstructs plausible resets, tracks ignored anomalies and never presents an impossible runtime as a valid delta.

Sample density remains a diagnostic indicator, not an automatic error verdict.
