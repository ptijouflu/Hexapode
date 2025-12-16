#!/usr/bin/env python3
"""
IHM Récepteur UDP pour le flux vidéo Hexapode
Interface graphique avec contrôles et statistiques

Usage:
    python3 udp_receiver_gui.py [PORT]
    python3 udp_receiver_gui.py 5555
"""

import numpy as np
import socket
import struct
import threading
import time
import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2

# Configuration
MAX_DGRAM_SIZE = 65000
DEFAULT_PORT = 5555


class UDPVideoReceiver:
    """Récepteur de flux vidéo UDP"""
    
    def __init__(self, port):
        self.port = port
        self.socket = None
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.frame_buffer = {}
        self.stats = {
            'packets_received': 0,
            'frames_complete': 0,
            'frames_dropped': 0,
            'errors': 0,
            'bytes_received': 0,
            'last_frame_time': 0
        }
        self.connected = False
    
    def start(self):
        """Démarre le récepteur"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Augmenter le buffer de réception
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
            except:
                pass
            
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.settimeout(0.5)
            self.running = True
            
            # Lancer le thread de réception
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            return True
        except Exception as e:
            print(f"Erreur démarrage: {e}")
            return False
    
    def stop(self):
        """Arrête le récepteur"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
    
    def _receive_loop(self):
        """Boucle de réception des paquets"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(MAX_DGRAM_SIZE)
                self.stats['packets_received'] += 1
                self.stats['bytes_received'] += len(data)
                self.connected = True
                
                if len(data) < 12:
                    continue
                
                # Décoder le header
                header = data[:12]
                frame_id, chunk_id, num_chunks, data_size = struct.unpack('!IHHI', header)
                chunk_data = data[12:]
                
                # Initialiser le buffer pour cette frame
                if frame_id not in self.frame_buffer:
                    self.frame_buffer[frame_id] = {
                        'chunks': {},
                        'num_chunks': num_chunks,
                        'data_size': data_size,
                        'timestamp': time.time()
                    }
                
                # Stocker le chunk
                self.frame_buffer[frame_id]['chunks'][chunk_id] = chunk_data
                
                # Vérifier si la frame est complète
                if len(self.frame_buffer[frame_id]['chunks']) == num_chunks:
                    self._reconstruct_frame(frame_id)
                
                # Nettoyer les vieux buffers
                self._cleanup_old_buffers()
                
            except socket.timeout:
                continue
            except Exception as e:
                self.stats['errors'] += 1
    
    def _reconstruct_frame(self, frame_id):
        """Reconstitue une frame"""
        try:
            buffer_info = self.frame_buffer[frame_id]
            
            # Assembler les chunks
            data = b''
            for i in range(buffer_info['num_chunks']):
                if i in buffer_info['chunks']:
                    data += buffer_info['chunks'][i]
                else:
                    self.stats['frames_dropped'] += 1
                    del self.frame_buffer[frame_id]
                    return
            
            # Décoder l'image
            nparr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Convertir BGR -> RGB pour Tkinter
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                with self.frame_lock:
                    self.current_frame = frame_rgb
                self.stats['frames_complete'] += 1
                self.stats['last_frame_time'] = time.time()
            
            del self.frame_buffer[frame_id]
            
        except Exception as e:
            self.stats['errors'] += 1
            if frame_id in self.frame_buffer:
                del self.frame_buffer[frame_id]
    
    def _cleanup_old_buffers(self):
        """Supprime les buffers trop vieux"""
        current_time = time.time()
        old_frames = [fid for fid, info in self.frame_buffer.items() 
                      if current_time - info['timestamp'] > 2.0]
        for fid in old_frames:
            self.stats['frames_dropped'] += 1
            del self.frame_buffer[fid]
    
    def get_frame(self):
        """Récupère la dernière frame"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None


