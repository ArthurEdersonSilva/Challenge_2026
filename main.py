import cv2
import math
import os
import threading
import time
import numpy as np
import torch

from ultralytics import YOLO

import config
import ambientes
import camera_registry

from analise_ambiente import (
    analisar_frame,
    desenhar_objetos
)

from objetos_globais import (
    criar_objetos_globais,
    preparar_objetos_para_salvar
)

from decision_engine import (
    processar_incidente,
    atualizar_incidentes_ausentes,
    criar_chave_incidente
)

from notificacoes import (
    atualizar_notificacoes,
    encerrar_notificacoes
)

from estado_sistema import (
    CAMERA_OFFLINE,
    CAMERA_ONLINE,
    CAMERA_RECONECTANDO,
    criar_estado_sistema_legado
)

from rastreamento_pessoas import (
    GerenciadorRastreamentoPessoas,
    desenhar_pose_debug,
)

from associacao_epi_pessoa import (
    associar_deteccoes_camera,
)


# ============================================================
# ESTADO CENTRAL
# ============================================================

estado_sistema = criar_estado_sistema_legado(
    config
)

# Perfil persistente atualmente selecionado na ETAPA 3.
perfil_ativo = None


# ============================================================
# CONFIGURAÇÕES
# ============================================================

MAX_INDICES_CAMERA = getattr(
    config,
    "MAX_CAMERAS",
    66
)

LIMITE_FALHAS_CAPTURA = 10

INTERVALO_ANALISE_AMBIENTE = 10

FRAMES_ANTES_CONFIGURACAO = 30


# ============================================================
# ESTABILIZACAO TEMPORAL DOS EPIs
# ============================================================

# Poucos frames para aceitar que o EPI apareceu.
FRAMES_CONFIRMAR_EPI_PRESENTE = 3

# Mais frames para aceitar uma ausência explícita.
FRAMES_CONFIRMAR_EPI_AUSENTE = 8

# Se o modelo não detectar nem presença nem ausência,
# preservamos o último estado por um tempo para evitar
# oscilação frame a frame.
FRAMES_SEM_EVIDENCIA_PARA_AUSENCIA = 25

estado_temporal_epis = {}

# Detalhes da última inferência por câmera.
# Usado para escolher a câmera/frame da foto de prova.
detalhes_epis_cameras = {}


# ============================================================
# INTERFACE DE CONFIGURAÇÃO
# ============================================================

NOME_JANELA_CONFIG = (
    "Configuracao Inicial"
)

clique_mouse = None
rolagem_mouse = 0


# ============================================================
# EPI - CLASSES
#
# A taxonomia das classes reais do best.pt pertence a config.py.
# O main.py consulta diretamente config.EPIS_PRESENCA e
# config.EPIS_AUSENCIA para evitar mapas ou aliases duplicados.
# ============================================================


# ============================================================
# MODELO DE EPI
# ============================================================

modelo_epi = None
modelo_pose = None
gerenciador_rastreamento_pessoas = None


def carregar_modelo_epi():

    global modelo_epi

    if modelo_epi is not None:

        return modelo_epi

    caminho = getattr(
        config,
        "PATH_MODELO",
        "best.pt"
    )

    if not os.path.exists(
        caminho
    ):

        print()
        print(
            f"⚠️ Modelo de EPI não encontrado: "
            f"{caminho}"
        )

        return None

    try:

        modelo_epi = YOLO(
            caminho
        )

        classes_esperadas = set(
            getattr(
                config,
                "CLASSES_MODELO_EPI",
                []
            )
        )

        nomes_modelo = getattr(
            modelo_epi,
            "names",
            {}
        )

        if isinstance(nomes_modelo, dict):
            classes_modelo = set(
                str(nome)
                for nome in nomes_modelo.values()
            )
        else:
            classes_modelo = set(
                str(nome)
                for nome in nomes_modelo
            )

        if classes_esperadas:

            faltantes = sorted(
                classes_esperadas - classes_modelo
            )

            inesperadas = sorted(
                classes_modelo - classes_esperadas
            )

            if faltantes or inesperadas:

                print()
                print(
                    "⚠️ Contrato de classes do best.pt "
                    "divergente."
                )

                if faltantes:
                    print(
                        "Classes esperadas ausentes: "
                        + ", ".join(faltantes)
                    )

                if inesperadas:
                    print(
                        "Classes inesperadas no modelo: "
                        + ", ".join(inesperadas)
                    )

            else:

                print()
                print(
                    "✅ Classes do best.pt validadas: "
                    f"{len(classes_modelo)} classes."
                )

        print()
        print(
            "=========================================="
        )
        print(
            " MODELO DE EPI CARREGADO"
        )
        print(
            "=========================================="
        )

        print(
            caminho
        )

        print(
            "=========================================="
        )
        print()

        return modelo_epi

    except Exception as erro:

        print(
            f"❌ Erro ao carregar modelo de EPI: "
            f"{erro}"
        )

        modelo_epi = None

        return None


# ============================================================
# MODELO POSE / TRACKING DE PESSOAS - ETAPA 5
# ============================================================

def carregar_modelo_pose():

    global modelo_pose
    global gerenciador_rastreamento_pessoas

    if modelo_pose is not None and gerenciador_rastreamento_pessoas is not None:
        return gerenciador_rastreamento_pessoas

    caminho = getattr(
        config,
        "PATH_MODELO_POSE",
        "yolov8n-pose.pt"
    )

    if not os.path.exists(caminho):
        print()
        print(f"⚠️ Modelo Pose não encontrado: {caminho}")
        estado_sistema.atualizar_latencia_pose(None)
        return None

    try:
        modelo_pose = YOLO(caminho)
        gerenciador_rastreamento_pessoas = GerenciadorRastreamentoPessoas(
            modelo_pose=modelo_pose,
            confianca_pose=getattr(config, "CONFIANCA_POSE", 0.5),
            confianca_keypoint=getattr(
                config,
                "CONFIANCA_KEYPOINT_POSE",
                0.5
            ),
            tamanho_imagem=getattr(config, "TAMANHO_IMAGEM", 640),
            iou_tracking=getattr(
                config,
                "POSE_TRACK_IOU_MINIMO",
                0.25
            ),
            distancia_centro_tracking=getattr(
                config,
                "POSE_TRACK_DISTANCIA_CENTRO_MAXIMA",
                0.80
            ),
            max_frames_sem_deteccao=getattr(
                config,
                "POSE_TRACK_MAX_FRAMES_SEM_DETECCAO",
                12
            ),
            device=DEVICE,
        )

        print()
        print("==========================================")
        print(" MODELO POSE CARREGADO - ETAPA 5")
        print("==========================================")
        print(caminho)
        print("Tracking isolado por camera: ATIVO")
        print("==========================================")
        print()

        return gerenciador_rastreamento_pessoas

    except Exception as erro:
        print(f"❌ Erro ao carregar modelo Pose: {erro}")
        modelo_pose = None
        gerenciador_rastreamento_pessoas = None
        estado_sistema.atualizar_latencia_pose(None)
        return None


def processar_pose_cameras(frames):
    """
    Executa Pose em todos os frames de monitoramento recebidos.

    Não altera frequência, resolução de captura ou frequência do detector
    de EPI. A latência registrada é a média real por câmera processada
    neste ciclo. O desenho de debug é aplicado somente em cópias para
    visualização, depois que o frame original já foi usado pelo pipeline
    atual de EPI/incidentes/notificações.
    """
    gerenciador = carregar_modelo_pose()

    if gerenciador is None or not frames:
        if not frames:
            estado_sistema.atualizar_latencia_pose(None)
        return frames

    resultados_por_camera = {}
    latencias = []

    for camera, frame in frames:
        try:
            resultado = gerenciador.processar_camera(
                camera_id=camera.camera_id,
                frame=frame,
            )
            resultados_por_camera[camera.camera_id] = resultado
            latencias.append(resultado.latencia_pose_ms)
            estado_sistema.atualizar_pessoas_camera(
                camera.camera_id,
                resultado.tracks,
            )
        except Exception as erro:
            print(f"⚠️ Erro Pose {camera.nome}: {erro}")
            tracks = gerenciador.marcar_camera_sem_frame(camera.camera_id)
            estado_sistema.atualizar_pessoas_camera(
                camera.camera_id,
                tracks,
            )

    if latencias:
        estado_sistema.atualizar_latencia_pose(
            sum(latencias) / len(latencias)
        )
    else:
        estado_sistema.atualizar_latencia_pose(None)

    if not getattr(config, "POSE_DEBUG", False):
        return frames

    frames_debug = []
    for camera, frame in frames:
        resultado = resultados_por_camera.get(camera.camera_id)
        if resultado is None:
            frames_debug.append((camera, frame))
            continue

        frames_debug.append(
            (
                camera,
                desenhar_pose_debug(frame, resultado.tracks),
            )
        )

    return frames_debug


def encerrar_tracking_camera(camera_id):
    global gerenciador_rastreamento_pessoas

    if gerenciador_rastreamento_pessoas is not None:
        gerenciador_rastreamento_pessoas.encerrar_camera(camera_id)

    estado_sistema.encerrar_pessoas_camera(camera_id)


def marcar_tracking_camera_sem_frame(camera_id):
    """
    Avança somente o ciclo de vida temporal do tracker quando uma câmera
    deixa de fornecer observação válida. Não executa Pose sobre frame antigo.
    """
    global gerenciador_rastreamento_pessoas

    if gerenciador_rastreamento_pessoas is None:
        return

    tracks = gerenciador_rastreamento_pessoas.marcar_camera_sem_frame(camera_id)
    estado_sistema.atualizar_pessoas_camera(camera_id, tracks)
    estado_sistema.limpar_associacoes_epi_camera(camera_id)


# ============================================================
# DEVICE
# ============================================================

if torch.cuda.is_available():

    DEVICE = 0

else:

    DEVICE = "cpu"


# ============================================================
# EVENTO DO MOUSE
# ============================================================

def evento_mouse(
    evento,
    x,
    y,
    flags,
    parametro
):

    global clique_mouse
    global rolagem_mouse

    if evento == cv2.EVENT_LBUTTONDOWN:

        clique_mouse = (
            x,
            y
        )

    elif evento == cv2.EVENT_MOUSEWHEEL:

        try:
            delta = cv2.getMouseWheelDelta(
                flags
            )
        except Exception:
            delta = flags

        if delta > 0:
            rolagem_mouse = -1
        elif delta < 0:
            rolagem_mouse = 1


# ============================================================
# VERIFICAR CLIQUE
# ============================================================

def ponto_dentro(
    ponto,
    caixa
):

    if ponto is None:

        return False

    x, y = ponto

    x1, y1, x2, y2 = caixa

    return (
        x1 <= x <= x2
        and
        y1 <= y <= y2
    )


# ============================================================
# DESENHAR BOTÃO
# ============================================================

