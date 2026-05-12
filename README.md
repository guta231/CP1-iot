# Nome do grupo<br>
**Back-yardigans**

## Integrantes<br>
Gabriel Luni Nakashima RM558096 <br>
Milena Garcia Costa RM555111<br>
Gustavo Henrique RM556712<br>
Renan Simões Gonçalves RM555584<br>
Vinícius Vilas Boas RM557843<br>


## Funcionalidades<br>
Este projeto contém um sistema integrado para cálculo dos dados e verificação da realização do agachamento esquerdo, auxiliando o usuário a ter uma sessão de treinos melhor, com verificação de execução e contagem de repetições. As funcionalidades incluem:

### Visão Computacional<br>

Utilização de landmarks espalhados pelo corpo junto com a verificação de ângulos para contagem de repetições (MediaPipe). Ajuda o usuário a verificar se o exercício está sendo realizado de forma correta e com uma boa postura.

### Validação de ID e Registro Automático<br>
O ID do cartão RFID lido é validado diretamente em um banco de dados. O sistema realiza o registro automático do horário de acesso assim que o cartão é autorizado.

### Painel Visual Interativo<br>
Interface gráfica construída em Tkinter que gerencia o fluxo de uso da estação. Apresenta o status claro de "Aguardando Login" no momento inicial e transita para "Pronta para Uso / Treino Ativo" após a leitura do cartão, exibindo uma mensagem de boas-vindas ao aluno e um contador de exercícios na tela.

## Arquitetura do Sistema<br>
O sistema está estruturado em três camadas principais que se comunicam entre si:

### Hardware (Captura) <br>
O leitor RFID conectado à Placa Arduíno/ESP 32 lê as credenciais do usuário e envia o UID via comunicação Serial (USB) para o computador. Simultaneamente, a webcam captura o feed de vídeo.

### Backend (Processamento e Persistência)<br>
Um script em Python recebe os dados Seriais, conecta-se ao banco de dados local para checar a validade do cartão, registrar o horário e obter o perfil do aluno (nome e exercícios). Em paralelo, utiliza o framework MediaPipe e OpenCV para processamento de imagem, detecção de pose e cálculos matemáticos dos ângulos para validar as repetições.

### Frontend (Interface com Usuário)
Uma aplicação visual em Tkinter gerencia a interação direta com o usuário, atualizando os status de tela em tempo real, exibindo os dados provindos do banco de dados e mostrando as informações processadas pela visão computacional (contador e ângulos).

## Estrutura do Banco de Dado
O sistema utiliza um banco de dados relacional leve (SQLite), estruturado para uma base simples de gestão da estação. A inserção prévia de dados é feita via script de inicialização do Python, onde alunos podem ser adicionados por SQL ou manualmente.<br>

A base é composta principalmente por duas tabelas:

#### Tabela Alunos:

ID (Chave Primária, Autoincremento) <br>
Nome (Texto - Nome do aluno, para mensagem de boas-vindas) <br>
UID (Texto - Código do cartão RFID, ex: D6 EE 4C 1F) <br>
Exercicio (Texto - Tipo de exercício, ex: Agachamento Esquerdo) <br>
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
Configure o código de acordo com a porta COM do arduino utilizado  <br>
### Leitura de cartão
O Arduino deve enviar a UID do cartão via serial como uma String. O Python fará a validação buscando este ID no banco de dados SQLite e permitindo o acesso apenas a cartões previamente cadastrados (Ex: D6 EE 4C 1F).


### Bibliotecas utilizadas
Mediapipe  <br>
CV2 (OpenCV) <br>
Numpy <br>
Pyserial <br>
Time <br>
Tkinter (Nativa do Python para o Painel Visual) <br>
SQLite3 (Nativa do Python para Banco de Dados) <br>


### Comando para instalar dependências externas:


pip install opencv-python mediapipe pyserial numpy

### Execução
Caso não há permissão para utilizar a camera, rodar no CMD: **net start audiosrv** <br>
Arquivos de Modelo: Você precisa baixar o modelo de pose do MediaPipe e colocá-lo na pasta raiz do projeto: **pose_landmarker_full.task** <br>
Conecte o Arduíno via USB. <br>
Rode o código arduino no Arduino IDE conectado na porta certa. <br>
Rode o script Python de configuração inicial do banco de dados (para popular os alunos base). <br>
Inicie o código principal em Python. <br>

## Programas e sites utilizados 
Programa que rode python (Pycharm, vscode etc) <br>
Arduino IDE <br>
Wokwii <br>


## Tela inicial e Painel Visual
Ao executar o programa, o painel em Tkinter abrirá com o status: "Aguardando Login". <br>
Aproxime o cartão RFID autorizado no leitor. Após o sistema consultar o SQLite e validar o ID, o horário de acesso será gravado. <br>
A interface então mudará de status para "Pronta para Uso / Treino Ativo", exibirá uma mensagem de boas-vindas com o nome do aluno recuperado do banco e a câmera será aberta disponibilizando a contagem de exercício. <br>

### Exercício (Agachamento)
Posicione a webcam de forma que seja visível o exercício sendo realizado <br>
A interface mostrará a variação do ângulo conforme o exercício <br>
O sistema conta uma repetição ao atingir a flexão máxima (<40 graus) e a extensão (>160 graus) <br>
O contador de exercícios no painel atualizará a cada nova execução <br>
Deve-se realizar as repetições estipuladas no banco (ex: 10 repetições) do exercício para finalização do programa <br>


## Vídeo demonstrativo
https://youtube.com/shorts/orMU3uC02u0?si=p4dXUH4WKOjTsDPt