class HexapodeReceiverGUI:
    """Interface graphique pour le récepteur vidéo"""
    
    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self.receiver = None
        self.running = False
        self.start_time = None
        
        # Créer la fenêtre principale
        self.root = tk.Tk()
        self.root.title("🤖 Hexapode - Récepteur Vidéo UDP")
        self.root.geometry("900x700")
        self.root.configure(bg='#1e1e1e')
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#1e1e1e')
        self.style.configure('TLabel', background='#1e1e1e', foreground='white')
        self.style.configure('TButton', padding=10)
        self.style.configure('Green.TButton', foreground='white', background='#28a745')
        self.style.configure('Red.TButton', foreground='white', background='#dc3545')
        
        self._create_widgets()
        self._update_loop()
    
    def _create_widgets(self):
        """Crée les widgets de l'interface"""
        
        # Frame principale
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === Header ===
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="🤖 Hexapode Camera Stream", 
                                font=('Arial', 18, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        # Status indicator
        self.status_label = ttk.Label(header_frame, text="⚫ Déconnecté", 
                                      font=('Arial', 12))
        self.status_label.pack(side=tk.RIGHT)
        
        # === Zone vidéo ===
        video_frame = ttk.Frame(main_frame)
        video_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Canvas pour la vidéo
        self.canvas = tk.Canvas(video_frame, bg='#2d2d2d', highlightthickness=2,
                                highlightbackground='#444')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Message d'attente initial
        self.canvas.create_text(320, 240, text="En attente du flux vidéo...",
                               fill='#888', font=('Arial', 16), tags='waiting')
        
        # === Contrôles ===
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        # Port
        port_frame = ttk.Frame(control_frame)
        port_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(port_frame, text="Port UDP:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value=str(self.port))
        self.port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=8)
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        # Boutons
        self.start_btn = ttk.Button(control_frame, text="▶ Démarrer", 
                                    command=self._start_receiver)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = ttk.Button(control_frame, text="⏹ Arrêter", 
                                   command=self._stop_receiver, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Bouton capture
        self.capture_btn = ttk.Button(control_frame, text="📷 Capturer", 
                                      command=self._capture_frame, state=tk.DISABLED)
        self.capture_btn.pack(side=tk.LEFT, padx=10)
        
        # Bouton plein écran
        self.fullscreen_btn = ttk.Button(control_frame, text="⛶ Plein écran", 
                                         command=self._toggle_fullscreen)
        self.fullscreen_btn.pack(side=tk.RIGHT, padx=5)
        
        # === Statistiques ===
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=5)
        
        # Ligne 1
        stats_line1 = ttk.Frame(stats_frame)
        stats_line1.pack(fill=tk.X)
        
        self.fps_label = ttk.Label(stats_line1, text="FPS: --", font=('Consolas', 10))
        self.fps_label.pack(side=tk.LEFT, padx=10)
        
        self.frames_label = ttk.Label(stats_line1, text="Frames: 0", font=('Consolas', 10))
        self.frames_label.pack(side=tk.LEFT, padx=10)
        
        self.packets_label = ttk.Label(stats_line1, text="Paquets: 0", font=('Consolas', 10))
        self.packets_label.pack(side=tk.LEFT, padx=10)
        
        self.bandwidth_label = ttk.Label(stats_line1, text="Débit: 0 KB/s", font=('Consolas', 10))
        self.bandwidth_label.pack(side=tk.LEFT, padx=10)
        
        # Ligne 2
        stats_line2 = ttk.Frame(stats_frame)
        stats_line2.pack(fill=tk.X)
        
        self.dropped_label = ttk.Label(stats_line2, text="Perdues: 0", 
                                       font=('Consolas', 10), foreground='#ff6b6b')
        self.dropped_label.pack(side=tk.LEFT, padx=10)
        
        self.errors_label = ttk.Label(stats_line2, text="Erreurs: 0", 
                                      font=('Consolas', 10), foreground='#ff6b6b')
        self.errors_label.pack(side=tk.LEFT, padx=10)
        
        self.latency_label = ttk.Label(stats_line2, text="Latence: -- ms", 
                                       font=('Consolas', 10))
        self.latency_label.pack(side=tk.LEFT, padx=10)
        
        # === Barre de statut ===
        self.statusbar = ttk.Label(main_frame, text="Prêt. Entrez le port et cliquez sur Démarrer.",
                                   font=('Arial', 9), foreground='#888')
        self.statusbar.pack(fill=tk.X, pady=(5, 0))
        
        # Bindings
        self.root.bind('<Escape>', lambda e: self._exit_fullscreen())
        self.root.bind('<F11>', lambda e: self._toggle_fullscreen())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.is_fullscreen = False
        self.last_bytes = 0
        self.last_bytes_time = time.time()
    
    def _start_receiver(self):
        """Démarre le récepteur"""
        try:
            port = int(self.port_var.get())
        except ValueError:
            self.statusbar.config(text="❌ Port invalide!")
            return
        
        self.receiver = UDPVideoReceiver(port)
        if self.receiver.start():
            self.running = True
            self.start_time = time.time()
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.capture_btn.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.DISABLED)
            self.statusbar.config(text=f"✅ Écoute sur le port UDP {port}...")
            self.status_label.config(text="🟡 En attente")
        else:
            self.statusbar.config(text="❌ Erreur de démarrage!")
    
    def _stop_receiver(self):
        """Arrête le récepteur"""
        self.running = False
        if self.receiver:
            self.receiver.stop()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.capture_btn.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.NORMAL)
        self.status_label.config(text="⚫ Déconnecté")
        self.statusbar.config(text="Récepteur arrêté.")
        
        # Réafficher le message d'attente
        self.canvas.delete('all')
        self.canvas.create_text(320, 240, text="En attente du flux vidéo...",
                               fill='#888', font=('Arial', 16), tags='waiting')
    
    def _capture_frame(self):
        """Capture et sauvegarde la frame actuelle"""
        if self.receiver:
            frame = self.receiver.get_frame()
            if frame is not None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.png"
                # Convertir RGB -> BGR pour OpenCV
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                cv2.imwrite(filename, frame_bgr)
                self.statusbar.config(text=f"📷 Image sauvegardée: {filename}")
    
    def _toggle_fullscreen(self):
        """Bascule le mode plein écran"""
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes('-fullscreen', self.is_fullscreen)
        if self.is_fullscreen:
            self.fullscreen_btn.config(text="⛶ Quitter plein écran")
        else:
            self.fullscreen_btn.config(text="⛶ Plein écran")
    
    def _exit_fullscreen(self):
        """Quitte le mode plein écran"""
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes('-fullscreen', False)
            self.fullscreen_btn.config(text="⛶ Plein écran")
    
    def _update_loop(self):
        """Boucle de mise à jour de l'interface"""
        if self.running and self.receiver:
            frame = self.receiver.get_frame()
            
            if frame is not None:
                # Mettre à jour le statut
                if self.receiver.connected:
                    self.status_label.config(text="🟢 Connecté")
                
                # Redimensionner la frame pour le canvas
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    # Calculer le ratio
                    h, w = frame.shape[:2]
                    ratio = min(canvas_width / w, canvas_height / h)
                    new_w = int(w * ratio)
                    new_h = int(h * ratio)
                    
                    # Redimensionner
                    frame_resized = cv2.resize(frame, (new_w, new_h))
                    
                    # Convertir pour Tkinter
                    image = Image.fromarray(frame_resized)
                    photo = ImageTk.PhotoImage(image)
                    
                    # Afficher
                    self.canvas.delete('all')
                    x = (canvas_width - new_w) // 2
                    y = (canvas_height - new_h) // 2
                    self.canvas.create_image(x, y, anchor=tk.NW, image=photo)
                    self.canvas.image = photo  # Garder une référence
            
            # Mettre à jour les statistiques
            stats = self.receiver.stats
            elapsed = time.time() - self.start_time if self.start_time else 1
            fps = stats['frames_complete'] / elapsed if elapsed > 0 else 0
            
            # Calcul du débit
            current_time = time.time()
            if current_time - self.last_bytes_time >= 1.0:
                bytes_diff = stats['bytes_received'] - self.last_bytes
                bandwidth = bytes_diff / 1024  # KB/s
                self.bandwidth_label.config(text=f"Débit: {bandwidth:.1f} KB/s")
                self.last_bytes = stats['bytes_received']
                self.last_bytes_time = current_time
            
            self.fps_label.config(text=f"FPS: {fps:.1f}")
            self.frames_label.config(text=f"Frames: {stats['frames_complete']}")
            self.packets_label.config(text=f"Paquets: {stats['packets_received']}")
            self.dropped_label.config(text=f"Perdues: {stats['frames_dropped']}")
            self.errors_label.config(text=f"Erreurs: {stats['errors']}")
            
            # Latence approximative
            if stats['last_frame_time'] > 0:
                latency = (time.time() - stats['last_frame_time']) * 1000
                self.latency_label.config(text=f"Latence: {latency:.0f} ms")
        
        # Planifier la prochaine mise à jour
        self.root.after(33, self._update_loop)  # ~30 FPS
    
    def _on_close(self):
        """Gère la fermeture de la fenêtre"""
        self._stop_receiver()
        self.root.destroy()
    
    def run(self):
        """Lance l'interface"""
        # Démarrer automatiquement si un port est spécifié
        self.root.after(100, self._auto_start)
        self.root.mainloop()
    
    def _auto_start(self):
        """Démarre automatiquement le récepteur"""
        self._start_receiver()


def main():
    # Récupérer le port depuis les arguments
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Port invalide: {sys.argv[1]}")
            print(f"Usage: python3 {sys.argv[0]} [PORT]")
            sys.exit(1)
    
    print("=" * 50)
    print("  Hexapode - Récepteur Vidéo UDP (GUI)")
    print("=" * 50)
    print(f"  Port: {port}")
    print()
    
    # Lancer l'interface
    app = HexapodeReceiverGUI(port)
    app.run()


if __name__ == '__main__':
    main()
