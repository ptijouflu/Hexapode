#!/usr/bin/env python3
"""
Hexapode - Contrôle manuel au clavier (ZQSD + AE)
Version refactorisée utilisant les modules partagés
"""

import time
from hexapod import MotorController, KeyboardHandler


def main():
    print("\n--- HEXAPODE CONTRÔLE (ZQSD + AE) ---")
    print(" [Z] Avancer")
    print(" [S] Reculer")
    print(" [Q] Translation Gauche")
    print(" [D] Translation Droite")
    print(" [A] Rotation Gauche")
    print(" [E] Rotation Droite")
    print(" [ESPACE] Stop")
    print(" [X] Quitter")
    print("-" * 40)
    
    # Initialisation
    motors = MotorController()
    keyboard = KeyboardHandler()
    
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
    
    try:
        while True:
            # Lecture clavier
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
                        time.sleep(0.1)
                    current_mode = new_mode
                    
                    action_names = {
                        'forward': 'AVANCER',
                        'backward': 'RECULER', 
                        'slide_left': 'GAUCHE',
                        'slide_right': 'DROITE',
                        'pivot_left': 'ROT. GAUCHE',
                        'pivot_right': 'ROT. DROITE',
                        'stop': 'STOP'
                    }
                    print(f"\r >> {action_names.get(current_mode, current_mode)}      ", end="")
            
            # Exécuter l'action
            if current_mode == 'stop':
                motors.stop()
                time.sleep(0.1)
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
            
            # Délai selon l'action
            time.sleep(motors.get_delay())
    
    except KeyboardInterrupt:
        print("\n\nInterruption...")
    
    finally:
        motors.disconnect()
        keyboard.restore()
        print("Fin.")


if __name__ == '__main__':
    main()