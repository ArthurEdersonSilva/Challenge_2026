import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from estado_sistema import (
    INCIDENTE_ATIVO,
    INCIDENTE_ENCERRADO,
    INCIDENTE_OBSERVACAO_SUSPENSA,
    NOTIFICACAO_EMAIL_EM_FILA,
    NOTIFICACAO_EMAIL_ENVIADO,
    NOTIFICACAO_EMAIL_ENVIANDO,
    NOTIFICACAO_EMAIL_FALHOU,
    NOTIFICACAO_EMAIL_CANCELADO,
)
from notificacoes import mensagem_incidente, reproduzir_audio, enviar_email_incidente


@dataclass(frozen=True)
class JobAudio:
    incidente_id: str
    mensagem: str
    severidade: str


@dataclass(frozen=True)
class JobEmail:
    incidente_id: str
    severidade: str


class GestorNotificacoesIncidentes:
    """Política da ETAPA 11. Filas são transporte; EstadoSistema é a verdade."""

    def __init__(
        self,
        estado_sistema,
        ativar_visual=True,
        ativar_audio=True,
        ativar_email=True,
        severidade_padrao="ALTA",
        intervalo_audio_segundos=7.0,
        audio_fila_maxima=8,
        audio_retry_fila_segundos=1.0,
        email_atraso_segundos=15.0,
        email_fila_maxima=8,
        email_max_tentativas=3,
        email_retry_segundos=30.0,
        email_retry_fila_segundos=1.0,
        email_repeticao_segundos=None,
        relogio: Callable[[], float] = time.monotonic,
        driver_audio: Callable = reproduzir_audio,
        driver_email: Callable = enviar_email_incidente,
        iniciar_workers=True,
    ):
        self.estado_sistema = estado_sistema
        self.ativar_visual = bool(ativar_visual)
        self.ativar_audio = bool(ativar_audio)
        self.ativar_email = bool(ativar_email)
        self.severidade_padrao = str(severidade_padrao or "ALTA")
        self.intervalo_audio = max(0.0, float(intervalo_audio_segundos))
        self.audio_retry_fila = max(0.0, float(audio_retry_fila_segundos))
        self.email_atraso = max(0.0, float(email_atraso_segundos))
        self.email_max_tentativas = max(1, int(email_max_tentativas))
        self.email_retry = max(0.0, float(email_retry_segundos))
        self.email_retry_fila = max(0.0, float(email_retry_fila_segundos))
        self.email_repeticao = None if email_repeticao_segundos is None else max(0.0, float(email_repeticao_segundos))
        self.relogio = relogio
        self.driver_audio = driver_audio
        self.driver_email = driver_email
        self.fila_audio = queue.PriorityQueue(maxsize=max(1, int(audio_fila_maxima)))
        self.fila_email = queue.Queue(maxsize=max(1, int(email_fila_maxima)))
        self._ordem = 0
        self._lock_ordem = threading.Lock()
        self._parar = threading.Event()
        self._workers = []
        if iniciar_workers:
            self._iniciar_workers()

    @staticmethod
    def _prioridade(severidade):
        return {"CRITICA": 0, "ALTA": 1, "MEDIA": 2}.get(str(severidade), 1)

    def _proxima_ordem(self):
        with self._lock_ordem:
            self._ordem += 1
            return self._ordem

    def _iniciar_workers(self):
        ta = threading.Thread(target=self._worker_audio, daemon=True, name="notificacao-audio")
        te = threading.Thread(target=self._worker_email, daemon=True, name="notificacao-email")
        ta.start(); te.start()
        self._workers.extend((ta, te))

    def encerrar(self, timeout_segundos=1.0):
        """Solicita parada e aguarda workers sem bloquear indefinidamente."""
        self._parar.set()
        timeout = max(0.0, float(timeout_segundos))
        for worker in tuple(self._workers):
            if worker is threading.current_thread():
                continue
            if worker.is_alive():
                worker.join(timeout=timeout)


    def _severidade_incidente(self, incidente):
        # ETAPA 11: nenhuma classificação específica por EPI foi aprovada.
        return self.severidade_padrao

    def processar(self, agora_monotonico: Optional[float] = None):
        if self._parar.is_set():
            return False
        agora = float(self.relogio() if agora_monotonico is None else agora_monotonico)
        incidentes = self.estado_sistema.obter_incidentes_para_notificacao()
        for incidente in incidentes:
            severidade = self._severidade_incidente(incidente)
            estado = self.estado_sistema.sincronizar_notificacao_incidente(
                incidente.incidente_id, severidade, agora
            )
            if estado is None:
                continue
            # Visual é apenas estado consumível; nenhuma interface final aqui.
            if incidente.estado_incidente == INCIDENTE_ENCERRADO:
                continue
            if incidente.estado_incidente == INCIDENTE_OBSERVACAO_SUSPENSA:
                continue
            if incidente.estado_incidente != INCIDENTE_ATIVO:
                continue
            self._avaliar_audio(incidente, estado, agora)
            self._avaliar_email(incidente, estado, agora)

    def _avaliar_audio(self, incidente, estado, agora):
        if self._parar.is_set():
            return False
        if not self.ativar_audio or estado.audio_em_fila:
            return False
        if agora < float(estado.proxima_tentativa_audio_monotonica or 0.0):
            return False
        if estado.ultimo_audio_monotonico is not None and agora - estado.ultimo_audio_monotonico < self.intervalo_audio:
            return False
        job = JobAudio(
            incidente_id=incidente.incidente_id,
            mensagem=mensagem_incidente(incidente.epi, incidente.tipo_irregularidade, incidente.camera_nome),
            severidade=estado.severidade,
        )
        try:
            self.fila_audio.put_nowait((self._prioridade(estado.severidade), self._proxima_ordem(), job))
        except queue.Full:
            # Não marca executado nem sucesso. Nova tentativa fica elegível.
            self.estado_sistema.registrar_rejeicao_fila_audio(
                incidente.incidente_id, "FILA_AUDIO_CHEIA", agora + self.audio_retry_fila
            )
            return False
        self.estado_sistema.marcar_audio_enfileirado(incidente.incidente_id, True)
        return True

    def _email_elegivel(self, estado, agora):
        if estado.status_email in {NOTIFICACAO_EMAIL_ENVIADO, NOTIFICACAO_EMAIL_EM_FILA, NOTIFICACAO_EMAIL_ENVIANDO, NOTIFICACAO_EMAIL_CANCELADO}:
            return False
        if estado.status_email == NOTIFICACAO_EMAIL_FALHOU and estado.tentativas_email >= self.email_max_tentativas:
            return False
        if agora < float(estado.proxima_tentativa_email_monotonica or 0.0):
            return False
        if estado.tempo_ativo_acumulado < self.email_atraso:
            return False
        return True

    def _avaliar_email(self, incidente, estado, agora):
        if self._parar.is_set():
            return False
        if not self.ativar_email or not self._email_elegivel(estado, agora):
            return False
        job = JobEmail(incidente_id=incidente.incidente_id, severidade=estado.severidade)
        try:
            self.fila_email.put_nowait(job)
        except queue.Full:
            # Não marca enviado nem em fila em caso de rejeição.
            self.estado_sistema.registrar_rejeicao_fila_email(
                incidente.incidente_id, "FILA_EMAIL_CHEIA", agora + self.email_retry_fila
            )
            return False
        self.estado_sistema.marcar_email_em_fila(incidente.incidente_id, agora)
        return True

    def _executar_job_audio(self, job):
        agora = float(self.relogio())
        try:
            if not self.estado_sistema.incidente_notificavel(job.incidente_id):
                self.estado_sistema.marcar_audio_enfileirado(job.incidente_id, False)
                return False
            sucesso, detalhe = self.driver_audio(job.mensagem)
            self.estado_sistema.registrar_resultado_audio(
                job.incidente_id, bool(sucesso), agora, detalhe,
                retry_segundos=self.audio_retry_fila,
            )
            return bool(sucesso)
        except Exception as erro:
            self.estado_sistema.registrar_resultado_audio(
                job.incidente_id, False, agora, f"EXCECAO_AUDIO:{erro}",
                retry_segundos=self.audio_retry_fila,
            )
            return False

    def processar_um_audio(self):
        try:
            _, _, job = self.fila_audio.get_nowait()
        except queue.Empty:
            return False
        try:
            return self._executar_job_audio(job)
        finally:
            self.fila_audio.task_done()

    def _executar_job_email(self, job):
        agora = float(self.relogio())
        try:
            if not self.estado_sistema.incidente_notificavel(job.incidente_id):
                self.estado_sistema.cancelar_email_incidente(job.incidente_id, "INCIDENTE_ENCERRADO_ANTES_SMTP")
                return False
            if not self.estado_sistema.marcar_email_enviando(job.incidente_id):
                return False
            dados = self.estado_sistema.obter_incidente_notificacao(job.incidente_id)
            estado = self.estado_sistema.notificacoes_incidentes.get(job.incidente_id)
            if dados is None or estado is None:
                return False
            caminho = dados.get("caminho_frame") or dados.get("caminho_crop")

            def pre_envio():
                return self.estado_sistema.incidente_notificavel(job.incidente_id)

            sucesso, detalhe = self.driver_email(
                dados_incidente=dados,
                severidade=job.severidade,
                caminho_evidencia=caminho,
                duracao_ativa_segundos=estado.tempo_ativo_acumulado,
                pre_envio_validador=pre_envio,
            )
            if job.incidente_id not in self.estado_sistema.notificacoes_incidentes:
                return False
            if detalhe == "INCIDENTE_NAO_NOTIFICAVEL":
                self.estado_sistema.cancelar_email_incidente(job.incidente_id, detalhe)
                return False
            self.estado_sistema.registrar_resultado_email(
                job.incidente_id, bool(sucesso), agora, detalhe,
                retry_segundos=self.email_retry,
                max_tentativas=self.email_max_tentativas,
            )
            return bool(sucesso)
        except Exception as erro:
            self.estado_sistema.registrar_resultado_email(
                job.incidente_id, False, agora, f"EXCECAO_EMAIL:{erro}",
                retry_segundos=self.email_retry,
                max_tentativas=self.email_max_tentativas,
            )
            return False

    def processar_um_email(self):
        try:
            job = self.fila_email.get_nowait()
        except queue.Empty:
            return False
        try:
            return self._executar_job_email(job)
        finally:
            self.fila_email.task_done()

    def _worker_audio(self):
        while not self._parar.is_set():
            try:
                _, _, job = self.fila_audio.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._executar_job_audio(job)
            finally:
                self.fila_audio.task_done()

    def _worker_email(self):
        while not self._parar.is_set():
            try:
                job = self.fila_email.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._executar_job_email(job)
            finally:
                self.fila_email.task_done()

