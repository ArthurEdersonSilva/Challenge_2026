<div align="center">

[![Visão Computacional](https://img.shields.io/badge/VIS%C3%83O%20COMPUTACIONAL-%23150458.svg?style=for-the-badge&logo=opencv&logoColor=white)](https://github.com/ArthurEdersonSilva?tab=repositories)
[![Inteligência Artificial](https://img.shields.io/badge/Inteligência%20Artificial-purple?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://github.com/ArthurEdersonSilva?tab=repositories)

# 🏭 FIAP x SPI Challenge 2026 - Proteção Ativa

</div>

Este repositório contém a solução desenvolvida para o **Challenge FIAP x SPI 2026**, focada na criação de uma **Pipeline Unificada de Proteção Ativa** com monitoramento inteligente de segurança industrial. O sistema integra modelos de Inteligência Artificial de última geração para realizar a detecção em tempo real de não conformidades no uso de EPIs (**Fase 1**), análise ergonômica de postura corporativa (**Fase 2**), e processamento de dados através de um motor de decisão baseado em contexto por níveis de severidade com múltiplos canais de alerta (**Fase 3**).

---

<div align="center">

**Tecnologias Utilizadas:**

![Python](https://img.shields.io/badge/python-%233776AB.svg?style=for-the-badge&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=for-the-badge&logo=pytorch&logoColor=white)
![Ultralytics](https://img.shields.io/badge/YOLOv8-%23006400.svg?style=for-the-badge&logo=ultralytics&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-%235C3EE8.svg?style=for-the-badge&logo=opencv&logoColor=white)
![Git](https://img.shields.io/badge/git-%23F05033.svg?style=for-the-badge&logo=git&logoColor=white)

</div>

* **Python 3.10+:** Linguagem principal para estruturação do loop de processamento de vídeo, lógicas do motor analítico de regras e barramento de notificações.
* **YOLOv8 Object Detection (Ultralytics):** Modelo computacional customizado e treinado especificamente para detectar a ausência de EPIs em ambiente de chão de fábrica. Suporta aceleração por hardware nativa via CUDA (Windows) e MPS (Mac).
* **YOLOv8-Pose (Pose Estimation):** Arquitetura voltada para a extração nativa de *keypoints* (articulações) do corpo do operador, garantindo alta performance (FPS elevado) e eliminando dependências externas de pacotes C++.
* **OpenCV:** Biblioteca utilizada para manipulação matemática de frames de vídeo, cálculo geométrico espacial de polígonos e renderização de elementos gráficos na interface de segurança.
* **Git & GitHub:** Versionamento de código e governança do repositório.

---

## 🧠 Detalhes do Treinamento (Fase 1)

O modelo customizado (`best.pt`) focado em segurança industrial foi treinado com as seguintes especificações técnicas:
* **Dataset Origem:** PPE-Dataset via Roboflow.
* **Volume de Treino:** 25 épocas completas utilizando a arquitetura YOLOv8 (Versões Nano e Small).
* **Resolução de Entrada:** Imagens de 640px, otimizando o balanço entre velocidade de inferência (FPS) e precisão média global ($mAP$).
* **Abordagem Híbrida:** Identificação simultânea de classes padrão de segurança (*person*) e de classes customizadas de infração de EPI em inglês (*Without Helmet, Without Glass, Without Mask, Without Glove, Without Ear Protectors*), mapeadas via software para saídas amigáveis em português.

---

## 📐 Arquitetura e Fluxo de Dados

O ecossistema opera de forma síncrona através de uma arquitetura modular dividida em três frentes analíticas:

1. **Mapeamento de Riscos e Fator Humano (Fase 1):** A pipeline captura o fluxo da webcam e realiza inferências para extrair caixas delimitadoras (*bounding boxes*) de operadores e ausências de equipamentos.
2. **Análise de Fadiga Ergonômica Dinâmica (Fase 2 & NR-17):** O modelo YOLO-Pose rastreia as coordenadas bidimensionais de articulações críticas. O sistema calcula o alinhamento anatômico vertical entre o complexo ombro-quadril, identificando a persistência temporal (90 frames consecutivos) de posturas inclinadas/fletidas que caracterizam risco ergonômico.
3. **Engine de Severidade Contextual e Alerta de Dois Canais (Fase 3):** O motor de decisão (`decision_engine.py`) consolida as violações e classifica o risco operacional em três níveis de criticidade:
   * 🔴 **CRÍTICA:** Operador dentro do polígono geométrico de perigo direto (`config.PONTOS_ZONA_RISCO`) desprotegido de capacete. Dispara um **alerta visual em tela** e um **estímulo sonoro físico (Buzzer/Bipe via `winsound`)** para o trabalhador em campo.
   * 🟠 **ALTA:** Operador posicionado na área de risco em desconformidade de EPIs leves ou com indicação crônica de fadiga postural na coluna.
   * 🟡 **INFORMATIVA:** Infrações gerais ou de prevenção identificadas fora do polígono de risco de maquinários.

---

## 💾 Pipeline de Ciência de Dados (Logs de Incidentes)

O sistema conta com inteligência de persistência para apoiar tomadas de decisão e auditorias de SSMA. Para evitar redundância de dados por quadros estáticos, o software implementa um filtro de estado (*Anti-Flood*): dados contendo timestamp preciso, nível de severidade e a cadeia de infrações ocorridas são salvos no arquivo estruturado `historico_incidentes.csv` estritamente nos momentos em que ocorrem alterações no cenário de risco detectado pela câmera.

---

## ⚙️ Como Executar

1. Clone este repositório:
   ```bash
   git clone [https://github.com/ArthurEdersonSilva/Challenger_2026.git](https://github.com/ArthurEdersonSilva/Challenger_2026.git)
