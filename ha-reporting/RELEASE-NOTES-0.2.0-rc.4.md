# HA Reporting 0.2.0-rc.4

`0.2.0-rc.4` hardens AI report reliability by changing the model from a report writer into an evidence selector. HA Reporting now owns every quantitative sentence shown to the user.

## Highlights

- Introduces `ha-reporting-ai-context-v10` and the `id_only_v1` selection protocol.
- AI providers return only ledger IDs for the summary, attention points and recommendation evidence.
- HA Reporting validates all selected IDs and ignores unsupported IDs or actions.
- HA Reporting renders device names, metrics, units, current/reference values, absolute gaps and percentages deterministically from the selected ledger item.
- Prevents one source's values, coverage, unit or trend from being combined with another source in the final report text.
- Prevents cumulative `counter_end` readings from being selected as period-consumption headline facts.
- Excludes ordinary power `max`/`p95` facts from normal headline selection so isolated forecast peak gaps cannot dominate EMHASS commentary.
- Keeps forecast/measured relationships deterministic. Incomplete forecast coverage can be highlighted as a limitation, but cannot become a full-period performance gap.
- Recommendation text is generated from a small allow-list of actions bound to validated evidence IDs.
- If an AI provider returns malformed JSON, unsupported IDs, free-form prose or no valid summary selection, HA Reporting falls back to a deterministic ledger selection instead of publishing unsupported quantitative text.
- Keeps the full semantic AI context lossless: partial, limited, reconstructed and current-period data remain present; raw time-series samples are still intentionally excluded.
- Keeps the read-only VictoriaMetrics maintenance inventory from RC3 unchanged and isolated from HA Reporting catalogs.
- Keeps authenticated Home Assistant/Nabu Casa downloads, notifications, PDF generation, Paperless export and long-running AI handling unchanged.

## Why this change

Testing RC3 with both a smaller local model and Qwen3:8B showed that larger models improve interpretation quality, but can still occasionally mix device names, comparison percentages, coverage values or statistics in large monthly reports. RC4 removes that failure mode from the model boundary: the model selects what matters, while HA Reporting writes the numbers.

## Upgrade notes

The update is intended to be compatible with `0.2.0-rc.3`. Existing catalogs, reports, automations, provider settings, documents and exports remain compatible.

After upgrading on Home Assistant OS, validate at least:

- one daily EMHASS report;
- one large monthly N/N-x report;
- one AI provider response using the normal local model;
- optionally a second report with a larger local model such as Qwen3:8B;
- the existing VictoriaMetrics maintenance **Analyze** action;
- one PDF download through Home Assistant/Nabu Casa.

The expected RC4 difference is that AI prose may become slightly more structured, but every displayed quantitative statement should now be traceable to one selected ledger ID and rendered by HA Reporting itself.

See `VALIDATION-0.2.0-rc.4.md` for automated validation details.
