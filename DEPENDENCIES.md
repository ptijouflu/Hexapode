# 📦 Résumé de l'installation des dépendances

## ✅ Dépendances installées

Les packages suivants ont été installés avec succès :

```
✅ dynamixel_sdk      - Communication avec les servomoteurs Dynamixel
✅ opencv-python (cv2) - Traitement d'images et détection de couleurs
✅ numpy              - Calculs numériques
✅ evdev              - Accès aux événements d'entrée
✅ keyboard           - Contrôle du clavier
✅ pyserial (serial)  - Communication série
```

## 📌 Vérification des dépendances

Vous pouvez à tout moment vérifier les dépendances avec :

```bash
python3 check_dependencies.py
```

## ⚠️ Note sur pynput

`pynput.keyboard` est utilisé dans `keyboard_test.py` mais nécessite un serveur X11 qui n'est pas disponible en SSH.

**Solution :** 
- Exécutez `keyboard_test.py` directement sur le Raspberry Pi avec un écran (HDMI)
- Ou utilisez le module `keyboard` à la place (déjà installé)

## 🎥 Lancer la détection de couleur

```bash
# Mode simple
python3 Pictures/camera_color_detection_ssh.py

# Avec calibration
python3 Pictures/calibrate_interactive.py
```

## 🧪 Lancer les tests

```bash
# Test du mouvement forward
python3 test_forward.py

# Test de calibration des couleurs
python3 Pictures/calibrate_interactive.py
```

## 📝 Installation manuelle des dépendances

Si vous rencontrez des problèmes, vous pouvez réinstaller manuellement :

```bash
pip3 install --break-system-packages \
  dynamixel-sdk \
  opencv-python \
  numpy \
  evdev \
  keyboard \
  pynput
```

---
**Date:** 6 Décembre 2025
**Plateforme:** Raspberry Pi + SSH
**Python:** 3.13
