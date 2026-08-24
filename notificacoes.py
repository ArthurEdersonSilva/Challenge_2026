import os
import re
import time
import smtplib
import threading
from email.message import EmailMessage
from mimetypes import guess_type

import config


# ============================================================
# CONFIGURAÇÕES
# ============================================================

TEMPO_EMAIL_SEGUNDOS = getattr(
    config,
    "TEMPO_EMAIL_SEGUNDOS",
    15
)

INTERVALO_AUDIO_SEGUNDOS = getattr(
    config,
    "INTERVALO_AUDIO_SEGUNDOS",
    7
)

ATIVAR_AUDIO = getattr(
    config,
    "ATIVAR_ALERTA_AUDIO",
    True
)

ATIVAR_EMAIL = getattr(
    config,
    "ATIVAR_ALERTA_EMAIL",
    True
)

PASTA_PROVAS = getattr(
    config,
    "PASTA_PROVAS_INCIDENTES",
    "provas_incidentes"
)


# ============================================================
# ESTADO GLOBAL DAS NOTIFICAÇÕES
# ============================================================

alertas_ativos = {}

_lock_alertas = threading.Lock()

_audio_em_execucao = False
_lock_audio = threading.Lock()


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def _texto_seguro(valor):

    return (
        str(valor)
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )


def criar_chave_notificacao(
    camera_id,
    matricula,
    tipo_infracao
):

    camera = (
        str(camera_id)
        if camera_id is not None
        else "global"
    )

    matricula = (
        str(matricula)
        if matricula
        else "DESCONHECIDO"
    )

    return (
        f"{camera}|"
        f"{matricula}|"
        f"{tipo_infracao}"
    )


def mensagem_educativa(
    tipo_infracao
):

    mensagens = {

        "Capacete":
            "Capacete necessário nesta área.",

        "Óculos":
            "Óculos de proteção necessários nesta área.",

        "Máscara":
            "Máscara de proteção necessária nesta área.",

        "Luvas":
            "Luvas de proteção necessárias nesta atividade.",

        "Protetor auricular":
            "Protetor auricular necessário nesta área.",

        "Colete":
            "Colete de segurança necessário nesta área.",

        "FADIGA_ERGONOMICA":
            "Atenção à postura. Faça o ajuste recomendado para esta atividade.",
    }

    return mensagens.get(
        tipo_infracao,
        f"Atenção. Verifique a condição de segurança: {tipo_infracao}."
    )


# ============================================================
# FOTO MAIS RECENTE DO INCIDENTE
# ============================================================

def localizar_foto_recente(
    camera_id,
    matricula,
    tipo_infracao
):

    if not os.path.isdir(
        PASTA_PROVAS
    ):

        return None

    camera_segura = (
        str(camera_id)
        if camera_id is not None
        else "global"
    )

    matricula_segura = (
        _texto_seguro(
            matricula
        )
    )

    tipo_seguro = (
        _texto_seguro(
            tipo_infracao
        )
    )

    prefixo = (
        f"cam_{camera_segura}_"
        f"{matricula_segura}_"
        f"{tipo_seguro}_"
    )

    candidatos = []

    try:

        for nome in os.listdir(
            PASTA_PROVAS
        ):

            if (
                nome.startswith(
                    prefixo
                )
                and nome.lower().endswith(
                    (
                        ".jpg",
                        ".jpeg",
                        ".png"
                    )
                )
            ):

                caminho = os.path.join(
                    PASTA_PROVAS,
                    nome
                )

                try:

                    candidatos.append(
                        (
                            os.path.getmtime(
                                caminho
                            ),
                            caminho
                        )
                    )

                except OSError:

                    pass

    except OSError:

        return None

    if not candidatos:

        return None

    candidatos.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidatos[0][1]


# ============================================================
# ÁUDIO / TTS
# ============================================================

def _executar_audio(
    mensagem
):

    global _audio_em_execucao

    try:

        # ----------------------------------------------------
        # Tenta TTS primeiro.
        # ----------------------------------------------------

        try:

            import pyttsx3

            engine = pyttsx3.init()

            engine.setProperty(
                "rate",
                165
            )

            engine.say(
                mensagem
            )

            engine.runAndWait()

            return

        except Exception:

            pass

        # ----------------------------------------------------
        # Fallback Windows: padrão sonoro.
        # ----------------------------------------------------

        try:

            import winsound

            winsound.Beep(
                1200,
                250
            )

            time.sleep(
                0.12
            )

            winsound.Beep(
                1450,
                350
            )

        except Exception:

            pass

    finally:

        with _lock_audio:

            _audio_em_execucao = False


