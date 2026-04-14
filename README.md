# Nome do grupo

Back-yardigans

## Integrantes

Gabriel Luni Nakashima RM558096 <br>
Milena Garcia Costa RM555111 <br>
Gustavo Henrique RM556712 <br>
Renan Simões Gonçalves RM555584 <br>
Vinícius Vilas Boas RM557843 <br>

# Funcionalidade

Este projeto contém um código python para cálculo dos dados e a verificação da realização do agachamento esquerdo para auxiliar o usuário a ter uma sessão detreinos
melhor, com verificação de execução e contagem de repetição. Utiliza a utilização de landmarkers espalhadas no corpo junto com a verificação de ângulos para contagem de repetições.
Tem como objetivo ajudar o usuário a verificar se o exercício está sendo realizado de forma correta e com uma postura boa, contando a quantidade de exercícios realizados com boa forma

# Componentes fisicos

Placa Arduíno/ESP 32 <br>
Leitor RFID <br>
Webcam <br>
Cartão para leitura <br>

# Diagrama

<img width="500" height="400" alt="image" src="https://github.com/user-attachments/assets/ab250b1e-3356-4790-b2a3-03b633e99b40" />

# Instruções

Conexão com Arduino: Configure o código de acordo com a porta COM do arduino utilizado <br>

Leitura de cartão: O Arduino deve enviar a UID do cartão via serial como uma String e permitir o acesso apenas com cartão com ID validado (D6 EE 4C 1F) <br>

## Bibliotecas utilizadas

Mediapipe <br>
CV2 <br>
Numpy <br>
Pyserial <br>
Time <br>
OpenCV <br>

Comando para instalar dependências: <br>

pip install opencv-python mediapipe pyserial numpy

## Execução

Caso não há permissão para utilizar a camera, rodar no CMD: net start audiosrv <br>

Arquivos de Modelo: Você precisa baixar o modelo de pose do MediaPipe e colocá-lo na pasta raiz do projeto: pose_landmarker_full.task <br>

Arduíno conectado via USB <br>

Rodar código arduino no Arduino IDE conectado na porta certa e código python <br>

## Programas e sites utilizados

Programa que rode python (Pycharm, vscode etc) <br>
Arduino IDE <br>
Wokwii <br>

## Tela inicial

Aproxime o cartão RFID autorizado (D6 EE 4C 1F), após a verificação do ID a camera é aberta caso seja o ID registrado e é disponibilizado a tela exercício <br>

## Exercício (Agachamento)

Posicione a webcam de forma que seja visível o exercício sendo realizado <br>
O gráfico mostrará a variação do ângulo conforme o exercício <br>
O sistema conta uma repetição ao atingir a flexão máxima (<40°) e a extensão (>160°) <br>
Deve-se realizar 10 repetições do exercício para finalização do programa <br>

# Vídeo demonstrativo

https://youtu.be/mEVUSG8fIRY?si=ZLOVYfnC38UfiQWg
