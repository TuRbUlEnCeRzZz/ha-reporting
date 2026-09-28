# Validation — HA Reporting 0.1.0-beta.19

Date : 28.09.2026

## Périmètre

Beta.19 est une passe de consolidation UX et de gestion des périodes construite sur la beta.18 :

- navigation principale par onglets persistants : Catalogues, Rapports, Documents, Automatisations, Paramètres ;
- suppression de l'empilement d'historique entre les sections principales ;
- bouton Retour réservé aux écrans de détail/édition et retour déterministe vers leur section parente ;
- en-tête simplifié à `HA Reporting` + numéro de version ;
- accords français corrigés pour les périodes complètes ;
- libellés de comparaison lisibles (`1 période précédente`, `2 années précédentes`, etc.) ;
- heure de début de journée configurable par rapport (`boundary_time`, défaut `00:00`) ;
- conservation de l'heure murale locale dans `Europe/Zurich`, y compris autour des changements DST ;
- compatibilité des rapports existants sans migration : absence de `boundary_time` = `00:00`.

Le moteur statistique, le prompt/transport IA, le rendu PDF, le stockage documentaire, Paperless-ngx et le scheduler beta.18 ne sont pas modifiés fonctionnellement.

## Validation locale

- 106 tests Python : OK ;
- 49 contrôles JavaScript UI : OK ;
- compilation Python add-on + Companion : OK ;
- syntaxe JavaScript : OK ;
- syntaxe `run.sh` : OK ;
- parsing YAML / JSON : OK ;
- rendu PDF natif couvert par la suite Python : OK ;
- journée EMHASS de test : `27.09.2026 05:30 → 28.09.2026 05:30` résolue correctement ;
- comparaison quotidienne autour du passage à l'heure d'été : heure locale 05:30 conservée et durée réelle de 23 h lorsque la fenêtre traverse le changement ;
- valeur historique sans `boundary_time` : minuit conservé.

## Acceptation sur Home Assistant OS / Raspberry Pi 4

1. Vérifier la présence et le défilement mobile des cinq onglets.
2. Ouvrir plusieurs écrans de détail puis utiliser Retour ; la navigation ne doit plus rebondir entre les sections principales.
3. Modifier `Rapport quotidien EMHASS` : `Jour`, `Période précédente complète`, début de journée `05:30`.
4. Exécuter le rapport après 05:30 et vérifier que la période résolue est exactement la veille 05:30 → aujourd'hui 05:30.
5. Comparer les valeurs avec l'ancienne automatisation EMHASS sur la même fenêtre.
6. Vérifier une automatisation existante avec IA, PDF, Paperless et notification persistante afin d'écarter toute régression du pipeline beta.18.

## Limites de la validation locale

Pas de build Supervisor/ARM ni d'exécution réelle VictoriaMetrics / AI Task / Paperless dans cet environnement. Ces points doivent être confirmés sur Home Assistant OS / Raspberry Pi 4.
