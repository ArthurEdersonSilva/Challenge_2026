import os
import json
import numpy as np


# ============================================================
# MODELO DE VISÃO COMPUTACIONAL
# ============================================================

PATH_MODELO = "best.pt"

CONFIDENCIA_MINIMA = 0.5

TAMANHO_IMAGEM = 640


# ============================================================
# CÂMERAS
# ============================================================

LARGURA_CAM = 640
ALTURA_CAM = 480

MAX_CAMERAS = 66


# ============================================================
# EPIs DISPONÍVEIS
# ============================================================

EPIS_DISPONIVEIS = [
    "Capacete",
    "Óculos",
    "Máscara",
    "Luvas",
    "Protetor auricular",
    "Colete",
]


# ============================================================
# CONFIGURAÇÃO PADRÃO DOS EPIs
# ============================================================

EPIS_PADRAO = [
    "Capacete",
    "Óculos",
    "Máscara",
    "Luvas",
    "Protetor auricular",
    "Colete",
]


# ============================================================
# ZONA DE RISCO PADRÃO
#
# Cada câmera poderá possuir sua própria zona.
# ============================================================

PONTOS_ZONA_RISCO_PADRAO = np.array(
    [
        [100, 400],
        [250, 200],
        [450, 200],
        [600, 400],
    ],
    dtype=np.int32
)


# Mantido para compatibilidade com códigos antigos.
PONTOS_ZONA_RISCO = PONTOS_ZONA_RISCO_PADRAO.copy()


# ============================================================
# CAMERAS
#
# Estrutura:
#
# CAMERAS = {
#     0: {
#         "nome": "...",
#         "fonte": 0,
#         "ativa": True,
#         "ambiente": "...",
#         "epis_obrigatorios": [...],
#         "pontos_zona": [...]
#     }
# }
#
# A câmera 0 continua sendo a câmera real utilizada agora.
# As demais ficam desativadas até serem configuradas.
# ============================================================

CAMERAS = {}


for camera_id in range(MAX_CAMERAS):

    CAMERAS[camera_id] = {
        "nome": f"Camera {camera_id + 1:02d}",

        # Câmera 0 utiliza webcam.
        # As demais começam sem fonte válida.
        "fonte": camera_id if camera_id == 0 else camera_id,

        # Somente a câmera 0 começa ativa.
        "ativa": True if camera_id == 0 else False,

        "ambiente": (
            "Ambiente principal"
            if camera_id == 0
            else f"Ambiente {camera_id + 1:02d}"
        ),

        # Por padrão, todos os EPIs são obrigatórios.
        "epis_obrigatorios": EPIS_PADRAO.copy(),

        # Cada câmera possui sua própria zona.
        "pontos_zona": PONTOS_ZONA_RISCO_PADRAO.copy(),

        # Maquinário configurado naquela câmera.
        "maquinarios": [],
    }


# ============================================================
# EXEMPLO DE CONFIGURAÇÃO DAS CÂMERAS
#
# Quando tivermos as câmeras reais, basta alterar aqui.
#
# Exemplo:
#
# CAMERAS[1] = {
#     "nome": "Camera 02",
#     "fonte": "rtsp://usuario:senha@ip:554/stream",
#     "ativa": True,
#     "ambiente": "Linha de Produção",
#     "epis_obrigatorios": [
#         "Capacete",
#         "Luvas",
#     ],
#     "pontos_zona": np.array([
#         [50, 400],
#         [200, 200],
#         [500, 200],
#         [630, 400],
#     ], dtype=np.int32),
#     "maquinarios": [2, 4],
# }
# ============================================================


# ============================================================
# MAQUINÁRIO
# ============================================================

PATH_CONFIG_MAQUINARIOS = os.path.join(
    "configuracoes",
    "maquinarios.json"
)


def garantir_pasta_configuracoes():

    pasta = os.path.dirname(
        PATH_CONFIG_MAQUINARIOS
    )

    os.makedirs(
        pasta,
        exist_ok=True
    )


