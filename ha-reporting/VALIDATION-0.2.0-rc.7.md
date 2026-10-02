# Validation — HA Reporting 0.2.0-rc.7

This document records the automated and targeted validation performed for `0.2.0-rc.7`.

## Scope

RC7 adds configurable AI context depth while preserving the deterministic fact-ledger and ID-only output boundary introduced in earlier release candidates. It also includes the final presentation refinements identified during real RC6 daily, monthly and annual report testing.

Validated changes:

- global AI context level stored independently from report definitions;
- **Optimized / Extended / Complete / Automatic** context modes;
- safe fallback to a smaller effective mode if a larger projection exceeds the application-side context guard;
- requested/effective context-level metadata exposed to the UI/PDF renderer;
- `ha-reporting-ai-context-v13` + `id_only_v4_context_levels`;
- relationship/component summary deduplication;
- coherent relationship numeric precision;
- annual total-electrical-energy priority when N/N-x has zero representative comparisons;
- unchanged deterministic calculation/relationship safeguards across all modes.

## Automated tests

### Python regression suite

Command:

```bash
python -m unittest tests.test_regressions
```

Result:

```text
Ran 176 tests
OK
```

New RC7 regression coverage includes:

- context-mode expansion without changing the deterministic selection contract;
- Automatic mode choosing Complete for small contexts and a bounded projection for larger contexts;
- settings persistence and invalid-level rejection;
- suppression of standalone forecast/actual facts already represented by selected relationships;
- coherent decimal precision for relationship endpoints and deterministic gaps;
- annual no-representative-reference summaries prioritizing total electrical energy.

### JavaScript UI checks

Command:

```bash
node tests/test_ui.cjs
```

Result:

```text
104 JavaScript UI checks passed
```

The UI checks include the new AI context-level controls, English translations and context-mode metadata formatting.

## Static validation

The following checks passed:

```bash
python -m compileall -q ha-reporting/app custom_components/ha_reporting
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
bash -n ha-reporting/run.sh
```

`ha-reporting/config.yaml`, `repository.yaml` and `custom_components/ha_reporting/manifest.json` also parse successfully as YAML/JSON metadata.

## Context-level stress check

A synthetic power-source ledger was executed through all four RC7 modes.

For **160 sources / 480 facts**:

| Requested mode | Effective mode | Model context | Facts sent | Full facts |
| --- | --- | ---: | ---: | ---: |
| Optimized | Optimized | 6,949 chars | 28 | 480 |
| Extended | Extended | 17,645 chars | 96 | 480 |
| Complete | Complete | 45,222 chars | 480 | 480 |
| Automatic | Extended | 17,645 chars | 96 | 480 |

For **500 sources / 1,500 facts**:

| Requested mode | Effective mode | Model context | Facts sent | Full facts |
| --- | --- | ---: | ---: | ---: |
| Optimized | Optimized | 7,144 chars | 28 | 1,500 |
| Extended | Extended | 18,165 chars | 96 | 1,500 |
| Complete | Complete | 138,883 chars | 1,500 | 1,500 |
| Automatic | Optimized | 7,144 chars | 28 | 1,500 |

This verifies that a future larger model can receive materially more evidence without changing the fact ledger, while the default Optimized mode keeps current CPU-oriented latency characteristics.

## AI safety boundary

Schema: `ha-reporting-ai-context-v13`

Selection protocol: `id_only_v4_context_levels`

All four context modes preserve these rules:

- the LLM selects existing IDs only;
- HA Reporting owns calculations and numeric prose;
- units are semantic and cannot be changed by the model;
- cross-source comparisons are allowed only through explicit deterministic `relationships`;
- unsupported/low-coverage relationships do not gain a fabricated full-period gap;
- current-period and N/N-x quality rules remain authoritative.

## Compatibility

The add-on metadata version and custom integration manifest are both `0.2.0-rc.7`. The release remains targeted at Home Assistant OS, primarily the project's Raspberry Pi 4 `aarch64` reference installation, while also declaring `amd64` support.

Automated tests do not replace an end-to-end run on the target Home Assistant OS host. Before promoting RC7 to `0.2.0` stable, validate at least one real daily EMHASS report and one larger monthly or annual report with the desired AI context level.
