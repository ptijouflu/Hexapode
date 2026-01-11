"""
Hexapode - Gestionnaire de clavier
Gestion des entrées clavier en mode non-bloquant
"""

import sys
import select
import termios
import tty


class KeyboardHandler:
    """
    Gestion du clavier en mode non-bloquant.
    Permet de lire les touches sans bloquer l'exécution.
    """
    
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        self._setup()
    
    def _setup(self):
        """Configure le terminal en mode raw/cbreak"""
        tty.setcbreak(self.fd)
    
    def get_key(self):
        """
        Retourne la touche pressée ou None si aucune touche.
        Non-bloquant.
        """
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return None
    
    def wait_key(self, timeout=None):
        """
        Attend une touche avec timeout optionnel.
        
        Args:
            timeout: Temps d'attente en secondes (None = infini)
        
        Returns:
            La touche pressée ou None si timeout
        """
        if timeout is None:
            return sys.stdin.read(1)
        
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            return sys.stdin.read(1)
        return None
    
    def restore(self):
        """Restaure les paramètres originaux du terminal"""
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
    
    def __enter__(self):
        """Support du context manager (with statement)"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restaure le terminal à la sortie du context manager"""
        self.restore()
        return False
    
    def __del__(self):
        """Destructeur - assure la restauration du terminal"""
        try:
            self.restore()
        except:
            pass