def desenhar_botao(
    tela,
    texto,
    caixa,
    selecionado=False
):

    x1, y1, x2, y2 = caixa

    if selecionado:

        cor = (
            50,
            125,
            60
        )

    else:

        cor = (
            55,
            55,
            55
        )

    cv2.rectangle(
        tela,
        (x1, y1),
        (x2, y2),
        cor,
        -1
    )

    cv2.rectangle(
        tela,
        (x1, y1),
        (x2, y2),
        (140, 140, 140),
        1
    )

    cv2.putText(
        tela,
        texto,
        (
            x1 + 12,
            y1 + 27
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )


# ============================================================
# CLASSE DA CÂMERA
# ============================================================

class CameraSistema:

    def __init__(
        self,
        camera_id,
        fonte=None,
        nome=None
    ):
        self.camera_id = camera_id
        self.fonte = camera_id if fonte is None else fonte
        self.nome = nome if nome else f"Camera {camera_id + 1:02d}"
        self.cap = None
        self.ativa = False
        self.ultimo_frame = None
        self.falhas_consecutivas = 0
        self.objetos = []
        self.total_objetos = 0
        self.tipo_rede = not isinstance(self.fonte, int)
        self.camera_uid = None
        self.status_identidade = None

        self.thread_captura = None
        self.parar_thread = threading.Event()
        self.lock_frame = threading.Lock()

        self.ultimo_frame_em = 0.0
        self.ultima_leitura_ok_em = 0.0
        self.intervalo_reconexao = 1.0
        self.tempo_sem_frame_para_reconectar = 5.0
        self.tempo_max_frame_rede = float(
            getattr(config, "TEMPO_MAX_FRAME_REDE_SEGUNDOS", 2.0)
        )

    def _abrir_captura_rede(self):
        fonte_texto = str(self.fonte)
        eh_rtsp = fonte_texto.lower().startswith("rtsp://")

        if eh_rtsp:
            tentativas = [
                ("RTSP automatico", None, None),
                ("FFmpeg automatico", cv2.CAP_FFMPEG, None),
                ("RTSP via TCP", cv2.CAP_FFMPEG, "rtsp_transport;tcp"),
                ("RTSP via UDP", cv2.CAP_FFMPEG, "rtsp_transport;udp"),
            ]
        else:
            tentativas = [
                ("Stream automatico", None, None),
                ("FFmpeg", cv2.CAP_FFMPEG, None),
            ]

        for descricao, backend, opcoes_ffmpeg in tentativas:
            cap_teste = None
            try:
                if opcoes_ffmpeg:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = opcoes_ffmpeg
                else:
                    os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)

                print(f"   Tentando {self.nome}: {descricao}...")

                if backend is None:
                    cap_teste = cv2.VideoCapture(self.fonte)
                else:
                    cap_teste = cv2.VideoCapture(self.fonte, backend)

                if not cap_teste.isOpened():
                    cap_teste.release()
                    continue

                try:
                    cap_teste.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

                sucesso, frame = cap_teste.read()

                if sucesso and frame is not None and frame.size > 0:
                    print(f"   ✅ Funcionou com {descricao}")
                    return cap_teste, frame

                cap_teste.release()

            except Exception as erro:
                if cap_teste is not None:
                    try:
                        cap_teste.release()
                    except Exception:
                        pass
                print(f"   ⚠️ Falhou {descricao}: {erro}")

            finally:
                os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)

        return None, None

    def _loop_captura_rede(self):
        while not self.parar_thread.is_set():
            if self.cap is None or not self.cap.isOpened():
                cap_novo, frame_inicial = self._abrir_captura_rede()

                if cap_novo is None:
                    self.falhas_consecutivas += 1
                    time.sleep(self.intervalo_reconexao)
                    continue

                self.cap = cap_novo

                with self.lock_frame:
                    self.ultimo_frame = frame_inicial.copy()
                    agora = time.time()
                    self.ultimo_frame_em = agora
                    self.ultima_leitura_ok_em = agora

                self.falhas_consecutivas = 0

            try:
                sucesso, frame = self.cap.read()
            except Exception:
                sucesso = False
                frame = None

            if sucesso and frame is not None and frame.size > 0:
                with self.lock_frame:
                    self.ultimo_frame = frame.copy()
                    agora = time.time()
                    self.ultimo_frame_em = agora
                    self.ultima_leitura_ok_em = agora

                self.falhas_consecutivas = 0
                continue

            self.falhas_consecutivas += 1
            agora = time.time()
            tempo_sem_frame = agora - self.ultima_leitura_ok_em

            if tempo_sem_frame >= self.tempo_sem_frame_para_reconectar:
                print(f"⚠️ {self.nome}: stream instavel, tentando reconectar...")
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
                time.sleep(self.intervalo_reconexao)
            else:
                time.sleep(0.02)

    def abrir(self):
        self.liberar()

        if not self.tipo_rede:
            try:
                self.cap = cv2.VideoCapture(self.fonte, cv2.CAP_DSHOW)
            except Exception:
                self.cap = None
                return False

            if self.cap is None or not self.cap.isOpened():
                if self.cap is not None:
                    self.cap.release()
                self.cap = None
                return False

            self.cap.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                getattr(config, "LARGURA_CAM", 640)
            )
            self.cap.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                getattr(config, "ALTURA_CAM", 480)
            )

            sucesso, frame = self.cap.read()

            if not sucesso or frame is None or frame.size == 0:
                self.cap.release()
                self.cap = None
                return False

            self.ultimo_frame = frame
            self.ativa = True
            self.falhas_consecutivas = 0
            print(f"✅ {self.nome} encontrada (USB)")
            return True

        cap_inicial, frame_inicial = self._abrir_captura_rede()

        if cap_inicial is None:
            return False

        self.cap = cap_inicial

        with self.lock_frame:
            self.ultimo_frame = frame_inicial.copy()
            agora = time.time()
            self.ultimo_frame_em = agora
            self.ultima_leitura_ok_em = agora

        self.ativa = True
        self.falhas_consecutivas = 0
        self.parar_thread.clear()

        self.thread_captura = threading.Thread(
            target=self._loop_captura_rede,
            daemon=True,
            name=f"captura_{self.camera_id}"
        )
        self.thread_captura.start()

        print(f"✅ {self.nome} encontrada (WIFI/IP - captura em thread)")
        return True

    def grab(self):
        if not self.ativa:
            return False

        if self.tipo_rede:
            return True

        if self.cap is None:
            return False

        try:
            sucesso = self.cap.grab()
        except Exception:
            sucesso = False

        if not sucesso:
            self.falhas_consecutivas += 1

        return sucesso

    def frame_rede_fresco(self, agora=None):
        if not self.tipo_rede:
            return True

        if agora is None:
            agora = time.time()

        with self.lock_frame:
            if self.ultimo_frame is None or self.ultimo_frame_em <= 0:
                return False
            idade = agora - self.ultimo_frame_em

        return idade <= self.tempo_max_frame_rede

    def status_rede_sem_frame(self):
        if not self.tipo_rede:
            return CAMERA_OFFLINE

        thread_ativa = (
            self.thread_captura is not None
            and self.thread_captura.is_alive()
            and not self.parar_thread.is_set()
        )

        if self.ativa and thread_ativa:
            return CAMERA_RECONECTANDO

        return CAMERA_OFFLINE

    def retrieve(self):
        if not self.ativa:
            return None

        if self.tipo_rede:
            agora = time.time()
            with self.lock_frame:
                if self.ultimo_frame is None or self.ultimo_frame_em <= 0:
                    return None
                if agora - self.ultimo_frame_em > self.tempo_max_frame_rede:
                    return None
                return self.ultimo_frame.copy()

        if self.cap is None:
            return None

        try:
            sucesso, frame = self.cap.retrieve()
        except Exception:
            sucesso = False
            frame = None

        if not sucesso or frame is None or frame.size == 0:
            self.falhas_consecutivas += 1
            return None

        self.falhas_consecutivas = 0
        self.ultimo_frame = frame
        return frame

    def perdeu_conexao(self):
        if self.tipo_rede:
            return False

        return self.falhas_consecutivas >= LIMITE_FALHAS_CAPTURA

    def liberar(self):
        self.ativa = False

        if self.tipo_rede:
            self.parar_thread.set()

        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass

        self.cap = None

        if (
            self.thread_captura is not None
            and self.thread_captura.is_alive()
            and threading.current_thread() is not self.thread_captura
        ):
            try:
                self.thread_captura.join(timeout=1.5)
            except Exception:
                pass

        self.thread_captura = None


# ============================================================
# ABRIR CÂMERAS A PARTIR DE UMA CONFIGURAÇÃO
# ============================================================

def abrir_cameras_configuradas(
    configuracoes,
    modo
):

    cameras = {}

    for camera_id, dados in configuracoes.items():

        if not dados.get(
            "ativa",
            True
        ):
            continue

        fonte = dados.get(
            "fonte",
            camera_id
        )

        nome = dados.get(
            "nome",
            f"Camera {camera_id + 1:02d}"
        )

        camera = CameraSistema(
            camera_id,
            fonte,
            nome
        )

        if camera.abrir():

            cameras[
                camera_id
            ] = camera

    return cameras


# ============================================================
# DESCOBRIR CÂMERAS
# ============================================================

def descobrir_cameras():

    modo = getattr(
        config,
        "MODO_CAMERAS",
        "usb"
    ).lower()

    print()
    print(
        "=========================================="
    )
    print(
        " PROCURANDO CAMERAS DISPONIVEIS"
    )
    print(
        "=========================================="
    )

    # ========================================================
    # WIFI / IP TEM PRIORIDADE
    # ========================================================

    if modo == "wifi":

        print(
            "Modo configurado: WIFI / IP"
        )

        print(
            "Tentando abrir somente as cameras "
            "salvas em camera_wifi/cameras_wifi.json"
        )

        configuracoes_wifi = getattr(
            config,
            "CAMERAS",
            {}
        )

        cameras = abrir_cameras_configuradas(
            configuracoes_wifi,
            "wifi"
        )

        if cameras:

            print(
                "=========================================="
            )

            print(
                f"Total de cameras WiFi/IP abertas: "
                f"{len(cameras)}"
            )

            print(
                "=========================================="
            )
            print()

            return cameras

        # ----------------------------------------------------
        # WIFI EXISTE NO JSON, MAS NENHUMA ABRIU
        # ----------------------------------------------------

        print()
        print(
            "⚠️ Nenhuma camera WiFi/IP configurada "
            "conseguiu abrir."
        )

        resposta = input(
            "Deseja usar cameras USB como fallback? "
            "[S/n]: "
        ).strip().lower()

        if resposta not in (
            "",
            "s",
            "sim",
            "y",
            "yes"
        ):

            print()
            print(
                "Fallback USB cancelado."
            )
            print()

            return {}

        print()
        print(
            "Usando fallback USB..."
        )

        if hasattr(
            config,
            "criar_cameras_usb"
        ):

            configuracoes_usb = (
                config.criar_cameras_usb()
            )

        else:

            configuracoes_usb = {

                camera_id: {
                    "nome":
                        f"Camera {camera_id + 1:02d}",

                    "fonte":
                        camera_id,

                    "tipo":
                        "usb",

                    "ativa":
                        True,
                }

                for camera_id in range(
                    MAX_INDICES_CAMERA
                )
            }

        cameras = abrir_cameras_configuradas(
            configuracoes_usb,
            "usb"
        )

        print(
            "=========================================="
        )

        print(
            f"Total de cameras USB encontradas: "
            f"{len(cameras)}"
        )

        print(
            "=========================================="
        )
        print()

        return cameras

    # ========================================================
    # USB PADRÃO
    # ========================================================

    print(
        "Modo configurado: USB"
    )

    if hasattr(
        config,
        "criar_cameras_usb"
    ):

        configuracoes_usb = (
            config.criar_cameras_usb()
        )

    else:

        configuracoes_usb = getattr(
            config,
            "CAMERAS",
            {}
        )

    cameras = abrir_cameras_configuradas(
        configuracoes_usb,
        "usb"
    )

    print(
        "=========================================="
    )

    print(
        f"Total de cameras USB encontradas: "
        f"{len(cameras)}"
    )

    print(
        "=========================================="
    )
    print()

    return cameras
