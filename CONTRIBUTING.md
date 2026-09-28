# Contributing to HA Reporting

HA Reporting uses English as the maintenance language of the repository.

## Language policy

New or modified maintainer-facing content must be written in English, including:

- source comments and docstrings;
- commit/release notes and changelog entries;
- validation files and technical documentation;
- internal identifiers and newly introduced technical error messages when practical.

User-facing text must be localizable. The beta.21 interface currently supports French (`fr`) and English (`en`) through `ha-reporting/app/i18n.js`. New UI work should use stable message IDs through `hrT(messageId)` instead of adding hard-coded labels. When adding a message, provide both French and English values in the same change.

Generated reports have their own language setting. Renderer-owned labels and AI instructions must follow the report language and must not translate user-owned names such as report names, catalog names, device names or entity IDs.

## Validation

Before preparing a release, run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_ui.cjs
python3 -m compileall -q ha-reporting/app custom_components/ha_reporting
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
```

Keep release-specific validation notes in `VALIDATION-<version>.md`.
