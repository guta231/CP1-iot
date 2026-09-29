import cv2
import mediapipe as mp
import time
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from ultralytics import YOLO  # IMPORTAÇÃO DO YOLO
import sqlite3
import tkinter as tk

# Conecta ao banco
db = sqlite3.connect('smartgym.db')
cursor = db.cursor()

# MODELO POSE (MediaPipe)
base_options_pose = python.BaseOptions(model_asset_path='pose_landmarker_full.task')
options_pose = vision.PoseLandmarkerOptions(base_options=base_options_pose, running_mode=vision.RunningMode.VIDEO)
detector_pose = vision.PoseLandmarker.create_from_options(options_pose)

# MODELO DETECÇÃO DE OBJETOS (YOLOv8)
modelo_yolo = YOLO('yolov8s.pt') 


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
    viu_garrafa_na_rep = False 

    print(f"{exercicio} Liberado! Faça {repeticoes} repetições.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or contador >= repeticoes: 
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        # INÍCIO DA DETECÇÃO YOLO (Classe 39 = bottle)
        resultados_yolo = modelo_yolo(frame, classes=[39], verbose=False)
        garrafa_detectada_agora = False

        for r in resultados_yolo:
            if len(r.boxes) > 0:
                garrafa_detectada_agora = True
                viu_garrafa_na_rep = True
                frame = r.plot() # O YOLO desenha a caixa automaticamente no frame
        # FIM DA DETECÇÃO YOLO

        # PREPARAÇÃO PARA O MEDIAPIPE (POSE)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        ts += 33
        res_pose = detector_pose.detect_for_video(mp_image, ts)
        
        # Lógica de contagem de exercício
        if res_pose.pose_landmarks:
            p = res_pose.pose_landmarks[0]
            qua, joe, tor = [p[11].x * w, p[11].y * h], [p[13].x * w, p[13].y * h], [p[15].x * w, p[15].y * h]
            ang = calcular_angulo(qua, joe, tor)

            if ang > 160: 
                if estagio == "CONTRAIDO":
                    viu_garrafa_na_rep = False 
                estagio = "EXTENDIDO"
                
            if ang < 60 and estagio == "EXTENDIDO":
                if viu_garrafa_na_rep:
                    estagio = "CONTRAIDO"
                    contador += 1
                else:
                    cv2.putText(frame, 'CADE A GARRAFA? Rep. nao contabilizada!', (50, int(h/2)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            cv2.line(frame, (int(qua[0]), int(qua[1])), (int(joe[0]), int(joe[1])), (255, 255, 255), 3)
            cv2.line(frame, (int(joe[0]), int(joe[1])), (int(tor[0]), int(tor[1])), (255, 255, 255), 3)

        cor_texto = (0, 255, 0) if garrafa_detectada_agora else (0, 0, 255)
        status_garrafa = "Garrafa: VISIVEL" if garrafa_detectada_agora else "Garrafa: AUSENTE"
        
        cv2.putText(frame, f'Aluno: {nome} | {exercicio}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f'CONTAGEM: {contador}/{repeticoes}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
        cv2.putText(frame, status_garrafa, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_texto, 2)
        cv2.putText(frame, f'Fase: {estagio}', (10, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        cv2.imshow("SmartGym", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break

    cap.release()
    cv2.destroyAllWindows()


# --- INTERFACE GRÁFICA DO USUÁRIO (TKINTER) ---
def verificar_aluno(event=None):
    uid = entry_id.get().strip().upper()
    
    if not uid:
        label_status.config(text="Por favor, digite um ID.", fg="orange")
        return

    print(f"ID Digitado: {uid}")

    cursor.execute("SELECT nome, exercicio, repeticoes FROM alunos WHERE id = ?", (uid,))
    dados = cursor.fetchone()
    
    if dados:
        nome, exercicio, repeticoes = dados
        label_status.config(text="Acesso Liberado!", fg="green")
        
        # Oculta a janela de login enquanto o exercício acontece
        root.withdraw() 
        
        iniciar_exercicio(nome, exercicio, repeticoes)
        
        print("Sessão finalizada. Aguardando novo aluno...")
        
        # Limpa o campo e mostra a janela novamente
        entry_id.delete(0, tk.END)
        label_status.config(text="")
        root.deiconify() 
    else:
        print("Aluno não encontrado.")
        label_status.config(text="Aluno não encontrado!", fg="red")


root = tk.Tk()
root.title("Smart Gym - Estacao 01")
root.geometry("400x250") 

label_boas_vindas = tk.Label(root, text="Digite o ID do Aluno:", font=("Arial", 14))
label_boas_vindas.pack(pady=15)

# Campo para digitação do ID
entry_id = tk.Entry(root, font=("Arial", 16), justify="center")
entry_id.pack(pady=10)
entry_id.focus() # Já deixa o cursor piscando no campo

# Label para exibir mensagens de erro/sucesso
label_status = tk.Label(root, text="", font=("Arial", 12))
label_status.pack(pady=5)

# Botão para validar o ID
btn_iniciar = tk.Button(root, text="Iniciar Exercício", font=("Arial", 12), command=verificar_aluno)
btn_iniciar.pack(pady=10)

# Permite que o usuário aperte "Enter" no teclado para iniciar
root.bind('<Return>', verificar_aluno)

# Mantém a janela aberta gerenciando os eventos nativamente
root.mainloop()