# ============================================================
# CAPTURA SINCRONIZADA
# ============================================================

def capturar_frames_sincronizados(
    cameras
):

    for camera in cameras.values():

        if camera.ativa:

            camera.grab()

    frames = []

    remover = []

    for (
        camera_id,
        camera
    ) in list(
        cameras.items()
    ):

        frame = camera.retrieve()

        if frame is None:

            # Câmeras de rede permanecem cadastradas/ativas para que a
            # thread existente possa reconectar. Um ultimo_frame obsoleto
            # nunca volta ao pipeline como se fosse observação atual.
            if camera.tipo_rede:
                status_rede = camera.status_rede_sem_frame()

                estado_sistema.atualizar_camera_runtime(
                    camera_id=camera_id,
                    status=status_rede,
                    ativa=camera.ativa,
                    ultimo_frame_em=(
                        camera.ultimo_frame_em
                        if camera.ultimo_frame_em > 0
                        else None
                    ),
                    ultima_leitura_ok_em=(
                        camera.ultima_leitura_ok_em
                        if camera.ultima_leitura_ok_em > 0
                        else None
                    ),
                    falhas_consecutivas=camera.falhas_consecutivas
                )

                if status_rede == CAMERA_RECONECTANDO:
                    marcar_tracking_camera_sem_frame(camera_id)
                else:
                    encerrar_tracking_camera(camera_id)

                continue

            if camera.perdeu_conexao():

                remover.append(
                    camera_id
                )

                continue

            # Compatibilidade USB: somente fontes locais podem recorrer ao
            # ultimo_frame legado. Para rede esse fallback é proibido acima.
            if camera.ultimo_frame is not None:

                frame = (
                    camera.ultimo_frame.copy()
                )

            else:

                estado_sistema.limpar_associacoes_epi_camera(camera_id)
                continue

        frames.append(
            (
                camera,
                frame
            )
        )

        estado_sistema.atualizar_camera_runtime(
            camera_id=camera_id,
            status=CAMERA_ONLINE,
            ativa=camera.ativa,
            ultimo_frame_em=(
                camera.ultimo_frame_em
                if camera.ultimo_frame_em > 0
                else time.time()
            ),
            ultima_leitura_ok_em=(
                camera.ultima_leitura_ok_em
                if camera.ultima_leitura_ok_em > 0
                else time.time()
            ),
            falhas_consecutivas=camera.falhas_consecutivas
        )

    for camera_id in remover:

        camera = cameras.get(
            camera_id
        )

        if camera:

            print(
                f"⚠️ {camera.nome} "
                "desconectada."
            )

            camera.liberar()

            estado_sistema.atualizar_camera_runtime(
                camera_id=camera_id,
                status=CAMERA_OFFLINE,
                ativa=False,
                falhas_consecutivas=camera.falhas_consecutivas
            )

            encerrar_tracking_camera(camera_id)

        cameras.pop(
            camera_id,
            None
        )

    return frames


# ============================================================
# ANALISAR AMBIENTE
# ============================================================

def analisar_ambiente_cameras(
    frames
):

    resultado = []

    for (
        camera,
        frame
    ) in frames:

        try:

            objetos = analisar_frame(
                frame,
                camera.camera_id
            )

        except Exception as erro:

            print(
                f"Erro analisando "
                f"{camera.nome}: {erro}"
            )

            objetos = []

        camera.objetos = objetos

        camera.total_objetos = len(
            objetos
        )

        frame_visual = (
            desenhar_objetos(
                frame,
                objetos
            )
        )

        resultado.append(
            (
                camera,
                frame_visual
            )
        )

    return resultado


# ============================================================
# DESENHAR OBJETOS EXISTENTES
# ============================================================

def desenhar_objetos_existentes(
    frames
):

    resultado = []

    for (
        camera,
        frame
    ) in frames:

        frame_visual = (
            desenhar_objetos(
                frame,
                camera.objetos
            )
        )

        resultado.append(
            (
                camera,
                frame_visual
            )
        )

    return resultado


# ============================================================
# SELECIONAR MAQUINÁRIOS
# ============================================================

