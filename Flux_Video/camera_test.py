#!/usr/bin/env python3
"""
Script de Test de la Caméra - Démarrage et Vérification
Teste si la caméra fonctionne correctement avec rpicam
"""

import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path


class CameraTest:
    """Test et valide le fonctionnement de la caméra"""

    def __init__(self):
        self.test_dir = Path("./camera_test_output")
        self.test_dir.mkdir(exist_ok=True)
        self.success_count = 0
        self.fail_count = 0

    def print_header(self, text):
        """Affiche un titre formaté"""
        print("\n" + "=" * 70)
        print(f"  {text}")
        print("=" * 70)

    def print_status(self, status, message):
        """Affiche un statut avec emoji"""
        symbols = {
            "OK": "✅",
            "FAIL": "❌",
            "INFO": "ℹ️",
            "WARN": "⚠️",
            "TEST": "🧪",
            "CAMERA": "📷"
        }
        symbol = symbols.get(status, "•")
        print(f"{symbol} {message}")

    def test_rpicam_installed(self):
        """Vérifie que rpicam est installé"""
        self.print_status("TEST", "Vérification rpicam...")
        
        result = subprocess.run(
            ["which", "rpicam-jpeg"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            path = result.stdout.strip()
            self.print_status("OK", f"rpicam-jpeg trouvé: {path}")
            self.success_count += 1
            return True
        else:
            self.print_status("FAIL", "rpicam-jpeg non trouvé")
            self.print_status("WARN", "Installer: sudo apt-get install -y libcamera-apps")
            self.fail_count += 1
            return False

    def test_rpicam_hello(self):
        """Teste rpicam-hello (aperçu rapide)"""
        self.print_status("TEST", "Test rpicam-hello (3 secondes)...")
        
        try:
            result = subprocess.run(
                ["timeout", "3", "rpicam-hello"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # rpicam-hello affiche beaucoup d'infos, juste vérifier qu'il s'est exécuté
            if "libcamera" in result.stderr or result.returncode in [0, 124]:
                self.print_status("OK", "rpicam-hello fonctionne (caméra réactive)")
                self.success_count += 1
                return True
            else:
                self.print_status("FAIL", "rpicam-hello n'a pas répondu correctement")
                self.fail_count += 1
                return False
                
        except subprocess.TimeoutExpired:
            self.print_status("FAIL", "rpicam-hello timeout")
            self.fail_count += 1
            return False
        except Exception as e:
            self.print_status("FAIL", f"Erreur: {e}")
            self.fail_count += 1
            return False

    def test_capture_photo(self):
        """Teste une capture de photo"""
        self.print_status("TEST", "Capture d'une photo...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_path = self.test_dir / f"test_photo_{timestamp}.jpg"
        
        cmd = f"rpicam-jpeg -o {photo_path} --timeout=1000 --nopreview 2>/dev/null"
        
        try:
            exit_code = os.system(cmd)
            
            if exit_code == 0 and photo_path.exists():
                size = photo_path.stat().st_size
                self.print_status("OK", f"Photo capturée: {photo_path.name} ({size} bytes)")
                self.success_count += 1
                return True
            else:
                self.print_status("FAIL", "Photo non sauvegardée")
                self.fail_count += 1
                return False
                
        except Exception as e:
            self.print_status("FAIL", f"Erreur capture: {e}")
            self.fail_count += 1
            return False

    def test_video_capture(self):
        """Teste une capture vidéo courte"""
        self.print_status("TEST", "Capture vidéo courte (2 secondes)...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_path = self.test_dir / f"test_video_{timestamp}.h264"
        
        cmd = f"rpicam-vid -t 2000 -o {video_path} --nopreview 2>/dev/null"
        
        try:
            exit_code = os.system(cmd)
            
            if exit_code == 0 and video_path.exists():
                size = video_path.stat().st_size
                self.print_status("OK", f"Vidéo capturée: {video_path.name} ({size} bytes)")
                self.success_count += 1
                return True
            else:
                self.print_status("FAIL", "Vidéo non sauvegardée")
                self.fail_count += 1
                return False
                
        except Exception as e:
            self.print_status("FAIL", f"Erreur capture vidéo: {e}")
            self.fail_count += 1
            return False

    def check_opencv(self):
        """Vérifie que OpenCV est disponible"""
        self.print_status("TEST", "Vérification OpenCV...")
        
        try:
            import cv2
            version = cv2.__version__
            self.print_status("OK", f"OpenCV {version} disponible")
            self.success_count += 1
            return True
        except ImportError:
            self.print_status("FAIL", "OpenCV non trouvé")
            self.print_status("WARN", "Installer: pip install opencv-contrib-python")
            self.fail_count += 1
            return False

    def check_imagezmq(self):
        """Vérifie que imagezmq est disponible"""
        self.print_status("TEST", "Vérification imagezmq...")
        
        try:
            import imagezmq
            self.print_status("OK", "imagezmq disponible")
            self.success_count += 1
            return True
        except ImportError:
            self.print_status("FAIL", "imagezmq non trouvé")
            self.print_status("WARN", "Installer: pip install imagezmq")
            self.fail_count += 1
            return False

    def show_system_info(self):
        """Affiche des infos système"""
        self.print_status("INFO", "Informations système:")
        
        # Hostname
        try:
            hostname = subprocess.check_output(["hostname"], text=True).strip()
            print(f"    Hostname: {hostname}")
        except:
            pass
        
        # Python version
        print(f"    Python: {sys.version.split()[0]}")
        
        # Répertoire de test
        print(f"    Test output: {self.test_dir.absolute()}")

    def run_all_tests(self):
        """Exécute tous les tests"""
        self.print_header("🧪 TEST DE LA CAMÉRA - DÉMARRAGE")
        
        self.show_system_info()
        
        self.print_header("📷 TESTS MATÉRIEL")
        
        # Tests matériel
        rpicam_ok = self.test_rpicam_installed()
        if not rpicam_ok:
            self.print_header("❌ ARRÊT - rpicam non disponible")
            return False
        
        hello_ok = self.test_rpicam_hello()
        if not hello_ok:
            self.print_header("❌ ARRÊT - Caméra non réactive")
            return False
        
        photo_ok = self.test_capture_photo()
        video_ok = self.test_video_capture()
        
        self.print_header("📦 TESTS LOGICIELS")
        
        # Tests logiciels
        opencv_ok = self.check_opencv()
        zmq_ok = self.check_imagezmq()
        
        self.print_header("📊 RÉSUMÉ")
        
        print(f"✅ Succès: {self.success_count}")
        print(f"❌ Échecs: {self.fail_count}")
        
        if self.fail_count == 0:
            self.print_status("OK", "🎉 TOUS LES TESTS RÉUSSIS!")
            print("\n✅ Le système est prêt pour le streaming vidéo")
            print("   Lancer: python3 camera_stream.py")
            return True
        else:
            self.print_status("FAIL", f"⚠️  {self.fail_count} test(s) échoué(s)")
            print("\n   Voir les messages d'erreur ci-dessus")
            return False

    def cleanup_test_output(self):
        """Nettoie les fichiers de test"""
        import shutil
        try:
            shutil.rmtree(self.test_dir)
            self.print_status("INFO", f"Répertoire de test nettoyé: {self.test_dir}")
        except Exception as e:
            self.print_status("WARN", f"Impossible de nettoyer: {e}")


def main():
    """Fonction principale"""
    tester = CameraTest()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interruption par l'utilisateur")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Erreur non gérée: {e}")
        sys.exit(1)
    finally:
        # Optionnel: nettoyer les tests
        # tester.cleanup_test_output()
        pass


if __name__ == "__main__":
    main()
