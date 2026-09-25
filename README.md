# HA Reporting

Add-on Home Assistant OS — version **0.1.0-alpha.22**.

Le dossier `ha-reporting/` contient l'add-on à installer/construire.
Voir [la documentation](ha-reporting/DOCS.md), le
[changelog](ha-reporting/CHANGELOG.md) et le
[rapport de validation](VALIDATION-alpha22.md).

Tests locaux depuis ce dossier (Python 3.11+ avec PyYAML, Node.js) :

```sh
python3 -m unittest discover -s tests -v
node --check ha-reporting/app/app.js
node tests/test_ui.cjs
bash -n ha-reporting/run.sh
```

Les fixtures runtime sont des captures anonymisées en lecture seule ; les tests
ne contactent aucun serveur et ne modifient aucun historique Home Assistant.