def selecionar_maquinarios(
    objetos_globais
):

    global clique_mouse
    global rolagem_mouse

    clique_mouse = None
    rolagem_mouse = 0

    selecionados = set()

    itens = sorted(
        objetos_globais.items(),
        key=lambda item: item[1].get("numero", 999999)
    )

    largura_tela = 760
    altura_tela = 600
    topo_lista = 115
    rodape = 100
    altura_item = 52

    x_lista_inicio = 30
    x_lista_fim = 690
    x_barra_inicio = 710
    x_barra_fim = 728

    area_lista = altura_tela - topo_lista - rodape
    itens_por_pagina = max(1, area_lista // altura_item)
    max_offset = max(0, len(itens) - itens_por_pagina)
    offset = 0

    cv2.namedWindow(NOME_JANELA_CONFIG, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(NOME_JANELA_CONFIG, largura_tela, altura_tela)
    cv2.setMouseCallback(NOME_JANELA_CONFIG, evento_mouse)

    while True:

        if rolagem_mouse != 0:
            offset += rolagem_mouse
            offset = max(0, min(max_offset, offset))
            rolagem_mouse = 0

        tela = np.zeros(
            (altura_tela, largura_tela, 3),
            dtype=np.uint8
        )
        tela[:] = (28, 28, 28)

        cv2.putText(
            tela,
            "ANALISE DO AMBIENTE",
            (30, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            tela,
            "Quais objetos sao maquinarios?",
            (30, 78),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            (0, 220, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            tela,
            "Role o mouse, use W/S ou clique na barra",
            (30, 103),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (170, 170, 170),
            1,
            cv2.LINE_AA
        )

        botoes = {}
        visiveis = itens[offset:offset + itens_por_pagina]
        y = topo_lista

        for objeto_id, objeto in visiveis:

            cameras_texto = ", ".join(
                f"CAM {camera + 1:02d}"
                for camera in objeto.get("cameras", [])
            )

            nome_global = objeto.get("nome", objeto_id)
            texto = f"{nome_global}  |  {cameras_texto}"

            caixa = (
                x_lista_inicio,
                y,
                x_lista_fim,
                y + 42
            )

            botoes[objeto_id] = caixa

            desenhar_botao(
                tela,
                texto,
                caixa,
                objeto_id in selecionados
            )

            y += altura_item

        # Barra de rolagem visível.
        y_barra_inicio = topo_lista
        y_barra_fim = topo_lista + area_lista - 5

        cv2.rectangle(
            tela,
            (x_barra_inicio, y_barra_inicio),
            (x_barra_fim, y_barra_fim),
            (65, 65, 65),
            -1
        )

        if len(itens) > itens_por_pagina:

            altura_trilho = y_barra_fim - y_barra_inicio

            altura_cursor = max(
                45,
                int(
                    altura_trilho
                    * itens_por_pagina
                    / len(itens)
                )
            )

            espaco_cursor = max(
                1,
                altura_trilho - altura_cursor
            )

            proporcao = (
                offset / max_offset
                if max_offset > 0
                else 0
            )

            y_cursor = (
                y_barra_inicio
                + int(proporcao * espaco_cursor)
            )

            cv2.rectangle(
                tela,
                (x_barra_inicio + 2, y_cursor),
                (x_barra_fim - 2, y_cursor + altura_cursor),
                (180, 180, 180),
                -1
            )

        inicio = offset + 1 if itens else 0
        fim = min(len(itens), offset + itens_por_pagina)

        cv2.putText(
            tela,
            f"Objetos {inicio}-{fim} de {len(itens)}",
            (30, altura_tela - 52),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.43,
            (170, 170, 170),
            1,
            cv2.LINE_AA
        )

        # Fixo no rodapé da janela.
        confirmar = (
            500,
            altura_tela - 75,
            720,
            altura_tela - 25
        )

        desenhar_botao(
            tela,
            "CONFIRMAR",
            confirmar,
            True
        )

        cv2.imshow(NOME_JANELA_CONFIG, tela)

        tecla = cv2.waitKey(20) & 0xFF

        if tecla == ord("q"):
            return None

        if tecla in (ord("s"), 84):
            offset = min(max_offset, offset + 1)

        elif tecla in (ord("w"), 82):
            offset = max(0, offset - 1)

        if clique_mouse is None:
            continue

        clique = clique_mouse
        clique_mouse = None

        for objeto_id, caixa in botoes.items():

            if ponto_dentro(clique, caixa):

                if objeto_id in selecionados:
                    selecionados.remove(objeto_id)
                else:
                    selecionados.add(objeto_id)

        # Clique na barra move a lista.
        if (
            x_barra_inicio <= clique[0] <= x_barra_fim
            and y_barra_inicio <= clique[1] <= y_barra_fim
            and max_offset > 0
        ):

            proporcao = (
                (clique[1] - y_barra_inicio)
                / max(1, y_barra_fim - y_barra_inicio)
            )

            offset = int(round(proporcao * max_offset))
            offset = max(0, min(max_offset, offset))

        if ponto_dentro(clique, confirmar):
            break

    for objeto_id, objeto in objetos_globais.items():
        objeto["maquinario"] = objeto_id in selecionados

    return objetos_globais
# ============================================================
# SELECIONAR EPIs
# ============================================================

def selecionar_epis():

    global clique_mouse
    global rolagem_mouse

    clique_mouse = None
    rolagem_mouse = 0

    selecionados = set()

    epis = list(
        getattr(
            config,
            "EPIS_DISPONIVEIS",
            []
        )
    )

    largura_tela = 760
    altura_tela = 610
    topo_lista = 120
    rodape = 90
    altura_item = 58

    x_lista_inicio = 30
    x_lista_fim = 690
    x_barra_inicio = 710
    x_barra_fim = 728

    area_lista = (
        altura_tela
        - topo_lista
        - rodape
    )

    itens_por_pagina = max(
        1,
        area_lista // altura_item
    )

    max_offset = max(
        0,
        len(epis) - itens_por_pagina
    )

    offset = 0

    cv2.namedWindow(
        NOME_JANELA_CONFIG,
        cv2.WINDOW_NORMAL
    )

    cv2.resizeWindow(
        NOME_JANELA_CONFIG,
        largura_tela,
        altura_tela
    )

    cv2.setMouseCallback(
        NOME_JANELA_CONFIG,
        evento_mouse
    )

    while True:

        if rolagem_mouse != 0:

            offset += rolagem_mouse
            offset = max(
                0,
                min(max_offset, offset)
            )
            rolagem_mouse = 0

        tela = np.zeros(
            (
                altura_tela,
                largura_tela,
                3
            ),
            dtype=np.uint8
        )

        tela[:] = (
            28,
            28,
            28
        )

        cv2.putText(
            tela,
            "CONFIGURACAO DE EPIs",
            (30, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            tela,
            "Quais EPIs sao obrigatorios?",
            (30, 78),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            (0, 220, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            tela,
            "Role o mouse, use W/S ou clique na barra",
            (30, 103),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (170, 170, 170),
            1,
            cv2.LINE_AA
        )

        botoes = {}

        visiveis = epis[
            offset:
            offset + itens_por_pagina
        ]

        y = topo_lista

        for epi in visiveis:

            caixa = (
                x_lista_inicio,
                y,
                x_lista_fim,
                y + 45
            )

            botoes[epi] = caixa

            if epi in selecionados:
                prefixo = "[X]"
            else:
                prefixo = "[ ]"

            desenhar_botao(
                tela,
                f"{prefixo}  {epi}",
                caixa,
                epi in selecionados
            )

            y += altura_item

        y_barra_inicio = topo_lista
        y_barra_fim = (
            topo_lista
            + area_lista
            - 5
        )

        cv2.rectangle(
            tela,
            (x_barra_inicio, y_barra_inicio),
            (x_barra_fim, y_barra_fim),
            (65, 65, 65),
            -1
        )

        if len(epis) > itens_por_pagina:

            altura_trilho = (
                y_barra_fim
                - y_barra_inicio
            )

            altura_cursor = max(
                45,
                int(
                    altura_trilho
                    * itens_por_pagina
                    / len(epis)
                )
            )

            espaco_cursor = max(
                1,
                altura_trilho
                - altura_cursor
            )

            proporcao = (
                offset / max_offset
                if max_offset > 0
                else 0
            )

            y_cursor = (
                y_barra_inicio
                + int(
                    proporcao
                    * espaco_cursor
                )
            )

            cv2.rectangle(
                tela,
                (
                    x_barra_inicio + 2,
                    y_cursor
                ),
                (
                    x_barra_fim - 2,
                    y_cursor + altura_cursor
                ),
                (180, 180, 180),
                -1
            )

        inicio = (
            offset + 1
            if epis
            else 0
        )

        fim = min(
            len(epis),
            offset + itens_por_pagina
        )

        cv2.putText(
            tela,
            f"EPIs {inicio}-{fim} de {len(epis)}",
            (30, altura_tela - 52),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.43,
            (170, 170, 170),
            1,
            cv2.LINE_AA
        )

        confirmar = (
            500,
            altura_tela - 75,
            720,
            altura_tela - 25
        )

        desenhar_botao(
            tela,
            "CONFIRMAR",
            confirmar,
            True
        )

        cv2.imshow(
            NOME_JANELA_CONFIG,
            tela
        )

        tecla = (
            cv2.waitKey(20)
            & 0xFF
        )

        if tecla == ord("q"):
            return None

        if tecla in (ord("s"), 84):
            offset = min(
                max_offset,
                offset + 1
            )

        elif tecla in (ord("w"), 82):
            offset = max(
                0,
                offset - 1
            )

        if clique_mouse is None:
            continue

        clique = clique_mouse
        clique_mouse = None

        for epi, caixa in botoes.items():

            if ponto_dentro(
                clique,
                caixa
            ):

                if epi in selecionados:
                    selecionados.remove(epi)
                else:
                    selecionados.add(epi)

        if (
            x_barra_inicio
            <= clique[0]
            <= x_barra_fim
            and
            y_barra_inicio
            <= clique[1]
            <= y_barra_fim
            and
            max_offset > 0
        ):

            proporcao = (
                (
                    clique[1]
                    - y_barra_inicio
                )
                / max(
                    1,
                    y_barra_fim
                    - y_barra_inicio
                )
            )

            offset = int(
                round(
                    proporcao
                    * max_offset
                )
            )

            offset = max(
                0,
                min(max_offset, offset)
            )

        if ponto_dentro(
            clique,
            confirmar
        ):
            break

    return [
        epi
        for epi in epis
        if epi in selecionados
    ]


# ============================================================
# CONFIGURAR AMBIENTE
# ============================================================

def configurar_ambiente(
    frames_originais
):

    global estado_sistema
    global perfil_ativo

    print()
    print(
        "Agrupando objetos entre as cameras..."
    )

    objetos_globais = (
        criar_objetos_globais(
            frames_originais
        )
    )

    if not objetos_globais:

        print(
            "⚠️ Nenhum objeto detectado."
        )

        return False

    print(
        f"Objetos globais: "
        f"{len(objetos_globais)}"
    )

    # ========================================================
    # MAQUINÁRIOS
    # ========================================================

    objetos_globais = (
        selecionar_maquinarios(
            objetos_globais
        )
    )

    if objetos_globais is None:

        return False

    objetos_salvar = (
        preparar_objetos_para_salvar(
            objetos_globais
        )
    )

    # ========================================================
    # EPIs
    # ========================================================

    estado_sistema.definir_fase(
        config.ESTADO_CONFIGURACAO_EPI
    )

    epis = selecionar_epis()

    if epis is None:

        return False

    if perfil_ativo is None:
        print(
            "❌ Nenhum perfil de ambiente ativo para salvar."
        )
        return False

    perfil_ativo["calibrado"] = True
    perfil_ativo["objetos_globais"] = objetos_salvar
    perfil_ativo["epis_obrigatorios"] = list(epis)

    try:
        caminho_salvo = ambientes.salvar_perfil(
            perfil_ativo
        )
    except Exception as erro:
        print(
            f"❌ Erro ao salvar perfil do ambiente: {erro}"
        )
        return False

    config.aplicar_perfil_runtime(
        perfil_ativo
    )

    estado_sistema.ativar_ambiente_perfil(
        ambiente_id=perfil_ativo["ambiente_id"],
        nome=perfil_ativo["nome"],
        calibrado=perfil_ativo["calibrado"],
        cameras_associadas=perfil_ativo.get("cameras", []),
        epis_obrigatorios=perfil_ativo.get("epis_obrigatorios", []),
        objetos_globais=perfil_ativo.get("objetos_globais", {})
    )

    print(
        f"✅ Perfil salvo em: {caminho_salvo}"
    )

    # ========================================================
    # MONITORAMENTO
    # ========================================================

    estado_sistema.definir_fase(
        config.ESTADO_MONITORAMENTO
    )

    carregar_modelo_epi()

    try:

        cv2.destroyWindow(
            NOME_JANELA_CONFIG
        )

    except Exception:

        pass

    print()
    print(
        "=========================================="
    )
    print(
        " CONFIGURACAO CONCLUIDA"
    )
    print(
        "=========================================="
    )

    print(
        f"EPIs obrigatorios: "
        f"{epis}"
    )

    print(
        "Estado: MONITORAMENTO"
    )

    print(
        "=========================================="
    )
    print()

    return True


# ============================================================
# ANALISAR EPIs EM UM FRAME
# ============================================================

def analisar_epis_frame(
    frame
):

    obrigatorios = getattr(
        config,
        "EPIS_OBRIGATORIOS",
        []
    )

    status = {

        epi: False

        for epi in obrigatorios
    }

    if not obrigatorios:

        return status

    modelo = carregar_modelo_epi()

    if modelo is None:

        return status

    try:

        resultados = modelo.predict(
            frame,
            conf=getattr(
                config,
                "CONFIDENCIA_MINIMA",
                0.5
            ),
            imgsz=getattr(
                config,
                "TAMANHO_IMAGEM",
                640
            ),
            device=DEVICE,
            verbose=False
        )

    except Exception as erro:

        print(
            f"⚠️ Erro na análise de EPI: "
            f"{erro}"
        )

        return status

    classes = set()

    for resultado in resultados:

        if resultado.boxes is None:

            continue

        for box in resultado.boxes:

            classe_id = int(
                box.cls[0]
            )

            nome = resultado.names[
                classe_id
            ]

            classes.add(
                nome
            )

    for epi in obrigatorios:

        classe_presenca = None

        classe_ausencia = None

        for (
            classe,
            nome
        ) in config.EPIS_PRESENCA.items():

            if nome == epi:

                classe_presenca = classe

                break

        for (
            classe,
            nome
        ) in config.EPIS_AUSENCIA.items():

            if nome == epi:

                classe_ausencia = classe

                break

        # Ausência explícita tem prioridade.
        if (
            classe_ausencia is not None
            and classe_ausencia in classes
        ):

            status[
                epi
            ] = False

        elif (
            classe_presenca is not None
            and classe_presenca in classes
        ):

            status[
                epi
            ] = True

        else:

            status[
                epi
            ] = False

    return status


# ============================================================
# ANALISAR EPIs EM TODAS AS CÂMERAS
# ============================================================

def analisar_epis_cameras(
    frames
):

    global detalhes_epis_cameras

    obrigatorios = list(
        getattr(
            config,
            "EPIS_OBRIGATORIOS",
            []
        )
    )

    if not obrigatorios:

        detalhes_epis_cameras = {}

        return {}

    modelo = carregar_modelo_epi()

    if (
        modelo is None
        or not frames
    ):

        detalhes_epis_cameras = {}

        return {
            epi: estado_temporal_epis.get(
                epi,
                {}
            ).get(
                "status",
                False
            )
            for epi in obrigatorios
        }

    # --------------------------------------------------------
    # Evidência agregada entre todas as câmeras.
    #
    # Regra principal:
    # se QUALQUER câmera enxergar o EPI presente,
    # a presença vence a ausência de outra câmera.
    # --------------------------------------------------------

    presenca_global = {
        epi: False
        for epi in obrigatorios
    }

    ausencia_explicita_global = {
        epi: False
        for epi in obrigatorios
    }

    detalhes_epis_cameras = {}

    for camera, frame in frames:

        detalhes_camera = {
            "camera":
                camera,

            "frame":
                frame,

            "presentes":
                set(),

            "ausentes":
                set(),

            "confiancas_presenca":
                {},

            "confiancas_ausencia":
                {},

            # ETAPA 6: reaproveita a MESMA inferência best.pt deste frame.
            # Guarda somente bbox/classe/confiança dos EPIs obrigatórios.
            "deteccoes_epi":
                [],
        }

        try:

            resultados = modelo.predict(
                frame,
                conf=getattr(
                    config,
                    "CONFIDENCIA_MINIMA",
                    0.5
                ),
                imgsz=getattr(
                    config,
                    "TAMANHO_IMAGEM",
                    640
                ),
                device=DEVICE,
                verbose=False
            )

        except Exception as erro:

            print(
                f"⚠️ Erro EPI "
                f"{camera.nome}: "
                f"{erro}"
            )

            detalhes_epis_cameras[
                camera.camera_id
            ] = detalhes_camera

            continue

        for resultado in resultados:

            if resultado.boxes is None:
                continue

            for box in resultado.boxes:

                classe_id = int(
                    box.cls[0]
                )

                nome_classe = str(
                    resultado.names[
                        classe_id
                    ]
                )

                confianca = 0.0

                try:

                    confianca = float(
                        box.conf[0]
                    )

                except Exception:

                    pass

                epi_detectado = None
                if nome_classe in config.EPIS_PRESENCA:
                    epi_detectado = config.EPIS_PRESENCA[nome_classe]
                elif nome_classe in config.EPIS_AUSENCIA:
                    epi_detectado = config.EPIS_AUSENCIA[nome_classe]

                if epi_detectado in obrigatorios:
                    try:
                        xyxy = box.xyxy[0]
                        bbox_epi = tuple(float(v) for v in xyxy.tolist())
                    except Exception:
                        bbox_epi = None

                    if bbox_epi is not None and len(bbox_epi) == 4:
                        detalhes_camera["deteccoes_epi"].append({
                            "classe_modelo": nome_classe,
                            "bbox": bbox_epi,
                            "confianca": confianca,
                        })

                # --------------------------------------------
                # PRESENÇA
                # --------------------------------------------

                if nome_classe in config.EPIS_PRESENCA:

                    epi = config.EPIS_PRESENCA[
                        nome_classe
                    ]

                    if epi in obrigatorios:

                        detalhes_camera[
                            "presentes"
                        ].add(
                            epi
                        )

                        detalhes_camera[
                            "confiancas_presenca"
                        ][epi] = max(
                            confianca,
                            detalhes_camera[
                                "confiancas_presenca"
                            ].get(
                                epi,
                                0.0
                            )
                        )

                        presenca_global[
                            epi
                        ] = True

                # --------------------------------------------
                # AUSÊNCIA EXPLÍCITA
                # --------------------------------------------

                if nome_classe in config.EPIS_AUSENCIA:

                    epi = config.EPIS_AUSENCIA[
                        nome_classe
                    ]

                    if epi in obrigatorios:

                        detalhes_camera[
                            "ausentes"
                        ].add(
                            epi
                        )

                        detalhes_camera[
                            "confiancas_ausencia"
                        ][epi] = max(
                            confianca,
                            detalhes_camera[
                                "confiancas_ausencia"
                            ].get(
                                epi,
                                0.0
                            )
                        )

                        ausencia_explicita_global[
                            epi
                        ] = True

        detalhes_epis_cameras[
            camera.camera_id
        ] = detalhes_camera

    status_final = {}

    for epi in obrigatorios:

        estado = estado_temporal_epis.setdefault(
            epi,
            {
                "status":
                    False,

                "frames_presente":
                    0,

                "frames_ausente":
                    0,

                "frames_sem_evidencia":
                    0,
            }
        )

        tem_presenca = presenca_global[
            epi
        ]

        # Se uma câmera detectou presença, ela vence.
        tem_ausencia_explicita = (
            not tem_presenca
            and
            ausencia_explicita_global[
                epi
            ]
        )

        if tem_presenca:

            estado[
                "frames_presente"
            ] += 1

            estado[
                "frames_ausente"
            ] = 0

            estado[
                "frames_sem_evidencia"
            ] = 0

            if (
                estado[
                    "frames_presente"
                ]
                >= FRAMES_CONFIRMAR_EPI_PRESENTE
            ):

                estado[
                    "status"
                ] = True

        elif tem_ausencia_explicita:

            estado[
                "frames_ausente"
            ] += 1

            estado[
                "frames_presente"
            ] = 0

            estado[
                "frames_sem_evidencia"
            ] = 0

            if (
                estado[
                    "frames_ausente"
                ]
                >= FRAMES_CONFIRMAR_EPI_AUSENTE
            ):

                estado[
                    "status"
                ] = False

        else:

            # Nenhuma evidência confiável neste frame.
            # Não mudamos imediatamente o status.
            estado[
                "frames_sem_evidencia"
            ] += 1

            estado[
                "frames_presente"
            ] = max(
                0,
                estado[
                    "frames_presente"
                ] - 1
            )

            estado[
                "frames_ausente"
            ] = max(
                0,
                estado[
                    "frames_ausente"
                ] - 1
            )

            # Se estava em uso e desapareceu por bastante
            # tempo em TODAS as câmeras, passa a ausente.
            if (
                estado[
                    "status"
                ]
                and
                estado[
                    "frames_sem_evidencia"
                ]
                >= FRAMES_SEM_EVIDENCIA_PARA_AUSENCIA
            ):

                estado[
                    "status"
                ] = False

        status_final[
            epi
        ] = bool(
            estado[
                "status"
            ]
        )

    return status_final

# ============================================================
# ASSOCIAÇÃO EPI ↔ PESSOA - ETAPA 6
# ============================================================

def processar_associacoes_epi_pessoa(frames):
    """Associa as detecções da inferência best.pt já executada às pessoas.

    Não executa nova inferência de EPI e não produz estados semânticos de
    conformidade. A associação é recalculada por câmera a cada frame.
    """
    cameras_com_frame = {camera.camera_id for camera, _ in (frames or [])}

    for camera_id in cameras_com_frame:
        detalhes = detalhes_epis_cameras.get(camera_id, {})
        deteccoes = detalhes.get("deteccoes_epi", [])
        pessoas = estado_sistema.obter_pessoas_camera_para_associacao(camera_id)

        # ETAPA 6: a fonte da obrigatoriedade é o ambiente ativo no
        # EstadoSistema. config.EPIS_OBRIGATORIOS permanece apenas como
        # espelho de compatibilidade do fluxo legado agregado.
        epis_obrigatorios_ambiente = (
            estado_sistema.obter_epis_obrigatorios_ambiente()
        )

        resultados = associar_deteccoes_camera(
            camera_id=camera_id,
            deteccoes_brutas=deteccoes,
            pessoas=pessoas,
            epis_obrigatorios=epis_obrigatorios_ambiente,
            mapa_presenca=config.EPIS_PRESENCA,
            mapa_ausencia=config.EPIS_AUSENCIA,
            score_minimo=getattr(
                config, "ASSOCIACAO_EPI_SCORE_MINIMO", 0.45
            ),
            margem_ambiguidade=getattr(
                config, "ASSOCIACAO_EPI_MARGEM_AMBIGUIDADE", 0.08
            ),
            intersecao_minima=getattr(
                config, "ASSOCIACAO_EPI_INTERSECAO_MINIMA", 0.05
            ),
            expansao_bbox=getattr(
                config, "ASSOCIACAO_EPI_EXPANSAO_BBOX_PESSOA", 0.08
            ),
        )
        estado_sistema.atualizar_associacoes_epi_camera(
            camera_id,
            resultados,
        )


# ============================================================
# INCIDENTES DE EPI
# ============================================================

def processar_incidentes_epis(
    status_epis,
    frames,
    operador
):

    obrigatorios = list(
        getattr(
            config,
            "EPIS_OBRIGATORIOS",
            []
        )
    )

    ambiente = getattr(
        config,
        "NOME_AMBIENTE",
        "Ambiente Principal"
    )

    # Até a biometria ser integrada ao main,
    # usamos uma matrícula estável para não criar
    # uma chave diferente a cada frame.
    matricula = "DESCONHECIDO"

    chaves_detectadas = set()

    if not frames:

        atualizar_incidentes_ausentes(
            chaves_detectadas
        )

        return

    for epi in obrigatorios:

        presente = bool(
            status_epis.get(
                epi,
                False
            )
        )

        if presente:
            continue

        # ----------------------------------------------------
        # Escolhe preferencialmente uma câmera que tenha
        # detectado explicitamente a ausência deste EPI.
        # Se não houver, usa a primeira câmera disponível.
        # ----------------------------------------------------

        camera_escolhida = None
        frame_escolhido = None
        melhor_confianca = -1.0

        for (
            camera_id,
            detalhes
        ) in detalhes_epis_cameras.items():

            if epi in detalhes.get(
                "ausentes",
                set()
            ):

                confianca = detalhes.get(
                    "confiancas_ausencia",
                    {}
                ).get(
                    epi,
                    0.0
                )

                if confianca > melhor_confianca:

                    camera_escolhida = detalhes.get(
                        "camera"
                    )

                    frame_escolhido = detalhes.get(
                        "frame"
                    )

                    melhor_confianca = confianca

        if camera_escolhida is None:

            camera_escolhida, frame_escolhido = (
                frames[0]
            )

        camera_id = getattr(
            camera_escolhida,
            "camera_id",
            None
        )

        camera_nome = getattr(
            camera_escolhida,
            "nome",
            "Camera"
        )

        chave = criar_chave_incidente(
            camera_id,
            matricula,
            epi
        )

        chaves_detectadas.add(
            chave
        )

        processar_incidente(
            camera_id=camera_id,
            camera_nome=camera_nome,
            ambiente=ambiente,
            matricula=matricula,
            operador=operador,
            tipo_infracao=epi,
            severidade="ALTA",
            frame=frame_escolhido
        )

    # Remove/reset incidentes que deixaram de existir.
    atualizar_incidentes_ausentes(
        chaves_detectadas
    )


# ============================================================
# CALCULAR SEVERIDADE
# ============================================================

def calcular_severidade_epi(
    status_epis
):

    if not status_epis:

        return "NORMAL"

    faltando = any(
        not presente
        for presente
        in status_epis.values()
    )

    if faltando:

        return "ALTA"

    return "NORMAL"


# ============================================================
# PREPARAR FRAME PARA GRADE
# ============================================================

def preparar_frame(
    camera,
    frame,
    largura,
    altura
):

    frame = cv2.resize(
        frame,
        (
            largura,
            altura
        )
    )

    cv2.rectangle(
        frame,
        (0, 0),
        (largura, 40),
        (25, 25, 25),
        -1
    )

    cv2.putText(
        frame,
        camera.nome,
        (12, 27),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    return frame


# ============================================================
# CRIAR GRADE
# ============================================================

def criar_grade(
    frames
):

    quantidade = len(
        frames
    )

    if quantidade == 0:

        return None

    if quantidade == 1:

        colunas = 1

        largura = 600

        altura = 450

    elif quantidade <= 4:

        colunas = 2

        largura = 480

        altura = 360

    else:

        colunas = 3

        largura = 380

        altura = 285

    linhas = math.ceil(
        quantidade
        / colunas
    )

    imagens = []

    for (
        camera,
        frame
    ) in frames:

        imagens.append(
            preparar_frame(
                camera,
                frame,
                largura,
                altura
            )
        )

    while (
        len(imagens)
        < linhas * colunas
    ):

        imagens.append(
            np.zeros(
                (
                    altura,
                    largura,
                    3
                ),
                dtype=np.uint8
            )
        )

    grade_linhas = []

    indice = 0

    for _ in range(
        linhas
    ):

        grade_linhas.append(
            np.hstack(
                imagens[
                    indice:
                    indice + colunas
                ]
            )
        )

        indice += colunas

    return np.vstack(
        grade_linhas
    )


# ============================================================
# PAINEL CENTRAL
# ============================================================

def criar_painel(
    altura,
    cameras,
    status_epis=None,
    operador="Buscando Biometria...",
    severidade="NORMAL"
):

    largura = getattr(
        config,
        "LARGURA_PAINEL_CENTRAL",
        330
    )

    painel = np.zeros(
        (altura, largura, 3),
        dtype=np.uint8
    )

    painel[:] = (28, 28, 28)

    # ========================================================
    # CABECALHO
    # ========================================================

    cv2.putText(
        painel,
        "STATUS DOS EPIs",
        (16, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.line(
        painel,
        (16, 40),
        (largura - 16, 40),
        (80, 80, 80),
        1
    )

    # ========================================================
    # OPERADOR
    # ========================================================

    cv2.putText(
        painel,
        "OPERADOR",
        (16, 62),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
        (160, 160, 160),
        1,
        cv2.LINE_AA
    )

    operador_tela = str(operador)

    if len(operador_tela) > 30:
        operador_tela = operador_tela[:30] + "..."

    cv2.putText(
        painel,
        operador_tela,
        (16, 84),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )

    # ========================================================
    # SEVERIDADE
    # ========================================================

    cv2.putText(
        painel,
        "SEVERIDADE",
        (16, 108),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
        (160, 160, 160),
        1,
        cv2.LINE_AA
    )

    if severidade == "NORMAL":
        cor_severidade = (0, 200, 0)
    elif severidade == "CRITICA":
        cor_severidade = (0, 0, 255)
    else:
        cor_severidade = (0, 80, 255)

    cv2.putText(
        painel,
        severidade,
        (16, 132),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        cor_severidade,
        2,
        cv2.LINE_AA
    )

    # ========================================================
    # ESTADO
    # ========================================================

    cv2.putText(
        painel,
        "ESTADO",
        (16, 158),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
        (160, 160, 160),
        1,
        cv2.LINE_AA
    )

    if estado_sistema.fase_execucao == config.ESTADO_CALIBRACAO_AMBIENTE:
        texto_estado = "ANALISE DO AMBIENTE"
        cor_estado = (0, 220, 255)

    elif estado_sistema.fase_execucao == config.ESTADO_CONFIGURACAO_EPI:
        texto_estado = "CONFIGURACAO EPI"
        cor_estado = (0, 220, 255)

    else:
        texto_estado = "MONITORAMENTO"
        cor_estado = (0, 200, 0)

    cv2.putText(
        painel,
        texto_estado,
        (16, 182),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        cor_estado,
        2,
        cv2.LINE_AA
    )

    cv2.line(
        painel,
        (16, 196),
        (largura - 16, 196),
        (80, 80, 80),
        1
    )

    # ========================================================
    # EPIs OBRIGATORIOS
    # ========================================================

    cv2.putText(
        painel,
        "EPIs OBRIGATORIOS",
        (16, 218),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
        (160, 160, 160),
        1,
        cv2.LINE_AA
    )

    epis_obrigatorios = list(
        getattr(
            config,
            "EPIS_OBRIGATORIOS",
            []
        )
    )

    if status_epis is None:
        status_epis = {}

    y = 246

    if not epis_obrigatorios:

        cv2.putText(
            painel,
            "Nenhum EPI selecionado",
            (16, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (150, 150, 150),
            1,
            cv2.LINE_AA
        )

        return painel

    # Ajusta automaticamente o espacamento conforme a altura.
    espaco_disponivel = max(
        1,
        altura - y - 8
    )

    passo = min(
        38,
        max(
            22,
            espaco_disponivel // max(
                1,
                len(epis_obrigatorios)
            )
        )
    )

    for epi in epis_obrigatorios:

        if y > altura - 8:
            break

        presente = bool(
            status_epis.get(
                epi,
                False
            )
        )

        if presente:
            texto_status = "EM USO"
            cor_epi = (0, 200, 0)
        else:
            texto_status = "NAO EM USO"
            cor_epi = (0, 0, 255)

        # Nome do EPI na propria cor do status.
        cv2.putText(
            painel,
            epi,
            (16, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.39,
            cor_epi,
            2,
            cv2.LINE_AA
        )

        tamanho_status, _ = cv2.getTextSize(
            texto_status,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.34,
            1
        )

        x_status = largura - tamanho_status[0] - 16

        cv2.putText(
            painel,
            texto_status,
            (x_status, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.34,
            cor_epi,
            1,
            cv2.LINE_AA
        )

        cv2.line(
            painel,
            (16, y + 8),
            (largura - 16, y + 8),
            (60, 60, 60),
            1
        )

        y += passo

    return painel
# ============================================================
# PERFIS DE AMBIENTE + IDENTIDADE DE CÂMERAS - ETAPAS 3 E 4
# ============================================================

def _tipo_rede(tipo):
    return str(tipo or "").lower() != "usb"


def _referencia_legada(item):
    referencia = item.get("referencia_legada")
    if isinstance(referencia, dict):
        return referencia
    referencia = item.get("referencia")
    return referencia if isinstance(referencia, dict) else {}


def criar_referencias_cameras(cameras):
    """
    Cria referências persistentes por camera_uid.

    A descoberta/abertura continua sendo a mesma das ETAPAS 1-3.
    Aqui apenas cadastramos as fontes que o usuário já escolheu.
    """
    referencias = []
    tem_usb = any(not camera.tipo_rede for camera in cameras.values())
    dispositivos_usb = (
        camera_registry.enumerar_dispositivos_usb()
        if tem_usb
        else []
    )

    for camera_id, camera in sorted(cameras.items()):
        if camera.tipo_rede:
            dados_config = getattr(config, "CAMERAS", {}).get(
                camera_id,
                {}
            )
            tipo = str(dados_config.get("tipo", "wifi")).lower()
            cadastro = camera_registry.obter_ou_registrar_rede_selecionada(
                dados_config=dados_config,
                nome=camera.nome,
                config_index_legado=int(camera_id),
            )
            camera.camera_uid = cadastro["camera_uid"]
            camera.status_identidade = camera_registry.IDENTIFICADA
            referencias.append({
                "camera_uid": cadastro["camera_uid"],
                "tipo": tipo,
                "nome": camera.nome,
                "referencia_legada": {
                    "config_index": int(camera_id)
                },
            })
        else:
            indice = int(camera.fonte)
            cadastro = camera_registry.obter_ou_registrar_usb_selecionada(
                indice=indice,
                nome=camera.nome,
                dispositivos=dispositivos_usb,
            )
            camera.camera_uid = cadastro["camera_uid"]
            camera.status_identidade = camera_registry.IDENTIFICADA
            referencias.append({
                "camera_uid": cadastro["camera_uid"],
                "tipo": "usb",
                "nome": camera.nome,
                "referencia_legada": {
                    "indice": indice
                },
            })

    return referencias


def selecionar_cameras_abertas(cameras):
    if not cameras:
        return {}

    print()
    print("==========================================")
    print(" CAMERAS DISPONIVEIS PARA O AMBIENTE")
    print("==========================================")

    ids = []
    for camera_id, camera in sorted(cameras.items()):
        ids.append(camera_id)
        tipo = "WIFI/IP" if camera.tipo_rede else "USB"
        print(f"[{camera_id}] {camera.nome} - {tipo}")

    print()
    print(
        "Informe os IDs separados por virgula. "
        "ENTER seleciona todas as cameras abertas."
    )

    while True:
        resposta = input("Cameras do ambiente: ").strip()

        if not resposta:
            selecionados = set(ids)
            break

        try:
            selecionados = {
                int(parte.strip())
                for parte in resposta.split(",")
                if parte.strip()
            }
        except ValueError:
            print("⚠️ Use apenas IDs numericos separados por virgula.")
            continue

        invalidos = selecionados.difference(ids)
        if invalidos:
            print(
                "⚠️ IDs indisponiveis: "
                + ", ".join(str(item) for item in sorted(invalidos))
            )
            continue

        if not selecionados:
            print("⚠️ Selecione ao menos uma camera.")
            continue

        break

    resultado = {}

    for camera_id, camera in list(cameras.items()):
        if camera_id in selecionados:
            resultado[camera_id] = camera
        else:
            camera.liberar()

    return resultado


def ativar_perfil_runtime(perfil):
    global perfil_ativo
    global estado_sistema

    perfil_ativo = perfil

    config.aplicar_perfil_runtime(perfil)

    estado_sistema.ativar_ambiente_perfil(
        ambiente_id=perfil["ambiente_id"],
        nome=perfil["nome"],
        calibrado=perfil["calibrado"],
        cameras_associadas=perfil.get("cameras", []),
        epis_obrigatorios=perfil.get("epis_obrigatorios", []),
        objetos_globais=perfil.get("objetos_globais", {})
    )

    estado_sistema.definir_fase(
        config.obter_estado_inicial()
    )


def registrar_camera_esperada(
    camera_id,
    nome,
    tipo,
    online=False,
    camera_uid=None,
    status_identidade=None,
    indice_runtime=None,
):
    estado_sistema.registrar_camera(
        camera_id=camera_id,
        nome=nome,
        tipo=tipo,
        ativa=online,
        status=(
            CAMERA_ONLINE
            if online
            else CAMERA_OFFLINE
        ),
        camera_uid=camera_uid,
        status_identidade=status_identidade,
        indice_runtime=indice_runtime,
    )


def _id_estado_camera(item, posicao):
    legado = _referencia_legada(item)
    for chave in ("indice", "config_index"):
        valor = legado.get(chave)
        if isinstance(valor, int):
            return valor
    return MAX_INDICES_CAMERA + posicao


def _mostrar_usb_disponiveis(dispositivos):
    if not dispositivos:
        print("Nenhum dispositivo USB enumerado pelo DirectShow.")
        return

    for item in dispositivos:
        detalhes = []
        if item.get("vid") and item.get("pid"):
            detalhes.append(f"VID:{item['vid']} PID:{item['pid']}")
        if item.get("serial"):
            detalhes.append(f"serial:{item['serial']}")
        sufixo = f" ({' | '.join(detalhes)})" if detalhes else ""
        print(
            f"[{item.get('indice')}] "
            f"{item.get('nome_dispositivo') or 'Camera USB'}{sufixo}"
        )


def _selecionar_usb_manual(nome, dispositivos, mensagem):
    print()
    print(mensagem)
    _mostrar_usb_disponiveis(dispositivos)
    if not dispositivos:
        return None

    indices = {item.get("indice") for item in dispositivos}
    while True:
        resposta = input(
            f"Indice USB para '{nome}' (ENTER mantem OFFLINE): "
        ).strip()
        if not resposta:
            return None
        try:
            indice = int(resposta)
        except ValueError:
            print("⚠️ Informe um indice numerico.")
            continue
        if indice in indices:
            return indice
        print("⚠️ Indice USB nao esta na lista enumerada.")


def _selecionar_config_rede_manual(nome, mensagem):
    configuracoes = getattr(config, "CAMERAS", {})
    opcoes = {
        camera_id: dados
        for camera_id, dados in configuracoes.items()
        if isinstance(dados, dict)
        and _tipo_rede(dados.get("tipo", "wifi"))
    }

    print()
    print(mensagem)
    if not opcoes:
        print("Nenhuma configuracao WiFi/RTSP esta disponivel.")
        return None, None

    for camera_id, dados in sorted(opcoes.items()):
        fonte = dados.get("fonte") or "sem fonte"
        porta = dados.get("porta")
        if porta is not None:
            print(f"[{camera_id}] {dados.get('nome', 'Camera')} - porta {porta} - {fonte}")
        else:
            print(f"[{camera_id}] {dados.get('nome', 'Camera')} - {fonte}")

    while True:
        resposta = input(
            f"Configuracao para '{nome}' (ENTER mantem OFFLINE): "
        ).strip()
        if not resposta:
            return None, None
        try:
            camera_id = int(resposta)
        except ValueError:
            print("⚠️ Informe um ID numerico.")
            continue
        if camera_id in opcoes:
            return camera_id, opcoes[camera_id]
        print("⚠️ Configuracao inexistente.")


def _migrar_referencia_legada_interativa(
    perfil,
    indice_item,
    item,
    dispositivos_usb,
):
    """
    Migração conservadora ETAPA 3 -> ETAPA 4.

    Nunca grava camera_uid apenas por carregar o perfil. A associação
    legada precisa ser confirmada explicitamente pelo usuário.
    """
    tipo = str(item.get("tipo", "usb")).lower()
    nome = str(item.get("nome", "Camera"))
    legado = _referencia_legada(item)

    print()
    print("==========================================")
    print(" MIGRACAO DE REFERENCIA DE CAMERA")
    print("==========================================")
    print(f"Camera do perfil: {nome}")
    print("Este perfil ainda usa referencia da ETAPA 3.")

    if tipo == "usb":
        indice_antigo = legado.get("indice")
        print(f"Referencia USB legada: indice {indice_antigo}")
        indice = _selecionar_usb_manual(
            nome,
            dispositivos_usb,
            "Confirme explicitamente qual dispositivo fisico pertence ao ambiente.",
        )
        if indice is None:
            return None

        cadastro = camera_registry.registrar_usb_selecionada(
            indice=indice,
            nome=nome,
            dispositivos=dispositivos_usb,
        )
    else:
        config_antigo = legado.get("config_index")
        print(f"Referencia de rede legada: config_index {config_antigo}")
        config_id, dados = _selecionar_config_rede_manual(
            nome,
            "Confirme explicitamente qual entrada logica WiFi/RTSP pertence ao ambiente.",
        )
        if dados is None:
            return None

        cadastro = camera_registry.registrar_rede_selecionada(
            dados_config=dados,
            nome=nome,
            config_index_legado=config_id,
        )

    ambientes.persistir_camera_uid(
        perfil=perfil,
        indice_camera=indice_item,
        camera_uid=cadastro["camera_uid"],
        referencia_legada=legado,
    )
    print(f"✅ camera_uid persistido para {nome} mediante confirmacao explicita.")
    return cadastro["camera_uid"]


def _reassociar_uid_interativamente(
    camera_uid,
    nome,
    tipo,
    dispositivos_usb,
):
    resposta = input(
        f"Deseja reassociar '{nome}' explicitamente? [s/N]: "
    ).strip().lower()
    if resposta not in ("s", "sim", "y", "yes"):
        return False

    if tipo == "usb":
        indice = _selecionar_usb_manual(
            nome,
            dispositivos_usb,
            "Selecione a fonte USB que deve assumir o camera_uid existente.",
        )
        if indice is None:
            return False
        camera_registry.registrar_usb_selecionada(
            indice=indice,
            nome=nome,
            dispositivos=dispositivos_usb,
            camera_uid=camera_uid,
        )
        return True

    config_id, dados = _selecionar_config_rede_manual(
        nome,
        "Selecione a configuracao de conexao da mesma camera logica.",
    )
    if dados is None:
        return False
    camera_registry.registrar_rede_selecionada(
        dados_config=dados,
        nome=nome,
        camera_uid=camera_uid,
        config_index_legado=config_id,
    )
    return True


def _abrir_usb_por_uid(
    item,
    camera_uid,
    nome,
    dispositivos_usb,
    posicao,
):
    cadastro = camera_registry.obter_camera(camera_uid)
    camera_id_estado = _id_estado_camera(item, posicao)

    if cadastro is None:
        print(f"⚠️ {nome}: camera_uid nao existe no cadastro global.")
        if _reassociar_uid_interativamente(
            camera_uid, nome, "usb", dispositivos_usb
        ):
            cadastro = camera_registry.obter_camera(camera_uid)
        else:
            registrar_camera_esperada(
                camera_id_estado, nome, "usb", online=False,
                camera_uid=camera_uid,
                status_identidade=camera_registry.INDISPONIVEL,
            )
            return None, None

    resolucao = camera_registry.resolver_usb(
        cadastro,
        dispositivos=dispositivos_usb,
    )

    if resolucao["status_identidade"] != camera_registry.IDENTIFICADA:
        print(
            f"⚠️ {nome}: identidade {resolucao['status_identidade']}. "
            f"{resolucao.get('motivo', '')}"
        )
        if _reassociar_uid_interativamente(
            camera_uid, nome, "usb", dispositivos_usb
        ):
            cadastro = camera_registry.obter_camera(camera_uid)
            resolucao = camera_registry.resolver_usb(
                cadastro,
                dispositivos=dispositivos_usb,
            )

    if resolucao["status_identidade"] != camera_registry.IDENTIFICADA:
        registrar_camera_esperada(
            camera_id_estado, nome, "usb", online=False,
            camera_uid=camera_uid,
            status_identidade=resolucao["status_identidade"],
        )
        return None, None

    indice = resolucao.get("indice_runtime")
    if not isinstance(indice, int):
        registrar_camera_esperada(
            camera_id_estado, nome, "usb", online=False,
            camera_uid=camera_uid,
            status_identidade=camera_registry.INDISPONIVEL,
        )
        return None, None

    camera = CameraSistema(
        camera_id=indice,
        fonte=indice,
        nome=nome,
    )
    camera.camera_uid = camera_uid
    camera.status_identidade = camera_registry.IDENTIFICADA

    if camera.abrir():
        camera_registry.atualizar_ultimo_indice_usb(camera_uid, indice)
        registrar_camera_esperada(
            indice, nome, "usb", online=True,
            camera_uid=camera_uid,
            status_identidade=camera_registry.IDENTIFICADA,
            indice_runtime=indice,
        )
        return indice, camera

    # Identidade foi resolvida; falha ao abrir é conectividade/runtime,
    # não falha de identidade.
    print(f"⚠️ {nome}: identificada no indice {indice}, mas esta OFFLINE.")
    registrar_camera_esperada(
        indice, nome, "usb", online=False,
        camera_uid=camera_uid,
        status_identidade=camera_registry.IDENTIFICADA,
        indice_runtime=indice,
    )
    return None, None


def _abrir_rede_por_uid(item, camera_uid, nome, tipo, posicao):
    camera_id = _id_estado_camera(item, posicao)
    cadastro = camera_registry.obter_camera(camera_uid)

    if cadastro is None:
        print(f"⚠️ {nome}: camera_uid de rede nao existe no cadastro global.")
        if _reassociar_uid_interativamente(
            camera_uid, nome, tipo, []
        ):
            cadastro = camera_registry.obter_camera(camera_uid)
        else:
            registrar_camera_esperada(
                camera_id, nome, tipo, online=False,
                camera_uid=camera_uid,
                status_identidade=camera_registry.INDISPONIVEL,
            )
            return None, None

    # Para rede, camera_uid identifica a entrada lógica. A conectividade
    # é um estado separado; IP, porta e caminho podem mudar explicitamente
    # sem alterar camera_uid.
    conexao = cadastro.get("conexao") or {}
    fonte = conexao.get("fonte")

    if not fonte:
        print(f"⚠️ {nome}: identidade conhecida, mas sem conexao configurada.")
        if _reassociar_uid_interativamente(
            camera_uid, nome, tipo, []
        ):
            cadastro = camera_registry.obter_camera(camera_uid) or {}
            conexao = cadastro.get("conexao") or {}
            fonte = conexao.get("fonte")

    if not fonte:
        registrar_camera_esperada(
            camera_id, nome, tipo, online=False,
            camera_uid=camera_uid,
            status_identidade=camera_registry.IDENTIFICADA,
        )
        return None, None

    camera = CameraSistema(
        camera_id=camera_id,
        fonte=fonte,
        nome=nome,
    )
    camera.camera_uid = camera_uid
    camera.status_identidade = camera_registry.IDENTIFICADA

    if camera.abrir():
        registrar_camera_esperada(
            camera_id, nome, tipo, online=True,
            camera_uid=camera_uid,
            status_identidade=camera_registry.IDENTIFICADA,
        )
        return camera_id, camera

    print(
        f"⚠️ {nome}: camera identificada, mas o stream esta OFFLINE."
    )
    print(
        "   A identidade foi preservada; falha de stream nao "
        "altera o camera_uid."
    )

    # Mudança de IP/porta/caminho só ocorre mediante ação explícita.
    if _reassociar_uid_interativamente(
        camera_uid, nome, tipo, []
    ):
        cadastro = camera_registry.obter_camera(camera_uid) or {}
        fonte_nova = (cadastro.get("conexao") or {}).get("fonte")
        if fonte_nova:
            camera = CameraSistema(
                camera_id=camera_id,
                fonte=fonte_nova,
                nome=nome,
            )
            camera.camera_uid = camera_uid
            camera.status_identidade = camera_registry.IDENTIFICADA
            if camera.abrir():
                registrar_camera_esperada(
                    camera_id, nome, tipo, online=True,
                    camera_uid=camera_uid,
                    status_identidade=camera_registry.IDENTIFICADA,
                )
                return camera_id, camera

    registrar_camera_esperada(
        camera_id, nome, tipo, online=False,
        camera_uid=camera_uid,
        status_identidade=camera_registry.IDENTIFICADA,
    )
    return None, None


def abrir_cameras_do_perfil(perfil):
    cameras_abertas = {}
    referencias = perfil.get("cameras", [])
    dispositivos_usb = camera_registry.enumerar_dispositivos_usb()
    perfil_migrado = False

    print()
    print("==========================================")
    print(f" CAMERAS DO AMBIENTE: {perfil.get('nome', '')}")
    print("==========================================")

    for posicao, item in enumerate(referencias):
        if not isinstance(item, dict):
            continue

        tipo = str(item.get("tipo", "usb")).lower()
        nome = str(item.get("nome", "Camera"))
        camera_uid = item.get("camera_uid")

        if not isinstance(camera_uid, str) or not camera_uid.strip():
            camera_uid = _migrar_referencia_legada_interativa(
                perfil,
                posicao,
                item,
                dispositivos_usb,
            )
            if camera_uid:
                perfil_migrado = True
            else:
                camera_id = _id_estado_camera(item, posicao)
                registrar_camera_esperada(
                    camera_id, nome, tipo, online=False,
                    camera_uid=None,
                    status_identidade=camera_registry.INDISPONIVEL,
                )
                continue

        if tipo == "usb":
            camera_id, camera = _abrir_usb_por_uid(
                item,
                camera_uid,
                nome,
                dispositivos_usb,
                posicao,
            )
        else:
            camera_id, camera = _abrir_rede_por_uid(
                item,
                camera_uid,
                nome,
                tipo,
                posicao,
            )

        if camera is not None and camera_id is not None:
            cameras_abertas[camera_id] = camera

    if perfil_migrado:
        # Atualiza somente o estado operacional após migração explicitamente
        # confirmada. Não há regravação automática por mera leitura.
        ativar_perfil_runtime(perfil)
        for camera_id, camera in cameras_abertas.items():
            registrar_camera_esperada(
                camera_id=camera_id,
                nome=camera.nome,
                tipo=("wifi" if camera.tipo_rede else "usb"),
                online=True,
                camera_uid=camera.camera_uid,
                status_identidade=camera.status_identidade,
                indice_runtime=(camera_id if not camera.tipo_rede else None),
            )

    print("==========================================")
    print(
        f"Cameras ONLINE: {len(cameras_abertas)} "
        f"de {len(referencias)}"
    )
    print("==========================================")
    print()

    return cameras_abertas


def selecionar_ambiente_startup():
    perfis = ambientes.listar_perfis()
    mostrar_legado = (
        ambientes.legado_disponivel(config)
        and not ambientes.existe_perfil_migrado_legado(perfis)
    )

    opcoes = []

    print()
    print("==========================================")
    print(" PERFIS DE AMBIENTE")
    print("==========================================")

    for perfil in perfis:
        opcoes.append(("perfil", perfil))
        print(f"[{len(opcoes)}] {perfil['nome']}")

    if mostrar_legado:
        opcoes.append(("legado", None))
        print(f"[{len(opcoes)}] Ambiente Principal (legado)")

    opcoes.append(("novo", None))
    print(f"[{len(opcoes)}] + Novo ambiente")
    print("==========================================")

    while True:
        resposta = input("Selecione o ambiente: ").strip()

        try:
            indice = int(resposta) - 1
        except ValueError:
            print("⚠️ Informe o numero da opcao.")
            continue

        if 0 <= indice < len(opcoes):
            return opcoes[indice]

        print("⚠️ Opcao invalida.")


def solicitar_nome_novo_ambiente():
    perfis = ambientes.listar_perfis()

    while True:
        nome = input("Nome do novo ambiente: ").strip()

        if not nome:
            print("⚠️ O nome do ambiente nao pode ficar vazio.")
            continue

        if not ambientes.nome_ambiente_disponivel(nome, perfis):
            print("⚠️ Ja existe um ambiente com esse nome.")
            continue

        return nome


def preparar_startup_ambiente():
    tipo_opcao, perfil = selecionar_ambiente_startup()

    # --------------------------------------------------------
    # PERFIL EXISTENTE
    # --------------------------------------------------------
    if tipo_opcao == "perfil":
        ativar_perfil_runtime(perfil)
        cameras = abrir_cameras_do_perfil(perfil)

        if not cameras:
            print(
                "❌ Nenhuma camera associada ao ambiente "
                "conseguiu abrir. Monitoramento nao iniciado."
            )
            return None

        if len(cameras) < len(perfil.get("cameras", [])):
            print(
                "⚠️ Ambiente operando em modo degradado: "
                "uma ou mais cameras estao OFFLINE."
            )

        return cameras

    # --------------------------------------------------------
    # NOVO AMBIENTE OU MIGRAÇÃO DO LEGADO
    # Reutiliza integralmente a descoberta atual de cameras.
    # --------------------------------------------------------
    cameras_descobertas = descobrir_cameras()

    if not cameras_descobertas:
        print(
            "❌ Nenhuma camera disponivel. "
            "Nao e possivel preparar o ambiente."
        )
        return None

    cameras = selecionar_cameras_abertas(
        cameras_descobertas
    )

    if not cameras:
        print("❌ Nenhuma camera foi associada ao ambiente.")
        return None

    referencias = criar_referencias_cameras(cameras)

    if tipo_opcao == "legado":
        perfil = ambientes.criar_perfil_legado(
            config,
            referencias
        )

        if perfil is None:
            print("❌ Nao foi possivel carregar o ambiente legado.")
            for camera in cameras.values():
                camera.liberar()
            return None

        try:
            caminho = ambientes.salvar_perfil(perfil)
        except Exception as erro:
            print(f"❌ Erro ao migrar ambiente legado: {erro}")
            for camera in cameras.values():
                camera.liberar()
            return None

        print(f"✅ Ambiente legado migrado para: {caminho}")
        print(
            "ℹ️ configuracoes/ambiente.json e "
            "configuracoes/epis.json foram preservados."
        )

        ativar_perfil_runtime(perfil)

    else:
        nome = solicitar_nome_novo_ambiente()
        perfil = ambientes.criar_perfil(
            nome=nome,
            cameras=referencias,
            epis_obrigatorios=[],
            objetos_globais={},
            calibrado=False,
            origem=ambientes.ORIGEM_NOVO,
        )
        ativar_perfil_runtime(perfil)

    for camera_id, camera in cameras.items():
        registrar_camera_esperada(
            camera_id=camera_id,
            nome=camera.nome,
            tipo=("wifi" if camera.tipo_rede else "usb"),
            online=True,
            camera_uid=camera.camera_uid,
            status_identidade=(
                camera.status_identidade
                or camera_registry.IDENTIFICADA
            ),
            indice_runtime=(camera_id if not camera.tipo_rede else None),
        )

    return cameras


# ============================================================
# MAIN
# ============================================================

def main():

    global estado_sistema

    cameras = preparar_startup_ambiente()

    if cameras is None:
        return

    contador_frames = 0
    configuracao_iniciada = False

    if estado_sistema.fase_execucao == config.ESTADO_MONITORAMENTO:
        carregar_modelo_epi()
        carregar_modelo_pose()

    try:

        while True:

            contador_frames += 1

            frames = (
                capturar_frames_sincronizados(cameras)
                if cameras
                else []
            )

            status_epis = {}
            operador = "Buscando Biometria..."
            severidade = "NORMAL"

            # =================================================
            # CALIBRACAO
            # =================================================

            if estado_sistema.fase_execucao == config.ESTADO_CALIBRACAO_AMBIENTE:

                if frames:

                    nova_analise = (
                        contador_frames == 1
                        or contador_frames % INTERVALO_ANALISE_AMBIENTE == 0
                    )

                    if nova_analise:
                        frames_visuais = analisar_ambiente_cameras(frames)
                    else:
                        frames_visuais = desenhar_objetos_existentes(frames)

                    if (
                        contador_frames >= FRAMES_ANTES_CONFIGURACAO
                        and not configuracao_iniciada
                    ):

                        tem_objeto = any(
                            camera.total_objetos > 0
                            for camera in cameras.values()
                        )

                        if tem_objeto:

                            configuracao_iniciada = True

                            frames_config = capturar_frames_sincronizados(
                                cameras
                            )

                            analisar_ambiente_cameras(
                                frames_config
                            )

                            sucesso = configurar_ambiente(
                                frames_config
                            )

                            if not sucesso:
                                configuracao_iniciada = False

                else:
                    frames_visuais = []

            # =================================================
            # MONITORAMENTO
            # =================================================

            elif estado_sistema.fase_execucao == config.ESTADO_MONITORAMENTO:

                frames_visuais = frames

                if frames:
                    status_epis = analisar_epis_cameras(
                        frames
                    )

                    severidade = calcular_severidade_epi(
                        status_epis
                    )

                    processar_incidentes_epis(
                        status_epis,
                        frames,
                        operador
                    )

                    atualizar_notificacoes(
                        status_epis=status_epis,
                        frames=frames,
                        operador=operador,
                        severidade=severidade
                    )

                    # ETAPA 5: Pose e tracking são processados somente
                    # após o pipeline legado de EPI/incidentes, para que
                    # eventual overlay de debug nunca contamine evidências.
                    frames_visuais = processar_pose_cameras(frames)

                    # ETAPA 6: usa as detecções preservadas da mesma
                    # inferência best.pt e os tracks observados neste frame.
                    processar_associacoes_epi_pessoa(frames)
                else:
                    estado_sistema.atualizar_latencia_pose(None)
                    for camera_id in list(cameras.keys()):
                        estado_sistema.limpar_associacoes_epi_camera(camera_id)

            # =================================================
            # CONFIGURACAO DE EPI
            # =================================================

            else:
                frames_visuais = frames

            # =================================================
            # GRADE
            # =================================================

            grade = criar_grade(
                frames_visuais
            )

            if grade is not None:

                painel = criar_painel(
                    grade.shape[0],
                    cameras,
                    status_epis=status_epis,
                    operador=operador,
                    severidade=severidade
                )

                tela = np.hstack(
                    (
                        grade,
                        painel
                    )
                )

            else:

                tela = np.zeros(
                    (
                        500,
                        900,
                        3
                    ),
                    dtype=np.uint8
                )

                cv2.putText(
                    tela,
                    "PROCURANDO CAMERAS...",
                    (250, 250),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 220, 255),
                    2,
                    cv2.LINE_AA
                )

            cv2.imshow(
                getattr(
                    config,
                    "NOME_JANELA",
                    "FIAP x SPI Challenge 2026"
                ),
                tela
            )

            tecla = cv2.waitKey(1) & 0xFF

            if tecla == ord("q"):
                break

    finally:

        try:
            encerrar_notificacoes()
        except Exception as erro:
            print(
                f"⚠️ Erro ao encerrar notificações: {erro}"
            )

        for camera in list(
            cameras.values()
        ):
            encerrar_tracking_camera(camera.camera_id)
            camera.liberar()

        cv2.destroyAllWindows()


# ============================================================
# EXECUCAO
# ============================================================

if __name__ == "__main__":
    main()