def emitir_alerta_sonoro(
    mensagem
):

    global _audio_em_execucao

    if not ATIVAR_AUDIO:

        return False

    with _lock_audio:

        if _audio_em_execucao:

            return False

        _audio_em_execucao = True

    thread = threading.Thread(
        target=_executar_audio,
        args=(
            mensagem,
        ),
        daemon=True
    )

    thread.start()

    return True


# ============================================================
# CONFIGURAÇÃO DE E-MAIL
# ============================================================

def _obter_config_email():

    servidor = (
        getattr(
            config,
            "SMTP_SERVIDOR",
            None
        )
        or
        os.getenv(
            "SMTP_SERVIDOR"
        )
    )

    porta = int(
        getattr(
            config,
            "SMTP_PORTA",
            587
        )
        or
        os.getenv(
            "SMTP_PORTA",
            "587"
        )
    )

    usuario = (
        getattr(
            config,
            "SMTP_USUARIO",
            None
        )
        or
        os.getenv(
            "SMTP_USUARIO"
        )
    )

    senha = (
        getattr(
            config,
            "SMTP_SENHA",
            None
        )
        or
        os.getenv(
            "SMTP_SENHA"
        )
    )

    remetente = (
        getattr(
            config,
            "SMTP_REMETENTE",
            None
        )
        or
        os.getenv(
            "SMTP_REMETENTE"
        )
        or
        usuario
    )

    destinatario = (
        getattr(
            config,
            "EMAIL_ALERTA_DESTINO",
            None
        )
        or
        os.getenv(
            "EMAIL_ALERTA_DESTINO"
        )
    )

    usar_tls = getattr(
        config,
        "SMTP_USAR_TLS",
        True
    )

    return {
        "servidor":
            servidor,

        "porta":
            porta,

        "usuario":
            usuario,

        "senha":
            senha,

        "remetente":
            remetente,

        "destinatario":
            destinatario,

        "usar_tls":
            usar_tls,
    }


def email_configurado():

    dados = _obter_config_email()

    return all(
        [
            dados["servidor"],
            dados["usuario"],
            dados["senha"],
            dados["remetente"],
            dados["destinatario"],
        ]
    )


# ============================================================
# ENVIO DO E-MAIL
# ============================================================

def enviar_email_incidente(
    camera_id,
    camera_nome,
    ambiente,
    matricula,
    operador,
    tipo_infracao,
    severidade,
    caminho_foto=None,
    duracao_segundos=None
):

    if not ATIVAR_EMAIL:

        return False

    dados = _obter_config_email()

    if not email_configurado():

        print(
            "⚠️ E-mail não configurado. "
            "Defina SMTP_SERVIDOR, SMTP_USUARIO, "
            "SMTP_SENHA e EMAIL_ALERTA_DESTINO."
        )

        return False

    if (
        caminho_foto is None
        or not os.path.exists(
            caminho_foto
        )
    ):

        caminho_foto = localizar_foto_recente(
            camera_id,
            matricula,
            tipo_infracao
        )

    assunto = (
        f"[{severidade}] "
        f"{tipo_infracao} - "
        f"{camera_nome}"
    )

    mensagem_alerta = mensagem_educativa(
        tipo_infracao
    )

    corpo = [
        "Ocorrência de segurança detectada.",
        "",
        f"Ambiente: {ambiente}",
        f"Câmera: {camera_nome}",
        f"Operador: {operador}",
        f"Matrícula: {matricula}",
        f"Infração: {tipo_infracao}",
        f"Severidade: {severidade}",
    ]

    if duracao_segundos is not None:

        corpo.append(
            "Duração antes da notificação: "
            f"{duracao_segundos:.1f} segundos"
        )

    corpo.extend(
        [
            "",
            "Orientação:",
            mensagem_alerta,
            "",
            "Esta notificação possui caráter preventivo e educativo."
        ]
    )

    email = EmailMessage()

    email[
        "Subject"
    ] = assunto

    email[
        "From"
    ] = dados[
        "remetente"
    ]

    email[
        "To"
    ] = dados[
        "destinatario"
    ]

    email.set_content(
        "\n".join(
            corpo
        )
    )

    if (
        caminho_foto
        and os.path.exists(
            caminho_foto
        )
    ):

        tipo_mime, _ = guess_type(
            caminho_foto
        )

        if tipo_mime:

            principal, subtipo = (
                tipo_mime.split(
                    "/",
                    1
                )
            )

        else:

            principal = "image"
            subtipo = "jpeg"

        with open(
            caminho_foto,
            "rb"
        ) as arquivo:

            email.add_attachment(
                arquivo.read(),
                maintype=principal,
                subtype=subtipo,
                filename=os.path.basename(
                    caminho_foto
                )
            )

    try:

        with smtplib.SMTP(
            dados[
                "servidor"
            ],
            dados[
                "porta"
            ],
            timeout=15
        ) as smtp:

            if dados[
                "usar_tls"
            ]:

                smtp.starttls()

            smtp.login(
                dados[
                    "usuario"
                ],
                dados[
                    "senha"
                ]
            )

            smtp.send_message(
                email
            )

        print(
            "📧 E-mail de segurança enviado: "
            f"{tipo_infracao} | {camera_nome}"
        )

        return True

    except Exception as erro:

        print(
            f"❌ Erro ao enviar e-mail: "
            f"{erro}"
        )

        return False


