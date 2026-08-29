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

# ETAPA 5 - Pessoa + Pose.
# Nenhum destes parâmetros altera automaticamente FPS, resolução
# ou frequência de inferência. Pose é executado a cada frame de
# monitoramento efetivamente recebido.
CONFIANCA_KEYPOINT_POSE = 0.5
POSE_DEBUG = False
POSE_TRACK_IOU_MINIMO = 0.25
POSE_TRACK_DISTANCIA_CENTRO_MAXIMA = 0.80
POSE_TRACK_MAX_FRAMES_SEM_DETECCAO = 12

# ETAPA 5: frame de rede acima deste limite não é observação atual.
TEMPO_MAX_FRAME_REDE_SEGUNDOS = 2.0

CONFIANCA_MAQUINARIO = 0.5

TAMANHO_IMAGEM = 640


# ============================================================
# CÂMERAS
# ============================================================

LARGURA_CAM = 640
ALTURA_CAM = 480

MAX_CAMERAS = 66

# ------------------------------------------------------------
# CONFIGURAÇÃO WIFI
# ------------------------------------------------------------

PASTA_CAMERA_WIFI = "camera_wifi"

PATH_CAMERAS_WIFI = os.path.join(
    PASTA_CAMERA_WIFI,
    "cameras_wifi.json"
)

# Informa qual modo foi carregado.
# Valores possíveis: "wifi" ou "usb"
MODO_CAMERAS = "usb"


# ============================================================
# CARREGAR CÂMERAS WIFI
# ============================================================

def carregar_cameras_wifi():

    if not os.path.exists(
        PATH_CAMERAS_WIFI
    ):

        return {}

    try:

        with open(
            PATH_CAMERAS_WIFI,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(
                arquivo
            )

    except Exception as erro:

        print(
            f"⚠️ Erro ao carregar câmeras WiFi: "
            f"{erro}"
        )

        return {}

    cameras_salvas = dados.get(
        "cameras",
        []
    )

    if not isinstance(
        cameras_salvas,
        list
    ):

        return {}

    cameras = {}

    proximo_id = 0

    for item in cameras_salvas:

        if not isinstance(
            item,
            dict
        ):

            continue

        if not item.get(
            "ativa",
            True
        ):

            continue

        fonte = item.get(
            "fonte"
        )

        if not fonte:

            continue

        nome = item.get(
            "nome"
        )

        if not nome:

            nome = (
                f"Camera WiFi "
                f"{proximo_id + 1:02d}"
            )

        cameras[
            proximo_id
        ] = {

            "nome":
                nome,

            "fonte":
                fonte,

            "tipo":
                item.get(
                    "tipo",
                    "wifi"
                ),

            "ip":
                item.get(
                    "ip"
                ),

            # ETAPA 4: conexão pertence à câmera lógica individual.
            # Não existe porta RTSP global nem porta 554 presumida.
            "porta":
                item.get(
                    "porta"
                ),

            "caminho_stream":
                item.get(
                    "caminho_stream",
                    item.get("path")
                ),

            "camera_uid":
                item.get(
                    "camera_uid"
                ),

            "ativa":
                True,

            "onvif":
                item.get(
                    "onvif",
                    False
                ),

            "resolucao":
                item.get(
                    "resolucao"
                ),

            "fps":
                item.get(
                    "fps"
                ),
        }

        proximo_id += 1

    return cameras


# ============================================================
# CRIAR CÂMERAS USB PADRÃO
# ============================================================

def criar_cameras_usb():

    cameras = {}

    for camera_id in range(
        MAX_CAMERAS
    ):

        cameras[
            camera_id
        ] = {

            "nome":
                f"Camera "
                f"{camera_id + 1:02d}",

            "fonte":
                camera_id,

            "tipo":
                "usb",

            # Todas ficam disponíveis para tentativa.
            # O main.py mantém somente as que realmente
            # conseguem abrir.
            "ativa":
                True,
        }

    return cameras


# ============================================================
# ESCOLHER FONTE DAS CÂMERAS
#
# REGRA:
#
# 1. Se camera_wifi/cameras_wifi.json possuir pelo menos
#    uma câmera válida, usa SOMENTE as câmeras WiFi/IP.
#
# 2. Se o arquivo não existir, estiver vazio ou inválido,
#    mantém o comportamento atual e procura câmeras USB.
# ============================================================

_cameras_wifi = carregar_cameras_wifi()

if _cameras_wifi:

    CAMERAS = _cameras_wifi

    MODO_CAMERAS = "wifi"

    print()
    print(
        "=========================================="
    )
    print(
        " MODO DE CÂMERAS: WIFI / IP"
    )
    print(
        "=========================================="
    )
    print(
        f"Câmeras configuradas: "
        f"{len(CAMERAS)}"
    )
    print(
        "=========================================="
    )
    print()

else:

    CAMERAS = criar_cameras_usb()

    MODO_CAMERAS = "usb"
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

    "Protetor facial",

    "Macacão de proteção",

    "Cinto de segurança",

    "Bota de segurança",
]


# ============================================================
# CONTRATO DE CLASSES DO MODELO DE EPI
#
# Estes nomes correspondem exatamente às classes do best.pt.
# EPIS_DISPONIVEIS define apenas o catálogo selecionável.
# EPIS_OBRIGATORIOS continua sendo definido manualmente.
# ============================================================

