# HA Reporting 0.1.0-beta.16

Archive de développement pour Home Assistant OS.

Beta.16 ajoute les **automatisations internes HA Reporting** : un utilisateur peut planifier directement depuis l’Ingress le pipeline complet rapport → analyse IA → PDF natif → stockage local → export(s) → notification persistante, sans dépendre du Companion ni d’une automatisation YAML Home Assistant.

Le Companion Home Assistant reste compatible et facultatif pour les utilisateurs qui souhaitent l’action native `ha_reporting.run_report`, mais il n’est plus nécessaire pour planifier les rapports.

Voir `ha-reporting/README.md`, `ha-reporting/DOCS.md` et `VALIDATION-beta16.md`.
