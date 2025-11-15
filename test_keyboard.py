import curses

def main(stdscr):
    stdscr.nodelay(True)  # Ne bloque pas l'attente de touche
    stdscr.clear()
    stdscr.addstr("Appuyez sur z/q/s/d pour avancer/gauche/reculer/droite. Appuyez sur m pour quitter.\n")
    while True:
        key = stdscr.getch()
        if key != -1:  # Si une touche est pressée
            if key == ord('z'):
                stdscr.addstr("Vous venez d'appuyer sur la touche : Avancer (z)\n")
            elif key == ord('q'):
                stdscr.addstr("Vous venez d'appuyer sur la touche : Gauche (q)\n")
            elif key == ord('s'):
                stdscr.addstr("Vous venez d'appuyer sur la touche : Reculer (s)\n")
            elif key == ord('d'):
                stdscr.addstr("Vous venez d'appuyer sur la touche : Droite (d)\n")
            elif key == ord('m'):
                stdscr.addstr("Vous venez d'appuyer sur la touche : Quitter (m). Fermeture de l'application...\n")
                break
        stdscr.refresh()

if __name__ == '__main__':
    curses.wrapper(main)
