# HA Reporting 0.2.0-rc.5

`0.2.0-rc.5` focuses on reducing local-LLM workload without removing data from reports. It keeps the RC4 ID-only fact-ledger architecture, but HA Reporting now builds a deterministic model-facing shortlist from the complete internal ledger before calling AI Task.

## Highlights

### Deterministic AI shortlist

- Introduces **`ha-reporting-ai-context-v11`** and the **`id_only_v2_shortlist`** selection protocol.
- Builds the complete deterministic fact ledger internally, then sends only representative/significant facts, explicit relationships and quality evidence to the language model.
- Keeps the complete report dataset, PDF content and internal ledger available to HA Reporting; only the AI Task payload is shortened.
- Keeps routine `max`, `p95` and cumulative `counter_end` facts out of the normal LLM shortlist while retaining them in the report and internal ledger.
- Preserves mandatory low-quality evidence so shortlist optimization cannot hide incomplete data.

### Report-wide quality signals

- Adds deterministic `Q*` quality records for current-period source availability and N/N-x comparison representativeness.
- A report with low source availability can no longer present a partial annual value as if it represented the complete period without a quality warning.
- If a comparison target contains **zero representative comparisons**, HA Reporting now generates a mandatory deterministic summary/attention signal instead of asking the LLM to infer that limitation from dozens of individual records.
- Limited, reconstructed and unavailable comparisons remain visible as quality evidence but are no longer normal headline trend candidates.

### Source identity and deduplication

- Deduplicates shared Home Assistant sources by real `entity_id` + metric/unit before building the AI ledger.
- Prevents a shared room sensor from inheriting the label of the first appliance group that references it.
- Uses source-aware human labels for shared temperature/humidity sensors and common whole-home/forecast sources.
- Reduces duplicate facts when the same Home Assistant entity is reused by several report devices.

### Cleaner deterministic rendering

- Rounds coverage percentages in AI prose instead of exposing raw floating-point values.
- Deduplicates identical attention and recommendation lines.
- Keeps all quantitative sentences deterministic: the model still selects IDs only and cannot rewrite values, units, signs, percentages or source ownership.

### Context diagnostics

- Report metadata now exposes full-ledger versus shortlisted source/fact counts.
- The UI/PDF can indicate that the AI received a deterministic shortlist while the complete report data remained retained.
- Synthetic stress testing with **421 current sources + 420 N/N-x comparisons** reduced a **304,044-character internal ledger** to a **12,111-character model payload**, with **2,522 facts reduced to 28 shortlisted facts** and the critical low-coverage source still present.

## Unchanged behavior

- VictoriaMetrics maintenance remains **read-only**, independent from HA Reporting catalogs, and exposes no deletion endpoint.
- Same-session Home Assistant Ingress / Nabu Casa PDF downloads remain unchanged.
- Notifications, PDF generation, Paperless export, report statistics and catalog data remain unchanged.
- The shortlist does **not** remove information from the generated report; it only reduces what the LLM must read.

## Validation

The release-candidate validation includes Python regression coverage, JavaScript UI checks, Python compilation, JavaScript syntax checks, shell syntax validation and archive integrity checks. See `VALIDATION-0.2.0-rc.5.md` for details.

## Recommended real-world tests before 0.2.0

After upgrading, run the same reports used to stress RC4 and compare the AI context metadata and duration:

1. daily forecast-vs-measured report;
2. monthly N/N-1 report;
3. annual report without comparison;
4. annual N/N-1 report with incomplete historical reference data.

The main acceptance criteria are: correct deterministic facts, explicit quality warnings, no source-label mixing, no duplicate attention lines, and a meaningful reduction in AI Task duration/context on large reports.
