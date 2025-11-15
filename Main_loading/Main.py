import time
import threading
import keyboard
import os
from controller import Controller
from movementbank import MovementBank
from movementimport import import_all
from Pictures.CameraManager import CameraManager

class PhotoDeletionThread(threading.Thread):
    def __init__(self, photo_dir, buffer_size):
        super().__init__(daemon=True)
        self.photo_dir = photo_dir
        self.buffer_size = buffer_size

    def run(self):
        while True:
            try:
                photos = sorted(
                    [os.path.join(self.photo_dir, f) for f in os.listdir(self.photo_dir) if f.endswith(".jpg")],
                    key=os.path.getmtime
                )
                if len(photos) > self.buffer_size:
                    for photo in photos[:-self.buffer_size]:
                        os.remove(photo)
                        print(f"[INFO] Photo supprimée : {photo}")
            except Exception as e:
                print(f"[ERROR] Erreur lors de la suppression des photos : {e}")
            time.sleep(0.5)

class StateMachine:
    def __init__(self, controller, basic_set, camera_manager):
        self.controller = controller
        self.basic_set = basic_set
        self.camera_manager = camera_manager
        self.state = "autonomous"
        self.next_movement = "forward"
        self.movement_lock = threading.Lock()
        threading.Thread(target=self.key_listener, daemon=True).start()
    
    def key_listener(self):
        while True:
            if keyboard.is_pressed('m'):
                self.state = "manual"
                print("[INFO] Passage en mode manuel")
            elif keyboard.is_pressed('a'):
                self.state = "autonomous"
                print("[INFO] Passage en mode autonome")
            elif self.state == "manual":
                with self.movement_lock:
                    if keyboard.is_pressed('z'):
                        self.next_movement = "forward"
                    elif keyboard.is_pressed('q'):
                        self.next_movement = "left"
                    elif keyboard.is_pressed('s'):
                        self.next_movement = "backward"
                    elif keyboard.is_pressed('d'):
                        self.next_movement = "right"
                    elif keyboard.is_pressed('space'):
                        self.next_movement = "still"
            time.sleep(0.05)
    
    def run(self):
        while True:
            try:
                if self.state == "autonomous":
                    self.camera_manager.capture_photo()
                    detected_color = self.camera_manager.process_photos()
                    movement_name = {"red": "right", "green": "left", "none": "forward"}.get(detected_color, "forward")
                else:
                    with self.movement_lock:
                        movement_name = self.next_movement
                
                movement = self.basic_set.get_movement(movement_name)
                self.controller.execute_movement(movement)
                time.sleep(0.05)
            except KeyboardInterrupt:
                print("[INFO] Arrêt manuel détecté.")
                break
            except Exception as e:
                print(f"[ERROR] Erreur dans la machine d'états : {e}")

if __name__ == "__main__":
    try:
        movement_bank = MovementBank()
        import_all(movement_bank)
        basic_set = movement_bank.get_movement_set("basic movements")
        controller = Controller()
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'initialisation des modules : {e}")
        exit(1)
    
    PHOTO_DIR = "./Pictures/photos"
    BUFFER_SIZE = 10
    
    try:
        camera_manager = CameraManager(PHOTO_DIR, BUFFER_SIZE)
        deletion_thread = PhotoDeletionThread(PHOTO_DIR, BUFFER_SIZE)
        deletion_thread.start()
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'initialisation de la caméra ou du thread de suppression : {e}")
        exit(1)
    
    state_machine = StateMachine(controller, basic_set, camera_manager)
    state_machine.run()
