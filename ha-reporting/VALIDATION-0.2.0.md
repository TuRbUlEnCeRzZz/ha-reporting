# Validation — HA Reporting 0.2.0

This document records the validation performed for the first stable HA Reporting release, `0.2.0`.

## Promotion scope

`0.2.0` is a direct promotion of `0.2.0-rc.8`. No reporting, comparison, AI-selection, scheduler, PDF, export, maintenance or UI behavior was intentionally changed for the stable promotion.

The stable promotion changes only release/version identifiers, current-version documentation, changelog/release notes and regression expectations that assert the package version/User-Agent.

## Runtime contract retained from RC8

AI schema: `ha-reporting-ai-context-v14`

Selection protocol: `id_only_v5_recommendation_guard`

The model continues to return IDs/actions only. HA Reporting owns calculations, units, relationship eligibility and final quantitative prose. Automatic context selection remains conservative, and reconstructed-counter recommendations remain evidence-bound.

## Final RC8 field-validation gate

The final monthly N/N-1 report supplied immediately before stable promotion completed with:

- **78/78 sources OK**;
- **0** sources without data;
- **0** errors / invalid sources;
- **Automatic → Optimized** AI context selection;
- **34/268 facts** selected for the AI Task;
- **23.9 k / 220.0 k characters** of AI context;
- correct real-versus-forecast energy and mean-power relationships;
- reconstructed-counter guidance attached to reconstructed evidence;
- near-zero-reference ventilation guidance without a false reconstruction recommendation.

This run validated the behavior that RC8 introduced specifically as the final pre-stable hardening step.

## Automated regression results

### Python

Command:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

Result: **179 tests passed**.

### JavaScript UI

Command:

```bash
node tests/test_ui.cjs
```

Result: **118 checks passed**.

## Syntax and metadata checks

The stable release is validated with:

```bash
python -m compileall -q ha-reporting/app custom_components/ha_reporting
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
bash -n ha-reporting/run.sh
```

The add-on `config.yaml` and companion integration `manifest.json` both report version `0.2.0`. User-Agent/version strings used by VictoriaMetrics, Paperless and the add-on startup banner also report `0.2.0`.

## Compatibility target

The stable release remains targeted at **Home Assistant OS**, primarily the project's Raspberry Pi 4 `aarch64` reference installation, while also declaring `amd64` support. The reference Home Assistant Core installation is kept current as new releases become available.

## Manual smoke test recommended after upgrade

After installing `0.2.0`, run at least one end-to-end report and verify:

1. statistics and comparison sections are generated;
2. AI context mode resolves as expected;
3. PDF generation and authenticated download work;
4. configured export and notification steps complete;
5. Automation and Document collapse/sort preferences behave correctly.

The AI text remains commentary. Deterministic data and report sections are the authoritative reference.

## Archive checks

Both the full stable archive and the GitHub web-update archive are verified with `unzip -t` after packaging. The web-update archive contains **16 changed/new files** relative to `0.2.0-rc.8`, with no deletions, and stays well below GitHub's 100-file browser-upload limit.
