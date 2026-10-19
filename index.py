
import cv2
import mediapipe as mp
import serial
import time
import json
import sqlite3
import tkinter as tk
from datetime import datetime

import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from ultralytics import YOLO
import paho.mqtt.client as mqtt


PORTA_COM = 'COM5'
BAUD_RATE = 9600
TIMEOUT_SERIAL = 1
INTERVALO_LEITURA_SERIAL_MS = 150   
INTERVALO_RECONEXAO_SERIAL = 10     


MQTT_HOST = '3.135.234.101'
MQTT_PORT = 1883
MQTT_USER = ''
MQTT_PASSWORD = ''
MQTT_KEEPALIVE = 60
MQTT_TIMEOUT_CONEXAO = 5      
MQTT_TOPIC_BASE = 'smartgym/aluno'
MQTT_QOS = 1


CLASSE_GARRAFA = 39      
CONF_MINIMA = 0.25


ANGULO_EXTENDIDO = 160  
ANGULO_CONTRAIDO = 60    




db = sqlite3.connect('smartgym.db')
cursor = db.cursor()




base_options_pose = python.BaseOptions(model_asset_path='pose_landmarker_full.task')
options_pose = vision.PoseLandmarkerOptions(
    base_options=base_options_pose,
    running_mode=vision.RunningMode.VIDEO
)
detector_pose = vision.PoseLandmarker.create_from_options(options_pose)


modelo_yolo = YOLO('yolov8s.pt')




class ClienteMQTT:
    """Envelopa o paho-mqtt para publicar os dados do exercicio."""

    def __init__(self):
        client_id = f"smartgym-estacao01-{int(time.time())}"
        try:
            self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        except AttributeError:  
            self.cliente = mqtt.Client(client_id=client_id)

        if MQTT_USER:
            self.cliente.username_pw_set(MQTT_USER, MQTT_PASSWORD)

        self.cliente.on_connect = self._on_connect
        self.cliente.on_disconnect = self._on_disconnect
        self.conectado = False


    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self.conectado = True
            print(f"[MQTT] Conectado em {MQTT_HOST}:{MQTT_PORT}")
        else:
            self.conectado = False
            print(f"[MQTT] Falha na conexao: {reason_code}")

    def _on_disconnect(self, client, userdata, *args):
        self.conectado = False
        print("[MQTT] Desconectado do broker.")

    def conectar(self):
        """Conecta em background. Nao levanta excecao se o broker estiver fora do ar."""
        try:
            self.cliente.connect_async(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
            self.cliente.loop_start()

            limite = time.time() + MQTT_TIMEOUT_CONEXAO
            while time.time() < limite and not self.conectado:
                time.sleep(0.1)

            if self.conectado:
                return True

            print(f"[MQTT] Broker {MQTT_HOST}:{MQTT_PORT} ainda nao respondeu. "
                  "O treino continua funcionando e os dados serao enviados assim que a conexao subir.")
            return False
        except Exception as e:
            print(f"[MQTT] Erro ao conectar: {e}")
            return False

    def publicar(self, topico, payload):
        """Publica um payload (dict -> JSON). Retorna True se foi enfileirado."""
        try:
            info = self.cliente.publish(
                topico,
                json.dumps(payload, ensure_ascii=False),
                qos=MQTT_QOS
            )
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT] Falha ao publicar em '{topico}' (rc={info.rc}).")
                return False
            return True
        except Exception as e:
            print(f"[MQTT] Erro ao publicar: {e}")
            return False

    def desconectar(self):
        try:
            self.cliente.loop_stop()
            self.cliente.disconnect()
        except Exception:
            pass


mqtt_cliente = ClienteMQTT()
mqtt_cliente.conectar()




arduino = None
buffer_serial = ''
ultima_tentativa_serial = 0.0


def tentar_conectar_serial(forcar=False):
    """Abre a porta serial. Retorna True se a porta esta disponivel."""
    global arduino, ultima_tentativa_serial

    if arduino is not None and arduino.is_open:
        return True

    agora = time.time()
    if not forcar and (agora - ultima_tentativa_serial) < INTERVALO_RECONEXAO_SERIAL:
        return False
    ultima_tentativa_serial = agora

    try:
        arduino = serial.Serial(PORTA_COM, BAUD_RATE, timeout=TIMEOUT_SERIAL)
        time.sleep(2)  
        print(f"[RFID] Conectado na porta {PORTA_COM}.")
        return True
    except Exception as e:
        print(f"[RFID] Nao foi possivel abrir {PORTA_COM}: {e}")
        arduino = None
        return False




