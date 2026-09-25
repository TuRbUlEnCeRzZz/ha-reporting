# HA Reporting 0.1.0-alpha.22 — validation

Validation du 25 septembre 2026. Base : archive fournie
`ha-reporting-0.1.0-alpha.21.zip`. Les vérifications sur VictoriaMetrics ont
exclusivement utilisé des requêtes de lecture. Aucun historique n'a été modifié.

## Cause confirmée des deux fallbacks

Le code alpha.21 bascule en fallback dès que le rollup est reconstruit ou
physiquement suspect. Son rapport remplace ensuite les statistiques du rollup
par celles d'une série rééchantillonnée toutes les cinq minutes. Une absence
de reset dans cette série ne démontre donc pas l'absence de baisse dans les
échantillons bruts.

Lecture des points originaux pour la même période que le rapport fourni :
1er janvier 2026 00:00 Europe/Zurich → 25 septembre 2026 22:21:41.692432,
avec fin exclusive.

| Source | Instant Europe/Zurich | Avant (h) | Après (h) | Baisse |
|---|---|---:|---:|---:|
| Vinothèque, compresseur | 22.09.2026 13:12:21.743 | 1.169444444444 | 1.169 | ≈ 1,6 s |
| Vinothèque, compresseur | 23.09.2026 19:20:19.464 | 8.359 | 8.342 | 61,2 s |
| Armoire combinée, compresseur | 23.09.2026 19:20:19.484 | 23.777 | 23.760 | 61,2 s |

La première baisse est compatible avec l'arrondi secondes → heures à trois
décimales. Les deux autres dépassent nettement ce seuil. Elles sont présentes
dans les points bruts, pas seulement dans le rollup. Leur quasi-simultanéité
est constatée ; leur origine à la source (redémarrage, recalcul, etc.) n'est
pas établie par ces données.

**Décision : conserver les deux fallbacks.** Les supprimer au moyen d'une
large tolérance d'arrondi masquerait une baisse réelle. Le nombre de fallbacks
ne constitue pas à lui seul un indicateur d'échec du rapport.

## Changements livrés

- Fallback brut ciblé, sans grille de cinq minutes ni perte des extrémités.
- Statistiques initiales et exemples de baisses conservés dans le JSON.
- Indication « compatible avec un arrondi » purement diagnostique ; aucune
  nouvelle tolérance de calcul n'est introduite.
- Contrôles physiques conservés ; plafond détaillé calculé sur les points
  réellement observés, valeurs négatives refusées.
- Export incohérent, vide, partiel, ambigu, non fini ou trop volumineux : erreur
  explicite de la source, sans réutiliser silencieusement un rollup suspect.
- Fenêtres de rollup exactes à la milliseconde, au lieu d'arrondir leur durée
  à la seconde supérieure et de compter sur un `nextafter` submilliseconde.
- Ordre chronologique par epoch pour l'heure répétée d'automne ; rejet d'une
  heure locale inexistante au printemps.
- Densité pertinente pour la puissance uniquement, en détaillé comme en rollup.
- Métadonnée de transfert brut corrigée ; message de fallback clarifié dans l'UI.
- Démarrage du serveur isolé pour rendre les tests d'intégration reproductibles.

## Résultats sur les données réelles

| Runtime | Rapport alpha.21 fourni | Alpha.22, points bruts | Mode alpha.22 |
|---|---:|---:|---|
| Vinothèque, compresseur | 20,0865 h | 20,152 h | fallback brut |
| Armoire combinée, compresseur | 58,663 h | 58,792 h | fallback brut |
| Vinothèque, ventilateur | 22,417 h | 22,417 h | rollup |

Pour la vinothèque, l'ancien premier point détaillé valait 0,0475 h au lieu
de 0 h et sa dernière valeur était 20,134 h au lieu de 20,152 h. Pour l'armoire,
la dernière valeur détaillée était 58,663 h au lieu de 58,792 h. Les différences
proviennent donc des extrémités de la grille rééchantillonnée.

Les deux exports bruts contiennent respectivement 1 506 et 3 714 points. Le
moteur détaillé conserve 0 reset accepté dans les deux cas et signale
respectivement 2 et 31 points ignorés par les contrôles existants. Un nombre
de points ignorés n'est pas un nombre de baisses : plusieurs points peuvent
être écartés pendant la récupération d'une valeur précédemment acceptée ou
lors d'une progression localement jugée trop rapide.

Rapport N : **10 sources OK, 0 invalide, 0 erreur, 2 fallbacks**.
Référence 2025 : 3 sources OK, 7 sans données, 0 erreur.
Comparaison : **0 comparable, 2 partielles, 1 reconstruite, 7 indisponibles**.

La période N s'exécute en environ **0,32 à 0,36 seconde** lors des deux mesures
locales contre le VictoriaMetrics existant. Ce n'est pas un benchmark du
Raspberry Pi et ces durées ne sont pas garanties.

## Tests reproductibles

- **58 tests Python/YAML réussis** : bornes `[start,end)`, doublons, non-finis,
  limites d'export, isolation des erreurs, conservation du diagnostic,
  premier/dernier point, resets réels et minuscules, anomalies physiques,
  qualité métrique, DST 23/25 h, heure répétée, heure inexistante, années
  bissextiles, comparaisons, agrégation du rapport et fixtures réelles anonymisées.
- **11 contrôles JavaScript réussis** : fallback brut, qualité, nombre de points,
  erreurs/absence de données, valeurs invalides, échappement des libellés et
  absence de pourcentage de variation pour les températures.
- Compilation Python, syntaxe JavaScript, syntaxe du script de démarrage : OK.
- YAML, version, architecture aarch64 et structure du paquet : OK.
- **6 fenêtres limites réelles** comparées entre rollup et export brut : OK,
  dont une fenêtre ne contenant qu'un point et une fenêtre submilliseconde vide.
- Rapport complet 2026 et référence 2025 exécutés contre VictoriaMetrics : OK.

Les tests locaux fonctionnent sans connexion à Home Assistant ou VictoriaMetrics.
Les fixtures ne contiennent ni URL de serveur ni identifiants d'entités.
Les sources et tests sont inclus dans l'archive ; les exports privés de diagnostic
et les caches Python en sont exclus.

## Limites de validation

La construction OCI n'a pas pu être exécutée : Podman ne peut pas créer son
répertoire d'exécution dans cet environnement en lecture seule. L'archive est
un paquet source pour Supervisor, avec la structure d'installation de l'alpha.21.
Le démarrage sous Home Assistant OS sur Raspberry Pi 4, l'ingress réel et la
construction aarch64 restent à vérifier après installation. L'add-on n'a pas
été installé ni déployé pendant cette tâche.

Les limites de lecture brute (200 000 points, 32 Mio, 1 Mio par ligne) peuvent
faire échouer explicitement une source suspecte possédant un très gros
historique. Elles ne tronquent pas silencieusement les calculs.

Pour la validation sur le Pi, relancer le rapport annuel et la comparaison N/N-1.
Deux fallbacks sont encore attendus tant que la période couvre les baisses du
23 septembre. Les valeurs évolueront naturellement si la fin de période change.
