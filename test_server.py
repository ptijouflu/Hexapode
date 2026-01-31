#!/usr/bin/env python3
"""
Test simple du serveur web pour vérifier la connectivité
"""

import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            html = '''<!DOCTYPE html>
<html><head><title>Test Hexapode</title></head><body>
<h1>🕷️ Serveur Hexapode Fonctionnel</h1>
<p>Le serveur web démarre correctement sur le port 8080.</p>
<p><a href="/test">Page de test</a></p>
</body></html>'''
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        elif self.path == '/test':
            html = '<h1>✅ Test réussi !</h1>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            self.send_error(404)
    
    def log_message(self, *args):
        pass

def main():
    port = 8080
    print(f"Démarrage du serveur test sur port {port}...")
    
    try:
        server = ThreadedHTTPServer(('0.0.0.0', port), TestHandler)
        print(f"✅ Serveur démarré sur http://localhost:{port}")
        print("Appuyez sur Ctrl+C pour arrêter")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du serveur...")
        server.shutdown()
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == '__main__':
    main()