#!/usr/bin/env python3
"""
Hexapode - Navigation Autonome avec Évitement d'Obstacles
Avance automatiquement et esquive les obstacles détectés
Format large (640x240) pour meilleure vision latérale

Version refactorisée utilisant les modules partagés hexapod/
"""

import cv2
import time
import signal
import logging
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Import des modules partagés
from hexapod import (
    MotorController,
    KeyboardHandler,
    ObstacleDetector,
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
# SERVEUR HTTP STREAMING (spécifique à la navigation avec interface web)
# ============================================================================

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Serveur HTTP multi-thread pour meilleure réactivité"""
    daemon_threads = True
    allow_reuse_address = True


class NavigationStreamHandler(BaseHTTPRequestHandler):
    """Handler HTTP pour streaming vidéo en temps réel avec interface de navigation"""
    
    shared_frame = None
    shared_lock = threading.Lock()
    shared_stats = {
        'fps': 0, 'obstacles': 0, 'danger': 'INIT', 
        'action': 'stop', 'state': 'INIT', 'paused': False
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
<title>Hexapode Navigation</title>
<meta charset="utf-8">
<style>
body{font-family:Arial;background:#111;color:#eee;text-align:center;margin:10px}
h1{color:#0f8;margin:10px 0}
#v{max-width:95%;border:2px solid #0f8;border-radius:8px}
#s{margin:10px;padding:10px;border-radius:5px;font-size:18px;font-weight:bold}
#action{font-size:24px;margin:10px}
.info{font-size:12px;color:#888;margin-top:10px}
.leg{display:inline-block;background:#222;padding:10px;border-radius:5px;margin:10px;text-align:left}
.leg span{display:inline-block;width:12px;height:12px;margin-right:5px;border-radius:2px}
.paused{background:#f80!important;animation:blink 1s infinite}
@keyframes blink{50%{opacity:0.5}}
.controls{background:#222;padding:15px;border-radius:8px;margin:10px auto;max-width:400px}
</style>
<script>
function u(){fetch('/status').then(r=>r.json()).then(d=>{
let s=document.getElementById('s');
let a=document.getElementById('action');
let actions={'forward':'⬆️ AVANCE','slide_left':'⬅️ GAUCHE','slide_right':'➡️ DROITE','pivot_left':'↩️ ROT.GAUCHE','pivot_right':'↪️ ROT.DROITE','stop':'🛑 STOP'};
a.innerHTML=d.paused?'⏸️ PAUSE':actions[d.action]||d.action;
a.className=d.paused?'paused':'';
s.innerHTML='État: '+d.state+' | Danger: '+d.danger+' | Obs: '+d.obstacles+' | '+d.fps.toFixed(1)+' det/s';
s.style.background=d.danger=='STOP'?'#f00':d.danger=='WARN'?'#f80':d.danger=='OBS'?'#ff0':'#0f0';
s.style.color=d.danger=='OBS'||d.danger=='OK'?'#000':'#fff';
if(d.paused)s.style.background='#f80';
}).catch(e=>{});}
setInterval(u,200);
</script>
</head><body>
<h1>🤖 Hexapode - Navigation Autonome</h1>
<div id="action">Chargement...</div>
<img id="v" src="/stream">
<div id="s">Connexion...</div>
<div class="controls">
<b>Contrôles (sur le robot):</b><br>
ESPACE = Pause/Reprendre<br>
Ctrl+C ou Q = Quitter
</div>
<div class="leg">
<span style="background:#0f0"></span>OK - Libre
<span style="background:#ff0;margin-left:15px"></span>OBS - Obstacle
<span style="background:#f80;margin-left:15px"></span>WARN - Attention
<span style="background:#f00;margin-left:15px"></span>STOP - Danger
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


# ============================================================================
# NAVIGATEUR AUTONOME
# ============================================================================

class AutonomousNavigator:
    """
    Navigation autonome avec évitement d'obstacles
    
    Logique:
    1. Avancer par défaut
    2. Si obstacle à gauche -> translation droite
    3. Si obstacle à droite -> translation gauche
    4. Si obstacle au centre (DANGER) -> ROTATION vers le côté sûr puis avance
    5. Si obstacles des deux côtés -> rotation vers le côté le moins dangereux
    6. Si libre -> reprendre avance
    
    Contrôles:
    - ESPACE: Démarrer/Pause/Reprendre (arrête moteurs + position initiale)
    - Ctrl+C: Quitter complètement
    """
    
    def __init__(self):
        self.running = False
        self.paused = True  # Démarre en pause, attente ESPACE
        self.started = False  # Premier démarrage pas encore fait
        self.quit_requested = False  # Demande de quitter
        
        # Gestion clavier (module partagé)
        self.keyboard = KeyboardHandler()
        
        # Composants (modules partagés)
        self.camera = FastCamera()  # Utilise les constantes du module
        self.detector = ObstacleDetector()  # Utilise les constantes du module
        self.motors = MotorController()
        
        # Serveur HTTP pour streaming
        self.http_server = None
        self.http_thread = None
        self._start_http_server()
        
        # État de navigation
        self.current_state = "INIT"
        self.last_obstacle_position = None
        self.escape_direction = None
        self.escape_steps = 0
        self.max_escape_steps = 10
        
        # Gestion rotation en cas de danger
        self.danger_count = 0
        self.rotation_direction = None
        
        # Stats
        self.detection_count = 0
        self.start_time = None
        
        time.sleep(1)  # Attendre initialisation camera
        logger.info("✓ Navigateur autonome initialisé")
    
    def _start_http_server(self):
        """Démarre le serveur HTTP pour le streaming"""
        try:
            self.http_server = ThreadedHTTPServer(('0.0.0.0', HTTP_PORT), NavigationStreamHandler)
            self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.http_thread.start()
            logger.info(f"✓ Serveur HTTP sur port {HTTP_PORT}")
            logger.info(f"  SSH: ssh -L {HTTP_PORT}:localhost:{HTTP_PORT} user@[IP]")
            logger.info(f"  Puis: http://localhost:{HTTP_PORT}")
        except Exception as e:
            logger.warning(f"Impossible de démarrer le serveur HTTP: {e}")
    
    def _decide_action(self, danger, position, obstacles):
        """
        Machine à états pour décider de l'action
        Retourne: 'forward', 'slide_left', 'slide_right', 'pivot_left', 'pivot_right', 'stop'
        """
        
        # DANGER: Obstacle très proche au centre -> ROTATION (1 pas à la fois)
        if danger == "STOP":
            self.danger_count += 1
            self.current_state = "DANGER"
            
            # Déterminer le côté le plus sûr pour la rotation
            left_clear = True
            right_clear = True
            
            for o in obstacles:
                if o['pos'] == "G" and o['dist'] > 0.3:
                    left_clear = False
                if o['pos'] == "D" and o['dist'] > 0.3:
                    right_clear = False
            
            # Choisir direction de rotation
            if left_clear and not right_clear:
                self.rotation_direction = "LEFT"
            elif right_clear and not left_clear:
                self.rotation_direction = "RIGHT"
            elif self.rotation_direction is None:
                self.rotation_direction = "LEFT"
            
            logger.info(f"🔄 DANGER! Rotation {'GAUCHE' if self.rotation_direction == 'LEFT' else 'DROITE'} (1 pas)")
            
            if self.rotation_direction == "LEFT":
                return 'pivot_left'
            else:
                return 'pivot_right'
        
        # Reset compteur danger si pas en STOP
        self.danger_count = 0
        
        # Obstacle au centre (moins proche) -> essayer de contourner
        if position == "CENTER":
            self.current_state = "AVOIDING"
            if self.escape_direction is None:
                self.escape_direction = "LEFT"
            if self.escape_direction == "LEFT":
                return 'slide_left'
            else:
                return 'slide_right'
        
        # Obstacles des deux côtés
        if position == "BOTH":
            self.current_state = "BLOCKED"
            self.escape_steps += 1
            
            if self.escape_steps > 6:
                self.escape_steps = 0
                if self.rotation_direction is None:
                    self.rotation_direction = "LEFT"
                return 'pivot_left' if self.rotation_direction == "LEFT" else 'pivot_right'
            
            if self.escape_steps % 6 < 3:
                return 'slide_left'
            else:
                return 'slide_right'
        
        # Obstacle à gauche -> translation droite
        if position == "LEFT":
            self.current_state = "AVOIDING"
            self.escape_direction = "RIGHT"
            self.escape_steps += 1
            if self.escape_steps > self.max_escape_steps:
                self.escape_steps = 0
                return 'forward'
            return 'slide_right'
        
        # Obstacle à droite -> translation gauche
        if position == "RIGHT":
            self.current_state = "AVOIDING"
            self.escape_direction = "LEFT"
            self.escape_steps += 1
            if self.escape_steps > self.max_escape_steps:
                self.escape_steps = 0
                return 'forward'
            return 'slide_left'
        
        # Pas d'obstacle -> avancer
        self.current_state = "FORWARD"
        self.escape_direction = None
        self.escape_steps = 0
        return 'forward'
    
    def _handle_keyboard(self):
        """Gère les entrées clavier. Retourne True si on doit quitter."""
        key = self.keyboard.get_key()
        
        if key is None:
            return False
        
        # Espace = Démarrer/Pause/Reprendre
        if key == ' ':
            if not self.started:
                self.started = True
                self.paused = False
                self.start_time = time.time()
                logger.info("=" * 50)
                logger.info("🚀 NAVIGATION DÉMARRÉE !")
                logger.info("   ESPACE = Pause/Reprendre")
                logger.info("=" * 50)
            else:
                self.paused = not self.paused
                if self.paused:
                    self.motors.stop()
                    logger.info("⏸️  PAUSE - Appuyez sur ESPACE pour reprendre")
                else:
                    logger.info("▶️  REPRISE de la navigation")
            return False
        
        # Ctrl+C ou 'q' = Quitter
        if key == '\x03' or key == 'q' or key == 'Q':
            self.quit_requested = True
            return True
        
        return False
    
    def run(self):
        """Boucle principale de navigation"""
        self.running = True
        self.start_time = time.time()
        last_log_time = time.time()
        
        logger.info("=" * 50)
        logger.info("🤖 NAVIGATION AUTONOME PRÊTE")
        logger.info("   ▶️  Appuyez sur ESPACE pour DÉMARRER")
        logger.info("   Ctrl+C ou Q = Quitter")
        logger.info("=" * 50)
        
        try:
            while self.running and not self.quit_requested:
                # Vérifier le clavier
                if self._handle_keyboard():
                    break
                
                # Capturer frame
                frame = self.camera.get_frame()
                
                # Si en pause ou pas encore démarré
                if self.paused:
                    if frame is not None:
                        display_frame = frame.copy()
                        h, w = display_frame.shape[:2]
                        
                        if not self.started:
                            msg = "Appuyez sur ESPACE pour demarrer"
                            cv2.putText(display_frame, msg, (w//2 - 180, h//2), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                            status = "ATTENTE"
                        else:
                            msg = "PAUSE - ESPACE pour reprendre"
                            cv2.putText(display_frame, msg, (w//2 - 160, h//2), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                            status = "PAUSE"
                        
                        with NavigationStreamHandler.shared_lock:
                            NavigationStreamHandler.shared_frame = display_frame
                            NavigationStreamHandler.shared_stats = {
                                'fps': 0,
                                'obstacles': 0,
                                'danger': status,
                                'action': 'stop',
                                'state': status,
                                'paused': True
                            }
                    
                    time.sleep(0.1)
                    continue
                
                if frame is None:
                    time.sleep(0.05)
                    continue
                
                # Détecter obstacles
                obstacles, danger, position = self.detector.detect(frame)
                self.detection_count += 1
                
                # Décider action
                action = self._decide_action(danger, position, obstacles)
                
                # Dessiner les obstacles
                display_frame = self.detector.draw(frame.copy(), obstacles, danger, position)
                
                # Ajouter infos sur la frame
                elapsed = time.time() - self.start_time
                det_fps = self.detection_count / elapsed if elapsed > 0 else 0
                action_text = {
                    'forward': 'AVANCE', 
                    'slide_left': 'GAUCHE', 
                    'slide_right': 'DROITE',
                    'pivot_left': 'ROT.G',
                    'pivot_right': 'ROT.D',
                    'stop': 'STOP'
                }.get(action, action)
                status_text = f"{action_text} | {det_fps:.1f} det/s"
                cv2.putText(display_frame, status_text, (5, 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                
                # Mettre à jour le stream HTTP
                with NavigationStreamHandler.shared_lock:
                    NavigationStreamHandler.shared_frame = display_frame
                    NavigationStreamHandler.shared_stats = {
                        'fps': det_fps,
                        'obstacles': len(obstacles),
                        'danger': danger,
                        'action': action,
                        'state': self.current_state,
                        'paused': self.paused
                    }
                
                # Exécuter action
                if action == 'forward':
                    self.motors.forward()
                elif action == 'slide_left':
                    self.motors.slide_left()
                elif action == 'slide_right':
                    self.motors.slide_right()
                elif action == 'pivot_left':
                    self.motors.pivot_left()
                elif action == 'pivot_right':
                    self.motors.pivot_right()
                else:
                    self.motors.stop()
                
                # Log toutes les secondes
                if time.time() - last_log_time >= 1.0:
                    action_symbols = {
                        'forward': '⬆️  AVANCE',
                        'slide_left': '⬅️  GAUCHE',
                        'slide_right': '➡️  DROITE',
                        'pivot_left': '↩️  ROT.G',
                        'pivot_right': '↪️  ROT.D',
                        'stop': '🛑 STOP'
                    }
                    
                    obs_info = ""
                    if obstacles:
                        obs_info = " | " + ", ".join([f"{o['size']}{o['pos']}" for o in obstacles[:3]])
                    
                    logger.info(
                        f"[{danger:4}] {action_symbols.get(action, action):12} | "
                        f"{det_fps:.1f} det/s | {len(obstacles)} obs{obs_info}"
                    )
                    last_log_time = time.time()
                
                # Délai selon action
                time.sleep(self.motors.get_delay())
                
        except KeyboardInterrupt:
            logger.info("\n⚠️ Ctrl+C détecté - Arrêt...")
        finally:
            self.stop()
    
    def stop(self):
        """Arrête tout proprement"""
        logger.info("Arrêt en cours...")
        self.running = False
        
        self.motors.stop()
        time.sleep(0.5)
        self.motors.disconnect()
        self.camera.stop()
        
        if self.http_server:
            self.http_server.shutdown()
        
        self.keyboard.restore()
        
        logger.info("✓ Navigation arrêtée proprement")
        logger.info("Au revoir! 👋")


# ============================================================================
# MAIN
# ============================================================================

def main():
    original_sigint = signal.getsignal(signal.SIGINT)
    
    print()
    print("=" * 60)
    print("   🤖 HEXAPODE - NAVIGATION AUTONOME")
    print("   Format large (640x240) pour vision latérale")
    print("=" * 60)
    print()
    print("   Comportement:")
    print("   - Avance automatiquement")
    print("   - Obstacle à GAUCHE  → Translation DROITE")
    print("   - Obstacle à DROITE  → Translation GAUCHE")
    print("   - Obstacle au CENTRE → Contournement")
    print("   - Obstacles des 2 côtés → Alternance G/D")
    print()
    print("   Contrôles:")
    print("   - ESPACE   : DÉMARRER / Pause / Reprendre")
    print("   - Ctrl+C   : Quitter")
    print("   - Q        : Quitter")
    print()
    print("   📹 Streaming vidéo:")
    print(f"   - Port: {HTTP_PORT}")
    print(f"   - SSH: ssh -L {HTTP_PORT}:localhost:{HTTP_PORT} user@[IP]")
    print(f"   - Puis: http://localhost:{HTTP_PORT}")
    print()
    print("=" * 60)
    print()
    print("   ⏳ Initialisation...")
    
    time.sleep(2)
    
    navigator = None
    try:
        navigator = AutonomousNavigator()
        navigator.run()
    except Exception as e:
        logger.error(f"Erreur: {e}")
    finally:
        if navigator:
            navigator.stop()
        signal.signal(signal.SIGINT, original_sigint)


if __name__ == '__main__':
    main()
