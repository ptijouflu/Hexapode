#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH GUI Client pour Raspberry Pi Hexapode
Application principale
"""

import sys
from PyQt6.QtWidgets import QApplication
from ssh_main_window import SSHMainWindow


def main():
    """Point d'entrée de l'application"""
    app = QApplication(sys.argv)
    window = SSHMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