def _enviar_email_background(
    dados_alerta
):

    enviar_email_incidente(
        camera_id=dados_alerta[
            "camera_id"
        ],
        camera_nome=dados_alerta[
            "camera_nome"
        ],
        ambiente=dados_alerta[
            "ambiente"
        ],
        matricula=dados_alerta[
            "matricula"
        ],
        operador=dados_alerta[
            "operador"
        ],
        tipo_infracao=dados_alerta[
            "tipo_infracao"
        ],
        severidade=dados_alerta[
            "severidade"
        ],
        caminho_foto=dados_alerta.get(
            "caminho_foto"
        ),
        duracao_segundos=dados_alerta.get(
            "duracao_segundos"
        )
    )


# ============================================================
# ATUALIZAR ALERTA ATIVO
# ============================================================

def atualizar_alerta(
    camera_id,
    camera_nome,
    ambiente,
    matricula,
    operador,
    tipo_infracao,
    severidade="ALTA",
    caminho_foto=None
):

    chave = criar_chave_notificacao(
        camera_id,
        matricula,
        tipo_infracao
    )

    agora = time.time()

    mensagem = mensagem_educativa(
        tipo_infracao
    )

    with _lock_alertas:

        alerta = alertas_ativos.get(
            chave
        )

        if alerta is None:

            alerta = {

                "chave":
                    chave,

                "camera_id":
                    camera_id,

                "camera_nome":
                    camera_nome,

                "ambiente":
                    ambiente,

                "matricula":
                    matricula,

                "operador":
                    operador,

                "tipo_infracao":
                    tipo_infracao,

                "severidade":
                    severidade,

                "mensagem":
                    mensagem,

                "inicio":
                    agora,

                "ultima_deteccao":
                    agora,

                "ultimo_audio":
                    0.0,

                "email_enviado":
                    False,

                "email_em_processamento":
                    False,

                "caminho_foto":
                    caminho_foto,
            }

            alertas_ativos[
                chave
            ] = alerta

        else:

            alerta[
                "ultima_deteccao"
            ] = agora

            alerta[
                "camera_nome"
            ] = camera_nome

            alerta[
                "operador"
            ] = operador

            alerta[
                "severidade"
            ] = severidade

            if caminho_foto:

                alerta[
                    "caminho_foto"
                ] = caminho_foto

        duracao = (
            agora
            - alerta[
                "inicio"
            ]
        )

        deve_tocar = (
            agora
            - alerta[
                "ultimo_audio"
            ]
            >= INTERVALO_AUDIO_SEGUNDOS
        )

        deve_email = (
            ATIVAR_EMAIL
            and
            not alerta[
                "email_enviado"
            ]
            and
            not alerta[
                "email_em_processamento"
            ]
            and
            duracao
            >= TEMPO_EMAIL_SEGUNDOS
        )

        if deve_tocar:

            alerta[
                "ultimo_audio"
            ] = agora

        if deve_email:

            alerta[
                "email_em_processamento"
            ] = True

        dados_retorno = dict(
            alerta
        )

        dados_retorno[
            "duracao_segundos"
        ] = duracao

    # --------------------------------------------------------
    # Áudio fora do lock.
    # --------------------------------------------------------

    if deve_tocar:

        emitir_alerta_sonoro(
            mensagem
        )

    # --------------------------------------------------------
    # E-mail fora do lock e sem travar as câmeras.
    # --------------------------------------------------------

    if deve_email:

        if (
            not dados_retorno.get(
                "caminho_foto"
            )
        ):

            dados_retorno[
                "caminho_foto"
            ] = localizar_foto_recente(
                camera_id,
                matricula,
                tipo_infracao
            )

        thread = threading.Thread(
            target=_finalizar_envio_email,
            args=(
                chave,
                dados_retorno,
            ),
            daemon=True
        )

        thread.start()

    return dados_retorno


