# voltapeak_batch

**Analyse automatisée par lot de fichiers de voltampérométrie à onde carrée
(SWV — *Square Wave Voltammetry*) avec correction de ligne de base par
l'algorithme asPLS.**

Cet outil traite tous les fichiers `.txt` d'un dossier, corrige leur ligne
de base, détecte la position et l'amplitude du pic de courant, puis
agrège les résultats multi-électrodes dans un unique fichier Excel.
L'ensemble est exposé via une interface graphique Tkinter et parallélisé
sur tous les cœurs disponibles.

---

## Table des matières

1. [À quoi sert cet outil ?](#à-quoi-sert-cet-outil-)
2. [Pipeline de traitement](#pipeline-de-traitement)
3. [Prérequis](#prérequis)
4. [Installation](#installation)
5. [Lancement](#lancement)
6. [Format des fichiers d'entrée](#format-des-fichiers-dentrée)
7. [Fichiers produits en sortie](#fichiers-produits-en-sortie)
8. [Paramètres de l'algorithme](#paramètres-de-lalgorithme)
9. [Parallélisme](#parallélisme)
10. [Dépannage](#dépannage)
11. [Structure du code](#structure-du-code)
12. [Licence](#licence)

---

## À quoi sert cet outil ?

Lors d'expériences de voltampérométrie à onde carrée, on mesure un courant
en fonction du potentiel. Le signal utile — un pic centré sur le
potentiel caractéristique de l'espèce électroactive — est superposé à
une **ligne de base** lentement variable (capacité de la double couche,
fond électrochimique, dérives). L'analyse quantitative nécessite donc
de soustraire cette ligne de base pour ne garder que le pic.

Le script automatise ce traitement pour des **campagnes multi-électrodes
multi-échantillons** : chaque fichier porte un nom de la forme
`<base>_C<NN>.txt` (ex. `ESSAI1_C01.txt`, `ESSAI1_C02.txt`, …). L'outil
produit :

- un graphique PNG d'analyse par fichier ;
- éventuellement un CSV ou un XLSX par fichier (signal lissé + corrigé) ;
- un **fichier Excel récapitulatif** regroupant une ligne par base et
  des colonnes par électrode (Tension, Courant, Charge), avec une
  formule Excel `=Courant/Fréquence` injectée pour la charge.

---

## Pipeline de traitement

Pour chaque fichier `.txt`, la chaîne appliquée est la suivante :

```
┌─────────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────────────┐
│  readFile (CSV) │ → │ processData  │ → │ Savitzky-Golay │ → │ détection de pic │
└─────────────────┘   │ (tri + signe)│   │  (window=11,   │   │  (margin 10 %,   │
                      └──────────────┘   │    order=2)    │   │   maxSlope=500)  │
                                         └────────────────┘   └────────┬─────────┘
                                                                       │
                       ┌──────────────────────────────────────┐        │
                       │        asPLS (baseline)              │ ←──────┘
                       │  poids=0,001 dans la fenêtre du pic  │
                       │  λ = lambdaFactor · n²               │
                       └───────────────┬──────────────────────┘
                                       │
                       ┌───────────────▼──────────────────────┐
                       │   signal corrigé = lissé − baseline  │
                       │   re-détection de pic                │
                       └───────────────┬──────────────────────┘
                                       │
              ┌────────────┬───────────┼───────────┬─────────────────────┐
              ▼            ▼           ▼           ▼                     ▼
         PNG (300 dpi)   CSV/XLSX    tuple         agrégation      Excel final
                         optionnel   (V, A)        inter-fichiers  (1 ligne/base)
```

---

## Prérequis

- **Python ≥ 3.10** (les annotations `T | None` et `tuple[...]` utilisées
  dans le code nécessitent Python 3.10 ou supérieur).
- **Systèmes supportés** : Windows, macOS, Linux.
- **Tkinter** : inclus dans la bibliothèque standard sur Windows et macOS.
  Sous Linux, installer au préalable le paquet système :
  ```bash
  sudo apt install python3-tk        # Debian/Ubuntu
  sudo dnf install python3-tkinter   # Fedora
  ```

---

## Installation

Il est recommandé de créer un environnement virtuel dédié :

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

Puis installer les dépendances :

```bash
pip install numpy pandas matplotlib pybaselines scipy openpyxl
```

Alternative équivalente :

```bash
pip install -r requirements.txt
```

(le fichier [requirements.txt](requirements.txt) est tenu à jour avec
les dépendances déclarées dans `pyproject.toml`.)

---

## Lancement

Depuis le dossier du projet :

```bash
python voltapeak_batch.py
```

La fenêtre principale s'ouvre :

1. **Dossier d'entrée** — cliquer sur *Parcourir* et sélectionner le
   dossier contenant les fichiers `.txt`.
2. **Paramètres de lecture** — choisir :
   - le séparateur de colonnes (*Tabulation*, *Virgule*, *Point-virgule*,
     *Espace*) ;
   - le séparateur décimal (*Point* ou *Virgule*) ;
   - l'option d'export par fichier (*Ne pas exporter*, *CSV*, *Excel*) ;
   - le **traitement parallèle** (*Activer le multi-thread (un processus
     par cœur)* ou *Désactiver (traitement séquentiel)*) — activé par
     défaut ; passer en séquentiel si vous déboguez ou si le
     multiprocessing pose problème sur la machine hôte.
3. **Lancer l'analyse** — le traitement démarre. Le *Journal*
   affiche chaque fichier traité (ou l'erreur rencontrée en rouge) et
   la *Barre de progression* progresse au fil de l'eau.
4. **Ouvrir le dossier de résultats** — une fois le traitement terminé,
   ce bouton s'active et ouvre le dossier dans l'explorateur natif.

---

## Format des fichiers d'entrée

Chaque fichier `.txt` doit contenir :

- une **première ligne d'entête** (ignorée), généralement produite par
  le potentiostat ;
- **deux colonnes** : *Potentiel* (V) et *Courant* (A) ;
- **séparateur de colonnes** : configurable dans la GUI ;
- **séparateur décimal** : `.` ou `,` ;
- **encodage** : Latin-1 (par défaut les entêtes de potentiostats
  français peuvent contenir des caractères accentués).

### Convention de nommage

Pour permettre l'agrégation multi-électrodes, le nom de fichier doit
suivre le pattern :

```
<base>_C<NN>.txt
```

Exemples valides : `ESSAI1_C01.txt`, `MANIP_2025-04_C12.txt`.

Si un fichier ne respecte pas ce pattern, il est traité individuellement
mais apparaît dans le récapitulatif Excel avec son nom complet comme
*Base* et une colonne d'électrode vide.

### Exemple de contenu

```
Potentiel (V)	Courant (A)
-0.500	1.2345e-06
-0.495	1.3412e-06
-0.490	1.4561e-06
...
```

---

## Fichiers produits en sortie

À chaque exécution, un dossier frère du dossier d'entrée est créé :

```
<dossier_entrée>          ← vos fichiers .txt
<dossier_entrée> (results) ← sortie générée
```

Le dossier de sortie est **nettoyé automatiquement** au début de
chaque exécution : les fichiers existants `.png`, `.csv` et `.xlsx`
y sont supprimés.

### Par fichier traité

| Fichier | Toujours produit ? | Contenu |
|---|:---:|---|
| `<nom>.png` | oui | Graphique 300 dpi : signal brut, lissé, baseline asPLS, signal corrigé, marqueur de pic + ligne verticale au potentiel du pic. |
| `<nom>.csv` | si option « Exporter au format .CSV » | Colonnes `Potential`, `Current`, `SignalLisse`, `SignalCorrigé`. |
| `<nom>.xlsx` | si option « Exporter au format Excel » | Mêmes colonnes que le CSV. |

### Récapitulatif agrégé

Un unique `<nom_du_dossier>.xlsx` est écrit à la racine du dossier de
résultats. Il regroupe **une ligne par base**, avec les colonnes
suivantes pour chaque électrode détectée :

| Colonne | Source |
|---|---|
| `Base` | base extraite du nom de fichier |
| `Fréq (Hz)` | **50,0** par défaut (valeur codée en dur, voir [roadmap](ROADMAP.md#moyen-terme--robustesse-et-configurabilité)) |
| `C<NN> - Tension (V)` | potentiel du pic après correction |
| `C<NN> - Courant (A)` | amplitude du pic après correction |
| `C<NN> - Charge (C)` | **formule Excel** `=Courant / Fréq` — recalculée dynamiquement si vous modifiez la fréquence |

---

## Paramètres de l'algorithme

Les valeurs par défaut sont définies dans le code source et ne sont
pas (encore) exposées dans l'interface graphique.

| Paramètre | Valeur par défaut | Rôle |
|---|---|---|
| `window_length` (Savitzky-Golay) | **11** | largeur de la fenêtre de lissage |
| `polyorder` (Savitzky-Golay) | **2** | ordre du polynôme local |
| `marginRatio` | **0,10** | fraction des bords exclue pour la détection de pic (10 % de chaque côté) |
| `maxSlope` | **500** | plafond de pente absolue `|dI/dV|` : écarte les flancs des vrais sommets |
| `exclusionWidthRatio` | **0,03** | demi-largeur (en fraction de la plage de potentiel) de la zone débridée autour du pic pour asPLS |
| `lambdaFactor` | **1 000** | rigidité de la baseline : λ effectif = `lambdaFactor · n²` |
| `diff_order` (asPLS) | **2** | ordre de la différence pénalisée |
| `tol` (asPLS) | **1e-2** | tolérance de convergence |
| `max_iter` (asPLS) | **25** | nombre maximal d'itérations |
| Fréquence injectée | **50 Hz** | utilisée pour `Charge = Courant / Fréquence` |

### Ajuster ces paramètres

Les valeurs sont codées dans les appels à `getPeakValue`,
`calculateSignalBaseLine` et `run_analysis`. Pour les modifier :

- lissage plus / moins fort → changer `window_length` et `polyorder` ;
- pic plus / moins centré → ajuster `marginRatio` ;
- baseline plus souple (épouse le signal) → **diminuer** `lambdaFactor` ;
- baseline plus rigide (ligne quasi droite) → **augmenter** `lambdaFactor` ;
- fenêtre d'exclusion plus large → augmenter `exclusionWidthRatio`.

---

## Parallélisme

Le mode par défaut — et recommandé — est le traitement parallèle :
`multiprocessing.Pool(cpu_count())`, soit un processus par cœur logique.
L'implémentation s'appuie sur `pool.imap` (et non `pool.map`) afin de
récupérer les résultats **au fil de l'eau** et mettre à jour la barre
de progression et le journal sans attendre la fin du lot.

Un second mode, **séquentiel**, est disponible via la radio *Traitement
parallèle → Désactiver* dans la GUI. Les fichiers sont alors traités
un par un dans le processus principal. Deux cas où il est utile :

- **Déboguer** un fichier qui échoue — les tracebacks sont plus lisibles
  sans la sérialisation inter-processus ;
- **Contourner** un problème de multiprocessing (antivirus bloquant les
  sous-processus, OS sans `fork`, gel PyInstaller mal configuré).

Les deux modes partagent le même générateur `iter_results` : la boucle
d'affichage des logs et de la barre de progression reste identique.

Le backend matplotlib est forcé à `Agg` (non-interactif) dès le
chargement du module : les workers `multiprocessing` n'ont pas de
boucle Tk et un backend GUI y serait inutile, voire instable sur
Linux *headless*. Côté processus principal, seul Tkinter nécessite un
`$DISPLAY` ; les figures ne sont jamais affichées à l'écran,
uniquement sauvegardées en PNG.

L'appel `freeze_support()` dans `main()` est nécessaire pour la
compatibilité avec le gel Windows (PyInstaller).

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Erreur dans le fichier … : Error tokenizing data` | Mauvais séparateur de colonnes | Choisir le bon séparateur dans la GUI |
| Toutes les valeurs sont lues comme chaînes ou zéro | Mauvais séparateur décimal | Basculer entre « Point » et « Virgule » |
| Le pic détecté est sur un bord | Bruit important aux extrémités | Augmenter `marginRatio` dans le code |
| La baseline épouse le pic | `lambdaFactor` trop bas ou zone d'exclusion trop étroite | Augmenter `lambdaFactor` ou `exclusionWidthRatio` |
| Le fichier n'apparaît pas dans la bonne colonne d'électrode du récap | Nom de fichier ne respectant pas `<base>_C<NN>.txt` | Renommer les fichiers |
| Journal vide et pas de traitement | Aucun `.txt` dans le dossier sélectionné | Vérifier l'extension et le dossier |
| Crash au démarrage sous Linux (`ModuleNotFoundError: _tkinter`) | Tkinter non installé | `sudo apt install python3-tk` |

---

## Structure du code

Le projet est actuellement un **script monolithique** unique :

- [voltapeak_batch.py](voltapeak_batch.py) — 11 fonctions :
  - `open_folder` — ouverture multiplateforme de l'explorateur ;
  - `readFile` — chargement CSV avec encodage Latin-1 ;
  - `processData` — nettoyage + tri + inversion du signe ;
  - `smoothSignal` — filtre de Savitzky-Golay ;
  - `getPeakValue` — détection de pic (avec filtre de pente) ;
  - `calculateSignalBaseLine` — estimation asPLS avec exclusion ;
  - `plotSignalAnalysis` — graphique récapitulatif PNG ;
  - `processFileWrapper` — adaptateur `multiprocessing.Pool.imap` ;
  - `processSignalFile` — pipeline complet pour un fichier ;
  - `main` / `launch_gui` — interface Tkinter + orchestration.

Une découpe en modules est prévue (voir [ROADMAP.md](ROADMAP.md)).

---

## Licence

Distribué sous **licence MIT** — voir [LICENSE](LICENSE) pour le texte
intégral. Copyright (c) 2026 @scadinot.
