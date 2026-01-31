#!/usr/bin/env python3
"""
Script de test final pour vérifier le fonctionnement complet
"""
import subprocess
import time
import threading
import requests
import sys

def test_http_server():
    """Test du serveur HTTP"""
    print("🌐 Test du serveur HTTP...")
    
    # Attendre que le serveur démarre
    for i in range(10):
        try:
            response = requests.get("http://localhost:8080/", timeout=2)
            if response.status_code == 200:
                print("✅ Serveur HTTP accessible")
                print("✅ Interface web disponible sur http://localhost:8080")
                return True
        except:
            time.sleep(1)
    
    print("❌ Serveur HTTP non accessible")
    return False

def test_streaming():
    """Test du streaming vidéo"""
    print("📹 Test du streaming vidéo...")
    
    try:
        response = requests.get("http://localhost:8080/stream", timeout=5, stream=True)
        if response.status_code == 200:
            # Lire quelques bytes du stream
            content = next(response.iter_content(chunk_size=1024))
            if content:
                print("✅ Stream vidéo fonctionnel")
                return True
    except Exception as e:
        print(f"❌ Erreur streaming: {e}")
    
    return False

def main():
    print("🕷️  TEST COMPLET - HEXAPODE CONTRÔLE MANUEL")
    print("=" * 50)
    
    # Lancer Deplacement_Manuel.py en arrière-plan
    print("🚀 Lancement de Deplacement_Manuel.py...")
    
    try:
        # Tuer les processus existants
        subprocess.run("pkill -f Deplacement_Manuel", shell=True, check=False)
        time.sleep(1)
        
        # Lancer le script
        process = subprocess.Popen(
            ["python3", "Deplacement_Manuel.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/home/user/Documents/Hexapode"
        )
        
        # Attendre le démarrage
        time.sleep(5)
        
        # Vérifier que le processus est encore en cours
        if process.poll() is not None:
            print("❌ Le processus s'est arrêté prématurément")
            stdout, stderr = process.communicate()
            print("STDOUT:", stdout.decode())
            print("STDERR:", stderr.decode())
            return False
        
        print("✅ Deplacement_Manuel.py démarré")
        
        # Tests
        http_ok = test_http_server()
        stream_ok = test_streaming()
        
        # Résultats
        print("\n" + "=" * 50)
        print("📊 RÉSULTATS DES TESTS:")
        print(f"   Serveur HTTP: {'✅' if http_ok else '❌'}")
        print(f"   Streaming:    {'✅' if stream_ok else '❌'}")
        
        if http_ok and stream_ok:
            print("\n🎉 TOUS LES TESTS RÉUSSIS!")
            print("   Le système est opérationnel.")
            print("   Interface web: http://localhost:8080")
            print("\n⚡ Les déplacements devraient maintenant être fluides")
            print("   (séparation des threads vidéo/moteur)")
        else:
            print("\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        
        # Arrêter le processus
        process.terminate()
        process.wait(timeout=5)
        print("\n🛑 Processus arrêté")
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False
    
    return http_ok and stream_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)