# Nome do grupo<br>
**Back-yardigans**

## Integrantes<br>
Gabriel Luni Nakashima RM558096 <br>
Milena Garcia Costa RM555111<br>
Gustavo Henrique RM556712<br>
Renan Simões Gonçalves RM555584<br>
Vinícius Vilas Boas RM557843<br>


## Funcionalidades<br>
Este projeto contém um sistema integrado de smart gym para execução e verificação do exercício **Rosca Direita**, auxiliando o aluno a ter uma sessão de treino melhor, com verificação de execução, contagem de repetições e publicação dos dados em tempo real. O sistema é executado pelo script principal `index.py`.

### Leitura de Cartão RFID e Registro Automático<br>
O ID do cartão RFID lido pela Placa Arduino/ESP32 é validado diretamente em um banco de dados SQLite. O sistema realiza o registro automático do horário de acesso assim que o cartão é autorizado.

### Visão Computacional (Contagem de Repetições)<br>
Utilização de landmarks espalhados pelo corpo junto com a verificação do **ângulo do cotovelo** (ombro → cotovelo → pulso) para a contagem de repetições (MediaPipe). Ajuda o aluno a verificar se o exercício está sendo realizado de forma correta e com uma boa postura.

### Detecção de Objetos<br>
Utilização do YOLOv8 (Ultralytics) para detectar a garrafa de água. A repetição **só é contabilizada** se a garrafa estiver visível durante o movimento, garantindo a execução completa do exercício.

### Painel Visual Interativo<br>
Interface gráfica construída em Tkinter que gerencia o fluxo de uso da estação. Apresenta o status de "Aproxime seu cartão" no momento inicial e transita para "Treino Ativo" após a leitura do cartão, exibindo uma mensagem de boas-vindas ao aluno e um contador de exercícios na tela.

### Publicação dos Dados via MQTT<br>
A cada repetição contabilizada, o sistema publica um JSON no servidor MQTT, permitindo montar dashboards em tempo real (Google Colab, Node-RED, Grafana, etc.).

## Arquitetura do Sistema<br>
O sistema está estruturado em três camadas principais que se comunicam entre si:

### Hardware (Captura) <br>
O leitor RFID conectado à Placa Arduíno/ESP 32 lê as credenciais do usuário e envia o UID via comunicação Serial (USB) para o computador. Simultaneamente, a webcam captura o feed de vídeo.

### Backend (Processamento e Persistência)<br>
O `index.py` recebe os dados Seriais, conecta-se ao banco de dados local para checar a validade do cartão, registrar o horário e obter o perfil do aluno (nome, exercício e meta de repetições). Em paralelo, utiliza o framework MediaPipe e OpenCV para processamento de imagem, detecção de pose e cálculos matemáticos dos ângulos para validar as repetições, e o YOLOv8 para a detecção da garrafa. Cada repetição validada é publicada no broker MQTT.

### Frontend (Interface com Usuário)
Uma aplicação visual em Tkinter gerencia a interação direta com o usuário, atualizando os status de tela em tempo real, exibindo os dados provindos do banco de dados e mostrando as informações processadas pela visão computacional (contador, ângulo e status da garrafa).

## Estrutura do Banco de Dado
O sistema utiliza um banco de dados relacional leve (SQLite), estruturado para uma base simples de gestão da estação. A inserção prévia de dados é feita via script de inicialização do Python (`insert_sqlite.py`), onde alunos podem ser adicionados por SQL ou manualmente.<br>

A base é composta principalmente por duas tabelas:

#### Tabela Alunos:
ID (Texto - UID do cartão RFID, ex: A95D9B99) <br>
Nome (Texto - Nome do aluno, para mensagem de boas-vindas) <br>
Exercicio (Texto - Tipo de exercício, Rosca Direita) <br>
Repeticoes (Inteiro - Meta de repetições do exercício) <br>

#### Tabela Acessos (Log de uso):
ID_Acesso (Chave Primária, Autoincremento)<br>
UID_Aluno (Texto - Chave Estrangeira ligada ao Aluno)<br>
Horario_Acesso (Timestamp - Data e hora automática do momento de validação do ID)<br>

#### Componentes fisicos
Placa Arduíno/ESP 32 <br>
Leitor RFID <br>
Webcam <br>
Cartão para leitura <br>


## Diagrama

<img width="742" height="387" alt="Diagrama" src="https://github.com/user-attachments/assets/7aef88a8-346c-4192-b200-32b678b0debe" /> <br>


