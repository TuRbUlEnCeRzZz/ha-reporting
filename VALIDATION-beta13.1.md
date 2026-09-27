# Validation 0.1.0-beta.13.1

Hotfix du backend d’automatisation.

- 101 tests Python : OK
- 36 contrôles JavaScript UI : OK
- Compilation Python : OK
- YAML : OK
- run.sh : OK
- Régression `threading.Thread` non sérialisable : couverte
- Correctif : suppression des champs runtime privés avant `deepcopy` du payload public des jobs