def carregar_maquinarios():

    garantir_pasta_configuracoes()

    if not os.path.exists(
        PATH_CONFIG_MAQUINARIOS
    ):
        return {}

    try:

        with open(
            PATH_CONFIG_MAQUINARIOS,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(arquivo)

            return dados

    except Exception as erro:

        print(
            f"⚠️ Erro ao carregar "
            f"configuração de maquinários: {erro}"
        )

        return {}


def salvar_maquinarios(
    configuracao_maquinarios
):

    garantir_pasta_configuracoes()

    try:

        with open(
            PATH_CONFIG_MAQUINARIOS,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                configuracao_maquinarios,
                arquivo,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as erro:

        print(
            f"❌ Erro ao salvar "
            f"configuração de maquinários: {erro}"
        )

        return False


# Carrega configuração persistente.
MAQUINARIOS = carregar_maquinarios()


# ============================================================
# INCIDENTES
# ============================================================

PATH_LOGS_CSV = "historico_incidentes.csv"

PASTA_PROVAS_INCIDENTES = "provas_incidentes"


# ============================================================
# ALERTA SONORO
# ============================================================

FREQ_BEEP_CRITICO = 1500

DURACAO_BEEP_CRITICO = 400


# ============================================================
# BIOMETRIA
# ============================================================

PATH_BANCO_BIOMETRIA = "banco_biometria"

PATH_DADOS_OPERADORES = os.path.join(
    PATH_BANCO_BIOMETRIA,
    "dados_operadores.csv"
)

MODELO_FACE = "Facenet"

# Intervalo mínimo entre tentativas de
# reconhecimento da mesma pessoa.
INTERVALO_BIOMETRIA_SEGUNDOS = 3.0


# ============================================================
# POSE / ERGONOMIA
# ============================================================

PATH_MODELO_POSE = "yolov8n-pose.pt"

CONFIANCA_POSE = 0.5

LIMITE_FRAMES_FADIGA = 90

LIMIAR_POSTURA_INADEQUADA = 85


# ============================================================
# TRACKING
# ============================================================

TRACKING_ATIVO = True

# Tempo em segundos para manter uma pessoa
# temporariamente no sistema depois que ela
# deixa de ser detectada.
TEMPO_PERMANENCIA_TRACKING = 2.0


# ============================================================
# DETECTOR DE MAQUINÁRIO
#
# Ainda não existe um segundo modelo definido.
# Portanto, deixamos preparado sem fingir
# que o best.pt detecta máquinas.
# ============================================================

TRACKING_MAQUINARIO_ATIVO = True

PATH_MODELO_MAQUINARIO = None

CONFIANCA_MAQUINARIO = 0.5


# ============================================================
# INCIDENTES
# ============================================================

INTERVALO_REPETICAO_INCIDENTE_SEGUNDOS = 300

# 300 segundos = 5 minutos.
#
# A ideia é:
#
# primeira ocorrência
#       ↓
# registra foto
#       ↓
# incidente continua?
#       ↓
# aguarda 5 minutos
#       ↓
# nova evidência
#


# ============================================================
# INTERFACE
# ============================================================

LARGURA_SIDEBAR = 330

NOME_JANELA = "FIAP x SPI Challenge 2026"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def obter_config_camera(camera_id):

    if camera_id not in CAMERAS:

        raise ValueError(
            f"Câmera {camera_id} não está configurada."
        )

    return CAMERAS[camera_id]


def ativar_camera(
    camera_id,
    fonte=None,
    nome=None,
    ambiente=None,
    epis_obrigatorios=None
):

    if camera_id < 0 or camera_id >= MAX_CAMERAS:

        raise ValueError(
            f"O ID da câmera deve estar entre "
            f"0 e {MAX_CAMERAS - 1}."
        )

    CAMERAS[camera_id]["ativa"] = True

    if fonte is not None:
        CAMERAS[camera_id]["fonte"] = fonte

    if nome is not None:
        CAMERAS[camera_id]["nome"] = nome

    if ambiente is not None:
        CAMERAS[camera_id]["ambiente"] = ambiente

    if epis_obrigatorios is not None:
        CAMERAS[camera_id][
            "epis_obrigatorios"
        ] = epis_obrigatorios


def desativar_camera(camera_id):

    if camera_id not in CAMERAS:
        return

    CAMERAS[camera_id]["ativa"] = False


def configurar_zona_camera(
    camera_id,
    pontos
):

    if camera_id not in CAMERAS:

        raise ValueError(
            f"Câmera {camera_id} não existe."
        )

    CAMERAS[camera_id][
        "pontos_zona"
    ] = np.array(
        pontos,
        dtype=np.int32
    )


# ============================================================
# INFORMAÇÕES DO SISTEMA
# ============================================================

def mostrar_configuracao():

    cameras_ativas = sum(
        1
        for camera in CAMERAS.values()
        if camera["ativa"]
    )

    print("\n==========================================")
    print(" CONFIGURAÇÃO DO SISTEMA")
    print("==========================================")

    print(
        f"Modelo EPI: {PATH_MODELO}"
    )

    print(
        f"Confiança mínima: {CONFIDENCIA_MINIMA}"
    )

    print(
        f"Resolução: "
        f"{LARGURA_CAM}x{ALTURA_CAM}"
    )

    print(
        f"Câmeras configuradas: "
        f"{MAX_CAMERAS}"
    )

    print(
        f"Câmeras ativas: "
        f"{cameras_ativas}"
    )

    print(
        f"Banco biométrico: "
        f"{PATH_BANCO_BIOMETRIA}"
    )

    print(
        f"Log de incidentes: "
        f"{PATH_LOGS_CSV}"
    )

    print(
        f"Modelo de maquinário: "
        f"{PATH_MODELO_MAQUINARIO}"
    )

    print("==========================================\n")


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    mostrar_configuracao()