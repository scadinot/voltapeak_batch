# Feuille de route — voltapeak_batch

Ce document recense les évolutions envisagées pour le projet, classées
par horizon (court / moyen / long terme) et par criticité. Chaque
entrée précise la **motivation** (pourquoi c'est utile) et, lorsque
pertinent, une **piste technique** (comment s'y prendre).

La liste est volontairement ouverte : ce ne sont pas toutes des
promesses, mais un réservoir d'idées à prioriser selon les besoins
réels des utilisateurs.

---

## Vue d'ensemble

| Horizon | Objectif principal | Effort estimé |
|---|---|---|
| [Court terme](#court-terme--qualité-de-base-du-projet) | Rendre le projet installable et maintenable | quelques heures à 1 journée |
| [Moyen terme](#moyen-terme--robustesse-et-configurabilité) | Robustesse, tests, configurabilité | quelques jours |
| [Long terme](#long-terme--plate-forme-et-écosystème) | Distribution, pérennité, écosystème | plusieurs semaines |
| [Pistes exploratoires](#pistes-exploratoires) | Optimisations ponctuelles et UX avancée | à évaluer au cas par cas |

---

## Court terme — qualité de base du projet

### 1. Extraire le code en modules

**Motivation.** Les ~600 lignes actuelles mélangent entrée/sortie,
algorithmes numériques, génération de graphiques, parallélisme et
interface graphique. Cette structure freine la réutilisation (impossible
d'importer l'algorithme sans lancer Tkinter) et rend les tests
difficiles.

**Piste technique.** Éclater en :
```
voltapeak_batch/
├── __init__.py
├── io.py          # readFile, export
├── processing.py  # smoothSignal, getPeakValue, calculateSignalBaseLine
├── plotting.py    # plotSignalAnalysis
├── aggregate.py   # construction du récapitulatif Excel
├── gui.py         # launch_gui
└── cli.py         # mode batch sans GUI
```

### 2. Remplacer les `print` et mises à jour directes du widget par `logging`

**Motivation.** Les messages d'erreur sont actuellement imprimés sur la
sortie standard **et** insérés dans le widget Tk selon le contexte. Un
logger centralisé permettrait d'avoir un canal unique, configurable
(fichier rotatif, console, widget) et réutilisable en mode CLI.

**Piste technique.** Utiliser `logging.getLogger(__name__)` dans les
modules ; connecter un handler custom qui écrit dans le widget `Text`
de la GUI ; un handler fichier pour les exécutions automatisées.

### 3. Ajouter un mode CLI

**Motivation.** Pour intégrer l'outil à une chaîne automatisée (CI,
serveur d'analyse, script batch), la GUI Tkinter est un obstacle. Un
mode ligne de commande permettrait `voltapeak_batch --input ./data --export xlsx`.

**Piste technique.** `argparse` dans `cli.py`. Lancement via
`python -m voltapeak_batch.cli` — cohérent avec le `python -m voltapeak_batch`
qui lance déjà la GUI. Si une commande shell raccourcie est
souhaitée (`voltapeak-batch --input …`), il faudra réintroduire un
`pyproject.toml` (volontairement absent aujourd'hui) avec une
entrée `[project.scripts]`.

---

## Moyen terme — robustesse et configurabilité

### 4. Exposer les paramètres d'algorithme

**Motivation.** Les valeurs `window_length=11`, `lambdaFactor=1e3`,
`exclusionWidthRatio=0.03`, `maxSlope=500`, fréquence `50 Hz`, etc.
sont codées en dur. Un opérateur qui veut adapter l'outil à une autre
expérience doit modifier le code source.

**Piste technique.** Deux options complémentaires :
- **GUI** : ajouter un onglet « Paramètres avancés » avec champs
  éditables et valeurs par défaut raisonnables ;
- **Fichier** : `config.toml` à la racine du projet, chargé au
  démarrage (bibliothèque `tomllib` disponible en stdlib depuis
  Python 3.11).

### 5. Tests unitaires et de non-régression

**Motivation.** Aucun test n'existe. Toute modification (même une
correction de typo dans un libellé) peut altérer silencieusement les
sorties numériques.

**Piste technique.** `pytest` + un jeu de **fichiers SWV de référence**
avec sorties attendues :
- tests unitaires sur `smoothSignal`, `getPeakValue`, `calculateSignalBaseLine`
  (valeurs numériques à ε près avec `numpy.testing.assert_allclose`) ;
- tests bout-en-bout sur `processSignalFile` : comparaison du PNG
  (hash perceptuel ou comparaison pixel tolérante) et du CSV ;
- test d'intégration sur l'agrégation Excel (ouverture du XLSX,
  vérification des formules injectées).

### 6. Gestion d'erreurs typée

**Motivation.** `processSignalFile` capture toutes les `Exception` dans
un unique `except` et encapsule le message dans un dictionnaire. Le code
appelant ne peut pas distinguer un fichier mal formé d'un pic introuvable
ou d'un bug.

**Piste technique.** Définir `InvalidSWVFileError`, `PeakNotFoundError`,
`BaselineEstimationError` héritant de `SWVError`. Ne capturer que ces
exceptions spécifiques ; laisser remonter les bugs inattendus.

### 7. Détection automatique des séparateurs

**Motivation.** Chaque utilisateur doit manuellement cocher le bon
séparateur de colonnes et le bon séparateur décimal. Source d'erreur
fréquente.

**Piste technique.** Utiliser `csv.Sniffer` sur les premières lignes
pour détecter le séparateur ; tester le parse en `.` puis en `,`
et retenir celui qui produit des floats. La GUI conserverait le
choix manuel comme override.

### 8. Support d'autres formats d'entrée

**Motivation.** Les potentiostats produisent aussi du `.xlsx`, `.csv`,
ou des formats propriétaires (`.mpt` BioLogic, `.nox` Autolab, etc.).

**Piste technique.** Table de dispatchers `{".txt": readFileText,
".xlsx": readFileExcel, ".mpt": readFileMpt}` et parseurs dédiés par
format. Les premières lignes des fichiers propriétaires contiennent
des métadonnées exploitables (fréquence SWV, pas de potentiel, etc.)
qui pourraient alimenter automatiquement le récapitulatif.

### 9. Internationalisation

**Motivation.** Les libellés de la GUI sont en français. Pour un usage
hors équipe francophone, la traduction devient nécessaire.

**Piste technique.** `gettext` avec fichiers `.po` (fr, en, de…).
Détection automatique de la locale système au premier lancement.

---

## Long terme — plate-forme et écosystème

### 10. Packaging distribuable

**Motivation.** Les utilisateurs finaux (scientifiques) n'ont pas tous
un environnement Python fonctionnel. Leur demander d'installer Python
+ 6 dépendances est un obstacle à l'adoption.

**Piste technique.**
- **Exécutable Windows** via PyInstaller (`--onefile --windowed`) :
  un seul `.exe` double-cliquable. Bien penser à `freeze_support()`
  (déjà présent dans `main`).
- **Paquet pip** sur PyPI si le code est ouvert.
- **Installation isolée** avec `uv tool install` ou `pipx`.

### 11. Interface Web

**Motivation.** Permet un usage multi-utilisateurs, distant, sans
installation locale. Utile en laboratoire partagé.

**Piste technique.**
- **Streamlit** : prototypage rapide, GUI Python quasi-identique à Tkinter.
- **FastAPI + front React/Vue** : plus robuste, API réutilisable.
- Upload d'un dossier zippé, traitement en file d'attente (Celery,
  RQ), résultats téléchargeables.

### 12. Base de données expérimentale

**Motivation.** Chaque campagne produit aujourd'hui un dossier isolé.
Pour comparer entre campagnes, il faut ré-ouvrir manuellement chaque
Excel.

**Piste technique.** SQLite local (ou PostgreSQL pour du multi-utilisateur) ;
schéma `Run(date, opérateur, fréquence, …)`, `File(run_id, base,
électrode, pic_V, pic_A, charge_C, hash_source)`. Interface de
requête simple (Streamlit ou Jupyter).

### 13. Algorithmes alternatifs de baseline

**Motivation.** asPLS n'est pas universel : certains signaux
particuliers sont mieux traités par arPLS, airPLS, drPLS, rolling-ball,
ou une combinaison de polynômes orthogonaux. Offrir le choix
améliorerait la qualité des corrections sur les cas difficiles.

**Piste technique.** La bibliothèque `pybaselines` expose déjà la
plupart de ces algorithmes. Ajouter un sélecteur dans la GUI ;
optionnellement, un **mode comparaison** qui trace les baselines
concurrentes côte à côte sur le PNG.

### 14. Détection multi-pics

**Motivation.** Certains SWV présentent plusieurs pics (mélange
d'espèces électroactives). L'outil actuel n'en détecte qu'un seul.

**Piste technique.** `scipy.signal.find_peaks` sur le signal corrigé
avec seuil de prominence. Ajustement gaussien ou lorentzien pour
l'intégration. Nouvelles colonnes dans le récapitulatif pour le
deuxième pic, troisième pic…

### 15. Rapport PDF automatique

**Motivation.** Un fichier Excel + N fichiers PNG = peu pratique à
archiver ou à partager. Un rapport unifié faciliterait la traçabilité.

**Piste technique.** `reportlab` ou `weasyprint` (HTML → PDF) pour
générer un document par campagne : page de garde (métadonnées),
table des résultats, une page par électrode avec le PNG + les
valeurs numériques.

### 16. Intégration continue (CI/CD)

**Motivation.** Aucun garde-fou ne vérifie aujourd'hui qu'un commit
ne casse pas le code.

**Piste technique.** GitHub Actions (ou GitLab CI) :
- `ruff check` pour le lint ;
- `ruff format --check` pour le formatage ;
- `mypy` pour le typage ;
- `pytest` pour les tests ;
- build de l'exécutable PyInstaller à chaque tag.

### 17. Documentation web hébergée

**Motivation.** Le README est utile mais limité. Une documentation
structurée (tutoriels, référence API, équations d'asPLS) serait
précieuse pour l'adoption.

**Piste technique.** Sphinx ou MkDocs + hébergement GitHub Pages.
Équations rendues en LaTeX via MathJax pour expliquer le modèle
Whittaker/asPLS.

---

## Pistes exploratoires

Idées à évaluer au cas par cas, sans priorité ferme.

### Profilage et optimisation

- **Benchmarker** `Pool.imap` vs `concurrent.futures.ProcessPoolExecutor`
  avec `chunksize` ajusté sur de gros lots (> 500 fichiers).
- **Lazy-loading de matplotlib** : l'import top-level est lent et inutile
  tant que l'utilisateur n'a pas cliqué sur *Lancer l'analyse*.
  Déplacer l'import dans `plotSignalAnalysis`.
- **Cache** : ne pas retraiter un fichier dont le hash SHA-256 n'a pas
  changé depuis la dernière exécution.

### Expérience utilisateur

- **Mode « inspection interactive »** : rejouer l'analyse d'un fichier
  avec des sliders sur `lambdaFactor`, `exclusionWidthRatio` et
  `marginRatio` (matplotlib widgets ou Streamlit), pour ajuster à l'œil.
- **Prévisualisation** avant lancement : afficher le contenu d'un fichier
  pris au hasard pour vérifier que les séparateurs sont corrects.
- **Internationalisation de la colonne `Charge (C)`** : l'unité ambiguë
  (C = coulomb ? ou « Charge » ?) mérite une entête plus explicite.

### Robustesse aux données

- **Gestion des balayages aller-retour** (cyclic SWV) : l'inversion
  systématique du signe pourrait être mal adaptée si la première
  demi-vague est anodique.
- **Validation de la longueur minimale** du signal avant asPLS : le
  filtre `window_length=11` exige au moins 11 points ; en deçà, lever
  une `InvalidSWVFileError` explicite.

---

## Contribuer à cette feuille de route

Les priorités évoluent avec les retours utilisateurs. Si une évolution
vous intéresse — ou si vous en voyez une qui manque — ouvrez une issue
ou contactez le mainteneur.
