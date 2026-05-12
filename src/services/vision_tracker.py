import cv2
import mediapipe as mp
import math
import threading
import time
import os
import urllib.request
import numpy as np

def get_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

class VisionTracker:
    def __init__(self, task_queue=None, tts_instance=None, use_face_auth=False):
        self.task_queue = task_queue
        self.tts = tts_instance
        self.running = False
        self.thread = None
        self.use_face_auth = use_face_auth
        self.is_authenticated = False
        self.is_paused = True  # Começa pausado para economizar recursos!
        
        self.last_gesture = None
        self.gesture_time = 0

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def pause(self):
        self.is_paused = True
        print("[VisionTracker] ⏸️ Rastreador pausado.")

    def resume(self):
        self.is_paused = False
        print("[VisionTracker] ▶️ Rastreador retomado.")

    def _run_loop(self):
        try:
            mp_hands = mp.solutions.hands
            hands = mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )
        except Exception:
            print("[VisionTracker] MediaPipe incompatível com esta versão do PyTorch. Rastreamento de gestos desativado.")
            self.running = False
            return
        
        face_landmarker = None
        reference_landmarks = None
        
        if self.use_face_auth:
            print("[Vision] Face Auth ativado. Inicializando...")
            try:
                from mediapipe.tasks import python as mp_python
                from mediapipe.tasks.python import vision
                
                model_path = os.path.join(os.path.dirname(__file__), "face_landmarker.task")
                if not os.path.exists(model_path):
                    print("[Vision] Baixando face_landmarker.task...")
                    urllib.request.urlretrieve("https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task", model_path)
                
                base_options = mp_python.BaseOptions(model_asset_path=model_path)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options, num_faces=1
                )
                face_landmarker = vision.FaceLandmarker.create_from_options(options)
                
                # Carregar foto de referencia se existir (na raiz do projeto)
                root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                ref_path = os.path.join(root_dir, "reference.jpg")
                if os.path.exists(ref_path):
                    ref_img = cv2.imread(ref_path)
                    ref_rgb = cv2.cvtColor(ref_img, cv2.COLOR_BGR2RGB)
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=ref_rgb)
                    res = face_landmarker.detect(mp_img)
                    if res.face_landmarks:
                        reference_landmarks = np.array([[lm.x, lm.y, lm.z] for lm in res.face_landmarks[0]], dtype=np.float32).flatten()
                        print("[Vision] Face de referência carregada com sucesso!")
            except Exception as e:
                print(f"[Vision] Erro ao carregar Face Auth: {e}")

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print("[Vision] Rastreamento de visão iniciado em background (Pausado por padrão).")

        frame_count = 0
        cap_opened = False
        
        while self.running:
            if self.is_paused:
                if cap_opened:
                    cap.release()
                    cap_opened = False
                time.sleep(1.0)
                continue
                
            if not cap_opened:
                cap = cv2.VideoCapture(0)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap_opened = True

            success, img = cap.read()
            if not success:
                time.sleep(0.1)
                continue

            # Limitador de FPS para poupar CPU (~10 fps)
            time.sleep(0.1)

            img = cv2.flip(img, 1)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Gestures
            results = hands.process(img_rgb)
            gesture = "None"
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    lm = hand_landmarks.landmark
                    index_extended = lm[8].y < lm[6].y
                    middle_extended = lm[12].y < lm[10].y
                    ring_extended = lm[16].y < lm[14].y
                    pinky_extended = lm[20].y < lm[18].y
                    
                    if index_extended and middle_extended and ring_extended and pinky_extended:
                        gesture = "Open Palm"
                    elif not index_extended and not middle_extended and not ring_extended and not pinky_extended:
                        gesture = "Closed Fist"
                    elif index_extended and middle_extended and not ring_extended and not pinky_extended:
                        gesture = "Peace Sign"
                    
                    pinch_dist = get_distance(lm[4], lm[8])
                    if pinch_dist < 0.05: gesture = "Pinching"
            self._handle_gesture(gesture)

            # Face Auth Check (Apenas 1 vez a cada 10 frames pra poupar CPU)
            frame_count += 1
            if self.use_face_auth and face_landmarker and reference_landmarks is not None and frame_count % 10 == 0:
                try:
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
                    res = face_landmarker.detect(mp_img)
                    if res.face_landmarks:
                        curr_landmarks = np.array([[lm.x, lm.y, lm.z] for lm in res.face_landmarks[0]], dtype=np.float32).flatten()
                        sim = np.dot(reference_landmarks, curr_landmarks) / (np.linalg.norm(reference_landmarks) * np.linalg.norm(curr_landmarks))
                        self.is_authenticated = sim > 0.85
                    else:
                        self.is_authenticated = False
                except: pass

            time.sleep(0.05)

        cap.release()
        print("[Vision] Rastreamento desligado.")

    def _handle_gesture(self, gesture):
        if gesture == "None" or gesture == self.last_gesture: return
            
        now = time.time()
        if now - self.gesture_time < 1.0: return
            
        self.last_gesture = gesture
        self.gesture_time = now
        
        if gesture == "Closed Fist":
            print("\n[Vision] ✊ Punho Fechado detectado: Parando fala (Mute)!")
            if self.tts: self.tts.stop()
        elif gesture == "Peace Sign":
            print("\n[Vision] ✌️ Sinal da Paz detectado: Acionando agente!")
            if self.task_queue:
                self.task_queue.put(("[Gesto] O usuário fez sinal da paz. Cumprimente-o brevemente.", "Sistema"))
        elif gesture == "Pinching":
            print("\n[Vision] 🤏 Pinça detectada!")
            
# Instância global
vision_tracker = None
