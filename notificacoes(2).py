import os
import smtplib
from email.message import EmailMessage
from mimetypes import guess_type
from typing import Callable, Optional, Tuple

import config


ATIVAR_AUDIO = bool(getattr(config, "ATIVAR_ALERTA_AUDIO", True))
ATIVAR_EMAIL = bool(getattr(config, "ATIVAR_ALERTA_EMAIL", True))


def mensagem_incidente(epi: str, tipo_irregularidade: str, camera_nome: Optional[str] = None) -> str:
    camera = f" na {camera_nome}" if camera_nome else ""
    if str(tipo_irregularidade) == "AUSENCIA_EPI":
        return f"Atenção{camera}. {epi} obrigatório ausente."
    if str(tipo_irregularidade) == "USO_INCORRETO_EPI":
        return f"Atenção{camera}. {epi} identificado em uso incorreto."
    return f"Atenção{camera}. Verifique a condição de segurança relacionada a {epi}."


def reproduzir_audio(mensagem: str) -> Tuple[bool, str]:
    """Driver de áudio. Não mantém estado operacional."""
    if not ATIVAR_AUDIO:
        return False, "AUDIO_DESATIVADO"
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.say(str(mensagem))
        engine.runAndWait()
        return True, "TTS"
    except Exception as erro_tts:
        try:
            import winsound
            winsound.Beep(1200, 250)
            winsound.Beep(1450, 350)
            return True, "BEEP_FALLBACK"
        except Exception as erro_beep:
            return False, f"TTS={erro_tts}; BEEP={erro_beep}"


def obter_config_email():
    servidor = getattr(config, "SMTP_SERVIDOR", None) or os.getenv("SMTP_SERVIDOR")
    porta = int(getattr(config, "SMTP_PORTA", 587) or os.getenv("SMTP_PORTA", "587"))
    usuario = getattr(config, "SMTP_USUARIO", None) or os.getenv("SMTP_USUARIO")
    senha = getattr(config, "SMTP_SENHA", None) or os.getenv("VISION_SAFETY_SMTP_SENHA", "") or os.getenv("SMTP_SENHA")
    remetente = getattr(config, "SMTP_REMETENTE", None) or os.getenv("SMTP_REMETENTE") or usuario
    destinatario = getattr(config, "EMAIL_ALERTA_DESTINO", None) or os.getenv("EMAIL_ALERTA_DESTINO")
    usar_tls = bool(getattr(config, "SMTP_USAR_TLS", True))
    return {
        "servidor": servidor,
        "porta": porta,
        "usuario": usuario,
        "senha": senha,
        "remetente": remetente,
        "destinatario": destinatario,
        "usar_tls": usar_tls,
    }


def email_configurado() -> bool:
    dados = obter_config_email()
    return all((dados["servidor"], dados["usuario"], dados["senha"], dados["remetente"], dados["destinatario"]))


def _anexar_se_existir(email: EmailMessage, caminho: Optional[str]) -> bool:
    if not caminho or not os.path.isfile(caminho):
        return False
    tipo_mime, _ = guess_type(caminho)
    if tipo_mime and "/" in tipo_mime:
        principal, subtipo = tipo_mime.split("/", 1)
    else:
        principal, subtipo = "image", "jpeg"
    with open(caminho, "rb") as arquivo:
        email.add_attachment(
            arquivo.read(),
            maintype=principal,
            subtype=subtipo,
            filename=os.path.basename(caminho),
        )
    return True


def enviar_email_incidente(
    dados_incidente: dict,
    severidade: str,
    caminho_evidencia: Optional[str] = None,
    duracao_ativa_segundos: Optional[float] = None,
    pre_envio_validador: Optional[Callable[[], bool]] = None,
    smtp_factory=None,
) -> Tuple[bool, str]:
    """Driver SMTP sem estado. Revalida o incidente imediatamente antes do SMTP."""
    if not ATIVAR_EMAIL:
        return False, "EMAIL_DESATIVADO"
    dados_email = obter_config_email()
    if not all((dados_email["servidor"], dados_email["usuario"], dados_email["senha"], dados_email["remetente"], dados_email["destinatario"])):
        return False, "EMAIL_NAO_CONFIGURADO"

    epi = str(dados_incidente.get("epi") or "EPI")
    tipo = str(dados_incidente.get("tipo_irregularidade") or "IRREGULARIDADE")
    camera_nome = str(dados_incidente.get("camera_nome") or f"Camera {dados_incidente.get('camera_id', '--')}")
    assunto = f"[{severidade}] {epi} - {camera_nome}"
    corpo = [
        "Ocorrência de segurança detectada.", "",
        f"Incidente: {dados_incidente.get('incidente_id', '--')}",
        f"Ambiente: {dados_incidente.get('ambiente_nome', '--')}",
        f"Câmera: {camera_nome}",
        f"EPI: {epi}",
        f"Irregularidade: {tipo}",
        f"Severidade: {severidade}",
        f"Status da identidade: {dados_incidente.get('status_identidade', 'NAO_AVALIADO')}",
        f"Operador: {dados_incidente.get('nome', 'DESCONHECIDO')}",
        f"Matrícula: {dados_incidente.get('matricula', '--')}",
        f"Cargo: {dados_incidente.get('cargo', '--')}",
    ]
    if duracao_ativa_segundos is not None:
        corpo.append(f"Tempo ativo observável: {float(duracao_ativa_segundos):.1f} segundos")
    corpo.extend(["", "Orientação:", mensagem_incidente(epi, tipo, camera_nome), "", "Esta notificação possui caráter preventivo e educativo."])

    email = EmailMessage()
    email["Subject"] = assunto
    email["From"] = dados_email["remetente"]
    email["To"] = dados_email["destinatario"]
    email.set_content("\n".join(corpo))
    try:
        _anexar_se_existir(email, caminho_evidencia)
    except Exception:
        pass

    # EXIGÊNCIA ETAPA 11: revalidação imediatamente antes de abrir SMTP.
    if pre_envio_validador is not None:
        try:
            if not bool(pre_envio_validador()):
                return False, "INCIDENTE_NAO_NOTIFICAVEL"
        except Exception as erro:
            return False, f"FALHA_REVALIDACAO:{erro}"

    factory = smtp_factory or smtplib.SMTP
    try:
        with factory(dados_email["servidor"], dados_email["porta"], timeout=15) as smtp:
            if dados_email["usar_tls"]:
                smtp.starttls()
            smtp.login(dados_email["usuario"], dados_email["senha"])
            smtp.send_message(email)
        return True, "ENVIADO"
    except Exception as erro:
        return False, f"SMTP:{erro}"


# Compatibilidade: funções legadas permanecem disponíveis, mas não mantêm
# alertas_ativos e não são usadas pelo pipeline das ETAPAS 10/11.
def mensagem_educativa(tipo_infracao):
    return mensagem_incidente(str(tipo_infracao), "AUSENCIA_EPI")


def criar_chave_notificacao(camera_id, matricula, tipo_infracao):
    return f"LEGADO|{camera_id}|{matricula or 'DESCONHECIDO'}|{tipo_infracao}"


def atualizar_notificacoes(*args, **kwargs):
    return []


def obter_alertas_ativos():
    return []


def obter_alerta_principal():
    return None


def limpar_notificacoes():
    return None


def encerrar_notificacoes():
    return None
