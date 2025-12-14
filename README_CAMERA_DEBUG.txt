📷 CAMÉRA 5MP 1080p - KIT DE DÉPANNAGE COMPLET
===============================================

Vous avez installé une nouvelle caméra 5MP mais elle n'est pas détectée.
Ce kit fournit tous les outils pour diagnostiquer et résoudre le problème.

🎯 COMMANDES À ESSAYER (Dans l'ordre):

1. TEST RAPIDE (30 secondes)
   ╔════════════════════════════════════════════╗
   ║ bash quick_camera_check.sh                 ║
   ╚════════════════════════════════════════════╝
   
2. DIAGNOSTIC COMPLET (2-3 minutes)
   ╔════════════════════════════════════════════╗
   ║ python3 camera_diagnostic.py               ║
   ╚════════════════════════════════════════════╝
   
3. ASSISTANT INTERACTIF (guidé pas à pas)
   ╔════════════════════════════════════════════╗
   ║ python3 camera_assistant.py                ║
   ╚════════════════════════════════════════════╝

📚 FICHIERS D'AIDE DISPONIBLES:

┌─ GUIDES TEXTE ─────────────────────────────────────────────────────┐
│                                                                     │
│ 📄 CAMERA_5MP_SETUP.md                                              │
│    └─ Guide complet d'installation et activation                    │
│       • Démarrage rapide                                            │
│       • Vérification point par point                                │
│       • Problèmes courants                                          │
│                                                                     │
│ 📄 CAMERA_TROUBLESHOOTING.md                                        │
│    └─ Guide détaillé de dépannage                                   │
│       • Tous les cas d'erreur possibles                             │
│       • Solutions étape par étape                                   │
│       • Tests avancés                                               │
│                                                                     │
│ 📄 Flux_Video/CAMERA_STREAM_README.md                               │
│    └─ Documentation du streaming vidéo                              │
│       • Architecture système                                        │
│       • Utilisation du streaming                                    │
│       • Performance et configuration                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─ SCRIPTS PYTHON ────────────────────────────────────────────────────┐
│                                                                     │
│ 🐍 camera_diagnostic.py                    [⭐ À LANCER EN PRIORITÉ] │
│    └─ Diagnostic système complet                                    │
│       • Teste hardware, libcamera, rpicam, OpenCV                   │
│       • Sauvegarde rapport JSON                                     │
│       • Donne recommandations précises                              │
│                                                                     │
│ 🐍 camera_assistant.py                           [Mode interactif] │
│    └─ Assistant guidé pas à pas                                     │
│       • Questions simples                                           │
│       • Recommandations adaptées                                    │
│       • Résumé final                                                │
│                                                                     │
│ 🐍 camera_test.py                         [Test de capture] │
│    └─ Tests et validation                                           │
│       • Capture photo/vidéo                                         │
│       • Vérification des dépendances                                │
│                                                                     │
│ 🐍 camera_stream.py                      [Streaming MJPEG] │
│    └─ Serveur streaming vidéo                                       │
│       • Une fois caméra activée                                     │
│       • Accessible via navigateur                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─ SCRIPTS BASH ──────────────────────────────────────────────────────┐
│                                                                     │
│ 💻 setup_camera_5mp.sh                                              │
│    └─ Installation automatique                                      │
│       • Installe libcamera                                          │
│       • Active caméra dans raspi-config                             │
│       • Configure permissions                                       │
│                                                                     │
│ 💻 quick_camera_check.sh                                            │
│    └─ Test rapide (< 1 minute)                                      │
│       • Vérifie devices vidéo                                       │
│       • Test rpicam-hello                                           │
│       • Test capture JPEG                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

🔍 DIAGNOSTIC RAPIDE (Sans scripts):

Commandes pour comprendre le problème:

  # Voir les devices vidéo
  ls -la /dev/video*

  # Vérifier activation
  raspi-config nonint get_camera

  # Tester caméra (2 secondes)
  timeout 2 rpicam-hello

  # Capturer une photo
  rpicam-jpeg -o test.jpg --timeout=1000 --nopreview

  # Vérifier permissions
  groups $USER

⚠️ PROBLÈMES COURANTS:

┌─ SYMPTÔME: "Aucun /dev/video* trouvé" ──────────────────────────────┐
│                                                                     │
│ 🔧 Solution:                                                        │
│    1. Vérifier connexion CSI (ruban bien enfoncé?)                   │
│    2. Activer: sudo raspi-config nonint do_camera 1                 │
│    3. Redémarrer: sudo reboot                                       │
│                                                                     │
│ 📖 Plus d'infos: CAMERA_TROUBLESHOOTING.md > PROBLÈME 1            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─ SYMPTÔME: "rpicam-hello ne répond pas" ───────────────────────────┐
│                                                                     │
│ 🔧 Solution:                                                        │
│    1. Vérifier le câble CSI                                         │
│    2. Essayer: sudo rpicam-hello                                    │
│    3. Mettre à jour: sudo apt-get update && upgrade                 │
│    4. Redémarrer: sudo reboot                                       │
│                                                                     │
│ 📖 Plus d'infos: CAMERA_TROUBLESHOOTING.md > PROBLÈME 2            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─ SYMPTÔME: "OpenCV ne fonctionne pas" ────────────────────────────┐
│                                                                    │
│ ℹ️  C'est NORMAL avec libcamera                                    │
│                                                                    │
│ ✅ Camera_stream.py fonctionne quand même                          │
│                                                                    │
│ 🔧 Si vous avez besoin d'OpenCV:                                   │
│    pip install opencv-contrib-python                               │
│                                                                    │
│ 📖 Plus d'infos: CAMERA_TROUBLESHOOTING.md > PROBLÈME 3           │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

🚀 PROCHAINES ÉTAPES (Une fois caméra active):

1. Test du streaming:
   cd Flux_Video
   python3 camera_stream.py --port 8080

2. Accès depuis votre PC:
   ssh -L 8080:localhost:8080 user@<rpi_ip>
   Puis ouvrir: http://localhost:8080

3. Test de capture:
   python3 camera_test.py

4. Utiliser avec les scripts de déplacement:
   python3 deplacement_camera.py (ou autre script existant)

📊 ARBORESCENCE:

/Hexapode-main/
├── CAMERA_5MP_SETUP.md              ← Lire ici d'abord!
├── CAMERA_TROUBLESHOOTING.md        ← Guide dépannage complet
├── Flux_Video/
│   ├── setup_camera_5mp.sh          ← Installation auto
│   ├── quick_camera_check.sh        ← Test rapide
│   ├── camera_diagnostic.py         ← Diagnostic détaillé
│   ├── camera_assistant.py          ← Assistant interactif
│   ├── camera_test.py               ← Tests de capture
│   ├── camera_stream.py             ← Streaming MJPEG
│   └── config.env                   ← Configuration

💡 CONSEIL:

Si vous êtes perdu, lancez d'abord:
  python3 camera_diagnostic.py

Il vous donnera un diagnostic exact ET les solutions adaptées.

✨ SUPPORT:

Tous les documents contiennent des détails et solutions.
Si problème persiste après diagnostic:
  1. Générer rapport: python3 camera_diagnostic.py
  2. Sauvegarder: camera_diagnostics_report.json
  3. Consulter CAMERA_TROUBLESHOOTING.md
  4. Vérifier que redémarrage est fait après chaque changement

═══════════════════════════════════════════════════════════════════════════

Version: 11 Décembre 2025
Module: Caméra 5MP 1080p Raspberry Pi
Système: libcamera (pas v4l2 ancien)
Platform: Raspberry Pi 4/5 OS Bullseye/Bookworm
