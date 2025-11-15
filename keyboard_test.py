from pynput.keyboard import Listener, Key

def on_press(key):
    try:
        if key.char == 'z':  # Vérifie si la touche "z" est pressée
            print("Touche Z détectée")
    except AttributeError:
        pass

with Listener(on_press=on_press) as listener:
    listener.join()
