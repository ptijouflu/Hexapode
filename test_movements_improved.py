#!/usr/bin/env python3
"""
Script de test des mouvements améliorés
"""

import time
from controller import Controller
from movementbank import MovementBank
from movementimport import import_all

def test_movement(controller, movement, name, repetitions=3):
    """Teste un mouvement spécifique"""
    print(f"\n{'='*60}")
    print(f"Test du mouvement: {name}")
    print(f"{'='*60}")
    
    for i in range(repetitions):
        print(f"Répétition {i+1}/{repetitions}...")
        controller.execute_movement(movement)
        time.sleep(0.3)
    
    print(f"✓ Test de {name} terminé")

def main():
    print("\n🚀 Test des mouvements améliorés de l'hexapode\n")
    
    # Initialisation
    movement_bank = MovementBank()
    import_all(movement_bank)
    basic_set = movement_bank.get_movement_set("basic movements")
    controller = Controller()
    
    # Position still
    print("Position initiale (still)...")
    still = basic_set.get_movement("still")
    controller.execute_movement(still)
    time.sleep(1)
    
    try:
        # Test Forward
        test_movement(controller, basic_set.get_movement("forward"), "FORWARD", 5)
        time.sleep(1)
        
        # Retour à still
        controller.execute_movement(still)
        time.sleep(1)
        
        # Test Backward
        test_movement(controller, basic_set.get_movement("backward"), "BACKWARD", 5)
        time.sleep(1)
        
        # Retour à still
        controller.execute_movement(still)
        time.sleep(1)
        
        # Test Left
        test_movement(controller, basic_set.get_movement("left"), "LEFT", 4)
        time.sleep(1)
        
        # Retour à still
        controller.execute_movement(still)
        time.sleep(1)
        
        # Test Right
        test_movement(controller, basic_set.get_movement("right"), "RIGHT", 4)
        time.sleep(1)
        
        # Position finale
        controller.execute_movement(still)
        
        print("\n" + "="*60)
        print("✓ Tous les tests terminés avec succès!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n[INFO] Test interrompu")
    except Exception as e:
        print(f"\n[ERREUR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[INFO] Désactivation du couple des servomoteurs...")
        controller.disable_torque_all()
        print("[INFO] Test terminé")

if __name__ == '__main__':
    main()