## Instruções
### Conexão com Arduino
Configure o código de acordo com a porta COM do arduino utilizado (constante `PORTA_COM` no topo do `index.py`) <br>
### Leitura de cartão
O Arduino deve enviar a UID do cartão via serial como uma String. O Python fará a validação buscando este ID no banco de dados SQLite e permitindo o acesso apenas a cartões previamente cadastrados (Ex: A95D9B99). <br>
Como alternativa ao cartão, o painel aceita a digitação manual do ID (fallback para quando o leitor RFID estiver indisponível). <br>


### Publicação MQTT (dados do exercício)

Cada repetição contabilizada é publicada em um servidor MQTT, permitindo montar dashboards em tempo real (Google Colab, Node-RED, Grafana, etc.).

**Configuração (bloco no topo do `index.py`):**

```python
MQTT_HOST = '3.135.234.101'
MQTT_PORT = 1883
MQTT_USER = ''          # Vazio = broker sem autenticação
MQTT_PASSWORD = ''
MQTT_TOPIC_BASE = 'smartgym/aluno'
```

**Tópico:**

```
smartgym/aluno/<UID>/exercicio
```

Exemplo: `smartgym/aluno/A95D9B99/exercicio`

**Payload (JSON):**

```json
{
  "evento": "repeticao",
  "aluno": "Naka",
  "uid": "A95D9B99",
  "exercicio": "Rosca Direita",
  "repeticoes_meta": 10,
  "repeticoes_feitas": 3,
  "fase": "CONTRAIDO",
  "angulo_cotovelo": 45.3,
  "garrafa_visivel": true,
  "timestamp": "2026-10-19T14:23:11.456"
}
```

**Recebendo no Google Colab (exemplo):**

```python
!pip install paho-mqtt

import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    print(msg.topic, json.loads(msg.payload.decode()))

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.connect("3.135.234.101", 1883)
client.subscribe("smartgym/aluno/#")   # todos os alunos
client.loop_forever()
```

> Se o broker estiver fora do ar, o sistema **não trava**: o treino continua funcionando e os dados são enviados assim que a conexão voltar.

### Bibliotecas utilizadas

Mediapipe  <br>
CV2 (OpenCV) <br>
Numpy <br>
Pyserial <br>
Paho-mqtt (publicação no servidor MQTT) <br>
Ultralytics (YOLOv8 - detecção de objetos) <br>
Time <br>
Tkinter (Nativa do Python para o Painel Visual) <br>
SQLite3 (Nativa do Python para Banco de Dados) <br>


### Comando para instalar dependências externas:

```
pip install -r requirements.txt
```

ou, manualmente:

```
pip install opencv-python mediapipe pyserial numpy ultralytics paho-mqtt
```

### Execução
Caso não há permissão para utilizar a camera, rodar no CMD: **net start audiosrv** <br>
Arquivos de Modelo: Você precisa baixar o modelo de pose do MediaPipe e colocá-lo na pasta raiz do projeto: **pose_landmarker_full.task** <br>
Conecte o Arduíno via USB. <br>
Rode o código arduino no Arduino IDE conectado na porta certa. <br>
Rode o script Python de configuração inicial do banco de dados (`insert_sqlite.py`, para popular os alunos base). <br>
Inicie o código principal com **python index.py**. <br>

## Programas e sites utilizados 
Programa que rode python (Pycharm, vscode etc) <br>
Arduino IDE <br>
Wokwii <br>


## Tela inicial e Painel Visual
Ao executar o programa, o painel em Tkinter abrirá com a mensagem: "Aproxime seu cartão ...", mostrando também o estado da conexão MQTT. <br>
Aproxime o cartão RFID autorizado no leitor (ou digite o ID no campo do painel). Após o sistema consultar o SQLite e validar o ID, o horário de acesso será gravado na tabela `acessos`. <br>
A interface então muda o status para "Acesso liberado!", exibe a mensagem de boas-vindas com o nome do aluno recuperado do banco e a câmera é aberta, disponibilizando a contagem do exercício. <br>
Ao término do treino, o painel volta ao estado de espera para o próximo aluno. <br>

### Exercício (Rosca Direita)
Posicione a webcam de forma que seja visível o exercício sendo realizado <br>
A interface mostrará a variação do ângulo do cotovelo, o status da garrafa e a fase atual do movimento <br>
O sistema conta uma repetição ao atingir a flexão máxima (< 60 graus) e a extensão (> 160 graus) do cotovelo <br>
A repetição **só é contabilizada** se a garrafa estiver visível durante o movimento; caso contrário, o painel exibe "CADE A GARRAFA? Rep. nao contabilizada!" <br>
O contador de exercícios no painel atualizará a cada nova execução <br>
Deve-se realizar as repetições estipuladas no banco (ex: 10 repetições) do exercício para finalização do programa (ou apertar **q** na janela da câmera para encerrar) <br>


## Vídeo demonstrativo
https://youtube.com/shorts/orMU3uC02u0?si=p4dXUH4WKOjTsDPt
