# Validation 0.1.0-beta.14

Hotfix du backend d’automatisation.

- 101 tests Python : OK
- 36 contrôles JavaScript UI : OK
- Compilation Python : OK
- YAML : OK
- run.sh : OK
- Régression `threading.Thread` non sérialisable : couverte
- Correctif : suppression des champs runtime privés avant `deepcopy` du payload public des jobs

## Correctif beta.14

- Régression couverte : un job contenant un `threading.Thread` peut être exposé via l’API sans tenter de sérialiser son `contextvars.Context`.
- Les champs runtime privés (`_thread`, `_fingerprint`, etc.) sont filtrés avant la copie profonde destinée à la réponse publique.
