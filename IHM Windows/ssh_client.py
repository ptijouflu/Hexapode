#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH Client - Manages SSH connection with paramiko
"""

import re
import threading
import paramiko
from ssh_signals import SSHSignals
from config import DEFAULT_SSH_FOLDER, NAVIGATION_DELAY


class SSHClient:
    """Gestion de la connexion SSH"""
    
    # Expression régulière pour filtrer les codes ANSI (couleurs, formatage, modes spéciaux)
    # Capture: CSI sequences, OSC sequences, et autres codes de contrôle
    ANSI_ESCAPE_PATTERN = re.compile(
        r'\x1b\[[?!]?[0-9;]*[a-zA-Z]|'  # CSI sequences (incluant ?2004h, etc.)
        r'\x1b\][0-9];[^\x07]*\x07|'     # OSC sequences
        r'\x1b[>=]|'                      # Autres codes ESC
        r'\x1b\([B0]|'                    # Charset selection
        r'\x1b[@-_]'                      # Autres codes ESC
    )
    
    def __init__(self):
        self.client = None
        self.channel = None
        self.connected = False
        self.signals = SSHSignals()
        self.receive_thread = None
        
    def connect(self, host, port, username, password):
        """Établit la connexion SSH"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connexion au serveur
            self.client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=10
            )
            
            # Ouvrir un shell interactif
            self.channel = self.client.invoke_shell()
            self.connected = True
            
            # Démarrer le thread de réception
            self.receive_thread = threading.Thread(target=self._receive_output, daemon=True)
            self.receive_thread.start()
            
            self.signals.connection_status.emit(True, f"Connecté à {host}")
            
            # Navigation automatique vers le dossier Hexapode
            import time
            time.sleep(NAVIGATION_DELAY)
            self.channel.send(f'cd {DEFAULT_SSH_FOLDER}\n')
            
            return True
            
        except paramiko.AuthenticationException:
            self.signals.connection_status.emit(False, "Erreur d'authentification")
            return False
        except paramiko.SSHException as e:
            self.signals.connection_status.emit(False, f"Erreur SSH: {str(e)}")
            return False
        except Exception as e:
            self.signals.connection_status.emit(False, f"Erreur de connexion: {str(e)}")
            return False
    
    def _receive_output(self):
        """Reçoit les données du serveur SSH (exécuté dans un thread)"""
        while self.connected and self.channel:
            try:
                if self.channel.recv_ready():
                    output = self.channel.recv(4096).decode('utf-8', errors='replace')
                    # Nettoyer les codes ANSI pour un affichage lisible
                    clean_output = self.strip_ansi_codes(output)
                    self.signals.output_received.emit(clean_output)
            except Exception as e:
                if self.connected:
                    self.signals.output_received.emit(f"\n[Erreur de réception: {str(e)}]\n")
                break
    
    @staticmethod
    def strip_ansi_codes(text):
        """Supprime les codes d'échappement ANSI du texte"""
        return SSHClient.ANSI_ESCAPE_PATTERN.sub('', text)
    
    def send_command(self, command):
        """Envoie une commande au serveur SSH"""
        if self.connected and self.channel:
            try:
                self.channel.send(command + '\n')
            except Exception as e:
                self.signals.output_received.emit(f"\n[Erreur d'envoi: {str(e)}]\n")
    
    def disconnect(self):
        """Ferme la connexion SSH"""
        self.connected = False
        if self.channel:
            self.channel.close()
        if self.client:
            self.client.close()
        self.signals.connection_status.emit(False, "Déconnecté")
