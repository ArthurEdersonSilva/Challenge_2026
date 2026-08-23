import os
import json
import numpy as np


# ============================================================
# SISTEMA
# ============================================================

NOME_JANELA = "FIAP x SPI Challenge 2026"

NOME_AMBIENTE = "Ambiente Principal"


# ============================================================
# ESTADOS DO SISTEMA
# ============================================================

ESTADO_CALIBRACAO_AMBIENTE = "CALIBRACAO_AMBIENTE"

ESTADO_CONFIGURACAO_EPI = "CONFIGURACAO_EPI"

ESTADO_MONITORAMENTO = "MONITORAMENTO"


# ============================================================
# MODELOS
# ============================================================

PATH_MODELO = "best.pt"

PATH_MODELO_POSE = "yolov8n-pose.pt"

PATH_MODELO_MAQUINARIO = None

CONFIDENCIA_MINIMA = 0.5

CONFIANCA_POSE = 0.5

CONFIANCA_MAQUINARIO = 0.5

TAMANHO_IMAGEM = 640


# ============================================================
# CÂMERAS
# ============================================================

LARGURA_CAM = 640

ALTURA_CAM = 480

MAX_CAMERAS = 66


CAMERAS = {}


for camera_id in range(MAX_CAMERAS):

    CAMERAS[camera_id] = {

        "nome": f"Camera {camera_id + 1:02d}",

        "fonte": camera_id,

        # Todas ficam disponíveis para tentativa.
        # O main.py verifica automaticamente
        # quais realmente existem e consegue abrir.
        "ativa": True,
    }


# ============================================================
# CÂMERAS RTSP
#
# Caso futuramente seja necessário adicionar uma câmera IP,
# basta substituir a fonte correspondente.
#
# Exemplo:
#
# CAMERAS[10]["fonte"] = (
#     "rtsp://usuario:senha@192.168.0.20:554/stream"
# )
# ============================================================


# ============================================================
# EPIs DISPONÍVEIS
#
# IMPORTANTE:
# Esta lista NÃO significa que todos são obrigatórios.
# São somente as opções que serão apresentadas ao usuário.
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
# EPIs OBRIGATÓRIOS
#
# Começam vazios.
#
# Depois da análise do ambiente e confirmação dos
# maquinários, o sistema perguntará ao usuário quais
# EPIs são obrigatórios.
# ============================================================

EPIS_OBRIGATORIOS = []

EPIS_CONFIGURADOS = False


# ============================================================
# CALIBRAÇÃO DO AMBIENTE
# ============================================================

AMBIENTE_CALIBRADO = False


# ============================================================
# OBJETOS GLOBAIS
#
# Os objetos pertencem ao ambiente.
#
# Um mesmo objeto poderá aparecer em várias câmeras
# sem ser considerado vários objetos diferentes.
#
# Exemplo:
#
# OBJETO_001
#   Camera 01
#   Camera 02
#   Camera 03
#
# = um único equipamento físico
# ============================================================

OBJETOS_GLOBAIS = {}


# ============================================================
# PERSISTÊNCIA
# ============================================================

PASTA_CONFIGURACOES = (
    "configuracoes"
)


PATH_CONFIG_AMBIENTE = os.path.join(
    PASTA_CONFIGURACOES,
    "ambiente.json"
)


PATH_CONFIG_EPIS = os.path.join(
    PASTA_CONFIGURACOES,
    "epis.json"
)


# ============================================================
# CRIAR PASTA DE CONFIGURAÇÃO
# ============================================================

def garantir_pasta_configuracoes():

    os.makedirs(
        PASTA_CONFIGURACOES,
        exist_ok=True
    )


# ============================================================
# SALVAR AMBIENTE
# ============================================================

