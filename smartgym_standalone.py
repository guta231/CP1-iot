import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import sqlite3
import tkinter as tk
from ultralytics import YOLO
import threading

# ── Database ──────────────────────────────────────────────
db = sqlite3.connect('smartgym.db')
cursor = db.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS acessos (
    id_acesso INTEGER PRIMARY KEY AUTOINCREMENT,
    uid_aluno TEXT,
    horario_acesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
db.commit()

# ── YOLO Equipment Detection ──────────────────────────────
yolo_model = YOLO('yolov8s.pt')
EQUIPMENT_CLASS = 'bottle'
CONFIDENCE_THRESHOLD = 0.25

# ── MediaPipe Pose ───────────────────────────────────────
base_options = python.BaseOptions(model_asset_path='pose_landmarker_full.task')
options = vision.PoseLandmarkerOptions(base_options=base_options, running_mode=vision.RunningMode.VIDEO)
detector = vision.PoseLandmarker.create_from_options(options)

# ── Shared State (thread-safe enough for simple values) ──
exercise_state = {
    'contador': 0,
    'repeticoes': 0,
    'equipment_detected': False,
    'estagio': 'EXTENDIDO',
    'nome': '',
    'exercicio': '',
    'active': False,
}


def calcular_angulo(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radianos = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angulo = np.abs(radianos * 180.0 / np.pi)
    if angulo > 180.0:
        angulo = 360 - angulo
    return angulo


def detect_equipment(frame):
    """Returns (detected: bool, box) — True if bottle found."""
    results = yolo_model(frame, verbose=False, conf=CONFIDENCE_THRESHOLD, augment=True)
    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            if yolo_model.names[cls] == EQUIPMENT_CLASS:
                return True, box
    return False, None


def exercise_thread():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        exercise_state['active'] = False
        return

    contador = 0
    estagio = "EXTENDIDO"
    ts = 0
    repeticoes = exercise_state['repeticoes']

    # ── Movement detection improvements ──
    ANGLE_BUFFER_SIZE = 5          # Moving average window for angle smoothing
    EXTEND_THRESHOLD = 150         # Must exceed this to count as "extended"
    CONTRACT_THRESHOLD = 50        # Must drop below this to count as "contracted"
    REP_COOLDOWN_FRAMES = 15       # Minimum frames between reps (~0.5s at 30fps)
    EQUIPMENT_MEMORY_FRAMES = 30   # Keep "equipment detected" alive for ~1s after last sighting
    angle_buffer = []
    cooldown = 0
    equipment_memory = 0

    while cap.isOpened() and exercise_state['active']:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        # ── YOLO: detect equipment ──
        equipment_detected, eq_box = detect_equipment(frame)
        if equipment_detected:
            equipment_memory = EQUIPMENT_MEMORY_FRAMES
        elif equipment_memory > 0:
            equipment_memory -= 1
        equipment_visible = equipment_memory > 0
        exercise_state['equipment_detected'] = equipment_visible

        # ── MediaPipe: pose detection ──
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        ts += 33
        res = detector.detect_for_video(mp_image, ts)

        if res.pose_landmarks:
            p = res.pose_landmarks[0]
            ombro = [p[12].x * w, p[12].y * h]
            cotovelo = [p[14].x * w, p[14].y * h]
            pulso = [p[16].x * w, p[16].y * h]
            ang = calcular_angulo(ombro, cotovelo, pulso)

            # ── Angle smoothing: moving average to reduce jitter ──
            angle_buffer.append(ang)
            if len(angle_buffer) > ANGLE_BUFFER_SIZE:
                angle_buffer.pop(0)
            ang_smooth = sum(angle_buffer) / len(angle_buffer)

            # ── Cooldown counter ──
            if cooldown > 0:
                cooldown -= 1

            # ── State machine with hysteresis ──
            # EXTENDIDO → CONTRAIDO: angle drops below CONTRACT_THRESHOLD
            # CONTRAIDO → EXTENDIDO: angle rises above EXTEND_THRESHOLD (rep counted)
            if estagio == "EXTENDIDO" and ang_smooth < CONTRACT_THRESHOLD:
                estagio = "CONTRAIDO"
            elif estagio == "CONTRAIDO" and ang_smooth > EXTEND_THRESHOLD:
                if equipment_visible and cooldown == 0:
                    contador += 1
                    exercise_state['contador'] = contador
                    cooldown = REP_COOLDOWN_FRAMES
                estagio = "EXTENDIDO"

            exercise_state['estagio'] = estagio

            # Draw skeleton
            cv2.line(frame, (int(ombro[0]), int(ombro[1])), (int(cotovelo[0]), int(cotovelo[1])), (255, 255, 255), 3)
            cv2.line(frame, (int(cotovelo[0]), int(cotovelo[1])), (int(pulso[0]), int(pulso[1])), (255, 255, 255), 3)

        # ── Draw equipment bounding box ──
        if equipment_detected and eq_box is not None:
            x1, y1, x2, y2 = eq_box.xyxy[0].cpu().numpy()
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 2)
            cv2.putText(frame, "Equipment", (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # ── On-screen status ──
        status_text = "Equipment Detected" if equipment_visible else "Waiting for Equipment"
        status_color = (0, 255, 0) if equipment_visible else (0, 0, 255)
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        cv2.putText(frame, f"Reps: {contador}/{repeticoes}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Stage: {estagio}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        if angle_buffer:
            cv2.putText(frame, f"Angle: {ang_smooth:.1f} deg", (10, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, "Press 'q' to finish", (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow(f"{exercise_state['exercicio']} - SmartGym", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        if contador >= repeticoes:
            break

    cap.release()
    cv2.destroyAllWindows()
    exercise_state['active'] = False


# ── GUI ──────────────────────────────────────────────────
class SmartGymApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SmartGym - Standalone")
        self.root.geometry("400x300")

        self.login_frame = tk.Frame(root)
        self.exercise_frame = tk.Frame(root)

        self._setup_login()
        self._setup_exercise()
        self._show_login()

    def _setup_login(self):
        tk.Label(self.login_frame, text="SmartGym - Standalone", font=("Arial", 18, "bold")).pack(pady=20)
        tk.Label(self.login_frame, text="Enter your UID:", font=("Arial", 12)).pack(pady=5)

        self.uid_entry = tk.Entry(self.login_frame, font=("Arial", 14), width=20)
        self.uid_entry.pack(pady=5)
        self.uid_entry.bind('<Return>', lambda e: self._try_login())

        tk.Button(self.login_frame, text="Login", font=("Arial", 12), command=self._try_login).pack(pady=10)

        self.login_status = tk.Label(self.login_frame, text="", font=("Arial", 10))
        self.login_status.pack(pady=5)

    def _setup_exercise(self):
        tk.Label(self.exercise_frame, text="Exercise Active", font=("Arial", 18, "bold")).pack(pady=10)

        self.name_label = tk.Label(self.exercise_frame, text="", font=("Arial", 14))
        self.name_label.pack(pady=5)

        self.status_label = tk.Label(self.exercise_frame, text="Waiting for Equipment", font=("Arial", 14, "bold"))
        self.status_label.pack(pady=5)

        self.counter_label = tk.Label(self.exercise_frame, text="Reps: 0/0", font=("Arial", 16))
        self.counter_label.pack(pady=5)

        self.stage_label = tk.Label(self.exercise_frame, text="Stage: EXTENDIDO", font=("Arial", 12))
        self.stage_label.pack(pady=5)

        tk.Label(self.exercise_frame, text="Press 'q' on camera to finish", font=("Arial", 9), fg="gray").pack(pady=10)

    def _show_login(self):
        self.exercise_frame.pack_forget()
        self.login_frame.pack(fill="both", expand=True)

    def _show_exercise(self):
        self.login_frame.pack_forget()
        self.exercise_frame.pack(fill="both", expand=True)

    def _try_login(self):
        uid = self.uid_entry.get().strip().upper()
        if not uid:
            self.login_status.config(text="Please enter a UID", fg="red")
            return

        cursor.execute("SELECT nome, exercicio, repeticoes FROM alunos WHERE id = ?", (uid,))
        dados = cursor.fetchone()

        if dados is None:
            self.login_status.config(text="Invalid UID", fg="red")
            return

        nome, exercicio, repeticoes = dados

        # Record access
        try:
            cursor.execute("INSERT INTO acessos (uid_aluno) VALUES (?)", (uid,))
            db.commit()
        except Exception as e:
            print(f"Warning: Could not record access: {e}")

        # Set exercise state
        exercise_state['nome'] = nome
        exercise_state['exercicio'] = exercicio
        exercise_state['repeticoes'] = repeticoes
        exercise_state['contador'] = 0
        exercise_state['equipment_detected'] = False
        exercise_state['estagio'] = 'EXTENDIDO'
        exercise_state['active'] = True

        # Update GUI
        self.name_label.config(text=f"Welcome, {nome}!")
        self.counter_label.config(text=f"Reps: 0/{repeticoes}")
        self.status_label.config(text="Waiting for Equipment", fg="red")
        self.stage_label.config(text="Stage: EXTENDIDO")
        self._show_exercise()

        # Start exercise thread
        thread = threading.Thread(target=exercise_thread, daemon=True)
        thread.start()

        # Start polling
        self._poll_exercise()

    def _poll_exercise(self):
        if not exercise_state['active']:
            self._show_login()
            return

        # Update status
        if exercise_state['equipment_detected']:
            self.status_label.config(text="Equipment Detected", fg="green")
        else:
            self.status_label.config(text="Waiting for Equipment", fg="red")

        # Update counter
        self.counter_label.config(text=f"Reps: {exercise_state['contador']}/{exercise_state['repeticoes']}")

        # Update stage
        self.stage_label.config(text=f"Stage: {exercise_state['estagio']}")

        self.root.after(100, self._poll_exercise)


# ── Main ──────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = SmartGymApp(root)
    root.mainloop()
