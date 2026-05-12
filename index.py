import cv2
import mediapipe as mp
import serial
import time
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import sqlite3
import tkinter as tk

# CONFIGURAÇÃO SERIAL5
PORTA_COM = 'COM5'

# 1. Conecta ao banco (arquivo local)
db = sqlite3.connect('smartgym.db')
cursor = db.cursor()

try:
    arduino = serial.Serial(PORTA_COM, 9600, timeout=1)
    time.sleep(2)
except:
    print("Erro na Serial.");
    exit()

# MODELO POSE
base_options = python.BaseOptions(model_asset_path='pose_landmarker_full.task')
options = vision.PoseLandmarkerOptions(base_options=base_options, running_mode=vision.RunningMode.VIDEO)
detector = vision.PoseLandmarker.create_from_options(options)


def calcular_angulo(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radianos = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angulo = np.abs(radianos * 180.0 / np.pi)
    if angulo > 180.0: angulo = 360 - angulo
    return angulo


def iniciar_exercicio(nome, exercicio, repeticoes):
    cap = cv2.VideoCapture(0)
    contador = 0
    estagio = "EXTENDIDO"
    ts = 0

    print(F"{exercicio} Liberado! Faça {repeticoes} repetições.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or contador >= 10: break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        ts += 33
        res = detector.detect_for_video(mp_image, ts)

        if res.pose_landmarks:
            p = res.pose_landmarks[0]
            # Perna esquerda
            qua, joe, tor = [p[28].x * w, p[28].y * h], [p[26].x * w, p[26].y * h], [p[24].x * w, p[24].y * h]
            ang = calcular_angulo(qua, joe, tor)

            if ang > 160: estagio = "EXTENDIDO"
            if ang < 40 and estagio == "EXTENDIDO":
                estagio = "CONTRAIDO"
                contador += 1

            cv2.line(frame, (int(qua[0]), int(qua[1])), (int(joe[0]), int(joe[1])), (255, 255, 255), 3)
            cv2.line(frame, (int(joe[0]), int(joe[1])), (int(tor[0]), int(tor[1])), (255, 255, 255), 3)

        cv2.putText(frame, f'Boa tarde, {nome}!', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f'Boa tarde, {nome}! CONTAGEM: {contador}/{repeticoes}', (10, 50), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 255, 0), 2)
        cv2.imshow(f"{exercicio} - SmartGym", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()


while True:
    root = tk.Tk()
    root.title("Smart Gym - Estacao 01")
    root.geometry("400x200") 

    label_boas_vindas = tk.Label(root, text="Aproxime seu cartao ... ", font=("Arial", 16))

    label_boas_vindas.pack(pady=20)

    root.mainloop()

    if arduino.in_waiting > 0:
        root.qqqqqqqqqqqqquit()
        uid = arduino.readline().decode('utf-8').strip().upper()

        cursor.execute("SELECT nome, exercicio, repeticoes FROM alunos WHERE id = ?", (uid,))
        dados = cursor.fetchone()
        nome = dados[0]
        exercicio = dados[1]
        repeticoes = dados[2]

        iniciar_exercicio(nome, exercicio, repeticoes)
        print("Sessão finalizada. Aguardando novo aluno...")
    time.sleep(0.1)