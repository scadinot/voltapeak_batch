"""
voltapeak_batch
===============

Application Python / Tkinter d'analyse **par lot** de voltampérogrammes
SWV avec correction automatique de la ligne de base par l'algorithme
asPLS, détection robuste du pic, parallélisation
``multiprocessing.Pool`` et agrégation multi-électrodes dans un
unique classeur Excel.

Le code métier (lecture de fichier, lissage Savitzky-Golay, détection
de pic, baseline asPLS, parallélisation, GUI Tkinter, agrégation Excel)
tient en un seul module :mod:`voltapeak_batch.__main__` lancé par
``python -m voltapeak_batch`` depuis le dossier parent.

Ce ``__init__.py`` se contente d'exposer la version du paquet — il
n'effectue aucun effet de bord (pas de lancement de GUI à l'import).
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
