# Test de Détection d'Obstacles avec Photo

Ce dossier contient un programme de test pour la détection d'obstacles de l'hexapode avec capture et sauvegarde de photos.

## Fichiers

- `test_detection_photo.py` : Programme principal de test de détection avec photos
- `photos_obstacles/` : Dossier de sauvegarde des photos (créé automatiquement)

## Fonctionnalités

Le programme `test_detection_photo.py` permet de :

1. **Capture photo** : Prendre une photo avec la caméra de l'hexapode
2. **Détection d'obstacles** : Analyser l'image pour détecter les obstacles
3. **Annotation visuelle** : Entourer les obstacles détectés sur l'image
4. **Sauvegarde** : Enregistrer la photo annotée avec un nom horodaté

## Utilisation

### Lancement du programme

```bash
cd /home/user/Documents/Hexapode/test_detection
python3 test_detection_photo.py
```

### Commandes

Une fois le programme lancé :

- **[ESPACE]** : Prendre une photo et détecter les obstacles
- **[q]** : Quitter le programme
- **[h]** : Afficher l'aide

### Sortie

Les photos sont sauvegardées dans le dossier `photos_obstacles/` avec le format :
```
obstacle_detection_AAAAMMJJ_HHMMSS.jpg
```

## Informations affichées

### Sur la photo
- **Cadre coloré** : Indique le niveau de danger global
  - Vert (OK) : Pas d'obstacle dangereux
  - Jaune (OBS) : Obstacles détectés mais pas dangereux
  - Orange (WARN) : Obstacles proches, attention
  - Rouge (STOP) : Obstacles très proches, arrêt recommandé

- **Rectangles colorés** : Entourent chaque obstacle détecté
  - Bleu (G) : Obstacle à gauche
  - Rouge (C) : Obstacle au centre
  - Vert (D) : Obstacle à droite

- **Labels des obstacles** : Format `Position:Taille:Distance`
  - Position : G (Gauche), C (Centre), D (Droite)
  - Taille : S (Small), M (Medium), L (Large)
  - Distance : Valeur entre 0.0 et 1.0

- **Lignes de guide** :
  - Lignes horizontales cyan : Zone d'intérêt (ROI)
  - Lignes verticales cyan : Divisions gauche/centre/droite

### Dans la console
- Nombre d'obstacles détectés
- Niveau de danger global
- Position des obstacles (LEFT, RIGHT, CENTER, BOTH)
- Détails de chaque obstacle (position, distance, taille, coordonnées)

## Paramètres de détection

Le programme utilise les paramètres par défaut du module `obstacle_detector.py` :

- **Zone d'intérêt** : 30% à 90% de la hauteur de l'image
- **Aire minimale** : Obstacles trop petits filtrés
- **Seuils de distance** : Différents seuils pour gauche/droite et centre
- **Méthodes de détection** : Combinaison saturation, Laplacien, et Canny

## Dépendances

Le programme utilise les modules existants de l'hexapode :
- `hexapod.camera` : Capture caméra
- `hexapod.obstacle_detector` : Détection d'obstacles
- `hexapod.keyboard_handler` : Gestion clavier

## Troubleshooting

### Erreur de caméra
- Vérifier que la caméra est branchée
- S'assurer que `libcamera-vid` ou `rpicam-jpeg` sont installés

### Erreur de permissions
- Exécuter avec les bonnes permissions pour accéder à la caméra
- Vérifier les droits d'écriture dans le dossier

### Pas d'obstacles détectés
- Vérifier l'éclairage
- Placer des objets dans le champ de vision de la caméra
- Les objets doivent avoir une couleur/contraste suffisant