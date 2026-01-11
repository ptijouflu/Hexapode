#  Hexapode - Robot Hexapode Autonome

Robot hexapode à 6 pattes contrôlé par Raspberry Pi avec navigation autonome et évitement d'obstacles par vision.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.5+-green.svg)
![Dynamixel](https://img.shields.io/badge/Dynamixel-XL430-orange.svg)

---

##  Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Matériel requis](#-matériel-requis)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Architecture du code](#-architecture-du-code)
- [Configuration](#-configuration)
- [Dépannage](#-dépannage)

---

##  Fonctionnalités

- **Contrôle manuel** : Pilotage au clavier (ZQSD + AE)
- **Navigation autonome** : Évitement d'obstacles en temps réel
- **Streaming vidéo** : Interface web pour visualiser la caméra
- **Détection d'obstacles** : Vision par ordinateur (OpenCV)
- **Architecture modulaire** : Code réutilisable et maintenable

---

##  Matériel requis

| Composant | Description |
|-----------|-------------|
| **Raspberry Pi** | Pi 4 ou 5 recommandé |
| **Caméra** | Module caméra Raspberry Pi |
| **Moteurs** | 12x Dynamixel XL430-W250 |
| **Contrôleur** | U2D2 ou USB2AX |
| **Alimentation** | 12V pour les moteurs |

### Schéma de connexion

```
Raspberry Pi
    │
    ├── USB ──► U2D2 ──► Moteurs Dynamixel (1-12)
    │
    └── CSI ──► Caméra Pi
```

---

##  Installation

### Prérequis

- Raspberry Pi OS (Bookworm ou plus récent)
- Python 3.9+
- Connexion internet

### Installation automatique (recommandée)

```bash
# Cloner le dépôt
git clone https://github.com/ptijouflu/Hexapode.git
cd Hexapode

# Lancer l'installation
./install.sh
```

Le script `install.sh` effectue automatiquement :
- Mise à jour du système
- Installation des dépendances (OpenCV, Dynamixel SDK, etc.)
- Configuration du port série
- Ajout de l'utilisateur au groupe `dialout`

>  **Important** : Redémarrez le Raspberry Pi après la première installation pour appliquer les permissions du port série.

### Installation manuelle

```bash
# Dépendances système
sudo apt update
sudo apt install python3 python3-pip python3-opencv libcamera-apps

# Dépendances Python
pip3 install --user --break-system-packages -r requirements.txt

# Permissions port série
sudo usermod -aG dialout $USER

# Redémarrer
sudo reboot
```

---

##  Utilisation

### Contrôle manuel

```bash
python3 deplacement.py
```

**Touches :**
| Touche | Action |
|--------|--------|
| `Z` | Avancer |
| `S` | Reculer |
| `Q` | Translation gauche |
| `D` | Translation droite |
| `A` | Rotation gauche |
| `E` | Rotation droite |
| `ESPACE` | Stop |
| `X` | Quitter |

### Navigation autonome

```bash
python3 navigation_autonome.py
```

**Contrôles :**
- `ESPACE` : Démarrer / Pause / Reprendre
- `Q` ou `Ctrl+C` : Quitter

**Comportement autonome :**
1. Avance automatiquement
2. Obstacle à gauche → Translation droite
3. Obstacle à droite → Translation gauche
4. Obstacle au centre → Contournement
5. Bloqué → Rotation

### Streaming vidéo

Le serveur HTTP démarre automatiquement sur le port **8080**.

**Depuis un autre PC sur le réseau :**
```bash
# Tunnel SSH (remplacer [IP] par l'IP du Pi)
ssh -L 8080:localhost:8080 user@[IP]

# Puis ouvrir dans un navigateur
http://localhost:8080
```

---

##  Architecture du code

```
Hexapode/
├── hexapod/                    # Module principal (partagé)
│   ├── __init__.py
│   ├── constants.py            # Constantes (ports, IDs, seuils)
│   ├── movements.py            # Séquences de mouvement
│   ├── motor_controller.py     # Contrôle des moteurs
│   ├── keyboard_handler.py     # Gestion clavier
│   ├── obstacle_detector.py    # Détection d'obstacles
│   ├── camera.py               # Capture caméra
│   └── http_server.py          # Serveur streaming
│
├── deplacement.py              # Contrôle manuel (ZQSD)
├── navigation_autonome.py      # Navigation autonome
│
├── install.sh                  # Script d'installation
├── requirements.txt            # Dépendances Python
└── README.md                   # Ce fichier
```

### Description des modules

| Module | Description |
|--------|-------------|
| `constants.py` | Port série, IDs moteurs, paramètres caméra, seuils de détection |
| `movements.py` | Séquences d'animation (marche, translation, rotation) |
| `motor_controller.py` | Classe `MotorController` pour piloter les Dynamixel |
| `keyboard_handler.py` | Lecture clavier non-bloquante |
| `obstacle_detector.py` | Classe `ObstacleDetector` (vision OpenCV) |
| `camera.py` | Classe `FastCamera` (libcamera/rpicam) |
| `http_server.py` | Serveur HTTP pour le streaming MJPEG |

---

##  Configuration

### Paramètres moteurs (`hexapod/constants.py`)

```python
DEVICENAME = '/dev/ttyUSB0'     # Port série
BAUDRATE = 1000000              # Vitesse (1 Mbps)
DXL_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # IDs des moteurs
```

### Paramètres de détection (`hexapod/constants.py`)

```python
OBSTACLE_MIN_AREA = 4000        # Surface minimale (pixels²)
OBSTACLE_ROI_TOP = 0.25         # Début zone de détection (25% du haut)
OBSTACLE_EDGE_THRESH = 60       # Sensibilité Canny
OBSTACLE_DIST_THRESHOLD_STOP = 0.65  # Distance critique
```

### Paramètres caméra (`hexapod/constants.py`)

```python
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 240
CAMERA_FPS = 10
```

---

##  Dépannage

### Le port série n'est pas accessible

```bash
# Vérifier les permissions
ls -la /dev/ttyUSB0

# Ajouter l'utilisateur au groupe dialout
sudo usermod -aG dialout $USER

# Redémarrer
sudo reboot
```

### La caméra ne fonctionne pas

```bash
# Tester la caméra
rpicam-still -o test.jpg

# Vérifier que la caméra est activée
sudo raspi-config
# → Interface Options → Camera → Enable
```

### Les moteurs ne répondent pas

1. Vérifier l'alimentation 12V
2. Vérifier les connexions du U2D2
3. Tester avec Dynamixel Wizard 2.0
4. Vérifier les IDs des moteurs dans `constants.py`

### Erreur "No module named 'hexapod'"

```bash
# S'assurer d'être dans le bon répertoire
cd ~/Documents/Hexapode
python3 deplacement.py
```

---

##  Licence

Ce projet est sous licence MIT.

---

##  Auteur

**ptijouflu**

- GitHub: [@ptijouflu](https://github.com/ptijouflu)
