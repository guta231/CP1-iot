import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

def calcular_angulo(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radianos = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angulo = np.abs(radianos * 180.0 / np.pi)
    if angulo > 180.0: angulo = 360 - angulo
    return angulo

# Configuração do Modelo
base_options = python.BaseOptions(model_asset_path='pose_landmarker_full.task')
options = vision.PoseLandmarkerOptions(base_options=base_options, running_mode=vision.RunningMode.VIDEO)
detector = vision.PoseLandmarker.create_from_options(options)

contador = 0
estagio = "EXTENDIDO"
cap = cv2.VideoCapture(0)
timestamp = 0

print("Iniciando Rosca Unilateral... Use o braço DIREITO.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1) # Espelho para facilitar
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    timestamp += 33 
    result = detector.detect_for_video(mp_image, timestamp)

    if result.pose_landmarks:
        points = result.pose_landmarks[0]
        
        # Braço Direito: Ombro(12), Cotovelo(14), Pulso(16)
        ombro = [points[12].x * w, points[12].y * h]
        cotovelo = [points[14].x * w, points[14].y * h]
        pulso = [points[16].x * w, points[16].y * h]

        angulo = calcular_angulo(ombro, cotovelo, pulso)

        # Lógica de Contagem
        if angulo > 160:
            estagio = "EXTENDIDO"
        if angulo < 40 and estagio == "EXTENDIDO":
            estagio = "CONTRAIDO"
            contador += 1

        # Desenho
        cv2.line(frame, (int(ombro[0]), int(ombro[1])), (int(cotovelo[0]), int(cotovelo[1])), (255, 255, 255), 3)
        cv2.line(frame, (int(cotovelo[0]), int(cotovelo[1])), (int(pulso[0]), int(pulso[1])), (255, 255, 255), 3)
        cv2.putText(frame, str(int(angulo)), (int(cotovelo[0]), int(cotovelo[1])), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # UI
    cv2.rectangle(frame, (0,0), (220,100), (50,50,50), -1)
    cv2.putText(frame, f'REPS: {contador}', (15,40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    cv2.putText(frame, estagio, (15,80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

    cv2.imshow("Teste Rosca Unilateral", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()