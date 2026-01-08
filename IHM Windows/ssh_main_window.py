#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH Main Window - Main application window with all UI components
"""

import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox,
    QMessageBox, QSpinBox, QGridLayout
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QTextCursor

from ssh_client import SSHClient
from video_stream_reader import VideoStreamReader
from config import (
    DEFAULT_VIDEO_URL, DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT,
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    AUTO_PROGRAM, MANUAL_PROGRAM, PROGRAM_STOP_DELAY,
    HEXAPOD_COMMANDS
)


class SSHMainWindow(QMainWindow):
    """Fenêtre principale de l'application SSH"""
    
    def __init__(self):
        super().__init__()
        
        # URL du flux vidéo par défaut
        self.video_url = DEFAULT_VIDEO_URL
        
        # Suivi du programme hexapode en cours
        self.current_program = None  # None, 'auto', ou 'manual'
        
        self.ssh_client = SSHClient()
        self.video_stream = VideoStreamReader(self.video_url)
        self.init_ui()
        
        # Installer le filtre d'événements pour capturer les touches clavier
        self.installEventFilter(self)
        
        # Connexion des signaux vidéo
        self.video_stream.signals.frame_ready.connect(self.update_video_frame)
        self.video_stream.signals.status_changed.connect(self.update_video_status)
        
        # Connexion des signaux
        self.ssh_client.signals.output_received.connect(self.append_output)
        self.ssh_client.signals.connection_status.connect(self.update_connection_status)
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        self.setWindowTitle("SSH Client - Raspberry Pi Hexapode")
        self.setMinimumSize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # === Groupe de connexion ===
        connection_group = QGroupBox("Connexion SSH")
        connection_layout = QGridLayout()
        
        # Hôte
        connection_layout.addWidget(QLabel("Hôte:"), 0, 0)
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("192.168.1.100 ou raspberry.local")
        connection_layout.addWidget(self.host_input, 0, 1)
        
        # Port
        connection_layout.addWidget(QLabel("Port:"), 0, 2)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        connection_layout.addWidget(self.port_input, 0, 3)
        
        # Utilisateur
        connection_layout.addWidget(QLabel("Utilisateur:"), 1, 0)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("pi")
        connection_layout.addWidget(self.username_input, 1, 1)
        
        # Mot de passe
        connection_layout.addWidget(QLabel("Mot de passe:"), 1, 2)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        connection_layout.addWidget(self.password_input, 1, 3)
        
        # Bouton de connexion
        self.connect_button = QPushButton("Se connecter")
        self.connect_button.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(self.connect_button, 2, 0, 1, 2)
        
        # Label de statut
        self.status_label = QLabel("Déconnecté")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        connection_layout.addWidget(self.status_label, 2, 2, 1, 2)
        
        connection_group.setLayout(connection_layout)
        main_layout.addWidget(connection_group)
        
        # === Sélection de Mode ===
        mode_group = QGroupBox("Mode de Contrôle")
        mode_layout = QHBoxLayout()
        
        mode_layout.addWidget(QLabel("Lancer :"))
        
        self.btn_mode_auto = QPushButton("Automatique (navigation_autonome.py)")
        self.btn_mode_auto.setEnabled(False)
        self.btn_mode_auto.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_mode_auto.clicked.connect(self.launch_autonomous_mode)
        mode_layout.addWidget(self.btn_mode_auto)
        
        self.btn_mode_manual = QPushButton("Manuel (deplacement.py)")
        self.btn_mode_manual.setEnabled(False)
        self.btn_mode_manual.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 10px;")
        self.btn_mode_manual.clicked.connect(self.launch_manual_mode)
        mode_layout.addWidget(self.btn_mode_manual)
        
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)
        
        # === Layout horizontal pour Vidéo + Terminal ===
        content_layout = QHBoxLayout()
        
        # === Panneau Vidéo (Gauche) ===
        video_group = QGroupBox("Flux Caméra Hexapode")
        video_layout = QVBoxLayout()
        
        # Configuration URL du flux
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL Flux:"))
        self.video_url_input = QLineEdit()
        self.video_url_input.setText(self.video_url)
        self.video_url_input.setPlaceholderText("http://localhost:8081/stream")
        url_layout.addWidget(self.video_url_input)
        video_layout.addLayout(url_layout)
        
        # Affichage vidéo
        self.video_label = QLabel()
        self.video_label.setMinimumSize(DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT)
        self.video_label.setMaximumSize(DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT)
        self.video_label.setScaledContents(True)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #2a2a2a;
                border: 2px solid #555;
                color: #aaa;
            }
        """)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setText("Flux vidéo non démarré")
        video_layout.addWidget(self.video_label)
        
        # Contrôles vidéo
        video_controls_layout = QHBoxLayout()
        
        self.video_start_btn = QPushButton("Démarrer Flux")
        self.video_start_btn.clicked.connect(self.start_video_stream)
        video_controls_layout.addWidget(self.video_start_btn)
        
        self.video_stop_btn = QPushButton("Arrêter Flux")
        self.video_stop_btn.clicked.connect(self.stop_video_stream)
        self.video_stop_btn.setEnabled(False)
        video_controls_layout.addWidget(self.video_stop_btn)
        
        self.video_status_label = QLabel("Statut: Arrêté")
        self.video_status_label.setStyleSheet("font-size: 9pt; color: #888;")
        video_controls_layout.addWidget(self.video_status_label)
        
        video_layout.addLayout(video_controls_layout)
        video_group.setLayout(video_layout)
        content_layout.addWidget(video_group)
        
        # === Zone de terminal (Droite) ===
        terminal_group = QGroupBox("Terminal")
        terminal_layout = QVBoxLayout()
        
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        terminal_layout.addWidget(self.terminal_output)
        
        terminal_group.setLayout(terminal_layout)
        content_layout.addWidget(terminal_group)
        
        main_layout.addLayout(content_layout)
        
        # === Zone de saisie de commandes ===
        command_layout = QHBoxLayout()
        command_layout.addWidget(QLabel("Commande:"))
        
        self.command_input = QLineEdit()
        self.command_input.setEnabled(False)
        self.command_input.returnPressed.connect(self.send_command)
        command_layout.addWidget(self.command_input)
        
        self.send_button = QPushButton("Envoyer")
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self.send_command)
        command_layout.addWidget(self.send_button)
        
        main_layout.addLayout(command_layout)
        
        # === Panneau de contrôle Hexapode ===
        control_group = QGroupBox("Contrôle Hexapode")
        control_layout = QVBoxLayout()
        
        # Label d'instructions
        instructions_label = QLabel("Utilisez les boutons ou les touches Z/Q/S/D/A/E/Espace pour contrôler l'hexapode")
        instructions_label.setStyleSheet("font-style: italic; color: #666;")
        control_layout.addWidget(instructions_label)
        
        # Grille de boutons (3x3)
        buttons_layout = QGridLayout()
        
        # Ligne 1: A - Avancer - E
        self.btn_a = QPushButton("A")
        self.btn_a.setEnabled(False)
        self.btn_a.clicked.connect(lambda: self.send_hexapod_command('a'))
        buttons_layout.addWidget(self.btn_a, 0, 0)
        
        # Bouton Avancer (Z)
        self.btn_forward = QPushButton("Avancer (Z)")
        self.btn_forward.setEnabled(False)
        self.btn_forward.clicked.connect(lambda: self.send_hexapod_command('z'))
        buttons_layout.addWidget(self.btn_forward, 0, 1)
        
        self.btn_e = QPushButton("E")
        self.btn_e.setEnabled(False)
        self.btn_e.clicked.connect(lambda: self.send_hexapod_command('e'))
        buttons_layout.addWidget(self.btn_e, 0, 2)
        
        # Ligne 2: Gauche - Reculer - Droite
        # Bouton Gauche (Q)
        self.btn_left = QPushButton("Gauche (Q)")
        self.btn_left.setEnabled(False)
        self.btn_left.clicked.connect(lambda: self.send_hexapod_command('q'))
        buttons_layout.addWidget(self.btn_left, 1, 0)
        
        # Bouton Reculer (S)
        self.btn_backward = QPushButton("Reculer (S)")
        self.btn_backward.setEnabled(False)
        self.btn_backward.clicked.connect(lambda: self.send_hexapod_command('s'))
        buttons_layout.addWidget(self.btn_backward, 1, 1)
        
        # Bouton Droite (D)
        self.btn_right = QPushButton("Droite (D)")
        self.btn_right.setEnabled(False)
        self.btn_right.clicked.connect(lambda: self.send_hexapod_command('d'))
        buttons_layout.addWidget(self.btn_right, 1, 2)
        
        # Ligne 3: Espace (centré)
        self.btn_space = QPushButton("Pause/Stop (Espace)")
        self.btn_space.setEnabled(False)
        self.btn_space.clicked.connect(lambda: self.send_hexapod_command(' '))
        self.btn_space.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
        buttons_layout.addWidget(self.btn_space, 2, 0, 1, 3)  # Span 3 colonnes
        
        control_layout.addLayout(buttons_layout)
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
    
    def toggle_connection(self):
        """Gère la connexion/déconnexion"""
        if not self.ssh_client.connected:
            # Tentative de connexion
            host = self.host_input.text().strip()
            port = self.port_input.value()
            username = self.username_input.text().strip()
            password = self.password_input.text()
            
            if not host or not username:
                QMessageBox.warning(self, "Erreur", "Veuillez remplir l'hôte et l'utilisateur")
                return
            
            # Désactiver les champs pendant la connexion
            self.set_connection_fields_enabled(False)
            self.connect_button.setEnabled(False)
            self.status_label.setText("Connexion en cours...")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            
            # Connexion dans un thread séparé
            import threading
            thread = threading.Thread(
                target=self.ssh_client.connect,
                args=(host, port, username, password),
                daemon=True
            )
            thread.start()
        else:
            # Déconnexion
            self.ssh_client.disconnect()
    
    def update_connection_status(self, connected, message):
        """Met à jour le statut de connexion"""
        self.status_label.setText(message)
        
        if connected:
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.connect_button.setText("Se déconnecter")
            self.connect_button.setEnabled(True)
            self.command_input.setEnabled(True)
            self.send_button.setEnabled(True)
            self.set_connection_fields_enabled(False)
            # Activer les boutons de contrôle hexapode
            self.enable_hexapod_buttons(True)
            # Activer les boutons de mode
            self.btn_mode_auto.setEnabled(True)
            self.btn_mode_manual.setEnabled(True)
            # Démarrer automatiquement le flux vidéo
            self.start_video_stream()
            self.command_input.setFocus()
        else:
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connect_button.setText("Se connecter")
            self.connect_button.setEnabled(True)
            self.command_input.setEnabled(False)
            self.send_button.setEnabled(False)
            # Désactiver les boutons de contrôle hexapode
            self.enable_hexapod_buttons(False)
            # Désactiver les boutons de mode
            self.btn_mode_auto.setEnabled(False)
            self.btn_mode_manual.setEnabled(False)
            # Réinitialiser le programme en cours
            self.current_program = None
            self.set_connection_fields_enabled(True)
            
            if "Erreur" in message:
                QMessageBox.critical(self, "Erreur de connexion", message)
    
    def set_connection_fields_enabled(self, enabled):
        """Active/désactive les champs de connexion"""
        self.host_input.setEnabled(enabled)
        self.port_input.setEnabled(enabled)
        self.username_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
    
    def append_output(self, text):
        """Ajoute du texte à la zone de terminal"""
        self.terminal_output.moveCursor(QTextCursor.MoveOperation.End)
        self.terminal_output.insertPlainText(text)
        self.terminal_output.moveCursor(QTextCursor.MoveOperation.End)
    
    def send_command(self):
        """Envoie une commande au serveur SSH"""
        command = self.command_input.text()
        if command:
            self.ssh_client.send_command(command)
            self.command_input.clear()
    
    def send_hexapod_command(self, key):
        """Envoie une commande de contrôle hexapode (touche unique)"""
        if self.ssh_client.connected and self.ssh_client.channel:
            try:
                # Envoyer la touche directement au terminal
                self.ssh_client.channel.send(key)
                # Afficher dans le terminal pour feedback
                self.append_output(f" [{HEXAPOD_COMMANDS.get(key, key)}] ")
            except Exception as e:
                self.append_output(f"\n[Erreur envoi commande: {str(e)}]\n")
    
    def enable_hexapod_buttons(self, enabled):
        """Active/désactive les boutons de contrôle hexapode"""
        self.btn_forward.setEnabled(enabled)
        self.btn_left.setEnabled(enabled)
        self.btn_backward.setEnabled(enabled)
        self.btn_right.setEnabled(enabled)
        self.btn_a.setEnabled(enabled)
        self.btn_e.setEnabled(enabled)
        self.btn_space.setEnabled(enabled)
    
    def launch_autonomous_mode(self):
        """Lance le mode autonome (navigation_autonome.py)"""
        if self.ssh_client.connected:
            # Si le programme automatique est déjà lancé, ne rien faire
            if self.current_program == 'auto':
                self.append_output("\n[Mode Automatique déjà actif]\n")
                return
            
            # Si un autre programme tourne, l'arrêter d'abord
            if self.current_program is not None:
                self.append_output("\n[Arrêt du programme en cours...]\n")
                self.ssh_client.channel.send('\x03')  # Ctrl+C
                time.sleep(PROGRAM_STOP_DELAY)
            
            # Lancer le nouveau programme
            self.append_output("\n[Lancement Mode Automatique...]\n")
            self.ssh_client.send_command(AUTO_PROGRAM)
            self.current_program = 'auto'
    
    def launch_manual_mode(self):
        """Lance le mode manuel (deplacement.py)"""
        if self.ssh_client.connected:
            # Si le programme manuel est déjà lancé, ne rien faire
            if self.current_program == 'manual':
                self.append_output("\n[Mode Manuel déjà actif]\n")
                return
            
            # Si un autre programme tourne, l'arrêter d'abord
            if self.current_program is not None:
                self.append_output("\n[Arrêt du programme en cours...]\n")
                self.ssh_client.channel.send('\x03')  # Ctrl+C
                time.sleep(PROGRAM_STOP_DELAY)
            
            # Lancer le nouveau programme
            self.append_output("\n[Lancement Mode Manuel...]\n")
            self.ssh_client.send_command(MANUAL_PROGRAM)
            self.current_program = 'manual'
    
    def eventFilter(self, obj, event):
        """Filtre les événements clavier pour les raccourcis hexapode"""
        # Capturer les touches seulement si connecté et pas en train de taper dans un champ
        if (event.type() == QEvent.Type.KeyPress and 
            self.ssh_client.connected and
            not self.command_input.hasFocus() and
            not self.host_input.hasFocus() and
            not self.username_input.hasFocus() and
            not self.password_input.hasFocus() and
            not self.video_url_input.hasFocus()):
            
            key = event.key()
            # Mapper les touches aux commandes hexapode
            key_map = {
                Qt.Key.Key_Z: 'z',
                Qt.Key.Key_Q: 'q',
                Qt.Key.Key_S: 's',
                Qt.Key.Key_D: 'd',
                Qt.Key.Key_A: 'a',
                Qt.Key.Key_E: 'e',
                Qt.Key.Key_Space: ' '
            }
            
            if key in key_map:
                # Debug pour vérifier la capture (surtout pour Espace)
                if key == Qt.Key.Key_Space:
                    self.append_output(f"\n[DEBUG: Touche Espace détectée]\n")
                self.send_hexapod_command(key_map[key])
                return True  # Événement traité
        
        return super().eventFilter(obj, event)
    
    def start_video_stream(self):
        """Démarre le flux vidéo"""
        # Arrêter l'ancien stream s'il existe
        self.video_stream.stop()
        
        # Créer un nouveau stream avec l'URL du champ
        new_url = self.video_url_input.text().strip()
        if new_url:
            self.video_stream = VideoStreamReader(new_url)
            self.video_stream.signals.frame_ready.connect(self.update_video_frame)
            self.video_stream.signals.status_changed.connect(self.update_video_status)
            self.video_stream.start()
            self.video_start_btn.setEnabled(False)
            self.video_stop_btn.setEnabled(True)
        else:
            self.update_video_status("URL vide")
    
    def stop_video_stream(self):
        """Arrête le flux vidéo"""
        self.video_stream.stop()
        self.video_start_btn.setEnabled(True)
        self.video_stop_btn.setEnabled(False)
        self.video_label.setText("Flux vidéo arrêté")
    
    def update_video_frame(self, pixmap):
        """Met à jour la frame vidéo affichée"""
        self.video_label.setPixmap(pixmap)
    
    def update_video_status(self, status):
        """Met à jour le statut du flux vidéo"""
        self.video_status_label.setText(f"Statut: {status}")
        if "non disponible" in status or "Erreur" in status:
            self.video_label.setText(f"{status}\n\nAssurez-vous que:\n1. navigation_autonome.py est lancé\n2. Port forwarding SSH actif:\n   ssh -L 8080:localhost:8080 user@raspberry")
    
    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre"""
        self.video_stream.stop()
        if self.ssh_client.connected:
            self.ssh_client.disconnect()
        event.accept()
