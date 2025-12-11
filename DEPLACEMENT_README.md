# 🎮 Contrôle du Déplacement Hexapode - Versions SSH Compatible

## 📋 Vue d'ensemble

Trois versions du contrôle au clavier sont disponibles, chacune avec ses avantages :

### 1. **deplacement_keyboard.py** (Version modifiée originale) ✅ RECOMMANDÉE
- **Avantage** : Mode fallback automatique
- **Fonctionnement** : 
  - Essaie d'abord d'utiliser pynput (mode X11 avec écran HDMI)
  - Si pynput échoue, bascule automatiquement au module keyboard natif (SSH compatible)
- **Utilisation** : `python3 deplacement_keyboard.py`
- **Caractéristiques** : Affichage des mouvements tous les 10 frames

### 2. **deplacement_keyboard_ssh.py** (Version optimisée SSH)
- **Avantage** : Optimisé exclusivement pour SSH
- **Fonctionnement** : Utilise le module keyboard natif (pas de pynput)
- **Utilisation** : `python3 deplacement_keyboard_ssh.py`
- **Caractéristiques** :
  - Plus rapide que la version avec fallback
  - Meilleure réactivité en SSH
  - Affichage détaillé des frames

### 3. **deplacement_interactive.py** (Version interactive ligne de commande)
- **Avantage** : Aucune dépendance de clavier, basée sur stdin
- **Fonctionnement** : Saisir les commandes au clavier et presser ENTRÉE
- **Utilisation** : `python3 deplacement_interactive.py`
- **Caractéristiques** :
  - Parfait pour SSH
  - Interface conviviale avec aide intégrée
  - Commandes texte explicites

---

## 🎮 Contrôles

### Version clavier (deplacement_keyboard.py et deplacement_keyboard_ssh.py)
```
Z     - Avancer
Q     - Tourner à gauche
S     - Reculer
D     - Tourner à droite
ESPACE - Arrêter
Ctrl+C - Quitter
```

### Version interactive (deplacement_interactive.py)
```
z     - Avancer
q     - Tourner à gauche
s     - Reculer
d     - Tourner à droite
space - Arrêter
h     - Afficher l'aide
quit/exit - Quitter
```

---

## 🚀 Quelle version utiliser ?

### Sur Raspberry Pi avec écran (HDMI)
```bash
python3 deplacement_keyboard.py
# → Utilise pynput avec X11 (meilleure réactivité)
```

### En SSH (connexion distante)
**Option 1 (Recommandée)** - Avec fallback automatique :
```bash
python3 deplacement_keyboard.py
# → Utilise keyboard natif (SSH compatible)
```

**Option 2** - Version optimisée :
```bash
python3 deplacement_keyboard_ssh.py
# → Version dédiée à SSH
```

**Option 3** - Interface interactive :
```bash
python3 deplacement_interactive.py
# → Commandes textes interactives (plus simple à déboguer)
```

---

## 🔧 Dépendances

| Module | Version | Utilisé par | Statut |
|--------|---------|------------|--------|
| keyboard | - | Toutes les versions | ✅ Installé |
| pynput | 1.8.1 | deplacement_keyboard.py (optionnel) | ⚠️ Optionnel (X11 requis) |
| controller | Local | Toutes les versions | ✅ Local |
| movementbank | Local | Toutes les versions | ✅ Local |

---

## 🐛 Dépannage

### Erreur : "module 'keyboard' has no attribute 'Listener'"
**Cause** : pynput n'est pas disponible (normal en SSH)
**Solution** : Utiliser `deplacement_keyboard_ssh.py` ou `deplacement_interactive.py`

### Erreur : "pynput not supported on this platform"
**Cause** : Pas de serveur X11 (normal en SSH)
**Solution** : Utiliser `deplacement_keyboard_ssh.py` ou `deplacement_interactive.py`

### Pas de réactivité au clavier
**Cause** : Permissions insuffisantes pour accéder aux événements clavier
**Solution** :
```bash
# Pour keyboard natif, vous devez être root ou dans le groupe input
sudo python3 deplacement_keyboard_ssh.py
# Ou
sudo usermod -a -G input $USER
```

### Erreur de connexion au Dynamixel
**Cause** : Pas de connexion série avec les servomoteurs
**Solution** : Vérifier la connexion USB et les permissions :
```bash
ls -la /dev/ttyUSB*
sudo chmod 666 /dev/ttyUSB*
```

---

## 📊 Comparaison des versions

| Feature | Original | SSH | Interactive |
|---------|----------|-----|-------------|
| SSH compatible | ⚠️ (fallback) | ✅ | ✅ |
| Réactivité clavier | ✅ | ✅ | ⚠️ (ENTRÉE requise) |
| Dépendances externes | ⚠️ | ✅ | ✅ |
| Facile à déboguer | ⚠️ | ✅ | ✅ |
| Affichage frames | ✅ | ✅ | ✅ |

---

## 📝 Exemple de démarrage

```bash
# Sur Raspberry Pi en SSH
ssh user@raspberry-pi

# Vérifier les dépendances
python3 check_dependencies.py

# Lancer le contrôle (version recommandée)
python3 deplacement_keyboard.py

# Ou version interactive
python3 deplacement_interactive.py
```

---

**Créé le** : 6 Décembre 2025  
**Compatible** : Raspberry Pi + SSH  
**Python** : 3.13+
