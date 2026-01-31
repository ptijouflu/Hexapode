#!/usr/bin/env python3
"""
Hexapode - Contrôle manuel au clavier (ZQSD + AE) avec flux vidéo
Version refactorisée utilisant les modules partagés
"""

import cv2
import time
import threading
import json
import logging
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Import des modules partagés
from hexapod import (
    MotorController,
    KeyboardHandler,
    FastCamera,
    HTTP_PORT
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# SERVEUR HTTP STREAMING
# ============================================================================

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Serveur HTTP multi-thread pour meilleure réactivité"""
    daemon_threads = True
    allow_reuse_address = True


class ManualStreamHandler(BaseHTTPRequestHandler):
    """Handler HTTP pour streaming vidéo en contrôle manuel"""
    
    shared_frame = None
    shared_lock = threading.Lock()
    shared_stats = {
        'fps': 0, 'action': 'stop', 'mode': 'manuel'
    }
    
    protocol_version = 'HTTP/1.1'
    
    def do_GET(self):
        if self.path == '/':
            self._send_html()
        elif self.path == '/stream':
            self._send_stream()
        elif self.path == '/status':
            self._send_status()
        else:
            self.send_error(404)
    
    def _send_html(self):
        html = '''<!DOCTYPE html>
<html><head>
<title>Hexapode Contrôle Manuel</title>
<meta charset="utf-8">
<style>
body{font-family:Arial;background:#111;color:#eee;text-align:center;margin:10px}
h1{color:#0f8;margin:10px 0}
#v{max-width:95%;border:2px solid #0f8;border-radius:8px}
#s{margin:10px;padding:10px;border-radius:5px;font-size:18px;font-weight:bold;background:#0f8;color:#000}
#action{font-size:24px;margin:10px;color:#0f8}
.info{font-size:12px;color:#888;margin-top:10px}
.controls{background:#222;padding:15px;border-radius:8px;margin:10px auto;max-width:500px;text-align:left}
.controls b{color:#0f8}
</style>
<script>
function u(){fetch('/status').then(r=>r.json()).then(d=>{
let s=document.getElementById('s');
let a=document.getElementById('action');
let actions={'forward':'↑ AVANCER','backward':'↓ RECULER','slide_left':'← GAUCHE','slide_right':'→ DROITE','pivot_left':'↺ ROT.GAUCHE','pivot_right':'↻ ROT.DROITE','stop':'■ STOP'};
a.innerHTML=actions[d.action]||d.action;
s.innerHTML='Mode: '+d.mode+' | FPS: '+(d.fps||0).toFixed(1);
}).catch(e=>{});}
setInterval(u,200);
</script>
</head><body>
<h1>🕷️ Hexapode - Contrôle Manuel</h1>
<div id="action">Chargement...</div>
<img id="v" src="/stream">
<div id="s">Connexion...</div>
<div class="controls">
<b>Contrôles (sur le robot):</b><br><br>
<b>Z</b> = Avancer<br>
<b>S</b> = Reculer<br>
<b>Q</b> = Translation Gauche<br>
<b>D</b> = Translation Droite<br>
<b>A</b> = Rotation Gauche<br>
<b>E</b> = Rotation Droite<br>
<b>ESPACE</b> = Stop<br>
<b>X</b> = Quitter
</div>
<div class="info">SSH: ssh -L 8080:localhost:8080 user@[IP] puis http://localhost:8080</div>
</body></html>'''
        
        data = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)
    
    def _send_status(self):
        with self.shared_lock:
            data = json.dumps(self.shared_stats).encode()
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)
    
    def _send_stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=F')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        try:
            while True:
                with self.shared_lock:
                    frame = self.shared_frame
                
                if frame is not None:
                    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    self.wfile.write(b'--F\r\nContent-Type:image/jpeg\r\n\r\n')
                    self.wfile.write(buf)
                    self.wfile.write(b'\r\n')
                
                time.sleep(0.05)  # ~20 FPS max affichage
        except:
            pass
    
    def log_message(self, *args):
        pass  # Désactiver les logs HTTP


def start_video_thread(camera):
    """Thread dédié pour la capture et le streaming vidéo"""
    frame_count = 0
    start_time = time.time()
    
    def video_loop():
        nonlocal frame_count
        while True:
            try:
                # Capturer frame vidéo
                frame = camera.get_frame()
                
                if frame is not None:
                    frame_count += 1
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    
                    # Ajouter infos sur la frame
                    display_frame = frame.copy()
                    
                    # Récupérer l'action actuelle depuis les stats partagées
                    with ManualStreamHandler.shared_lock:
                        current_action = ManualStreamHandler.shared_stats.get('action', 'stop')
                    
                    action_names = {
                        'forward': 'AVANCER',
                        'backward': 'RECULER', 
                        'slide_left': 'GAUCHE',
                        'slide_right': 'DROITE',
                        'pivot_left': 'ROT. GAUCHE',
                        'pivot_right': 'ROT. DROITE',
                        'stop': 'STOP'
                    }
                    
                    status_text = f"{action_names.get(current_action, current_action)} | {fps:.1f} FPS"
                    cv2.putText(display_frame, status_text, (5, 15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    
                    # Action actuelle en gros au centre
                    action_display = action_names.get(current_action, current_action)
                    h, w = display_frame.shape[:2]
                    cv2.putText(display_frame, action_display, (w//2 - 60, h//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    
                    # Mettre à jour le stream HTTP
                    with ManualStreamHandler.shared_lock:
                        ManualStreamHandler.shared_frame = display_frame
                        ManualStreamHandler.shared_stats.update({
                            'fps': fps,
                            'mode': 'manuel'
                        })
                else:
                    # Créer une frame noire de test
                    black_frame = np.zeros((240, 640, 3), dtype=np.uint8)
                    
                    with ManualStreamHandler.shared_lock:
                        current_action = ManualStreamHandler.shared_stats.get('action', 'stop')
                    
                    action_names = {
                        'forward': 'AVANCER',
                        'backward': 'RECULER', 
                        'slide_left': 'GAUCHE',
                        'slide_right': 'DROITE',
                        'pivot_left': 'ROT. GAUCHE',
                        'pivot_right': 'ROT. DROITE',
                        'stop': 'STOP'
                    }
                    
                    action_display = action_names.get(current_action, current_action)
                    cv2.putText(black_frame, "CAMERA NON DISPONIBLE", (180, 100), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.putText(black_frame, action_display, (250, 140), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    
                    # Mettre à jour le stream HTTP avec frame noire
                    with ManualStreamHandler.shared_lock:
                        ManualStreamHandler.shared_frame = black_frame
                        ManualStreamHandler.shared_stats.update({
                            'fps': 0,
                            'mode': 'manuel (cam. off)'
                        })
                
                # Délai pour ne pas surcharger le CPU
                time.sleep(0.05)  # ~20 FPS
                
            except Exception as e:
                logger.error(f"Erreur dans le thread vidéo: {e}")
                time.sleep(0.1)
    
    # Démarrer le thread vidéo
    video_thread = threading.Thread(target=video_loop, daemon=True)
    video_thread.start()
    return video_thread


def start_http_server():
    """Démarre le serveur HTTP pour le streaming"""
    try:
        logger.info(f"Tentative de démarrage du serveur HTTP sur port {HTTP_PORT}...")
        
        # Vérifier si le port est disponible
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', HTTP_PORT))
        sock.close()
        
        if result == 0:
            logger.warning(f"Port {HTTP_PORT} déjà utilisé, tentative d'arrêt du processus existant...")
            import os
            os.system(f"pkill -f 'python.*{HTTP_PORT}'")
            time.sleep(1)
        
        http_server = ThreadedHTTPServer(('0.0.0.0', HTTP_PORT), ManualStreamHandler)
        http_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
        http_thread.start()
        logger.info(f"[OK] Serveur HTTP démarré sur port {HTTP_PORT}")
        logger.info(f"  Interface web: http://localhost:{HTTP_PORT}")
        logger.info(f"  SSH: ssh -L {HTTP_PORT}:localhost:{HTTP_PORT} user@[IP]")
        return http_server
    except Exception as e:
        logger.error(f"Impossible de démarrer le serveur HTTP: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def main():
    print("\n" + "=" * 60)
    print("    HEXAPODE - CONTRÔLE MANUEL avec FLUX VIDÉO")
    print("=" * 60)
    print(" [Z] Avancer")
    print(" [S] Reculer")
    print(" [Q] Translation Gauche")
    print(" [D] Translation Droite")
    print(" [A] Rotation Gauche")
    print(" [E] Rotation Droite")
    print(" [ESPACE] Stop")
    print(" [X] Quitter")
    print()
    print(f"    Streaming vidéo sur port {HTTP_PORT}:")
    print(f"  SSH: ssh -L {HTTP_PORT}:localhost:{HTTP_PORT} user@[IP]")
    print(f"  Puis: http://localhost:{HTTP_PORT}")
    print("=" * 60)
    print("\nInitialisation...")
    
    # Initialisation
    logger.info("Initialisation des composants...")
    
    try:
        motors = MotorController()
        logger.info("✅ Moteurs initialisés")
    except Exception as e:
        logger.error(f"❌ Erreur moteurs: {e}")
        return
    
    try:
        keyboard = KeyboardHandler()
        logger.info("✅ Clavier initialisé")
    except Exception as e:
        logger.error(f"❌ Erreur clavier: {e}")
        motors.disconnect()
        return
    
    logger.info("Initialisation de la caméra...")
    try:
        camera = FastCamera()
        logger.info("✅ Caméra initialisée")
    except Exception as e:
        logger.error(f"❌ Erreur caméra: {e}")
        motors.disconnect()
        keyboard.restore()
        return
    
    # Démarrer le serveur HTTP
    http_server = start_http_server()
    if http_server is None:
        logger.error("Impossible de démarrer le serveur HTTP - arrêt")
        motors.disconnect()
        keyboard.restore()
        return
    
    # Démarrer le thread vidéo séparé
    video_thread = start_video_thread(camera)
    
    # Attendre que la caméra soit prête
    logger.info("Attente initialisation caméra...")
    time.sleep(2)
    
    # Test de capture d'une frame
    test_frame = camera.get_frame()
    if test_frame is not None:
        logger.info(f"✅ Caméra fonctionnelle - Frame: {test_frame.shape}")
    else:
        logger.warning("⚠️  Caméra ne produit pas de frames - streaming avec frames de test")
    
    logger.info("[OK] Système prêt - Contrôle manuel avec vidéo")
    
    current_mode = 'stop'
    
    # Mapping des touches vers les actions
    key_actions = {
        'z': 'forward',
        's': 'backward',
        'q': 'slide_left',
        'd': 'slide_right',
        'a': 'pivot_left',
        'e': 'pivot_right',
        ' ': 'stop',
    }
    
    action_names = {
        'forward': 'AVANCER',
        'backward': 'RECULER', 
        'slide_left': 'GAUCHE',
        'slide_right': 'DROITE',
        'pivot_left': 'ROT. GAUCHE',
        'pivot_right': 'ROT. DROITE',
        'stop': 'STOP'
    }
    
    try:
        while True:
            # Lecture clavier (priorité maximale pour la réactivité)
            key = keyboard.get_key()
            
            if key:
                key = key.lower()
                
                # Quitter
                if key == 'x':
                    break
                
                # Changer d'action
                if key in key_actions:
                    new_mode = key_actions[key]
                    if current_mode != new_mode:
                        motors.step_index = 0
                        time.sleep(0.02)  # Délai minimal pour reset
                    current_mode = new_mode
                    
                    # Mettre à jour l'action dans les stats partagées
                    with ManualStreamHandler.shared_lock:
                        ManualStreamHandler.shared_stats['action'] = current_mode
                    
                    print(f"\r >> {action_names.get(current_mode, current_mode)}      ", end="")
            
            # Exécuter l'action moteur (boucle optimisée)
            if current_mode == 'stop':
                motors.stop()
                time.sleep(0.05)  # Délai court pour stop
                continue
            elif current_mode == 'forward':
                motors.forward()
            elif current_mode == 'backward':
                motors.backward()
            elif current_mode == 'slide_left':
                motors.slide_left()
            elif current_mode == 'slide_right':
                motors.slide_right()
            elif current_mode == 'pivot_left':
                motors.pivot_left()
            elif current_mode == 'pivot_right':
                motors.pivot_right()
            
            # Délai optimisé selon l'action (crucial pour la fluidité)
            time.sleep(motors.get_delay())
    
    except KeyboardInterrupt:
        print("\n\nInterruption...")
    
    finally:
        # Nettoyage
        motors.stop()
        time.sleep(0.5)
        motors.disconnect()
        camera.stop()
        
        if http_server:
            http_server.shutdown()
        
        keyboard.restore()
        logger.info("[OK] Système arrêté proprement")
        print("Fin.")


if __name__ == '__main__':
    main()