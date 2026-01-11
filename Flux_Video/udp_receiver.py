#!/usr/bin/env python3
"""
Récepteur UDP simple pour le flux vidéo Hexapode
Fonctionne sur PC Windows/Linux/Mac

Usage:
    python3 udp_receiver.py [PORT]
    python3 udp_receiver.py 5000
    python3 udp_receiver.py 5000 --headless   (sans affichage, pour test)
"""

import numpy as np
import socket
import struct
import threading
import time
import sys
import os
import platform

# Détecter si on est sur Windows ou si on a un display
IS_WINDOWS = platform.system() == 'Windows'
HAS_DISPLAY = IS_WINDOWS or os.environ.get('DISPLAY') is not None

# Mode headless uniquement si explicitement demandé
HEADLESS = '--headless' in sys.argv

if not HEADLESS:
    try:
        import cv2
        print("[OK] OpenCV chargé")
    except ImportError:
        print("[ERREUR] OpenCV non installé. Installez avec: pip install opencv-python")
        print("[INFO] Passage en mode headless...")
        HEADLESS = True
        cv2 = None
else:
    cv2 = None
    print("[INFO] Mode headless (sans affichage)")

# Configuration
MAX_DGRAM_SIZE = 65000
DEFAULT_PORT = 5000


class SimpleUDPReceiver:
    def __init__(self, port):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Augmenter le buffer de réception
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
        except:
            pass
        
        self.socket.bind(('0.0.0.0', port))
        self.socket.settimeout(1.0)
        
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.frame_buffer = {}
        self.stats = {'received': 0, 'displayed': 0, 'errors': 0}
        
        print(f"[OK] Récepteur UDP en écoute sur le port {port}")
        print(f"[INFO] En attente de données...")
    
    def receive_loop(self):
        """Boucle de réception des paquets"""
        self.running = True
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(MAX_DGRAM_SIZE)
                self.stats['received'] += 1
                
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
                if self.running:
                    print(f"[ERREUR] Réception: {e}")
    
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
                    del self.frame_buffer[frame_id]
                    return
            
            # En mode headless, on ne décode pas l'image
            if HEADLESS:
                self.stats['displayed'] += 1
                del self.frame_buffer[frame_id]
                return
            
            # Décoder l'image
            nparr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                with self.frame_lock:
                    self.current_frame = frame
                self.stats['displayed'] += 1
            
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
            del self.frame_buffer[fid]
    
    def get_frame(self):
        """Récupère la dernière frame"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def close(self):
        """Ferme le socket"""
        self.running = False
        self.socket.close()


def main():
    # Filtrer les arguments
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    
    # Récupérer le port depuis les arguments
    port = DEFAULT_PORT
    if len(args) > 0:
        try:
            port = int(args[0])
        except ValueError:
            print(f"[ERREUR] Port invalide: {args[0]}")
            print(f"Usage: python3 {sys.argv[0]} [PORT] [--headless]")
            sys.exit(1)
    
    print("=" * 50)
    print("  Hexapode - Récepteur Vidéo UDP")
    if HEADLESS:
        print("  (Mode HEADLESS - sans affichage)")
    print("=" * 50)
    print()
    
    # Créer le récepteur
    receiver = SimpleUDPReceiver(port)
    
    # Lancer le thread de réception
    receive_thread = threading.Thread(target=receiver.receive_loop, daemon=True)
    receive_thread.start()
    
    print()
    if HEADLESS:
        print("[INFO] Appuyez sur Ctrl+C pour quitter")
    else:
        print("[INFO] Appuyez sur 'q' pour quitter")
        print("[INFO] Appuyez sur 's' pour afficher les stats")
    print()
    
    start_time = time.time()
    last_stats_time = start_time
    
    try:
        if HEADLESS:
            # Mode headless - juste afficher les stats
            while True:
                time.sleep(5)
                elapsed = time.time() - start_time
                fps = receiver.stats['displayed'] / elapsed if elapsed > 0 else 0
                print(f"[STATS] Paquets: {receiver.stats['received']} | "
                      f"Frames: {receiver.stats['displayed']} | "
                      f"Erreurs: {receiver.stats['errors']} | "
                      f"FPS: {fps:.1f}")
        else:
            # Mode graphique
            while True:
                frame = receiver.get_frame()
                
                if frame is not None:
                    # Ajouter des infos sur l'image
                    elapsed = time.time() - start_time
                    fps = receiver.stats['displayed'] / elapsed if elapsed > 0 else 0
                    
                    info_text = f"RX: {receiver.stats['displayed']} frames | FPS: {fps:.1f}"
                    cv2.putText(frame, info_text, (10, frame.shape[0] - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    
                    cv2.imshow('Hexapode Camera - UDP Stream', frame)
                else:
                    # Créer une image d'attente
                    wait_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(wait_frame, "En attente du flux video...", (120, 240),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.putText(wait_frame, f"Port UDP: {port}", (220, 280),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    cv2.putText(wait_frame, f"Paquets recus: {receiver.stats['received']}", (200, 320),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.imshow('Hexapode Camera - UDP Stream', wait_frame)
                
                # Gérer les touches
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    print("\n[INFO] Arrêt demandé...")
                    break
                elif key == ord('s'):
                    elapsed = time.time() - start_time
                    fps = receiver.stats['displayed'] / elapsed if elapsed > 0 else 0
                    print(f"\n[STATS] Paquets: {receiver.stats['received']} | "
                          f"Frames: {receiver.stats['displayed']} | "
                          f"Erreurs: {receiver.stats['errors']} | "
                          f"FPS: {fps:.1f}")
                
                # Afficher les stats toutes les 10 secondes
                if time.time() - last_stats_time > 10:
                    elapsed = time.time() - start_time
                    fps = receiver.stats['displayed'] / elapsed if elapsed > 0 else 0
                    if receiver.stats['received'] > 0:
                        print(f"[STATS] Paquets: {receiver.stats['received']} | "
                              f"Frames: {receiver.stats['displayed']} | FPS: {fps:.1f}")
                    last_stats_time = time.time()
    
    except KeyboardInterrupt:
        print("\n[INFO] Interruption...")
    
    finally:
        receiver.close()
        if not HEADLESS:
            cv2.destroyAllWindows()
        print("[OK] Récepteur arrêté")


if __name__ == '__main__':
    main()