def _finalizar_envio_email(
    chave,
    dados_alerta
):

    sucesso = enviar_email_incidente(
        camera_id=dados_alerta[
            "camera_id"
        ],
        camera_nome=dados_alerta[
            "camera_nome"
        ],
        ambiente=dados_alerta[
            "ambiente"
        ],
        matricula=dados_alerta[
            "matricula"
        ],
        operador=dados_alerta[
            "operador"
        ],
        tipo_infracao=dados_alerta[
            "tipo_infracao"
        ],
        severidade=dados_alerta[
            "severidade"
        ],
        caminho_foto=dados_alerta.get(
            "caminho_foto"
        ),
        duracao_segundos=dados_alerta.get(
            "duracao_segundos"
        )
    )

    with _lock_alertas:

        alerta = alertas_ativos.get(
            chave
        )

        if alerta is None:

            return

        alerta[
            "email_em_processamento"
        ] = False

        if sucesso:

            alerta[
                "email_enviado"
            ] = True


# ============================================================
# ENCERRAR ALERTA QUANDO EPI VOLTAR
# ============================================================

def encerrar_alerta(
    camera_id,
    matricula,
    tipo_infracao
):

    chave = criar_chave_notificacao(
        camera_id,
        matricula,
        tipo_infracao
    )

    with _lock_alertas:

        return (
            alertas_ativos.pop(
                chave,
                None
            )
            is not None
        )


def encerrar_alertas_ausentes(
    chaves_ativas
):

    chaves_ativas = set(
        chaves_ativas
    )

    encerrados = []

    with _lock_alertas:

        for chave in list(
            alertas_ativos.keys()
        ):

            if chave not in chaves_ativas:

                alertas_ativos.pop(
                    chave,
                    None
                )

                encerrados.append(
                    chave
                )

    return encerrados


# ============================================================
# CONSULTA PARA O PAINEL / DASHBOARD
# ============================================================

def obter_alertas_ativos():

    agora = time.time()

    with _lock_alertas:

        resultado = []

        for alerta in alertas_ativos.values():

            item = dict(
                alerta
            )

            item[
                "duracao_segundos"
            ] = (
                agora
                - alerta[
                    "inicio"
                ]
            )

            resultado.append(
                item
            )

    resultado.sort(
        key=lambda item: item[
            "inicio"
        ]
    )

    return resultado


def obter_alerta_principal():

    alertas = obter_alertas_ativos()

    if not alertas:

        return None

    prioridade = {
        "CRITICA":
            3,

        "ALTA":
            2,

        "INFORMATIVA":
            1,

        "NORMAL":
            0,
    }

    alertas.sort(
        key=lambda item: (
            prioridade.get(
                item.get(
                    "severidade",
                    "NORMAL"
                ),
                0
            ),
            item.get(
                "duracao_segundos",
                0
            )
        ),
        reverse=True
    )

    return alertas[0]


# ============================================================
# RESET COMPLETO
# ============================================================

def limpar_notificacoes():

    global _audio_em_execucao

    with _lock_alertas:

        alertas_ativos.clear()

    with _lock_audio:

        _audio_em_execucao = False


# ============================================================
# INTEGRAÇÃO DIRETA COM O MAIN.PY
# ============================================================

def atualizar_notificacoes(
    status_epis,
    frames,
    operador,
    severidade="ALTA"
):

    ambiente = getattr(
        config,
        "NOME_AMBIENTE",
        "Ambiente Principal"
    )

    matricula = "DESCONHECIDO"

    chaves_ativas = set()

    if not frames:

        encerrar_alertas_ausentes(
            chaves_ativas
        )

        return []

    camera_padrao, _ = frames[0]

    for epi, presente in status_epis.items():

        if presente:
            continue

        camera_id = getattr(
            camera_padrao,
            "camera_id",
            None
        )

        camera_nome = getattr(
            camera_padrao,
            "nome",
            "Camera"
        )

        chave = criar_chave_notificacao(
            camera_id,
            matricula,
            epi
        )

        chaves_ativas.add(
            chave
        )

        foto = localizar_foto_recente(
            camera_id,
            matricula,
            epi
        )

        atualizar_alerta(
            camera_id=camera_id,
            camera_nome=camera_nome,
            ambiente=ambiente,
            matricula=matricula,
            operador=operador,
            tipo_infracao=epi,
            severidade=severidade,
            caminho_foto=foto
        )

    encerrar_alertas_ausentes(
        chaves_ativas
    )

    return obter_alertas_ativos()


def encerrar_notificacoes():

    limpar_notificacoes()
