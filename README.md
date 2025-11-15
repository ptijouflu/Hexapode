# Installation et Configuration du Projet

## 1. Installation d'une Image sur la Carte SD du Raspberry Pi

### Prérequis :
- Une carte microSD (minimum 8 Go recommandé)
- Un lecteur de carte SD
- Un ordinateur avec Windows, macOS ou Linux
- Un logiciel d'écriture d'image : **Raspberry Pi Imager**

### Étapes :
1. **Télécharger l'image du système**
   - Rendez-vous sur le site officiel : [https://www.raspberrypi.com/software/](https://www.raspberrypi.com/software/)
   - Téléchargez **Raspberry Pi OS** (version Lite ou Desktop selon les besoins)

2. **Flasher l'image sur la carte SD**
   - Insérez la carte SD dans votre ordinateur
   - Ouvrez **Raspberry Pi Imager** ou **balenaEtcher**
   - Sélectionnez l'image du système téléchargée
   - Choisissez la carte SD comme destination
   - Lancez l'écriture et attendez la fin du processus

3. **Configuration SSH et Wi-Fi (optionnel)**
   - Si vous souhaitez accéder au Raspberry Pi en SSH sans écran :
     - Créez un fichier vide nommé `ssh` (sans extension) dans la partition **boot**
   - Pour configurer le Wi-Fi :
     - Créez un fichier `wpa_supplicant.conf` dans la partition **boot** avec le contenu suivant :
       ```bash
       country=FR
       ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
       update_config=1
       network={
           ssid="NOM_DE_VOTRE_WIFI"
           psk="VOTRE_MOT_DE_PASSE"
           key_mgmt=WPA-PSK
       }
       ```

4. **Démarrer le Raspberry Pi**
   - Insérez la carte SD dans le Raspberry Pi et démarrez-le.

---

## 2. Installation des Bibliothèques Nécessaires

Une fois connecté à votre Raspberry Pi, exécutez les commandes suivantes :

```bash
sudo apt update && sudo apt upgrade -y  # Mise à jour du système
sudo apt install python3 python3-pip -y  # Installation de Python
pip3 install keyboard  # Installation de la bibliothèque keyboard
pip3 install opencv-python  # Installation de la bibliothèque OpenCV
pip3 install numpy  # Installation de la bibliothèque NumPy
pip3 install paho-mqtt  # Installation de la bibliothèque paho-mqtt
```

---

## 3. Installation des Environnements de Développement

Installer egalement un environnement de travail :

### a) Visual Studio Code
```bash
sudo apt install code -y
```

---

## 4. Lancer le Projet

1. **Accéder au répertoire du projet**
```bash
cd /hexapode
```


2. **Exécuter le script principal avec le deplacement du robot et de la caméra**
```bash
python deplacement_automatique.py
```

3. **Exécuter le script avec le deplacement du robot à l'aide du clavier**
```bash
python deplacement_keyboard.py
```

---

## 5. Automatiser le Lancement au Démarrage

Pour que le script démarre automatiquement à chaque démarrage du Raspberry Pi, ajoutez la ligne suivante à la fin du fichier `.bashrc` :

```bash
echo "python /home/pi/hexapode/deplacement_automatique.py" >> ~/.bashrc
```

Ou éditez manuellement :
```bash
nano ~/.bashrc
```
Ajoutez à la fin du fichier :
```bash
python /home/pi/hexapode/deplacement_automatique.py
```
Sauvegardez avec `CTRL + X`, `Y`, puis `ENTER`.

---

## 6. Redémarrer pour Tester l'automatisation au demarrage

```bash
sudo reboot
```

Après redémarrage, le script `deplacement_automatique.py` s'exécutera automatiquement.

### 🎯 Votre Raspberry Pi est maintenant prêt à exécuter le projet !


---