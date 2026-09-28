# HA Reporting 0.1.0-beta.21

Development repository for the HA Reporting add-on on Home Assistant OS.

Beta.21 introduces the first internationalization foundation and ships the interface in **French and English**. The interface language is detected from Home Assistant on first launch, can be overridden in **Settings**, and is stored locally in the browser. Each report also has its own language setting so generated HTML/PDF reports and AI analysis can be produced in French or English independently of the interface language.

This release also fixes two HTTP reliability issues:

- PDF downloads now use an RFC 5987-compatible `Content-Disposition` header, including a safe ASCII fallback and UTF-8 filename support;
- Home Assistant timezone discovery now prefers the Supervisor information endpoint, caches the result, and keeps the Core configuration endpoint as a fallback.

Repository-facing development content added or modified from beta.21 onward is written in **English**. User-facing text must go through the i18n layer when it is intended to be localized.

The existing reporting pipeline remains available: data calculation, optional AI analysis, native local PDF generation, Paperless-ngx export, scheduled automations and Home Assistant notifications.

See `ha-reporting/README.md`, `ha-reporting/DOCS.md`, `CONTRIBUTING.md` and `VALIDATION-beta21.md`.