def calcular_angulo(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radianos = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angulo = np.abs(radianos * 180.0 / np.pi)
    if angulo > 180.0:
        angulo = 360 - angulo
    return angulo


def publicar_repeticao(nome, uid, exercicio, repeticoes, contador, estagio, angulo, garrafa_visivel):
    """Publica os dados da repeticao no topico do aluno."""
    topico = f"{MQTT_TOPIC_BASE}/{uid}/exercicio"
    payload = {
        "evento": "repeticao",
        "aluno": nome,
        "uid": uid,
        "exercicio": exercicio,
        "repeticoes_meta": repeticoes,
        "repeticoes_feitas": contador,
        "fase": estagio,
        "angulo_cotovelo": round(float(angulo), 2),
        "garrafa_visivel": bool(garrafa_visivel),
        "timestamp": datetime.now().isoformat(timespec='milliseconds')
    }
    mqtt_cliente.publicar(topico, payload)
    print(f"[MQTT] {topico} -> {contador}/{repeticoes}")


def iniciar_exercicio(nome, exercicio, repeticoes, uid):
    cap = cv2.VideoCapture(0)
    contador = 0
    estagio = "EXTENDIDO"
    ts = 0
    viu_garrafa_na_rep = False
    angulo_atual = 0.0
    garrafa_visivel = False

    print(f"{exercicio} Liberado! Faca {repeticoes} repeticoes.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or contador >= repeticoes:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

  
        resultados_yolo = modelo_yolo(frame, classes=[CLASSE_GARRAFA], verbose=False, conf=CONF_MINIMA)
        garrafa_detectada_agora = False

        for r in resultados_yolo:
            if len(r.boxes) > 0:
                garrafa_detectada_agora = True
                viu_garrafa_na_rep = True
                frame = r.plot()  

        garrafa_visivel = garrafa_detectada_agora

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        ts += 33
        res_pose = detector_pose.detect_for_video(mp_image, ts)


        if res_pose.pose_landmarks:
            p = res_pose.pose_landmarks[0]
            qua, joe, tor = ([p[11].x * w, p[11].y * h],
                              [p[13].x * w, p[13].y * h],
                              [p[15].x * w, p[15].y * h])
            angulo_atual = calcular_angulo(qua, joe, tor)

            if angulo_atual > ANGULO_EXTENDIDO:
                if estagio == "CONTRAIDO":
                    viu_garrafa_na_rep = False
                estagio = "EXTENDIDO"

            if angulo_atual < ANGULO_CONTRAIDO and estagio == "EXTENDIDO":
                if viu_garrafa_na_rep:
                    estagio = "CONTRAIDO"
                    contador += 1
               
                    publicar_repeticao(nome, uid, exercicio, repeticoes,
                                       contador, estagio, angulo_atual, garrafa_visivel)
                else:
                    cv2.putText(frame, 'CADE A GARRAFA? Rep. nao contabilizada!', (50, int(h / 2)),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            cv2.line(frame, (int(qua[0]), int(qua[1])), (int(joe[0]), int(joe[1])), (255, 255, 255), 3)
            cv2.line(frame, (int(joe[0]), int(joe[1])), (int(tor[0]), int(tor[1])), (255, 255, 255), 3)

        cor_texto = (0, 255, 0) if garrafa_visivel else (0, 0, 255)
        status_garrafa = "Garrafa: VISIVEL" if garrafa_visivel else "Garrafa: AUSENTE"

        cv2.putText(frame, f'Aluno: {nome} | {exercicio}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f'CONTAGEM: {contador}/{repeticoes}', (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
        cv2.putText(frame, status_garrafa, (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_texto, 2)
        cv2.putText(frame, f'Fase: {estagio}', (10, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.putText(frame, f'Angulo: {angulo_atual:.1f} deg', (10, h - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("SmartGym", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()




root = tk.Tk()
root.title("Smart Gym - Estacao 01")
root.geometry("400x320")

label_boas_vindas = tk.Label(root, text="Aproxime seu cartao ...", font=("Arial", 16))
label_boas_vindas.pack(pady=15)

label_status = tk.Label(root, text="", font=("Arial", 11))
label_status.pack(pady=5)

label_mqtt = tk.Label(root, text="", font=("Arial", 9), fg="gray")
label_mqtt.pack(pady=2)

tk.Label(root, text="Ou digite o ID do aluno:", font=("Arial", 11)).pack(pady=(12, 2))

entry_id = tk.Entry(root, font=("Arial", 16), justify="center", width=18)
entry_id.pack(pady=6)

btn_iniciar = tk.Button(root, text="Iniciar Exercicio", font=("Arial", 12), command=lambda: verificar_aluno())
btn_iniciar.pack(pady=8)

root.bind('<Return>', lambda e: verificar_aluno())


def atualizar_status_mqtt():
    if mqtt_cliente.conectado:
        label_mqtt.config(text=f"MQTT: conectado ({MQTT_HOST}:{MQTT_PORT})", fg="green")
    else:
        label_mqtt.config(text=f"MQTT: offline ({MQTT_HOST}:{MQTT_PORT})", fg="orange")
    root.after(1000, atualizar_status_mqtt)


def abrir_sessao(uid, nome, exercicio, repeticoes):
    """Registra o acesso e executa o treino do aluno."""
    try:
        cursor.execute("INSERT INTO acessos (uid_aluno) VALUES (?)", (uid,))
        db.commit()
    except Exception as e:
        print(f"[DB] Falha ao registrar acesso: {e}")

    label_status.config(text=f"Treino ativo - {nome}", fg="green")
    root.withdraw()

    try:
        iniciar_exercicio(nome, exercicio, repeticoes, uid)
    finally:
        root.deiconify()
        entry_id.delete(0, tk.END)
        label_status.config(text="Sessao finalizada. Aguardando novo aluno...", fg="green")
        root.update()


def processar_uid(uid):
    """Valida o UID no banco e inicia a sessao de treino."""
    uid = (uid or '').strip().upper()
    if not uid:
        return

    cursor.execute("SELECT nome, exercicio, repeticoes FROM alunos WHERE id = ?", (uid,))
    dados = cursor.fetchone()

    if not dados:
        print(f"[RFID] Cartao nao cadastrado: {uid}")
        label_status.config(text=f"Cartao nao autorizado: {uid}", fg="red")
        return

    nome, exercicio, repeticoes = dados
    print(f"[RFID] Acesso liberado: {nome} ({uid}) - {exercicio}")
    label_status.config(text=f"Acesso liberado! Bem-vindo, {nome}.", fg="green")
    root.update()

    abrir_sessao(uid, nome, exercicio, repeticoes)


def verificar_aluno(event=None):
    """Fallback: login manual pelo ID digitado."""
    uid = entry_id.get().strip().upper()
    if not uid:
        label_status.config(text="Digite um ID ou aproxime o cartao.", fg="orange")
        return
    processar_uid(uid)


def verificar_arduino():
    """Polling da porta serial: le o UID enviado pelo Arduino."""
    global buffer_serial

    try:
        if arduino is None or not arduino.is_open:
            tentar_conectar_serial()
        elif arduino.in_waiting > 0:
            bruto = arduino.read(arduino.in_waiting).decode('utf-8', errors='ignore')
            buffer_serial += bruto
            while '\n' in buffer_serial:
                linha, buffer_serial = buffer_serial.split('\n', 1)
                linha = linha.strip().upper()
                if linha:
                    processar_uid(linha)
    except Exception as e:
        print(f"[RFID] Erro na leitura serial: {e}")

    root.after(INTERVALO_LEITURA_SERIAL_MS, verificar_arduino)




if __name__ == '__main__':
    print("=" * 60)
    print(" SmartGym - Estacao 01")
    print(f" MQTT: {MQTT_HOST}:{MQTT_PORT} | Topico: {MQTT_TOPIC_BASE}/<UID>/exercicio")
    print("=" * 60)

    tentar_conectar_serial(forcar=True)

    root.after(INTERVALO_LEITURA_SERIAL_MS, verificar_arduino)
    root.after(500, atualizar_status_mqtt)

    try:
        root.mainloop()
    finally:
        if arduino is not None:
            try:
                arduino.close()
            except Exception:
                pass
        mqtt_cliente.desconectar()
        db.close()