def salvar_configuracao_ambiente(
    objetos_globais
):

    garantir_pasta_configuracoes()

    dados = {

        "ambiente":
            NOME_AMBIENTE,

        "calibrado":
            True,

        "objetos":
            objetos_globais,
    }

    try:

        with open(
            PATH_CONFIG_AMBIENTE,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                dados,
                arquivo,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as erro:

        print(
            f"Erro ao salvar ambiente: "
            f"{erro}"
        )

        return False


# ============================================================
# CARREGAR AMBIENTE
# ============================================================

def carregar_configuracao_ambiente():

    if not os.path.exists(
        PATH_CONFIG_AMBIENTE
    ):

        return None

    try:

        with open(
            PATH_CONFIG_AMBIENTE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            return json.load(
                arquivo
            )

    except Exception as erro:

        print(
            f"Erro ao carregar ambiente: "
            f"{erro}"
        )

        return None


# ============================================================
# SALVAR EPIs
# ============================================================

def salvar_configuracao_epis(
    epis
):

    garantir_pasta_configuracoes()

    dados = {

        "configurado":
            True,

        "epis_obrigatorios":
            epis,
    }

    try:

        with open(
            PATH_CONFIG_EPIS,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                dados,
                arquivo,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as erro:

        print(
            f"Erro ao salvar EPIs: "
            f"{erro}"
        )

        return False


# ============================================================
# CARREGAR EPIs
# ============================================================

def carregar_configuracao_epis():

    if not os.path.exists(
        PATH_CONFIG_EPIS
    ):

        return None

    try:

        with open(
            PATH_CONFIG_EPIS,
            "r",
            encoding="utf-8"
        ) as arquivo:

            return json.load(
                arquivo
            )

    except Exception as erro:

        print(
            f"Erro ao carregar EPIs: "
            f"{erro}"
        )

        return None


# ============================================================
# ZONA DE RISCO
#
# A zona continua por câmera porque cada câmera possui
# perspectiva diferente do mesmo ambiente.
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


PONTOS_ZONAS = {}


for camera_id in range(MAX_CAMERAS):

    PONTOS_ZONAS[
        camera_id
    ] = (
        PONTOS_ZONA_RISCO_PADRAO.copy()
    )


# Compatibilidade com partes antigas do projeto.
PONTOS_ZONA_RISCO = (
    PONTOS_ZONA_RISCO_PADRAO.copy()
)


# ============================================================
# INCIDENTES
# ============================================================

PATH_LOGS_CSV = (
    "historico_incidentes.csv"
)


PASTA_PROVAS_INCIDENTES = (
    "provas_incidentes"
)


# ------------------------------------------------------------
# 5 MINUTOS ENTRE FOTOS DO MESMO INCIDENTE
# ------------------------------------------------------------

INTERVALO_REPETICAO_INCIDENTE_SEGUNDOS = 300


# ------------------------------------------------------------
# INFRAÇÃO PRECISA PERSISTIR POR ALGUNS FRAMES
# ------------------------------------------------------------

FRAMES_CONFIRMACAO_INFRACAO = 5


# ------------------------------------------------------------
# TEMPO PARA CONSIDERAR QUE UMA INFRAÇÃO DESAPARECEU
# ------------------------------------------------------------

TEMPO_RESET_INCIDENTE_SEGUNDOS = 1.0


# ============================================================
# ALERTA
# ============================================================

FREQ_BEEP_CRITICO = 1500

DURACAO_BEEP_CRITICO = 400


# ============================================================
# BIOMETRIA
# ============================================================

PATH_BANCO_BIOMETRIA = (
    "banco_biometria"
)


PATH_DADOS_OPERADORES = os.path.join(
    PATH_BANCO_BIOMETRIA,
    "dados_operadores.csv"
)


MODELO_FACE = "Facenet"

INTERVALO_BIOMETRIA_SEGUNDOS = 3.0


# ============================================================
# ERGONOMIA
# ============================================================

LIMITE_FRAMES_FADIGA = 90

LIMIAR_POSTURA_INADEQUADA = 85


# ============================================================
# TRACKING
# ============================================================

TRACKING_ATIVO = True

TRACKING_MAQUINARIO_ATIVO = True

TEMPO_PERMANENCIA_TRACKING = 2.0


# ============================================================
# INTERFACE
# ============================================================

LARGURA_PAINEL_CENTRAL = 330


# ============================================================
# CÂMERAS HABILITADAS PARA DESCOBERTA
#
# Isso NÃO significa que todas existem.
#
# O main.py tenta abrir automaticamente e mantém apenas
# as câmeras realmente disponíveis.
# ============================================================

def obter_cameras_ativas():

    return {

        camera_id: dados

        for camera_id, dados
        in CAMERAS.items()

        if dados.get(
            "ativa",
            True
        )
    }


# ============================================================
# OBTER CONFIGURAÇÃO DE CÂMERA
# ============================================================

def obter_config_camera(
    camera_id
):

    if camera_id not in CAMERAS:

        raise ValueError(
            f"Câmera {camera_id} não existe."
        )

    return CAMERAS[
        camera_id
    ]


# ============================================================
# ATIVAR CÂMERA
# ============================================================

def ativar_camera(
    camera_id,
    fonte=None,
    nome=None
):

    if (
        camera_id < 0
        or camera_id >= MAX_CAMERAS
    ):

        raise ValueError(
            f"ID deve estar entre 0 e "
            f"{MAX_CAMERAS - 1}."
        )

    CAMERAS[
        camera_id
    ]["ativa"] = True

    if fonte is not None:

        CAMERAS[
            camera_id
        ]["fonte"] = fonte

    if nome is not None:

        CAMERAS[
            camera_id
        ]["nome"] = nome


# ============================================================
# DESATIVAR CÂMERA
# ============================================================

def desativar_camera(
    camera_id
):

    if camera_id in CAMERAS:

        CAMERAS[
            camera_id
        ]["ativa"] = False


# ============================================================
# CONFIGURAR ZONA DA CÂMERA
# ============================================================

def configurar_zona_camera(
    camera_id,
    pontos
):

    PONTOS_ZONAS[
        camera_id
    ] = np.array(
        pontos,
        dtype=np.int32
    )


# ============================================================
# CARREGAMENTO DAS CONFIGURAÇÕES SALVAS
# ============================================================

def carregar_configuracoes():

    global AMBIENTE_CALIBRADO

    global OBJETOS_GLOBAIS

    global EPIS_CONFIGURADOS

    global EPIS_OBRIGATORIOS


    ambiente = (
        carregar_configuracao_ambiente()
    )


    if ambiente:

        AMBIENTE_CALIBRADO = (
            ambiente.get(
                "calibrado",
                False
            )
        )

        OBJETOS_GLOBAIS = (
            ambiente.get(
                "objetos",
                {}
            )
        )


    epis = (
        carregar_configuracao_epis()
    )


    if epis:

        EPIS_CONFIGURADOS = (
            epis.get(
                "configurado",
                False
            )
        )

        EPIS_OBRIGATORIOS = (
            epis.get(
                "epis_obrigatorios",
                []
            )
        )


# ============================================================
# ESTADO INICIAL
# ============================================================

def obter_estado_inicial():

    if not AMBIENTE_CALIBRADO:

        return (
            ESTADO_CALIBRACAO_AMBIENTE
        )

    if not EPIS_CONFIGURADOS:

        return (
            ESTADO_CONFIGURACAO_EPI
        )

    return (
        ESTADO_MONITORAMENTO
    )


# ============================================================
# MOSTRAR CONFIGURAÇÃO
# ============================================================

def mostrar_configuracao():

    print()
    print(
        "===================================="
    )
    print(
        " CONFIGURAÇÃO DO SISTEMA"
    )
    print(
        "===================================="
    )

    print(
        f"Ambiente: "
        f"{NOME_AMBIENTE}"
    )

    print(
        f"Máximo de câmeras: "
        f"{MAX_CAMERAS}"
    )

    print(
        "Descoberta de câmeras: "
        "AUTOMÁTICA"
    )

    print(
        f"Ambiente calibrado: "
        f"{AMBIENTE_CALIBRADO}"
    )

    print(
        f"EPIs configurados: "
        f"{EPIS_CONFIGURADOS}"
    )

    print(
        f"Estado inicial: "
        f"{obter_estado_inicial()}"
    )

    print(
        "===================================="
    )
    print()


# ============================================================
# INICIALIZAÇÃO
# ============================================================

carregar_configuracoes()


if __name__ == "__main__":

    mostrar_configuracao()