CLASSES_MODELO_EPI = [

    "Ear Protectors",
    "Face Shield",
    "Full body suit",
    "Glasses",
    "Gloves",
    "Helmet",
    "Mask",
    "Safety Harness",
    "Safety Shoes",
    "Safety Vest",
    "Without Ear Protectors",
    "Without Face Shield",
    "Without Full body suit",
    "Without Glass",
    "Without Glove",
    "Without Helmet",
    "Without Mask",
    "Without Safety Harness",
    "Without Safety Shoes",
    "Without Safety Vest",
]


EPIS_PRESENCA = {

    "Ear Protectors":
        "Protetor auricular",

    "Face Shield":
        "Protetor facial",

    "Full body suit":
        "Macacão de proteção",

    "Glasses":
        "Óculos",

    "Gloves":
        "Luvas",

    "Helmet":
        "Capacete",

    "Mask":
        "Máscara",

    "Safety Harness":
        "Cinto de segurança",

    "Safety Shoes":
        "Bota de segurança",

    "Safety Vest":
        "Colete",
}


EPIS_AUSENCIA = {

    "Without Ear Protectors":
        "Protetor auricular",

    "Without Face Shield":
        "Protetor facial",

    "Without Full body suit":
        "Macacão de proteção",

    "Without Glass":
        "Óculos",

    "Without Glove":
        "Luvas",

    "Without Helmet":
        "Capacete",

    "Without Mask":
        "Máscara",

    "Without Safety Harness":
        "Cinto de segurança",

    "Without Safety Shoes":
        "Bota de segurança",

    "Without Safety Vest":
        "Colete",
}


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
# ASSOCIAÇÃO EPI ↔ PESSOA - ETAPA 6
#
# Apenas parâmetros geométricos. Não representam estados
# CORRETO / INCORRETO / AUSENTE / INDETERMINADO.
# ============================================================

ASSOCIACAO_EPI_SCORE_MINIMO = 0.45
ASSOCIACAO_EPI_MARGEM_AMBIGUIDADE = 0.08
ASSOCIACAO_EPI_INTERSECAO_MINIMA = 0.05
ASSOCIACAO_EPI_EXPANSAO_BBOX_PESSOA = 0.08
ASSOCIACAO_EPI_DEBUG = False


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
# ATIVAÇÃO DE PERFIL EM RUNTIME - ETAPA 3
#
# O perfil JSON em ambientes/ é a fonte persistente.
# Estas variáveis continuam existindo somente como espelho
# de compatibilidade para o código legado do runtime.
# ============================================================

def aplicar_perfil_runtime(perfil):

    global NOME_AMBIENTE
    global AMBIENTE_CALIBRADO
    global OBJETOS_GLOBAIS
    global EPIS_CONFIGURADOS
    global EPIS_OBRIGATORIOS

    if not isinstance(perfil, dict):
        raise ValueError("Perfil de ambiente inválido.")

    NOME_AMBIENTE = str(
        perfil.get("nome", "Ambiente Principal")
    )

    AMBIENTE_CALIBRADO = bool(
        perfil.get("calibrado", False)
    )

    OBJETOS_GLOBAIS = dict(
        perfil.get("objetos_globais", {}) or {}
    )

    EPIS_OBRIGATORIOS = list(
        perfil.get("epis_obrigatorios", []) or []
    )

    # Em um perfil persistido, uma lista vazia também pode ser
    # uma escolha manual válida. Se o ambiente está calibrado,
    # a etapa de configuração de EPI é considerada concluída.
    EPIS_CONFIGURADOS = bool(
        AMBIENTE_CALIBRADO
    )


def limpar_perfil_runtime():

    global NOME_AMBIENTE
    global AMBIENTE_CALIBRADO
    global OBJETOS_GLOBAIS
    global EPIS_CONFIGURADOS
    global EPIS_OBRIGATORIOS

    NOME_AMBIENTE = "Ambiente Principal"
    AMBIENTE_CALIBRADO = False
    OBJETOS_GLOBAIS = {}
    EPIS_CONFIGURADOS = False
    EPIS_OBRIGATORIOS = []


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
        f"Modo de câmeras: "
        f"{MODO_CAMERAS.upper()}"
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
#
# ETAPA 3: o legado NÃO é mais ativado automaticamente no
# import. Ele permanece disponível exclusivamente para migração
# explícita pelo fluxo de startup do main.py.
# ============================================================

limpar_perfil_runtime()


if __name__ == "__main__":

    mostrar_configuracao()

# ============================================================
# NOTIFICACOES
# ============================================================

ATIVAR_ALERTA_AUDIO = True
ATIVAR_ALERTA_EMAIL = True

INTERVALO_AUDIO_SEGUNDOS = 7
TEMPO_EMAIL_SEGUNDOS = 15


# ============================================================
# EMAIL
# ============================================================

SMTP_SERVIDOR = "smtp.gmail.com"
SMTP_PORTA = 587
SMTP_USAR_TLS = True

# Email que envia os alertas
SMTP_USUARIO = "arthur.ederson.ae@gmail.com"

# Senha de app do Gmail - NÃO é a senha normal
SMTP_SENHA = os.getenv("VISION_SAFETY_SMTP_SENHA", "")
# Remetente
SMTP_REMETENTE = SMTP_USUARIO

# Email que recebe os alertas
EMAIL_ALERTA_DESTINO = "arthur.ederson.ae@gmail.com"