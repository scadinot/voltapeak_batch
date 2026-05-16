# voltapeak_batch

Outil graphique (Tkinter) de **traitement par lot** de fichiers de voltammétrie à vagues carrées (SWV — *Square Wave Voltammetry*), avec correction automatique de ligne de base par l'algorithme **asPLS Whittaker**, parallélisé sur tous les cœurs CPU et **agrégation multi-électrodes** des pics corrigés dans un classeur Excel.

---

## Table des matières

1. [À quoi sert cet outil ?](#à-quoi-sert-cet-outil)
2. [Fonctionnalités](#fonctionnalités)
3. [Prérequis](#prérequis)
4. [Installation](#installation)
5. [Lancement](#lancement)
6. [Format des fichiers d'entrée](#format-des-fichiers-dentrée)
7. [Utilisation — interface graphique](#utilisation--interface-graphique)
8. [Résultats produits](#résultats-produits)
9. [Chaîne de traitement par fichier](#chaîne-de-traitement-par-fichier)
10. [Paramètres algorithmiques](#paramètres-algorithmiques)
11. [Architecture du code](#architecture-du-code)
12. [Performance et multiprocessing](#performance-et-multiprocessing)
13. [Dépannage](#dépannage)
14. [Feuille de route](#feuille-de-route)
15. [Licence et auteur](#licence-et-auteur)

---

## À quoi sert cet outil ?

La **voltammétrie à vagues carrées** (Square Wave Voltammetry, SWV) est une technique électrochimique qui mesure le courant traversant une électrode en fonction d'un potentiel imposé. Le signal obtenu présente un **pic** caractéristique de l'espèce analysée, superposé à une **ligne de base** (*baseline*) qui dérive lentement avec le potentiel.

Pour exploiter le pic, il faut :

1. **lisser** le signal pour atténuer le bruit de mesure ;
2. **estimer puis soustraire** la ligne de base ;
3. **relever** les coordonnées (tension, courant) du pic corrigé.

`voltapeak_batch` automatise ces trois étapes en s'appuyant sur :

- **Savitzky-Golay** pour le lissage (convolution polynomiale locale) ;
- **asPLS Whittaker** (*asymmetric Penalized Least Squares*, bibliothèque [`pybaselines`](https://pybaselines.readthedocs.io/)) pour l'estimation robuste de la baseline, avec une pondération réduite autour du pic afin d'éviter que la baseline ne « suive » et n'efface le pic.

> **Convention de signe.** Le pipeline est calibré pour des **SWV cathodiques** : `processData` inverse systématiquement le signe du courant avant `argmax`, donc le pic doit apparaître **en courant négatif** dans le fichier d'entrée. Un fichier où le pic est déjà en courant positif (orientation anodique) sera mal traité — il faut alors inverser la colonne en amont.

`voltapeak_batch` cible les **campagnes multi-électrodes multi-échantillons** : chaque fichier porte un nom de la forme `<base>_C<NN>.txt` (`ESSAI1_C01.txt`, `ESSAI1_C02.txt`, …). L'outil traite tous les fichiers du dossier en parallèle et produit un **classeur Excel récapitulatif** regroupant une ligne par base et des colonnes par électrode (Tension, Courant, Charge). Pour de l'exploration interactive d'un seul fichier, utiliser [`voltapeak`](https://github.com/scadinot/voltapeak) ; pour les schémas d'expérience plus structurés (itérations *loops* ou séries de dosage), utiliser [`voltapeak_loops`](https://github.com/scadinot/voltapeak_loops).

---

## Fonctionnalités

- Traitement de **tous les `.txt` d'un dossier**, sélectionné via la GUI.
- **Parallélisation multi-processus** (`multiprocessing.Pool(cpu_count())`), basculable en mode séquentiel.
- **Séparateur de colonnes** et **séparateur décimal** configurables dans l'interface.
- **Lissage** Savitzky-Golay (fenêtre 11, ordre 2).
- **Détection de pic robuste** : exclusion des 10 % de bords du scan et filtre de pente.
- **Estimation de ligne de base asPLS** avec zone d'exclusion ±3 % centrée sur le pic.
- **Agrégation multi-électrodes** : nom `<base>_C<NN>.txt` exploité pour pivoter en colonnes par canal.
- **Excel récapitulatif** avec formule `=Courant/Fréquence` recalculée à la volée.
- **Exports optionnels par fichier** : graphique PNG 300 dpi, CSV ou XLSX nettoyé.
- **Journal de traitement** et **barre de progression** en temps réel.
- Bouton **« Ouvrir le dossier de résultats »** à la fin du traitement.

---

## Prérequis

- **Python ≥ 3.10** — la syntaxe des annotations de type (`T | None`, `tuple[...]`) utilisée dans le code l'impose.
- **Systèmes supportés** : Windows, macOS, Linux.
- **Tkinter** — inclus dans la distribution standard de Python sous Windows et macOS ; sous Linux, installer au préalable le paquet système :

  ```bash
  sudo apt install python3-tk        # Debian / Ubuntu
  sudo dnf install python3-tkinter   # Fedora
  ```

---

## Installation

### 1. Créer et activer un environnement virtuel (recommandé)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

> [`requirements.txt`](requirements.txt) borne les mises à jour aux versions de patch (`~=X.Y.Z`) : un `pip install` ultérieur peut prendre un correctif plus récent, mais ne franchira jamais un changement de version mineur ou majeur susceptible de casser le code. Pour une reproductibilité stricte (mêmes versions exactes sur toutes les machines, dans le temps), figer les versions (`==X.Y.Z`) ou ajouter un lock file (`pip-tools`, `uv`). Le projet n'a pas de `pyproject.toml` : la configuration de chaque outil de lint / typecheck vit dans son fichier dédié ([`ruff.toml`](ruff.toml), [`.pylintrc`](.pylintrc), [`mypy.ini`](mypy.ini), [`pyrightconfig.json`](pyrightconfig.json)).

---

## Lancement

Depuis le **dossier parent** du dossier `voltapeak_batch/` :

```bash
python -m voltapeak_batch
```

---

## Format des fichiers d'entrée

| Caractéristique          | Valeur                                                       |
|--------------------------|--------------------------------------------------------------|
| Extension                | `.txt`                                                       |
| Encodage                 | `latin-1`                                                    |
| Nombre de colonnes       | ≥ 2 (seules les 2 premières sont lues)                       |
| Première ligne           | en-tête — **ignorée** (`skiprows=1`)                         |
| Colonne 1                | Potentiel en volts (float)                                   |
| Colonne 2                | Courant en ampères — **pic attendu en valeur négative** (convention SWV cathodique : le pipeline inverse le signe avant `argmax`) |
| Séparateur de colonnes   | configurable : tabulation / virgule / point-virgule / espace |
| Séparateur décimal       | configurable : point / virgule                               |
| Nombre minimal de lignes | 11 (fenêtre Savitzky-Golay fixe — `savgol_filter` lève une exception en dessous) |

### Convention de nommage

Pour permettre l'agrégation multi-électrodes, le nom de fichier doit suivre le pattern :

```
<base>_C<NN>.txt
```

Exemples valides : `ESSAI1_C01.txt`, `MANIP_2025-04_C12.txt`.

Un fichier qui ne respecte pas ce pattern est traité individuellement mais apparaît dans le récapitulatif Excel avec son nom complet comme *Base* et une colonne d'électrode vide.

### Exemple de contenu (tabulation, point décimal)

```
Potential	Current
-0.500	-1.2e-6
-0.490	-1.1e-6
-0.480	-0.9e-6
...
```

---

## Utilisation — interface graphique

La fenêtre principale s'organise ainsi :

1. **Dossier d'entrée** — bouton **Parcourir** pour sélectionner le dossier contenant les fichiers `.txt`.
2. **Paramètres de lecture** :
   - *Séparateur de colonnes* : `Tabulation` (défaut), `Virgule`, `Point-virgule`, `Espace` ;
   - *Séparateur décimal* : `Point` (défaut) ou `Virgule` ;
   - *Export par fichier* : `Ne pas exporter` (défaut), `.CSV` ou `Excel` ;
   - *Mode de traitement* : `Activer le multi-thread (un processus par cœur)` (défaut) ou `Désactiver (traitement séquentiel)`.
3. **Progression du traitement** — barre se remplissant au fil de l'avancement.
4. **Journal de traitement** — chaque fichier traité (ou en erreur, en rouge) y apparaît, suivi d'un récapitulatif final (nombre de fichiers, durée totale).
5. **Actions** :
   - **Lancer l'analyse** : démarre le traitement parallèle ;
   - **Ouvrir le dossier de résultats** : s'active en fin de traitement et ouvre l'explorateur natif sur le dossier de sortie.

---

## Résultats produits

À chaque exécution, un dossier frère du dossier d'entrée est créé :

```
<dossier_entrée>            ← vos fichiers .txt
<dossier_entrée> (results)  ← sortie générée
```

Le dossier de sortie est **nettoyé automatiquement** au début de chaque exécution (fichiers `.png`, `.csv` et `.xlsx` supprimés).

### Par fichier traité

| Fichier      | Toujours produit ? | Contenu                                                                                                                         |
|--------------|:------------------:|---------------------------------------------------------------------------------------------------------------------------------|
| `<nom>.png`  | oui                | Graphique 300 dpi : signal brut, lissé, baseline asPLS, signal corrigé, marqueur de pic + ligne verticale au potentiel du pic.  |
| `<nom>.csv`  | si option *.CSV*   | Colonnes `Potential`, `Current`, `SignalLisse`, `SignalCorrigé`.                                                                |
| `<nom>.xlsx` | si option *Excel*  | Mêmes colonnes que le CSV.                                                                                                      |

### Récapitulatif agrégé

Un unique `<nom_du_dossier>.xlsx` est écrit à la racine du dossier de résultats **dès qu'au moins un fichier valide a été traité** (en l'absence de résultat exploitable, le classeur n'est pas produit). Il regroupe une ligne par base, avec les colonnes suivantes pour chaque électrode détectée :

| Colonne                  | Source                                                                                                                                |
|--------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| `Base`                   | base extraite du nom de fichier                                                                                                       |
| `Fréq (Hz)`              | **50,0** par défaut (valeur codée en dur, voir [`ROADMAP.md`](ROADMAP.md))                                                            |
| `C<NN> - Tension (V)`    | potentiel du pic après correction                                                                                                     |
| `C<NN> - Courant (A)`    | amplitude du pic après correction                                                                                                     |
| `C<NN> - Charge (C)`     | **formule Excel** `=Courant / Fréq` — recalculée dynamiquement si la fréquence est modifiée dans la cellule                            |

---

## Chaîne de traitement par fichier

```
┌──────────────────────────┐
│ Fichier *.txt (entrée)   │
└────────────┬─────────────┘
             │ readFile()       séparateur & décimale configurables
             ▼
┌──────────────────────────┐
│ DataFrame brut           │
└────────────┬─────────────┘
             │ processData()    courant=0 supprimé, tri sur potentiel, -I
             ▼
┌──────────────────────────┐
│ Signal nettoyé           │
└────────────┬─────────────┘
             │ smoothSignal()   Savitzky-Golay (w=11, ordre=2)
             ▼
┌──────────────────────────┐
│ Signal lissé             │
└────────────┬─────────────┘
             │ getPeakValue()   pic dans la zone centrale, filtre de pente
             ▼
┌───────────────────────────┐
│ (x_pic, y_pic) provisoires│
└────────────┬──────────────┘
             │ calculateSignalBaseLine()  asPLS, exclusion ±3 % autour du pic
             ▼
┌──────────────────────────┐
│ Baseline estimée         │
└────────────┬─────────────┘
             │ signal_corrigé = signal_lissé - baseline
             ▼
┌──────────────────────────┐
│ Signal corrigé           │
└────────────┬─────────────┘
             │ getPeakValue()   pic final
             ▼
┌──────────────────────────┐
│ (x_pic, y_pic) corrigés  │
└────────────┬─────────────┘
             │ exports optionnels (PNG / CSV / XLSX)
             ▼
┌──────────────────────────┐
│ dict de résultat         │  → agrégé dans le classeur Excel récap
└──────────────────────────┘
```

---

## Paramètres algorithmiques

Les hyperparamètres sont actuellement **codés en dur** dans le script. Leur exposition dans l'interface graphique est prévue (voir [`ROADMAP.md`](ROADMAP.md)).

| Paramètre               | Valeur     | Rôle                                                                                         |
|-------------------------|------------|----------------------------------------------------------------------------------------------|
| `window_length`         | `11`       | Largeur de la fenêtre Savitzky-Golay (nombre impair de points).                              |
| `polyorder`             | `2`        | Ordre du polynôme ajusté localement par Savitzky-Golay.                                      |
| `marginRatio`           | `0.10`     | Fraction de points exclus aux deux bords lors de la recherche du pic.                        |
| `maxSlope`              | `500`      | Pente absolue maximale tolérée pour un candidat-pic (filtre les fronts).                     |
| `exclusionWidthRatio`   | `0.03`     | Demi-largeur (fraction de la plage de potentiel) de la zone protégée autour du pic.          |
| `lambdaFactor`          | `1e3`      | Facteur multiplicatif du paramètre de lissage Whittaker : `lam = lambdaFactor · n²`.         |
| `aspls.diff_order`      | `2`        | Ordre de différence dans l'ajustement Whittaker.                                             |
| `aspls.tol`             | `1e-2`     | Tolérance de convergence.                                                                    |
| `aspls.max_iter`        | `25`       | Nombre maximum d'itérations de réajustement des poids.                                       |
| Fréquence injectée      | `50 Hz`    | Utilisée pour `Charge = Courant / Fréquence` dans le classeur récap.                         |

---

## Architecture du code

Le projet est un package Python minimal — deux fichiers seulement :

| Fichier                      | Rôle                                                                                                  |
|------------------------------|-------------------------------------------------------------------------------------------------------|
| [`__init__.py`](__init__.py) | Métadonnées du package (`__version__`) — marque le dossier comme package et permet `python -m voltapeak_batch`. |
| [`__main__.py`](__main__.py) | Code applicatif complet (pipeline + GUI Tkinter + entry point `main()`).                              |

Chaînage des appels :

```
main()
 └── launch_gui()                    Tkinter — construit et affiche la fenêtre
      ├── (callback Parcourir)       sélection du dossier d'entrée
      └── run_analysis()             callback du bouton Lancer l'analyse
           └── iter_results()        générateur — choisit le mode au runtime
                ├── (multi-thread)   Pool(cpu_count()).imap(processFileWrapper, …)
                └── (séquentiel)     boucle for args : processFileWrapper(args)
                     └── processSignalFile()     traitement d'un fichier
                          ├── readFile()
                          ├── processData()
                          ├── smoothSignal()
                          ├── getPeakValue()            (signal lissé)
                          ├── calculateSignalBaseLine()
                          ├── getPeakValue()            (signal corrigé)
                          └── plotSignalAnalysis()      (PNG)

           └── agrégation pandas → export .xlsx récap
```

---

## Performance et multiprocessing

- Par défaut, le script utilise `multiprocessing.Pool(processes=cpu_count())` : **tous les cœurs CPU** sont sollicités.
- `Pool.imap` (et non `Pool.map`) est volontairement choisi : les résultats sont **restitués au fil de l'eau dans l'ordre des fichiers d'entrée**, ce qui permet de rafraîchir la barre de progression et le journal pendant le traitement, sans attendre la fin du lot.
- Le backend matplotlib `'Agg'` (non-interactif) est **obligatoire** : les processus enfants du pool n'ont pas accès au thread Tk.

### Mode séquentiel (option *Désactiver*)

L'option *Mode de traitement → Désactiver (traitement séquentiel)* exécute la chaîne complète **dans le processus principal**, fichier après fichier. Utile quand :

- vous **déboguez** le pipeline : les exceptions des workers sont parfois absorbées par le pool et difficiles à tracer ;
- l'**export PNG matplotlib** se comporte mal sur votre installation (anciens drivers graphiques, conflits de backend) ;
- vous tournez sur un environnement **contraint** (machine virtuelle à 1 vCPU, sandbox CI) où le `Pool` apporte un surcoût sans gain réel.

`freeze_support()` est appelé dans `main()` pour permettre un éventuel packaging PyInstaller sous Windows.

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Erreur dans le fichier … : Error tokenizing data` | Mauvais séparateur de colonnes | Choisir le bon séparateur dans la GUI |
| Toutes les valeurs sont lues comme chaînes ou zéro | Mauvais séparateur décimal | Basculer entre *Point* et *Virgule* |
| Pic « inversé » ou détecté loin du sommet visible | Fichier avec pic déjà en courant positif (orientation anodique) | Pré-inverser la colonne courant en amont — le pipeline attend une convention cathodique (cf. [Format des fichiers d'entrée](#format-des-fichiers-dentrée)) |
| Le pic détecté est sur un bord | Bruit important aux extrémités | Augmenter `marginRatio` dans le code |
| La baseline épouse le pic | `lambdaFactor` trop bas ou zone d'exclusion trop étroite | Augmenter `lambdaFactor` ou `exclusionWidthRatio` |
| Le fichier n'apparaît pas dans la bonne colonne d'électrode du récap | Nom de fichier ne respectant pas `<base>_C<NN>.txt` | Renommer les fichiers |
| Journal vide et pas de traitement | Aucun `.txt` dans le dossier sélectionné | Vérifier l'extension et le dossier |
| Crash au démarrage sous Linux (`ModuleNotFoundError: _tkinter`) | Tkinter non installé | `sudo apt install python3-tk` |

---

## Feuille de route

Voir [`ROADMAP.md`](ROADMAP.md) pour l'ensemble des évolutions prévues.

---

## Licence et auteur

- **Auteur** : Stéphane Cadinot ([@scadinot](https://github.com/scadinot)).
- **Licence** : MIT — voir [`LICENSE`](LICENSE).

Pour toute question ou contribution, ouvrir une *issue* sur le dépôt GitHub.
