# SSH GUI Client pour Raspberry Pi Hexapode

Interface graphique Python/Qt pour contrôler un hexapode Raspberry Pi via SSH avec flux vidéo en temps réel.

## Prérequis

- **Python 3.9+** (testé avec Python 3.9.13)
- pip

## Installation

### Installation des dépendances

```bash
pip install -r requirements.txt
```

Les bibliothèques suivantes seront installées :
- PyQt6 (>=6.6.0) : Framework GUI
- paramiko (>=3.4.0) : Client SSH Python
- cryptography (>=41.0.0) : Chiffrement (requis par paramiko)

## Utilisation

### Lancer l'application

```bash
python main.py
```

### Connexion SSH

1. **Hôte** : Adresse IP (ex: `10.65.2.44`) ou hostname (ex: `raspberrypi.local`)
2. **Port** : 22 (port SSH standard)
3. **Utilisateur** : Nom d'utilisateur SSH (souvent `pi` ou `user`)
4. **Mot de passe** : Mot de passe SSH
5. Cliquez sur **Se connecter**

L'application navigue automatiquement vers `/Documents/Hexapode/`.

### Flux Vidéo

Le flux vidéo démarre automatiquement après la connexion SSH.

**Configuration** :
- URL par défaut : `http://localhost:8081/stream`
- Modifiable dans le champ "URL Flux"
- Nécessite que `navigation_autonome.py` soit lancé sur le Pi

**Dépannage** :
- Vérifiez que le port 8081 est correct (peut varier)
- Testez l'URL dans un navigateur : `http://localhost:8081`
- Relancez le flux avec le bouton "Démarrer Flux"

### Modes de Contrôle

**Mode Automatique** (bouton vert)
- Lance `python3 ./navigation_autonome.py`
- Navigation autonome avec évitement d'obstacles

**Mode Manuel** (bouton bleu)
- Lance `python3 ./deplacement.py`
- Contrôle manuel direct de l'hexapode

**Basculement intelligent** :
- Cliquer sur un mode arrête automatiquement l'autre (Ctrl+C)
- Cliquer 2x sur le même mode n'a pas d'effet (déjà actif)

### Contrôle Hexapode

#### Commandes disponibles

```
[A]     [Z]    [E]
[Q]     [S]    [D]
[    Espace    ]
```

- **Z** : Avancer
- **Q** : Gauche
- **S** : Reculer
- **D** : Droite
- **A** : Action A (personnalisable)
- **E** : Action E (personnalisable)
- **Espace** : Pause/Stop

#### Raccourcis clavier

Les touches Z/Q/S/D/A/E/Espace fonctionnent directement sans cliquer dans un champ de saisie.

**Important** : Ne tapez pas dans un champ de saisie pour utiliser les raccourcis.

## Configuration

Les paramètres sont modifiables dans `config.py` :

```python
# Flux vidéo
DEFAULT_VIDEO_URL = "http://localhost:8081/stream"
DEFAULT_VIDEO_WIDTH = 640
DEFAULT_VIDEO_HEIGHT = 240

# Navigation SSH
DEFAULT_SSH_FOLDER = "Documents/Hexapode"

# Fenêtre
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 700

# Programmes hexapode
AUTO_PROGRAM = "python3 ./navigation_autonome.py"
MANUAL_PROGRAM = "python3 ./deplacement.py"
```

## Structure du Projet

```
IHM/
├── main.py                   # Point d'entrée de l'application
├── ssh_main_window.py        # Fenêtre principale (UI)
├── ssh_client.py             # Gestion de la connexion SSH
├── video_stream_reader.py    # Lecture flux MJPEG
├── ssh_signals.py            # Signaux PyQt pour SSH
├── video_signals.py          # Signaux PyQt pour vidéo
├── config.py                 # Configuration centralisée
├── requirements.txt          # Dépendances Python
├── README.md                 # Ce fichier
└── Existant/
    ├── navigation_autonome.py  # Navigation automatique (Pi)
    ├── deplacement.py          # Contrôle manuel (Pi)
    └── test_keyboard.py        # Tests clavier (Pi)
```

## Architecture

### Classes principales

- **SSHClient** : Gestion de la connexion SSH avec paramiko
- **VideoStreamReader** : Lecture de flux MJPEG via HTTP
- **SSHMainWindow** : Interface graphique Qt
- **SSHSignals** : Signaux PyQt pour communication SSH
- **VideoSignals** : Signaux PyQt pour communication vidéo

### Schéma UI

```
┌─────────────────────────────────────────┐
│     Connexion SSH (Host/Port/User)      │
├─────────────────────────────────────────┤
│  [Automatique]     [Manuel]             │
├────────────┬────────────────────────────┤
│  Vidéo     │      Terminal              │
│  640x240   │      SSH Live              │
├────────────┴────────────────────────────┤
│  Commande: [________] [Envoyer]         │
├─────────────────────────────────────────┤
│         Contrôle Hexapode (7 btns)      │
└─────────────────────────────────────────┘
```

## Dépannage

### "Erreur d'authentification"
- Vérifiez utilisateur et mot de passe
- SSH doit être activé sur le Pi : `sudo raspi-config` → Interface Options → SSH

### "Flux non disponible"
- Vérifiez que `navigation_autonome.py` tourne sur le Pi
- Testez `http://localhost:8081` dans un navigateur
- Vérifiez le port dans le champ "URL Flux"

### Touches clavier ne fonctionnent pas
- Ne tapez pas dans un champ de saisie
- Cliquez sur le terminal ou ailleurs dans la fenêtre
- Le debug "[DEBUG: Touche Espace détectée]" apparaît si capturée

### Programmes ne se lancent pas
- Assurez-vous d'être dans `/Documents/Hexapode/`
- Vérifiez que les scripts existent sur le Pi
- Utilisez le terminal pour lancer manuellement si besoin

## Fonctionnalités

- Connexion SSH interactive avec terminal en temps réel
- Flux vidéo MJPEG de la caméra hexapode (640x240)
- Modes de contrôle : Automatique (navigation autonome) et Manuel
- Contrôle hexapode : 7 commandes (Z/Q/S/D/A/E/Espace)
- Nettoyage ANSI : Affichage terminal propre sans codes d'échappement
- Navigation automatique vers Documents/Hexapode/
- Gestion intelligente : Arrêt automatique de programme lors du changement de mode

## Améliorations Futures

- Sauvegarde de profils de connexion
- Authentification par clé SSH
- Transfert de fichiers (SFTP)
- Historique des commandes (flèches haut/bas)
- Onglets pour connexions multiples
- Enregistrement du flux vidéo

## Licence

Projet éducatif - Libre d'utilisation

## Informations

**Version** : 1.0  
**Python** : 3.9+  
**Date** : Janvier 2026
