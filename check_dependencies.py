#!/usr/bin/env python3
"""
Script pour vérifier tous les imports manquants
"""

import sys

imports_to_check = [
    'dynamixel_sdk',
    'cv2',
    'numpy',
    'evdev',
    'keyboard',
    'serial',
]

print("="*60)
print("🔍 VÉRIFICATION DES DÉPENDANCES")
print("="*60)

missing = []
installed = []

for module in imports_to_check:
    try:
        __import__(module)
        installed.append(module)
        print(f"✅ {module:20} - OK")
    except ImportError as e:
        missing.append(module)
        print(f"❌ {module:20} - MANQUANT ({str(e)[:40]}...)")

# Note: pynput requires X11 on Raspberry Pi, so we skip it for SSH
print(f"\n⚠️  Note: pynput.keyboard nécessite X11 (normalement sur SSH)")

print("\n" + "="*60)
if missing:
    print(f"❌ Modules manquants: {', '.join(missing)}")
    print("\nInstallez avec:")
    print(f"pip3 install --break-system-packages {' '.join(missing)}")
else:
    print("✅ Toutes les dépendances principales sont installées!")
    print("   (pynput.keyboard n'est nécessaire que pour test_keyboard.py avec X11)")

print("="*60)

