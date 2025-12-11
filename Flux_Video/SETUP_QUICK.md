# 🎥 Setup Streaming Hexapode - Quick Start

## Installation de dépendances (RPi)

```bash
# Sur le Raspberry Pi:
sudo apt update
sudo apt install rpicam-apps python3-venv

cd ~/Hexapode/Flux_Video

# Créer virtual env
python3 -m venv venv
source venv/bin/activate

# Installer packages Python
pip install -q opencv-python ultralytics numpy pillow

# Vérifier installation
python3 -c "import cv2; print(f'✓ OpenCV {cv2.__version__}')"
python3 -c "import ultralytics; print(f'✓ ultralytics {ultralytics.__version__}')"
rpicam-hello -t 1  # Test caméra
```

## Démarrer le streaming (RPi)

```bash
cd ~/Hexapode/Flux_Video
source venv/bin/activate

# Sans détection (plus rapide, ~300 FPS)
python3 camera_stream.py --port 8080 --no-detection

# Avec détection YOLO (nano = ~20 FPS)
python3 camera_stream.py --port 8080 --model nano

# Ou utiliser le script:
./start_stream.sh --no-detection
```

## Accès depuis PC

```bash
# Terminal PC:
ssh -L 8080:localhost:8080 user@10.187.69.95

# Navigateur PC:
http://localhost:8080
```

## Réseau

- **RPi IP:** 10.187.69.95
- **PC IP:** 10.187.69.179
- **Port:** 8080 (HTTP MJPEG)
- **SSH:** user@10.187.69.95:22

## Fichiers importants

| Fichier | Rôle |
|---------|------|
| `camera_stream.py` | ✅ **Script principal (production)** |
| `start_stream.sh` | Wrapper de démarrage |
| `camera_test.py` | Tests système (⚡ tout passe) |
| `CAMERA_STREAM_README.md` | Documentation complète |

## Vérification

```bash
# Sur RPi:
ps aux | grep camera_stream  # Vérifier le processus
netstat -tlnp | grep 8080     # Vérifier le port

# Test caméra:
rpicam-hello -t 3
rpicam-jpeg -o test.jpg
```

## Troubleshooting

```bash
# Si "Aucune frame disponible":
ls /tmp/camera_stream/     # Vérifier frames créées
which rpicam-jpeg          # Vérifier commande existe

# Si port déjà utilisé:
python3 camera_stream.py --port 9000

# Si YOLO lent:
python3 camera_stream.py --model nano  # Utiliser nano au lieu de small
```

---

**Status:** ✅ Fonctionnel  
**Testé:** Lau RPi avec caméra IMX219  
**Performance:** Sans détection 300+ FPS, Avec nano 15-25 FPS
