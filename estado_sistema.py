from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
import uuid
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# ESTADOS OPERACIONAIS PADRONIZADOS
# ============================================================

CAMERA_ONLINE = "ONLINE"
CAMERA_OFFLINE = "OFFLINE"
CAMERA_RECONECTANDO = "RECONECTANDO"

EPI_CORRETO = "CORRETO"
EPI_INCORRETO = "INCORRETO"
EPI_AUSENTE = "AUSENTE"
EPI_INDETERMINADO = "INDETERMINADO"

ESTADOS_EPI_VALIDOS = {
    EPI_CORRETO,
    EPI_INCORRETO,
    EPI_AUSENTE,
    EPI_INDETERMINADO,
}

INCIDENTE_ATIVO = "ATIVO"
INCIDENTE_OBSERVACAO_SUSPENSA = "OBSERVACAO_SUSPENSA"
INCIDENTE_ENCERRADO = "ENCERRADO"

TIPO_INCIDENTE_AUSENCIA_EPI = "AUSENCIA_EPI"
TIPO_INCIDENTE_USO_INCORRETO_EPI = "USO_INCORRETO_EPI"

NOTIFICACAO_EMAIL_NAO_AGENDADO = "NAO_AGENDADO"
NOTIFICACAO_EMAIL_AGUARDANDO_TEMPO = "AGUARDANDO_TEMPO"
NOTIFICACAO_EMAIL_EM_FILA = "EM_FILA"
NOTIFICACAO_EMAIL_ENVIANDO = "ENVIANDO"
NOTIFICACAO_EMAIL_ENVIADO = "ENVIADO"
NOTIFICACAO_EMAIL_FALHOU = "FALHOU"
NOTIFICACAO_EMAIL_CANCELADO = "CANCELADO"


# ============================================================
# UTILITÁRIOS
# ============================================================

def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp_iso(valor: Optional[datetime]) -> Optional[str]:
    if valor is None:
        return None
    return valor.isoformat()


# ============================================================
# CONTRATOS DE DADOS
#
# Nesta etapa, vários contratos existem apenas para preparar o
# modelo. Eles não antecipam pose, tracking, biometria,
# estabilização, incidentes ou notificações.
# ============================================================

IDENTIDADE_NAO_AVALIADO = "NAO_AVALIADO"
IDENTIDADE_AGUARDANDO_ROSTO = "AGUARDANDO_ROSTO"
IDENTIDADE_INDETERMINADO = "INDETERMINADO"
IDENTIDADE_IDENTIFICADO = "IDENTIFICADO"
IDENTIDADE_DESCONHECIDO = "DESCONHECIDO"

PROCESSAMENTO_BIOMETRIA_OCIOSO = "OCIOSO"
PROCESSAMENTO_BIOMETRIA_EM_FILA = "EM_FILA"
PROCESSAMENTO_BIOMETRIA_IDENTIFICANDO = "IDENTIFICANDO"


@dataclass
class IdentidadePessoa:
    conhecida: bool = False
    status_identidade: str = IDENTIDADE_NAO_AVALIADO
    status_processamento: str = PROCESSAMENTO_BIOMETRIA_OCIOSO
    matricula: str = "--"
    nome: str = "DESCONHECIDO"
    cargo: str = "--"
    confianca: Optional[float] = None
    distancia_match: Optional[float] = None
    metodo: Optional[str] = None
    modelo: Optional[str] = None
    tentativas: int = 0
    tentativas_validas: int = 0
    ultima_tentativa_monotonica: Optional[float] = None
    ultima_tentativa_em: Optional[datetime] = None
    candidato_matricula: Optional[str] = None
    candidato_nome: Optional[str] = None
    candidato_cargo: Optional[str] = None
    confirmacoes_candidato: int = 0
    confirmacoes_desconhecido: int = 0
    candidato_conflito: Optional[str] = None
    confirmacoes_conflito: int = 0
    job_pendente_id: Optional[str] = None
    observacao_pendente_id: Optional[str] = None
    jobs_processados: List[str] = field(default_factory=list)
    observacoes_processadas: List[str] = field(default_factory=list)
    identificada_em: Optional[datetime] = None
    ultima_confirmacao_em: Optional[datetime] = None
    motivo: Optional[str] = None


@dataclass
class EstabilizacaoEPI:
    frames_correto: int = 0
    frames_incorreto: int = 0
    frames_ausente: int = 0
    frames_indeterminado: int = 0
    ultimo_estado_confirmado: Optional[str] = None
    ultimo_estado_confirmado_em: Optional[datetime] = None


@dataclass
class EstadoEPI:
    epi: str
    estado: str = EPI_INDETERMINADO
    confianca: Optional[float] = None
    classe_detectada: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    camera_id: Optional[int] = None
    atualizado_em: Optional[datetime] = None
    evidencia_presenca: Optional[bool] = None
    evidencia_ausencia: Optional[bool] = None
    estabilizacao: Optional[EstabilizacaoEPI] = None

    def __post_init__(self):
        if self.estado not in ESTADOS_EPI_VALIDOS:
            raise ValueError(
                f"Estado de EPI inválido: {self.estado}"
            )


@dataclass(frozen=True)
class EstadoKeypoint:
    indice: int
    nome: str
    x: Optional[float] = None
    y: Optional[float] = None
    confianca: Optional[float] = None
    confiavel: bool = False


@dataclass(frozen=True)
class EstadoAssociacaoEPI:
    detection_id: str
    camera_id: int
    classe_modelo: str
    epi: str
    tipo_deteccao: str
    bbox_epi: Tuple[float, float, float, float]
    confianca_deteccao: float
    status_associacao: str
    track_id: Optional[int] = None
    track_instance_id: Optional[str] = None
    score_assoc: Optional[float] = None
    score_segundo_candidato: Optional[float] = None
    # ETAPA 6: ownership e compatibilidade anatômica são informações
    # distintas. Nenhum destes campos representa estado semântico de EPI.
    score_ownership: Optional[float] = None
    componente_bbox: Optional[float] = None
    componente_proximidade_corpo: Optional[float] = None
    componente_proximidade_keypoints: Optional[float] = None
    componente_regiao_esperada: Optional[float] = None
    distancia_corporal_normalizada: Optional[float] = None
    distancia_regiao_esperada_normalizada: Optional[float] = None
    regiao_corporal_mais_proxima: Optional[str] = None
    regiao_esperada: Optional[str] = None
    compatibilidade_regiao_esperada: Optional[float] = None
    metodo: Optional[str] = None
    metodo_regiao_esperada: Optional[str] = None
    qualidade_geometrica: Optional[str] = None
    candidatos: Tuple[Tuple[str, float], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EstadoEvidenciaSemanticaEPI:
    detection_id: str
    classe_modelo: str
    tipo_deteccao: str
    bbox_epi: Tuple[float, float, float, float]
    confianca_deteccao: float
    status_associacao: str
    score_ownership: Optional[float] = None
    compatibilidade_regiao_esperada_etapa6: Optional[float] = None
    compatibilidade_anatomica: Optional[float] = None
    regiao_corporal_mais_proxima: Optional[str] = None
    regiao_esperada: Optional[str] = None
    utilizavel: bool = False
    posicao: str = "INDETERMINADA"
    motivo: Optional[str] = None


@dataclass(frozen=True)
class EstadoEPIIndividual:
    camera_id: int
    track_id: int
    track_instance_id: str
    epi: str
    estado: str
    evidencias_positivas: Tuple[EstadoEvidenciaSemanticaEPI, ...] = field(default_factory=tuple)
    evidencias_negativas: Tuple[EstadoEvidenciaSemanticaEPI, ...] = field(default_factory=tuple)
    evidencias_ambiguas: Tuple[EstadoEvidenciaSemanticaEPI, ...] = field(default_factory=tuple)
    qualidade_anatomica: str = "INSUFICIENTE"
    metodo: str = "SEM_EVIDENCIA"
    motivos: Tuple[str, ...] = field(default_factory=tuple)
    atualizado_em: datetime = field(default_factory=_agora_utc)

    def __post_init__(self):
        if self.estado not in ESTADOS_EPI_VALIDOS:
            raise ValueError(f"Estado individual de EPI inválido: {self.estado}")


@dataclass(frozen=True)
class EstadoEPITemporal:
    camera_id: int
    track_id: int
    track_instance_id: str
    epi: str
    estado_instantaneo: str
    estado_candidato: Optional[str] = None
    estado_confirmado: Optional[str] = None
    candidato_desde: Optional[float] = None
    confirmado_desde: Optional[float] = None
    ultima_observacao: float = 0.0
    quantidade_observacoes_candidato: int = 0
    status_temporal: str = "SEM_ESTADO_CONFIRMADO"
    atualizado_em: datetime = field(default_factory=_agora_utc)

    def __post_init__(self):
        if self.estado_instantaneo not in ESTADOS_EPI_VALIDOS:
            raise ValueError(
                f"Estado instantâneo temporal inválido: {self.estado_instantaneo}"
            )
        if (
            self.estado_candidato is not None
            and self.estado_candidato not in ESTADOS_EPI_VALIDOS
        ):
            raise ValueError(
                f"Estado candidato temporal inválido: {self.estado_candidato}"
            )
        if (
            self.estado_confirmado is not None
            and self.estado_confirmado not in ESTADOS_EPI_VALIDOS
        ):
            raise ValueError(
                f"Estado confirmado temporal inválido: {self.estado_confirmado}"
            )


@dataclass
class PessoaTrack:
    camera_id: int
    track_id: int
    # UUID exclusivo do ciclo de vida do track. Impede que eventual
    # reutilização futura de um track_id seja interpretada como
    # continuidade automática da pessoa anterior.
    track_instance_id: str
    ativo: bool = True
    detectado_no_frame: bool = True
    frames_sem_deteccao: int = 0
    bbox: Optional[Tuple[float, float, float, float]] = None
    confianca: Optional[float] = None
    keypoints: Dict[str, EstadoKeypoint] = field(default_factory=dict)
    primeira_deteccao_em: Optional[datetime] = None
    ultima_deteccao_em: Optional[datetime] = None
    identidade: IdentidadePessoa = field(
        default_factory=IdentidadePessoa
    )
    epis: Dict[str, EstadoEPI] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenciaIncidenteEPI:
    evidencia_id: str
    incidente_id: str
    criado_em: datetime
    criado_monotonico: float
    caminho_frame: Optional[str] = None
    caminho_crop: Optional[str] = None
    falhas: Tuple[str, ...] = field(default_factory=tuple)


@dataclass
class EstadoIncidente:
    incidente_id: str
    ambiente_id: Optional[str]
    ambiente_nome: str
    camera_id: int
    camera_nome: str
    track_id: int
    track_instance_id: str
    epi: str
    tipo_irregularidade: str
    estado_incidente: str = INCIDENTE_ATIVO
    motivo_encerramento: Optional[str] = None
    iniciado_em: datetime = field(default_factory=_agora_utc)
    iniciado_monotonico: float = 0.0
    ultima_observacao_em: Optional[datetime] = None
    ultima_observacao_monotonica: Optional[float] = None
    ultima_tentativa_evidencia_em: Optional[datetime] = None
    ultima_tentativa_evidencia_monotonica: Optional[float] = None
    ultima_evidencia_em: Optional[datetime] = None
    ultima_evidencia_monotonica: Optional[float] = None
    encerrado_em: Optional[datetime] = None
    encerrado_monotonico: Optional[float] = None
    matricula: str = "--"
    nome: str = "DESCONHECIDO"
    cargo: str = "--"
    status_identidade: str = IDENTIDADE_NAO_AVALIADO
    identidade_atualizada_em: Optional[datetime] = None
    evidencias: List[EvidenciaIncidenteEPI] = field(default_factory=list)
    falhas_evidencia: List[str] = field(default_factory=list)
    falhas_persistencia: List[str] = field(default_factory=list)

    @property
    def ativo(self) -> bool:
        return self.estado_incidente != INCIDENTE_ENCERRADO

    @property
    def tipo_ocorrencia(self) -> str:
        return self.tipo_irregularidade


@dataclass
class EstadoNotificacao:
    notificacao_id: str
    incidente_id: str
    severidade: str = "ALTA"
    alerta_visual_ativo: bool = True
    suspensa: bool = False
    encerrada: bool = False
    iniciado_em: datetime = field(default_factory=_agora_utc)
    iniciado_monotonico: float = 0.0
    tempo_ativo_acumulado: float = 0.0
    ultima_referencia_monotonica: Optional[float] = None
    ultimo_audio_monotonico: Optional[float] = None
    quantidade_audios: int = 0
    audio_em_fila: bool = False
    proxima_tentativa_audio_monotonica: float = 0.0
    ultima_falha_audio: Optional[str] = None
    status_email: str = NOTIFICACAO_EMAIL_NAO_AGENDADO
    tentativas_email: int = 0
    ultimo_envio_email_monotonico: Optional[float] = None
    ultima_tentativa_email_monotonica: Optional[float] = None
    proxima_tentativa_email_monotonica: float = 0.0
    ultima_falha_email: Optional[str] = None
    identidade_notificada: Optional[str] = None
    atualizado_em: datetime = field(default_factory=_agora_utc)


@dataclass
class MetricasRuntime:
    fps_global: Optional[float] = None
    fps_por_camera: Dict[int, Optional[float]] = field(
        default_factory=dict
    )
    latencia_ppe_ms: Optional[float] = None
    latencia_pose_ms: Optional[float] = None
    latencia_biometria_ms: Optional[float] = None
    latencia_pipeline_ms: Optional[float] = None


@dataclass
class EstadoCamera:
    camera_id: int
    nome: str
    tipo: str
    camera_uid: Optional[str] = None
    status_identidade: Optional[str] = None
    indice_runtime: Optional[int] = None
    status: str = CAMERA_OFFLINE
    ativa: bool = False
    ultimo_frame_em: Optional[float] = None
    ultima_leitura_ok_em: Optional[float] = None
    falhas_consecutivas: int = 0
    tracks_ativos: List[int] = field(default_factory=list)


@dataclass
class EstadoAmbiente:
    ambiente_id: Optional[str] = None
    nome: str = "Ambiente Principal"
    carregado: bool = False
    calibrado: bool = False
    camera_ids: List[int] = field(default_factory=list)
    cameras_associadas: List[Dict[str, Any]] = field(default_factory=list)
    epis_obrigatorios: List[str] = field(default_factory=list)
    objetos_globais: Dict[str, Dict[str, Any]] = field(
        default_factory=dict
    )

    @property
    def maquinarios(self) -> List[str]:
        return [
            objeto_id
            for objeto_id, objeto in self.objetos_globais.items()
            if isinstance(objeto, dict)
            and objeto.get("maquinario", False)
        ]


# ============================================================
# ESTADO CENTRAL
# ============================================================

class EstadoSistema:
    """
    Fonte central do estado operacional do runtime.

    Não executa captura, inferência, pose, tracking, biometria,
    decisão de incidente ou envio de notificações.

    Os contratos de incidente e notificação existem neste módulo,
    porém o EstadoSistema não replica os estados internos de
    decision_engine.py ou notificacoes.py nesta etapa.
    """

    def __init__(
        self,
        fase_execucao: str,
        ambiente: Optional[EstadoAmbiente] = None,
    ):
        self._lock = threading.RLock()
        self.fase_execucao = fase_execucao
        self.ambiente = ambiente or EstadoAmbiente()
        self.cameras: Dict[int, EstadoCamera] = {}
        self.pessoas: Dict[Tuple[int, str], PessoaTrack] = {}
        # ETAPA 6: fonte operacional das associações do frame atual.
        # PessoaTrack permanece sem responsabilidade de associação.
        self.associacoes_epi: Dict[
            Tuple[int, str], List[EstadoAssociacaoEPI]
        ] = {}
        self.evidencias_epi_sem_associacao: Dict[
            int, List[EstadoAssociacaoEPI]
        ] = {}
        # ETAPA 7: estado semântico INSTANTÂNEO do frame atual, separado
        # de PessoaTrack.epis e sem qualquer estabilização temporal.
        self.estados_epi_individuais: Dict[
            Tuple[int, str, str], EstadoEPIIndividual
        ] = {}
        # ETAPA 8: memória temporal individual isolada por câmera, ciclo
        # de vida do track e EPI. Não substitui o estado instantâneo.
        self.estados_epi_temporais: Dict[
            Tuple[int, str, str], EstadoEPITemporal
        ] = {}
        # ETAPA 10: fonte única de verdade operacional dos incidentes.
        self.incidentes: Dict[str, EstadoIncidente] = {}
        self.indice_incidentes_ativos: Dict[Tuple[Optional[str], int, str, str], str] = {}
        # ETAPA 11: estado operacional de entrega por incidente_id.
        self.notificacoes_incidentes: Dict[str, EstadoNotificacao] = {}
        self.metricas_runtime = MetricasRuntime()
        self.iniciado_em = _agora_utc()
        self.atualizado_em = self.iniciado_em

    # --------------------------------------------------------
    # FASE
    # --------------------------------------------------------

    def definir_fase(self, fase_execucao: str) -> None:
        with self._lock:
            self.fase_execucao = fase_execucao
            self._marcar_atualizacao()

    # --------------------------------------------------------
    # AMBIENTE LEGADO
    # --------------------------------------------------------

    def atualizar_ambiente_legado(
        self,
        nome: str,
        calibrado: bool,
        epis_obrigatorios,
        objetos_globais,
    ) -> None:
        with self._lock:
            self.ambiente.nome = nome
            self.ambiente.calibrado = bool(calibrado)
            self.ambiente.carregado = bool(
                calibrado
                or objetos_globais
                or epis_obrigatorios
            )
            self.ambiente.epis_obrigatorios = list(
                epis_obrigatorios or []
            )
            self.ambiente.objetos_globais = dict(
                objetos_globais or {}
            )
            # ambiente_id permanece intencionalmente indefinido
            # até a ETAPA 3.
            self.ambiente.ambiente_id = None
            self._marcar_atualizacao()

    # --------------------------------------------------------
    # AMBIENTE DE PERFIL - ETAPA 3
    # --------------------------------------------------------

    def ativar_ambiente_perfil(
        self,
        ambiente_id: str,
        nome: str,
        calibrado: bool,
        cameras_associadas,
        epis_obrigatorios,
        objetos_globais,
    ) -> None:
        with self._lock:
            mudou_ambiente = (
                self.ambiente.ambiente_id != ambiente_id
            )

            self.ambiente.ambiente_id = ambiente_id
            self.ambiente.nome = nome
            self.ambiente.carregado = True
            self.ambiente.calibrado = bool(calibrado)

            if mudou_ambiente:
                self.ambiente.camera_ids = []

            self.ambiente.cameras_associadas = [
                dict(camera)
                for camera in (cameras_associadas or [])
                if isinstance(camera, dict)
            ]
            self.ambiente.epis_obrigatorios = list(
                epis_obrigatorios or []
            )
            self.ambiente.objetos_globais = dict(
                objetos_globais or {}
            )
            if mudou_ambiente:
                for chave_base, incidente_id in list(self.indice_incidentes_ativos.items()):
                    incidente = self.incidentes.get(incidente_id)
                    if incidente is not None:
                        incidente.estado_incidente = INCIDENTE_ENCERRADO
                        incidente.motivo_encerramento = "TROCA_AMBIENTE"
                        incidente.encerrado_em = _agora_utc()
                    self.indice_incidentes_ativos.pop(chave_base, None)
                # Barreira de estado entre ambientes: nenhum estado
                # operacional transitório do ambiente anterior pode
                # sobreviver sob o novo ambiente ativo. Persistências
                # (perfil, registry, biometria etc.) não são afetadas.
                self.cameras.clear()
                self.pessoas.clear()
                self.associacoes_epi.clear()
                self.evidencias_epi_sem_associacao.clear()
                self.estados_epi_individuais.clear()
                self.estados_epi_temporais.clear()
                self.metricas_runtime.fps_por_camera.clear()

            self._marcar_atualizacao()

    # --------------------------------------------------------
    # CÂMERAS
    # --------------------------------------------------------

    def registrar_camera(
        self,
        camera_id: int,
        nome: str,
        tipo: str,
        ativa: bool = True,
        status: str = CAMERA_ONLINE,
        camera_uid: Optional[str] = None,
        status_identidade: Optional[str] = None,
        indice_runtime: Optional[int] = None,
    ) -> None:
        with self._lock:
            camera = self.cameras.get(camera_id)

            if camera is None:
                camera = EstadoCamera(
                    camera_id=camera_id,
                    nome=nome,
                    tipo=tipo,
                )
                self.cameras[camera_id] = camera

            camera.nome = nome
            camera.tipo = tipo
            camera.camera_uid = camera_uid
            camera.status_identidade = status_identidade
            camera.indice_runtime = indice_runtime
            camera.ativa = bool(ativa)
            camera.status = status

            if camera_id not in self.ambiente.camera_ids:
                self.ambiente.camera_ids.append(camera_id)
                self.ambiente.camera_ids.sort()

            self._marcar_atualizacao()

    def atualizar_camera_runtime(
        self,
        camera_id: int,
        status: Optional[str] = None,
        ativa: Optional[bool] = None,
        ultimo_frame_em: Optional[float] = None,
        ultima_leitura_ok_em: Optional[float] = None,
        falhas_consecutivas: Optional[int] = None,
    ) -> None:
        with self._lock:
            camera = self.cameras.get(camera_id)

            if camera is None:
                return

            if status is not None:
                camera.status = status

            if ativa is not None:
                camera.ativa = bool(ativa)

            if ultimo_frame_em is not None:
                camera.ultimo_frame_em = ultimo_frame_em

            if ultima_leitura_ok_em is not None:
                camera.ultima_leitura_ok_em = ultima_leitura_ok_em

            if falhas_consecutivas is not None:
                camera.falhas_consecutivas = falhas_consecutivas

            self._marcar_atualizacao()

    # --------------------------------------------------------
    # PESSOAS / POSE - ETAPA 5
    # --------------------------------------------------------

    def atualizar_pessoas_camera(
        self,
        camera_id: int,
        tracks,
        preservar_estados_temporais_ausentes: bool = False,
    ) -> None:
        """
        Atualiza a projeção operacional dos tracks de uma câmera.

        A chave interna usa camera_id + track_instance_id. O track_id
        continua disponível para exibição/uso local, mas não é usado
        sozinho como identidade durável do ciclo de vida.

        preservar_estados_temporais_ausentes=True é usado somente quando
        a câmera está temporariamente sem observação válida. Nesse caso o
        tracker pode expirar seus tracks por ciclos internos, mas a memória
        temporal de EPI permanece sob responsabilidade da ETAPA 8 e de seu
        relógio monotônico. Em atualização normal, tracks realmente
        encerrados continuam limpando imediatamente sua memória temporal.
        """
        with self._lock:
            camera_id = int(camera_id)
            chaves_ativas = set()
            track_ids_ativos = []

            for track in tracks or []:
                instance_id = str(track.track_instance_id)
                chave = (camera_id, instance_id)
                chaves_ativas.add(chave)
                track_ids_ativos.append(int(track.track_id))

                keypoints = {}
                for nome, keypoint in (track.keypoints or {}).items():
                    keypoints[str(nome)] = EstadoKeypoint(
                        indice=int(keypoint.indice),
                        nome=str(keypoint.nome),
                        x=(None if keypoint.x is None else float(keypoint.x)),
                        y=(None if keypoint.y is None else float(keypoint.y)),
                        confianca=(
                            None
                            if keypoint.confianca is None
                            else float(keypoint.confianca)
                        ),
                        confiavel=bool(keypoint.confiavel),
                    )

                pessoa = self.pessoas.get(chave)
                if pessoa is None:
                    pessoa = PessoaTrack(
                        camera_id=camera_id,
                        track_id=int(track.track_id),
                        track_instance_id=instance_id,
                    )
                    self.pessoas[chave] = pessoa

                pessoa.track_id = int(track.track_id)
                pessoa.ativo = True
                pessoa.detectado_no_frame = bool(track.detectado_no_frame)
                pessoa.frames_sem_deteccao = int(track.frames_sem_deteccao)
                pessoa.bbox = tuple(float(v) for v in track.bbox)
                pessoa.confianca = float(track.confianca)
                pessoa.keypoints = keypoints
                pessoa.primeira_deteccao_em = track.primeira_deteccao_em
                pessoa.ultima_deteccao_em = track.ultima_deteccao_em

            remover = [
                chave
                for chave, pessoa in self.pessoas.items()
                if pessoa.camera_id == camera_id
                and chave not in chaves_ativas
            ]
            for chave in remover:
                self.pessoas.pop(chave, None)
                self.associacoes_epi.pop(chave, None)
                remover_estados = [
                    chave_estado
                    for chave_estado in self.estados_epi_individuais
                    if chave_estado[0] == camera_id
                    and chave_estado[1] == chave[1]
                ]
                for chave_estado in remover_estados:
                    self.estados_epi_individuais.pop(chave_estado, None)
                if not preservar_estados_temporais_ausentes:
                    remover_temporais = [
                        chave_estado
                        for chave_estado in self.estados_epi_temporais
                        if chave_estado[0] == camera_id
                        and chave_estado[1] == chave[1]
                    ]
                    for chave_estado in remover_temporais:
                        self.estados_epi_temporais.pop(chave_estado, None)
                    self._encerrar_incidentes_track_locked(
                        camera_id=camera_id,
                        track_instance_id=chave[1],
                        motivo="TRACK_ENCERRADO",
                    )

            camera = self.cameras.get(camera_id)
            if camera is not None:
                camera.tracks_ativos = sorted(set(track_ids_ativos))

            self._marcar_atualizacao()

    def encerrar_pessoas_camera(self, camera_id: int) -> None:
        with self._lock:
            camera_id = int(camera_id)
            remover = [
                chave
                for chave, pessoa in self.pessoas.items()
                if pessoa.camera_id == camera_id
            ]
            for chave in remover:
                self._encerrar_incidentes_track_locked(
                    camera_id=camera_id,
                    track_instance_id=chave[1],
                    motivo="CAMERA_ENCERRADA",
                )
                self.pessoas.pop(chave, None)
                self.associacoes_epi.pop(chave, None)

            remover_estados = [
                chave
                for chave in self.estados_epi_individuais
                if chave[0] == camera_id
            ]
            for chave in remover_estados:
                self.estados_epi_individuais.pop(chave, None)

            remover_temporais = [
                chave for chave in self.estados_epi_temporais
                if chave[0] == camera_id
            ]
            for chave in remover_temporais:
                self.estados_epi_temporais.pop(chave, None)

            self.evidencias_epi_sem_associacao.pop(camera_id, None)

            camera = self.cameras.get(camera_id)
            if camera is not None:
                camera.tracks_ativos = []

            self._marcar_atualizacao()

    # --------------------------------------------------------
    # BIOMETRIA / IDENTIDADE - ETAPA 9
    # --------------------------------------------------------

    def obter_contexto_biometria_camera(self, camera_id: int) -> List[Dict[str, Any]]:
        """Retorna somente dados leves necessários ao scheduler biométrico."""
        with self._lock:
            camera_id = int(camera_id)
            saida = []
            for pessoa in self.pessoas.values():
                if pessoa.camera_id != camera_id:
                    continue
                ident = pessoa.identidade
                saida.append({
                    "camera_id": pessoa.camera_id,
                    "track_id": pessoa.track_id,
                    "track_instance_id": pessoa.track_instance_id,
                    "detectado_no_frame": pessoa.detectado_no_frame,
                    "bbox": pessoa.bbox,
                    "keypoints": {
                        nome: {
                            "x": kp.x,
                            "y": kp.y,
                            "confianca": kp.confianca,
                            "confiavel": kp.confiavel,
                        }
                        for nome, kp in pessoa.keypoints.items()
                    },
                    "identidade": {
                        "status_identidade": ident.status_identidade,
                        "status_processamento": ident.status_processamento,
                        "matricula": ident.matricula,
                        "nome": ident.nome,
                        "cargo": ident.cargo,
                        "ultima_tentativa_monotonica": ident.ultima_tentativa_monotonica,
                        "job_pendente_id": ident.job_pendente_id,
                    },
                })
            saida.sort(key=lambda item: (item["track_id"], item["track_instance_id"]))
            return saida

    def marcar_rosto_biometrico_indisponivel(
        self,
        camera_id: int,
        track_instance_id: str,
        motivo: str,
    ) -> bool:
        with self._lock:
            chave = (int(camera_id), str(track_instance_id))
            pessoa = self.pessoas.get(chave)
            if pessoa is None:
                return False
            ident = pessoa.identidade
            if ident.status_identidade in {
                IDENTIDADE_NAO_AVALIADO,
                IDENTIDADE_AGUARDANDO_ROSTO,
                IDENTIDADE_INDETERMINADO,
            } and ident.job_pendente_id is None:
                ident.status_identidade = IDENTIDADE_AGUARDANDO_ROSTO
            ident.motivo = str(motivo)
            self._marcar_atualizacao()
            return True

    def marcar_job_biometria_pendente(
        self,
        camera_id: int,
        track_instance_id: str,
        job_id: str,
        observacao_id: str,
        agora_monotonico: float,
    ) -> bool:
        with self._lock:
            chave = (int(camera_id), str(track_instance_id))
            pessoa = self.pessoas.get(chave)
            if pessoa is None or not pessoa.detectado_no_frame:
                return False
            ident = pessoa.identidade
            if ident.job_pendente_id is not None:
                return False
            if str(job_id) in ident.jobs_processados:
                return False
            if str(observacao_id) in ident.observacoes_processadas:
                return False
            ident.job_pendente_id = str(job_id)
            ident.observacao_pendente_id = str(observacao_id)
            ident.status_processamento = PROCESSAMENTO_BIOMETRIA_EM_FILA
            ident.tentativas += 1
            ident.ultima_tentativa_monotonica = float(agora_monotonico)
            ident.ultima_tentativa_em = _agora_utc()
            ident.motivo = "JOB_BIOMETRIA_EM_FILA"
            self._marcar_atualizacao()
            return True

    def marcar_job_biometria_identificando(
        self,
        camera_id: int,
        track_instance_id: str,
        job_id: str,
    ) -> bool:
        with self._lock:
            pessoa = self.pessoas.get((int(camera_id), str(track_instance_id)))
            if pessoa is None:
                return False
            ident = pessoa.identidade
            if ident.job_pendente_id != str(job_id):
                return False
            ident.status_processamento = PROCESSAMENTO_BIOMETRIA_IDENTIFICANDO
            ident.motivo = "JOB_BIOMETRIA_IDENTIFICANDO"
            self._marcar_atualizacao()
            return True

    @staticmethod
    def _registrar_id_consumido(lista: List[str], valor: str, limite: int = 32) -> None:
        valor = str(valor)
        if valor not in lista:
            lista.append(valor)
        if len(lista) > limite:
            del lista[:-limite]

    def aplicar_resultado_biometria(
        self,
        camera_id: int,
        track_instance_id: str,
        job_id: str,
        observacao_id: str,
        status_resultado: str,
        matricula: Optional[str],
        nome: Optional[str],
        cargo: Optional[str],
        distancia_match: Optional[float],
        metodo: Optional[str],
        modelo: Optional[str],
        motivo: str,
        confirmacoes_identidade: int,
        confirmacoes_desconhecido: int,
        conflitos_para_invalidar: int,
    ) -> bool:
        """Aplica uma observação biométrica independente ao track atual.

        Resultado duplicado do mesmo job ou da mesma observação nunca conta
        novamente. Se o track já terminou, o resultado é simplesmente obsoleto.
        """
        with self._lock:
            chave = (int(camera_id), str(track_instance_id))
            pessoa = self.pessoas.get(chave)
            if pessoa is None:
                return False

            ident = pessoa.identidade
            job_id = str(job_id)
            observacao_id = str(observacao_id)
            if job_id in ident.jobs_processados or observacao_id in ident.observacoes_processadas:
                return False
            if ident.job_pendente_id != job_id or ident.observacao_pendente_id != observacao_id:
                return False

            self._registrar_id_consumido(ident.jobs_processados, job_id)
            self._registrar_id_consumido(ident.observacoes_processadas, observacao_id)
            ident.job_pendente_id = None
            ident.observacao_pendente_id = None
            ident.status_processamento = PROCESSAMENTO_BIOMETRIA_OCIOSO
            ident.metodo = metodo
            ident.modelo = modelo
            ident.motivo = str(motivo)

            status_resultado = str(status_resultado)
            conclusivo = status_resultado in {"MATCH", "SEM_MATCH"}
            if conclusivo:
                ident.tentativas_validas += 1

            if status_resultado == "MATCH" and matricula and nome:
                matricula = str(matricula)
                if ident.status_identidade == IDENTIDADE_IDENTIFICADO:
                    if ident.matricula == matricula:
                        ident.confianca = None if distancia_match is None else max(0.0, 1.0 - float(distancia_match))
                        ident.distancia_match = None if distancia_match is None else float(distancia_match)
                        ident.ultima_confirmacao_em = _agora_utc()
                        ident.candidato_conflito = None
                        ident.confirmacoes_conflito = 0
                        ident.motivo = "IDENTIDADE_REVALIDADA"
                    else:
                        if ident.candidato_conflito == matricula:
                            ident.confirmacoes_conflito += 1
                        else:
                            ident.candidato_conflito = matricula
                            ident.confirmacoes_conflito = 1
                        ident.motivo = "CONFLITO_IDENTIDADE"
                        if ident.confirmacoes_conflito >= max(1, int(conflitos_para_invalidar)):
                            ident.conhecida = False
                            ident.status_identidade = IDENTIDADE_INDETERMINADO
                            ident.matricula = "--"
                            ident.nome = "DESCONHECIDO"
                            ident.cargo = "--"
                            ident.identificada_em = None
                            ident.ultima_confirmacao_em = None
                            ident.candidato_matricula = matricula
                            ident.candidato_nome = str(nome)
                            ident.candidato_cargo = str(cargo or "--")
                            ident.confirmacoes_candidato = 1
                            ident.confirmacoes_desconhecido = 0
                            ident.candidato_conflito = None
                            ident.confirmacoes_conflito = 0
                            ident.motivo = "IDENTIDADE_INVALIDADA_POR_CONFLITO"
                else:
                    ident.confirmacoes_desconhecido = 0
                    if ident.candidato_matricula == matricula:
                        ident.confirmacoes_candidato += 1
                    else:
                        ident.candidato_matricula = matricula
                        ident.candidato_nome = str(nome)
                        ident.candidato_cargo = str(cargo or "--")
                        ident.confirmacoes_candidato = 1
                    ident.status_identidade = IDENTIDADE_INDETERMINADO
                    ident.motivo = "CANDIDATO_IDENTIDADE"
                    if ident.confirmacoes_candidato >= max(1, int(confirmacoes_identidade)):
                        ident.conhecida = True
                        ident.status_identidade = IDENTIDADE_IDENTIFICADO
                        ident.matricula = matricula
                        ident.nome = str(nome)
                        ident.cargo = str(cargo or "--")
                        ident.distancia_match = None if distancia_match is None else float(distancia_match)
                        ident.confianca = None if distancia_match is None else max(0.0, 1.0 - float(distancia_match))
                        agora = _agora_utc()
                        ident.identificada_em = agora
                        ident.ultima_confirmacao_em = agora
                        ident.candidato_matricula = None
                        ident.candidato_nome = None
                        ident.candidato_cargo = None
                        ident.confirmacoes_candidato = 0
                        ident.candidato_conflito = None
                        ident.confirmacoes_conflito = 0
                        ident.motivo = "IDENTIDADE_CONFIRMADA"

            elif status_resultado == "SEM_MATCH":
                if ident.status_identidade == IDENTIDADE_IDENTIFICADO:
                    ident.motivo = "SEM_MATCH_ISOLADO_IDENTIDADE_PRESERVADA"
                else:
                    ident.candidato_matricula = None
                    ident.candidato_nome = None
                    ident.candidato_cargo = None
                    ident.confirmacoes_candidato = 0
                    ident.confirmacoes_desconhecido += 1
                    ident.status_identidade = IDENTIDADE_INDETERMINADO
                    ident.conhecida = False
                    ident.matricula = "--"
                    ident.nome = "DESCONHECIDO"
                    ident.cargo = "--"
                    ident.motivo = "CANDIDATO_DESCONHECIDO"
                    if ident.confirmacoes_desconhecido >= max(1, int(confirmacoes_desconhecido)):
                        ident.status_identidade = IDENTIDADE_DESCONHECIDO
                        ident.motivo = "DESCONHECIDO_CONFIRMADO"

            elif status_resultado in {"AMBIGUO", "DADOS_OPERADOR_AUSENTES", "BASE_VAZIA", "ERRO"}:
                if ident.status_identidade not in {IDENTIDADE_IDENTIFICADO, IDENTIDADE_DESCONHECIDO}:
                    ident.status_identidade = IDENTIDADE_INDETERMINADO
                ident.motivo = str(motivo or status_resultado)

            self._marcar_atualizacao()
            return True

    # --------------------------------------------------------
    # INCIDENTES DE EPI - ETAPA 10
    # --------------------------------------------------------

    @staticmethod
    def _chave_incidente_base(ambiente_id, camera_id, track_instance_id, epi):
        return (ambiente_id, int(camera_id), str(track_instance_id), str(epi))

    def obter_contexto_incidentes_camera(self, camera_id: int) -> Dict[str, Any]:
        with self._lock:
            camera_id = int(camera_id)
            pessoas = {}
            for pessoa in self.pessoas.values():
                if pessoa.camera_id != camera_id:
                    continue
                ident = pessoa.identidade
                pessoas[pessoa.track_instance_id] = {
                    "track_id": pessoa.track_id,
                    "track_instance_id": pessoa.track_instance_id,
                    "bbox": pessoa.bbox,
                    "detectado_no_frame": pessoa.detectado_no_frame,
                    "identidade": {
                        "status_identidade": ident.status_identidade,
                        "matricula": ident.matricula,
                        "nome": ident.nome,
                        "cargo": ident.cargo,
                    },
                }
            estados = [
                item for chave, item in self.estados_epi_temporais.items()
                if chave[0] == camera_id
            ]
            estados.sort(key=lambda item: (item.track_instance_id, item.epi))
            camera = self.cameras.get(camera_id)
            return {
                "ambiente": {
                    "ambiente_id": self.ambiente.ambiente_id,
                    "nome": self.ambiente.nome,
                },
                "camera_nome": None if camera is None else camera.nome,
                "pessoas": pessoas,
                "estados_temporais": tuple(estados),
            }

    def garantir_incidente_epi_atomico(
        self, ambiente_id, ambiente_nome, camera_id, camera_nome, track_id,
        track_instance_id, epi, tipo_irregularidade, identidade,
        agora_monotonico: float, agora_datetime: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            agora_datetime = agora_datetime or _agora_utc()
            chave = self._chave_incidente_base(ambiente_id, camera_id, track_instance_id, epi)
            incidente_id = self.indice_incidentes_ativos.get(chave)
            incidente_atual = self.incidentes.get(incidente_id) if incidente_id else None
            encerrado_anterior = None
            if incidente_atual is not None and incidente_atual.tipo_irregularidade != str(tipo_irregularidade):
                incidente_atual.estado_incidente = INCIDENTE_ENCERRADO
                incidente_atual.motivo_encerramento = "MUDANCA_TIPO_IRREGULARIDADE"
                incidente_atual.encerrado_em = agora_datetime
                incidente_atual.encerrado_monotonico = float(agora_monotonico)
                encerrado_anterior = incidente_atual
                self.indice_incidentes_ativos.pop(chave, None)
                incidente_atual = None

            criado = False
            reativado = False
            if incidente_atual is None:
                incidente_atual = EstadoIncidente(
                    incidente_id=str(uuid.uuid4()),
                    ambiente_id=ambiente_id,
                    ambiente_nome=str(ambiente_nome or "Ambiente"),
                    camera_id=int(camera_id),
                    camera_nome=str(camera_nome or f"Camera {camera_id}"),
                    track_id=int(track_id),
                    track_instance_id=str(track_instance_id),
                    epi=str(epi),
                    tipo_irregularidade=str(tipo_irregularidade),
                    iniciado_em=agora_datetime,
                    iniciado_monotonico=float(agora_monotonico),
                    ultima_observacao_em=agora_datetime,
                    ultima_observacao_monotonica=float(agora_monotonico),
                )
                self.incidentes[incidente_atual.incidente_id] = incidente_atual
                self.indice_incidentes_ativos[chave] = incidente_atual.incidente_id
                criado = True
            else:
                if incidente_atual.estado_incidente == INCIDENTE_OBSERVACAO_SUSPENSA:
                    incidente_atual.estado_incidente = INCIDENTE_ATIVO
                    reativado = True
                incidente_atual.ultima_observacao_em = agora_datetime
                incidente_atual.ultima_observacao_monotonica = float(agora_monotonico)
                incidente_atual.track_id = int(track_id)
                incidente_atual.camera_nome = str(camera_nome or incidente_atual.camera_nome)

            identidade = identidade or {}
            status_identidade = str(identidade.get("status_identidade") or IDENTIDADE_NAO_AVALIADO)
            if status_identidade:
                incidente_atual.status_identidade = status_identidade
                incidente_atual.matricula = str(identidade.get("matricula") or "--")
                incidente_atual.nome = str(identidade.get("nome") or "DESCONHECIDO")
                incidente_atual.cargo = str(identidade.get("cargo") or "--")
                incidente_atual.identidade_atualizada_em = agora_datetime

            self._marcar_atualizacao()
            return {
                "incidente": incidente_atual,
                "criado": criado,
                "reativado": reativado,
                "encerrado_anterior": encerrado_anterior,
            }

    def encerrar_incidente_epi_base(
        self, ambiente_id, camera_id, track_instance_id, epi, motivo,
        agora_monotonico: float, agora_datetime: Optional[datetime] = None,
    ):
        with self._lock:
            chave = self._chave_incidente_base(ambiente_id, camera_id, track_instance_id, epi)
            incidente_id = self.indice_incidentes_ativos.pop(chave, None)
            if incidente_id is None:
                return None
            incidente = self.incidentes.get(incidente_id)
            if incidente is None:
                return None
            incidente.estado_incidente = INCIDENTE_ENCERRADO
            incidente.motivo_encerramento = str(motivo)
            incidente.encerrado_em = agora_datetime or _agora_utc()
            incidente.encerrado_monotonico = float(agora_monotonico)
            self._marcar_atualizacao()
            return incidente

    def suspender_incidente_epi_base(
        self, ambiente_id, camera_id, track_instance_id, epi,
        agora_monotonico: float, agora_datetime: Optional[datetime] = None,
        motivo: Optional[str] = None,
    ):
        with self._lock:
            chave = self._chave_incidente_base(ambiente_id, camera_id, track_instance_id, epi)
            incidente_id = self.indice_incidentes_ativos.get(chave)
            incidente = self.incidentes.get(incidente_id) if incidente_id else None
            if incidente is None or incidente.estado_incidente == INCIDENTE_OBSERVACAO_SUSPENSA:
                return None
            incidente.estado_incidente = INCIDENTE_OBSERVACAO_SUSPENSA
            self._marcar_atualizacao()
            return incidente

    def _encerrar_incidentes_track_locked(self, camera_id: int, track_instance_id: str, motivo: str):
        agora = _agora_utc()
        for chave, incidente_id in list(self.indice_incidentes_ativos.items()):
            if chave[1] != int(camera_id) or chave[2] != str(track_instance_id):
                continue
            incidente = self.incidentes.get(incidente_id)
            if incidente is not None:
                incidente.estado_incidente = INCIDENTE_ENCERRADO
                incidente.motivo_encerramento = str(motivo)
                incidente.encerrado_em = agora
            self.indice_incidentes_ativos.pop(chave, None)

    def marcar_tentativa_evidencia_incidente(self, incidente_id, agora_monotonico, agora_datetime=None):
        with self._lock:
            incidente = self.incidentes.get(str(incidente_id))
            if incidente is None:
                return False
            incidente.ultima_tentativa_evidencia_monotonica = float(agora_monotonico)
            incidente.ultima_tentativa_evidencia_em = agora_datetime or _agora_utc()
            self._marcar_atualizacao()
            return True

    def registrar_evidencia_incidente(
        self, incidente_id, evidencia_id, caminho_frame, caminho_crop,
        agora_monotonico, agora_datetime=None, falhas=(),
    ):
        with self._lock:
            incidente = self.incidentes.get(str(incidente_id))
            if incidente is None:
                return None
            import os as _os
            frame = caminho_frame if caminho_frame and _os.path.exists(caminho_frame) else None
            crop = caminho_crop if caminho_crop and _os.path.exists(caminho_crop) else None
            if frame is None and crop is None:
                return None
            evidencia = EvidenciaIncidenteEPI(
                evidencia_id=str(evidencia_id), incidente_id=incidente.incidente_id,
                criado_em=agora_datetime or _agora_utc(),
                criado_monotonico=float(agora_monotonico),
                caminho_frame=frame, caminho_crop=crop,
                falhas=tuple(str(x) for x in falhas),
            )
            incidente.evidencias.append(evidencia)
            incidente.ultima_evidencia_em = evidencia.criado_em
            incidente.ultima_evidencia_monotonica = evidencia.criado_monotonico
            self._marcar_atualizacao()
            return evidencia

    def registrar_falha_evidencia_incidente(self, incidente_id, detalhe, agora_datetime=None):
        with self._lock:
            incidente = self.incidentes.get(str(incidente_id))
            if incidente is None:
                return None
            incidente.falhas_evidencia.append(str(detalhe))
            self._marcar_atualizacao()
            return incidente

    def registrar_falha_persistencia_incidente(self, incidente_id, detalhe, agora_datetime=None):
        with self._lock:
            incidente = self.incidentes.get(str(incidente_id))
            if incidente is None:
                return None
            incidente.falhas_persistencia.append(str(detalhe))
            self._marcar_atualizacao()
            return incidente

    def enriquecer_incidentes_identidade(self, camera_id, track_instance_id, identidade, agora_datetime=None):
        with self._lock:
            identidade = identidade or {}
            if str(identidade.get("status_identidade")) != IDENTIDADE_IDENTIFICADO:
                return []
            atualizados = []
            for incidente in self.incidentes.values():
                if incidente.camera_id != int(camera_id) or incidente.track_instance_id != str(track_instance_id):
                    continue
                matricula = str(identidade.get("matricula") or "--")
                nome = str(identidade.get("nome") or "DESCONHECIDO")
                cargo = str(identidade.get("cargo") or "--")
                atual = (incidente.matricula, incidente.nome, incidente.cargo, incidente.status_identidade)
                novo = (matricula, nome, cargo, IDENTIDADE_IDENTIFICADO)
                if atual == novo:
                    continue
                incidente.matricula = matricula
                incidente.nome = nome
                incidente.cargo = cargo
                incidente.status_identidade = IDENTIDADE_IDENTIFICADO
                incidente.identidade_atualizada_em = agora_datetime or _agora_utc()
                atualizados.append(incidente)
            if atualizados:
                self._marcar_atualizacao()
            return atualizados

    def obter_incidentes_ativos(self):
        with self._lock:
            return tuple(
                self.incidentes[incidente_id]
                for incidente_id in self.indice_incidentes_ativos.values()
                if incidente_id in self.incidentes
            )

    def obter_incidentes_para_notificacao(self):
        with self._lock:
            return tuple(self.incidentes.values())

    # --------------------------------------------------------
    # NOTIFICACOES POR INCIDENTE - ETAPA 11
    # --------------------------------------------------------

    def sincronizar_notificacao_incidente(self, incidente_id, severidade, agora_monotonico, agora_datetime=None):
        with self._lock:
            incidente = self.incidentes.get(str(incidente_id))
            if incidente is None:
                return None
            agora = float(agora_monotonico)
            agora_dt = agora_datetime or _agora_utc()
            estado = self.notificacoes_incidentes.get(incidente.incidente_id)
            if estado is None:
                estado = EstadoNotificacao(
                    notificacao_id=str(uuid.uuid4()),
                    incidente_id=incidente.incidente_id,
                    severidade=str(severidade or "ALTA"),
                    alerta_visual_ativo=incidente.estado_incidente != INCIDENTE_ENCERRADO,
                    suspensa=incidente.estado_incidente == INCIDENTE_OBSERVACAO_SUSPENSA,
                    encerrada=incidente.estado_incidente == INCIDENTE_ENCERRADO,
                    iniciado_em=agora_dt,
                    iniciado_monotonico=agora,
                    ultima_referencia_monotonica=(
                        agora if incidente.estado_incidente == INCIDENTE_ATIVO else None
                    ),
                    status_email=(
                        NOTIFICACAO_EMAIL_CANCELADO
                        if incidente.estado_incidente == INCIDENTE_ENCERRADO
                        else NOTIFICACAO_EMAIL_AGUARDANDO_TEMPO
                    ),
                    atualizado_em=agora_dt,
                )
                self.notificacoes_incidentes[incidente.incidente_id] = estado
            else:
                # Acumula apenas tempo realmente observável em ATIVO.
                if estado.ultima_referencia_monotonica is not None:
                    delta = max(0.0, agora - estado.ultima_referencia_monotonica)
                    estado.tempo_ativo_acumulado += delta
                estado.ultima_referencia_monotonica = None
                estado.severidade = str(severidade or estado.severidade)
                if incidente.estado_incidente == INCIDENTE_ATIVO:
                    estado.suspensa = False
                    estado.encerrada = False
                    estado.alerta_visual_ativo = True
                    estado.ultima_referencia_monotonica = agora
                    if estado.status_email == NOTIFICACAO_EMAIL_CANCELADO:
                        estado.status_email = NOTIFICACAO_EMAIL_AGUARDANDO_TEMPO
                elif incidente.estado_incidente == INCIDENTE_OBSERVACAO_SUSPENSA:
                    estado.suspensa = True
                    estado.alerta_visual_ativo = True
                    estado.audio_em_fila = False
                else:
                    estado.encerrada = True
                    estado.suspensa = False
                    estado.alerta_visual_ativo = False
                    estado.audio_em_fila = False
                    if estado.status_email not in {NOTIFICACAO_EMAIL_ENVIADO}:
                        estado.status_email = NOTIFICACAO_EMAIL_CANCELADO
                estado.atualizado_em = agora_dt
            self._marcar_atualizacao()
            return estado

    def incidente_notificavel(self, incidente_id):
        with self._lock:
            incidente = self.incidentes.get(str(incidente_id))
            estado = self.notificacoes_incidentes.get(str(incidente_id))
            return bool(
                incidente is not None
                and estado is not None
                and incidente.estado_incidente == INCIDENTE_ATIVO
                and not estado.encerrada
                and not estado.suspensa
            )

    def obter_incidente_notificacao(self, incidente_id):
        with self._lock:
            incidente = self.incidentes.get(str(incidente_id))
            if incidente is None:
                return None
            evidencia = incidente.evidencias[-1] if incidente.evidencias else None
            return {
                "incidente_id": incidente.incidente_id,
                "ambiente_id": incidente.ambiente_id,
                "ambiente_nome": incidente.ambiente_nome,
                "camera_id": incidente.camera_id,
                "camera_nome": incidente.camera_nome,
                "track_id": incidente.track_id,
                "track_instance_id": incidente.track_instance_id,
                "epi": incidente.epi,
                "tipo_irregularidade": incidente.tipo_irregularidade,
                "estado_incidente": incidente.estado_incidente,
                "matricula": incidente.matricula,
                "nome": incidente.nome,
                "cargo": incidente.cargo,
                "status_identidade": incidente.status_identidade,
                "caminho_frame": None if evidencia is None else evidencia.caminho_frame,
                "caminho_crop": None if evidencia is None else evidencia.caminho_crop,
            }

    def obter_notificacoes_incidentes(self):
        with self._lock:
            return tuple(self.notificacoes_incidentes.values())

    def marcar_audio_enfileirado(self, incidente_id, enfileirado=True):
        with self._lock:
            estado = self.notificacoes_incidentes.get(str(incidente_id))
            if estado is None:
                return False
            estado.audio_em_fila = bool(enfileirado)
            estado.atualizado_em = _agora_utc()
            self._marcar_atualizacao()
            return True

    def registrar_resultado_audio(self, incidente_id, sucesso, agora_monotonico, detalhe=None, retry_segundos=0.0):
        with self._lock:
            estado = self.notificacoes_incidentes.get(str(incidente_id))
            if estado is None:
                return False
            estado.audio_em_fila = False
            if sucesso:
                estado.ultimo_audio_monotonico = float(agora_monotonico)
                estado.quantidade_audios += 1
                estado.ultima_falha_audio = None
            else:
                estado.ultima_falha_audio = str(detalhe or "FALHA_AUDIO")
                estado.proxima_tentativa_audio_monotonica = (
                    float(agora_monotonico) + max(0.0, float(retry_segundos))
                )
            estado.atualizado_em = _agora_utc()
            self._marcar_atualizacao()
            return True

    def registrar_rejeicao_fila_audio(self, incidente_id, detalhe, proxima_tentativa_monotonica):
        with self._lock:
            estado = self.notificacoes_incidentes.get(str(incidente_id))
            if estado is None:
                return False
            estado.audio_em_fila = False
            estado.ultima_falha_audio = str(detalhe)
            estado.proxima_tentativa_audio_monotonica = float(proxima_tentativa_monotonica)
            self._marcar_atualizacao()
            return True

    def marcar_email_em_fila(self, incidente_id, agora_monotonico):
        with self._lock:
            estado = self.notificacoes_incidentes.get(str(incidente_id))
            if estado is None or estado.encerrada:
                return False
            estado.status_email = NOTIFICACAO_EMAIL_EM_FILA
            estado.ultima_tentativa_email_monotonica = float(agora_monotonico)
            self._marcar_atualizacao()
            return True

    def marcar_email_enviando(self, incidente_id):
        with self._lock:
            estado = self.notificacoes_incidentes.get(str(incidente_id))
            if estado is None or estado.encerrada:
                return False
            estado.status_email = NOTIFICACAO_EMAIL_ENVIANDO
            self._marcar_atualizacao()
            return True

    def registrar_resultado_email(self, incidente_id, sucesso, agora_monotonico, detalhe=None, retry_segundos=0.0, max_tentativas=3):
        with self._lock:
            estado = self.notificacoes_incidentes.get(str(incidente_id))
            if estado is None:
                return False
            if estado.encerrada:
                estado.status_email = NOTIFICACAO_EMAIL_CANCELADO
                return False
            estado.tentativas_email += 1
            estado.ultima_tentativa_email_monotonica = float(agora_monotonico)
            if sucesso:
                estado.status_email = NOTIFICACAO_EMAIL_ENVIADO
                estado.ultimo_envio_email_monotonico = float(agora_monotonico)
                estado.ultima_falha_email = None
            else:
                estado.ultima_falha_email = str(detalhe or "FALHA_EMAIL")
                if estado.tentativas_email >= max(1, int(max_tentativas)):
                    estado.status_email = NOTIFICACAO_EMAIL_FALHOU
                else:
                    estado.status_email = NOTIFICACAO_EMAIL_AGUARDANDO_TEMPO
                    estado.proxima_tentativa_email_monotonica = float(agora_monotonico) + max(0.0, float(retry_segundos))
            self._marcar_atualizacao()
            return True

    def registrar_rejeicao_fila_email(self, incidente_id, detalhe, proxima_tentativa_monotonica):
        with self._lock:
            estado = self.notificacoes_incidentes.get(str(incidente_id))
            if estado is None or estado.encerrada:
                return False
            estado.status_email = NOTIFICACAO_EMAIL_AGUARDANDO_TEMPO
            estado.ultima_falha_email = str(detalhe)
            estado.proxima_tentativa_email_monotonica = float(proxima_tentativa_monotonica)
            self._marcar_atualizacao()
            return True

    def cancelar_email_incidente(self, incidente_id, detalhe="INCIDENTE_NAO_NOTIFICAVEL"):
        with self._lock:
            estado = self.notificacoes_incidentes.get(str(incidente_id))
            if estado is None:
                return False
            if estado.status_email != NOTIFICACAO_EMAIL_ENVIADO:
                estado.status_email = NOTIFICACAO_EMAIL_CANCELADO
                estado.ultima_falha_email = str(detalhe)
            self._marcar_atualizacao()
            return True

    def atualizar_latencia_biometria(self, latencia_biometria_ms: Optional[float]) -> None:
        with self._lock:
            self.metricas_runtime.latencia_biometria_ms = (
                None if latencia_biometria_ms is None else float(latencia_biometria_ms)
            )
            self._marcar_atualizacao()

    def obter_contexto_metricas_runtime(self) -> Dict[str, Any]:
        """Retorna somente o contexto leve necessário à instrumentação.

        Não expõe frames nem cria fonte paralela de estado operacional.
        """
        with self._lock:
            camera_ids = tuple(int(v) for v in self.ambiente.camera_ids)
            return {
                "ambiente_id": self.ambiente.ambiente_id,
                "camera_ids": camera_ids,
                "status_cameras": {
                    camera_id: (
                        self.cameras[camera_id].status
                        if camera_id in self.cameras
                        else CAMERA_OFFLINE
                    )
                    for camera_id in camera_ids
                },
            }

    def publicar_metricas_runtime(
        self,
        fps_global: Optional[float],
        fps_por_camera: Dict[int, Optional[float]],
        latencia_ppe_ms: Optional[float],
        latencia_pose_ms: Optional[float],
        latencia_biometria_ms: Optional[float],
        latencia_pipeline_ms: Optional[float],
    ) -> None:
        """Publica atomicamente a projeção atual das métricas de runtime."""
        with self._lock:
            self.metricas_runtime.fps_global = (
                None if fps_global is None else float(fps_global)
            )
            self.metricas_runtime.fps_por_camera = {
                int(camera_id): (None if valor is None else float(valor))
                for camera_id, valor in (fps_por_camera or {}).items()
            }
            self.metricas_runtime.latencia_ppe_ms = (
                None if latencia_ppe_ms is None else float(latencia_ppe_ms)
            )
            self.metricas_runtime.latencia_pose_ms = (
                None if latencia_pose_ms is None else float(latencia_pose_ms)
            )
            self.metricas_runtime.latencia_biometria_ms = (
                None if latencia_biometria_ms is None else float(latencia_biometria_ms)
            )
            self.metricas_runtime.latencia_pipeline_ms = (
                None if latencia_pipeline_ms is None else float(latencia_pipeline_ms)
            )
            self._marcar_atualizacao()

    # --------------------------------------------------------
    # ASSOCIAÇÃO EPI ↔ PESSOA - ETAPA 6
    # --------------------------------------------------------

    def obter_pessoas_camera_para_associacao(self, camera_id: int) -> List[Dict[str, Any]]:
        """Retorna uma projeção leve e imutável dos tracks da câmera.

        Somente dados necessários à geometria de associação são expostos.
        A função não cria uma segunda fonte persistente de pessoas.
        """
        with self._lock:
            camera_id = int(camera_id)
            saida = []
            for pessoa in self.pessoas.values():
                if pessoa.camera_id != camera_id:
                    continue
                saida.append({
                    "camera_id": pessoa.camera_id,
                    "track_id": pessoa.track_id,
                    "track_instance_id": pessoa.track_instance_id,
                    "detectado_no_frame": pessoa.detectado_no_frame,
                    "bbox": pessoa.bbox,
                    "keypoints": {
                        nome: {
                            "x": kp.x,
                            "y": kp.y,
                            "confianca": kp.confianca,
                            "confiavel": kp.confiavel,
                        }
                        for nome, kp in pessoa.keypoints.items()
                    },
                })
            return saida

    def obter_epis_obrigatorios_ambiente(self) -> List[str]:
        """Retorna os EPIs obrigatórios do ambiente ativo.

        ETAPA 6: a obrigatoriedade pertence ao ambiente, nunca à pessoa.
        A cópia evita expor a lista mutável interna fora do lock.
        """
        with self._lock:
            return list(self.ambiente.epis_obrigatorios)

    def atualizar_associacoes_epi_camera(
        self,
        camera_id: int,
        associacoes,
    ) -> None:
        """Substitui atomicamente as associações operacionais da câmera.

        A associação é recalculada a cada frame; não há estabilização temporal
        nem decisão CORRETO/INCORRETO/AUSENTE nesta etapa.
        """
        with self._lock:
            camera_id = int(camera_id)
            associacoes = list(associacoes or [])

            # Valida TODO o lote antes de remover o estado vigente. Assim,
            # um lote inconsistente não deixa a câmera sem seu último estado
            # válido nem corrige silenciosamente camera_id upstream.
            detection_ids = set()
            for assoc in associacoes:
                assoc_camera_id = int(assoc.camera_id)
                if assoc_camera_id != camera_id:
                    raise ValueError(
                        "Associação EPI com camera_id inconsistente: "
                        f"lote={camera_id}, associacao={assoc_camera_id}, "
                        f"detection_id={getattr(assoc, 'detection_id', '--')}"
                    )
                detection_id = str(assoc.detection_id)
                if detection_id in detection_ids:
                    raise ValueError(
                        "Detecção EPI duplicada no mesmo lote de câmera: "
                        f"camera_id={camera_id}, detection_id={detection_id}"
                    )
                detection_ids.add(detection_id)

            # Remove somente o estado anterior desta câmera.
            remover = [
                chave for chave in self.associacoes_epi
                if chave[0] == camera_id
            ]
            for chave in remover:
                self.associacoes_epi.pop(chave, None)

            por_track: Dict[Tuple[int, str], List[EstadoAssociacaoEPI]] = {}
            sem_associacao: List[EstadoAssociacaoEPI] = []

            def _float_opcional(valor):
                return None if valor is None else float(valor)

            def _str_opcional(valor):
                return None if valor is None else str(valor)

            for assoc in associacoes:
                estado = EstadoAssociacaoEPI(
                    detection_id=str(assoc.detection_id),
                    camera_id=int(assoc.camera_id),
                    classe_modelo=str(assoc.classe_modelo),
                    epi=str(assoc.epi),
                    tipo_deteccao=str(assoc.tipo_deteccao),
                    bbox_epi=tuple(float(v) for v in assoc.bbox_epi),
                    confianca_deteccao=float(assoc.confianca_deteccao),
                    status_associacao=str(assoc.status_associacao),
                    track_id=(None if assoc.track_id is None else int(assoc.track_id)),
                    track_instance_id=(
                        None if assoc.track_instance_id is None
                        else str(assoc.track_instance_id)
                    ),
                    score_assoc=_float_opcional(assoc.score_assoc),
                    score_segundo_candidato=_float_opcional(
                        assoc.score_segundo_candidato
                    ),
                    score_ownership=_float_opcional(
                        getattr(assoc, "score_ownership", None)
                    ),
                    componente_bbox=_float_opcional(
                        getattr(assoc, "componente_bbox", None)
                    ),
                    componente_proximidade_corpo=_float_opcional(
                        getattr(assoc, "componente_proximidade_corpo", None)
                    ),
                    componente_proximidade_keypoints=_float_opcional(
                        getattr(assoc, "componente_proximidade_keypoints", None)
                    ),
                    componente_regiao_esperada=_float_opcional(
                        getattr(assoc, "componente_regiao_esperada", None)
                    ),
                    distancia_corporal_normalizada=_float_opcional(
                        getattr(assoc, "distancia_corporal_normalizada", None)
                    ),
                    distancia_regiao_esperada_normalizada=_float_opcional(
                        getattr(
                            assoc,
                            "distancia_regiao_esperada_normalizada",
                            None,
                        )
                    ),
                    regiao_corporal_mais_proxima=_str_opcional(
                        getattr(assoc, "regiao_corporal_mais_proxima", None)
                    ),
                    regiao_esperada=_str_opcional(
                        getattr(assoc, "regiao_esperada", None)
                    ),
                    compatibilidade_regiao_esperada=_float_opcional(
                        getattr(assoc, "compatibilidade_regiao_esperada", None)
                    ),
                    metodo=_str_opcional(getattr(assoc, "metodo", None)),
                    metodo_regiao_esperada=_str_opcional(
                        getattr(assoc, "metodo_regiao_esperada", None)
                    ),
                    qualidade_geometrica=_str_opcional(
                        getattr(assoc, "qualidade_geometrica", None)
                    ),
                    candidatos=tuple(
                        (str(track_instance_id), float(score))
                        for track_instance_id, score in assoc.candidatos
                    ),
                )

                if (
                    estado.status_associacao == "ASSOCIADA"
                    and estado.track_instance_id is not None
                ):
                    chave = (camera_id, estado.track_instance_id)
                    por_track.setdefault(chave, []).append(estado)
                else:
                    sem_associacao.append(estado)

            for chave, itens in por_track.items():
                itens.sort(key=lambda item: item.detection_id)
                self.associacoes_epi[chave] = itens

            sem_associacao.sort(key=lambda item: item.detection_id)
            self.evidencias_epi_sem_associacao[camera_id] = sem_associacao
            self._marcar_atualizacao()

    def limpar_associacoes_epi_camera(self, camera_id: int) -> None:
        with self._lock:
            camera_id = int(camera_id)
            remover = [
                chave for chave in self.associacoes_epi
                if chave[0] == camera_id
            ]
            for chave in remover:
                self.associacoes_epi.pop(chave, None)
            self.evidencias_epi_sem_associacao.pop(camera_id, None)
            self._marcar_atualizacao()

    def obter_contexto_avaliacao_epi_camera(self, camera_id: int) -> Dict[str, Any]:
        """Retorna cópia leve dos insumos instantâneos da ETAPA 7.

        A obrigatoriedade vem exclusivamente do ambiente ativo. O método
        não consulta config.EPIS_OBRIGATORIOS nem o status agregado legado.
        """
        with self._lock:
            camera_id = int(camera_id)
            pessoas = []
            for (cid, _track_instance_id), pessoa in self.pessoas.items():
                if cid != camera_id:
                    continue
                pessoas.append({
                    "camera_id": pessoa.camera_id,
                    "track_id": pessoa.track_id,
                    "track_instance_id": pessoa.track_instance_id,
                    "detectado_no_frame": pessoa.detectado_no_frame,
                    "bbox": pessoa.bbox,
                    "keypoints": {
                        nome: {
                            "indice": kp.indice,
                            "x": kp.x,
                            "y": kp.y,
                            "confianca": kp.confianca,
                            "confiavel": kp.confiavel,
                        }
                        for nome, kp in pessoa.keypoints.items()
                    },
                })
            pessoas.sort(key=lambda p: (str(p["track_instance_id"]), int(p["track_id"])))

            associacoes = {
                chave: tuple(itens)
                for chave, itens in self.associacoes_epi.items()
                if chave[0] == camera_id
            }
            sem_associacao = tuple(
                self.evidencias_epi_sem_associacao.get(camera_id, [])
            )
            return {
                "camera_id": camera_id,
                "epis_obrigatorios": tuple(self.ambiente.epis_obrigatorios),
                "pessoas": tuple(pessoas),
                "associacoes_por_track": associacoes,
                "evidencias_sem_associacao": sem_associacao,
            }

    def atualizar_estados_epi_individuais_camera(
        self,
        camera_id: int,
        estados,
    ) -> None:
        """Substitui atomicamente o estado instantâneo da câmera.

        Não há debounce, histerese, votação, confirmação por frames ou
        reaproveitamento do estado anterior nesta etapa.
        """
        with self._lock:
            camera_id = int(camera_id)
            estados = list(estados or [])
            obrigatorios = set(self.ambiente.epis_obrigatorios)
            chaves_lote = set()

            for item in estados:
                if int(item.camera_id) != camera_id:
                    raise ValueError(
                        "Estado individual com camera_id inconsistente: "
                        f"lote={camera_id}, estado={item.camera_id}"
                    )
                epi = str(item.epi)
                if epi not in obrigatorios:
                    raise ValueError(
                        f"Estado individual produzido para EPI não obrigatório: {epi}"
                    )
                track_instance_id = str(item.track_instance_id)
                chave_pessoa = (camera_id, track_instance_id)
                pessoa = self.pessoas.get(chave_pessoa)
                if pessoa is None or not pessoa.detectado_no_frame:
                    raise ValueError(
                        "Estado individual sem pessoa detectada no frame atual: "
                        f"camera_id={camera_id}, track_instance_id={track_instance_id}"
                    )
                chave = (camera_id, track_instance_id, epi)
                if chave in chaves_lote:
                    raise ValueError(f"Estado individual duplicado no lote: {chave}")
                chaves_lote.add(chave)

            remover = [
                chave for chave in self.estados_epi_individuais
                if chave[0] == camera_id
            ]
            for chave in remover:
                self.estados_epi_individuais.pop(chave, None)

            def _converter_evidencia(ev):
                return EstadoEvidenciaSemanticaEPI(
                    detection_id=str(ev.detection_id),
                    classe_modelo=str(ev.classe_modelo),
                    tipo_deteccao=str(ev.tipo_deteccao),
                    bbox_epi=tuple(float(v) for v in ev.bbox_epi),
                    confianca_deteccao=float(ev.confianca_deteccao),
                    status_associacao=str(ev.status_associacao),
                    score_ownership=(None if ev.score_ownership is None else float(ev.score_ownership)),
                    compatibilidade_regiao_esperada_etapa6=(
                        None
                        if ev.compatibilidade_regiao_esperada_etapa6 is None
                        else float(ev.compatibilidade_regiao_esperada_etapa6)
                    ),
                    compatibilidade_anatomica=(
                        None
                        if ev.compatibilidade_anatomica is None
                        else float(ev.compatibilidade_anatomica)
                    ),
                    regiao_corporal_mais_proxima=(
                        None if ev.regiao_corporal_mais_proxima is None
                        else str(ev.regiao_corporal_mais_proxima)
                    ),
                    regiao_esperada=(None if ev.regiao_esperada is None else str(ev.regiao_esperada)),
                    utilizavel=bool(ev.utilizavel),
                    posicao=str(ev.posicao),
                    motivo=(None if ev.motivo is None else str(ev.motivo)),
                )

            agora = _agora_utc()
            for item in estados:
                chave = (camera_id, str(item.track_instance_id), str(item.epi))
                self.estados_epi_individuais[chave] = EstadoEPIIndividual(
                    camera_id=camera_id,
                    track_id=int(item.track_id),
                    track_instance_id=str(item.track_instance_id),
                    epi=str(item.epi),
                    estado=str(item.estado),
                    evidencias_positivas=tuple(_converter_evidencia(ev) for ev in item.evidencias_positivas),
                    evidencias_negativas=tuple(_converter_evidencia(ev) for ev in item.evidencias_negativas),
                    evidencias_ambiguas=tuple(_converter_evidencia(ev) for ev in item.evidencias_ambiguas),
                    qualidade_anatomica=str(item.qualidade_anatomica),
                    metodo=str(item.metodo),
                    motivos=tuple(str(m) for m in item.motivos),
                    atualizado_em=agora,
                )
            self._marcar_atualizacao()

    def limpar_estados_epi_individuais_camera(self, camera_id: int) -> None:
        with self._lock:
            camera_id = int(camera_id)
            remover = [
                chave for chave in self.estados_epi_individuais
                if chave[0] == camera_id
            ]
            for chave in remover:
                self.estados_epi_individuais.pop(chave, None)
            self._marcar_atualizacao()

    # --------------------------------------------------------
    # ESTABILIZAÇÃO TEMPORAL DE EPI - ETAPA 8
    # --------------------------------------------------------

    def obter_contexto_estabilizacao_epi_camera(self, camera_id: int) -> Dict[str, Any]:
        """Retorna estados instantâneos atuais e memória temporal da câmera."""
        with self._lock:
            camera_id = int(camera_id)
            instantaneos = tuple(
                item for chave, item in self.estados_epi_individuais.items()
                if chave[0] == camera_id
            )
            temporais = {
                chave: item
                for chave, item in self.estados_epi_temporais.items()
                if chave[0] == camera_id
            }
            return {
                "camera_id": camera_id,
                "epis_obrigatorios": tuple(self.ambiente.epis_obrigatorios),
                "estados_instantaneos": instantaneos,
                "estados_temporais": temporais,
            }

    def atualizar_estados_epi_temporais_camera(
        self,
        camera_id: int,
        estados,
    ) -> None:
        """Substitui atomicamente a memória temporal da câmera.

        A lógica de confirmação pertence a estabilizacao_temporal_epi.py;
        EstadoSistema apenas valida e centraliza o resultado operacional.
        """
        with self._lock:
            camera_id = int(camera_id)
            estados = list(estados or [])
            obrigatorios = set(self.ambiente.epis_obrigatorios)
            chaves_lote = set()

            for item in estados:
                if int(item.camera_id) != camera_id:
                    raise ValueError(
                        "Estado temporal com camera_id inconsistente: "
                        f"lote={camera_id}, estado={item.camera_id}"
                    )
                epi = str(item.epi)
                if epi not in obrigatorios:
                    raise ValueError(
                        f"Estado temporal produzido para EPI não obrigatório: {epi}"
                    )
                chave = (camera_id, str(item.track_instance_id), epi)
                if chave in chaves_lote:
                    raise ValueError(f"Estado temporal duplicado no lote: {chave}")
                chaves_lote.add(chave)

            remover = [
                chave for chave in self.estados_epi_temporais
                if chave[0] == camera_id
            ]
            for chave in remover:
                self.estados_epi_temporais.pop(chave, None)

            agora = _agora_utc()
            for item in estados:
                chave = (camera_id, str(item.track_instance_id), str(item.epi))
                self.estados_epi_temporais[chave] = EstadoEPITemporal(
                    camera_id=camera_id,
                    track_id=int(item.track_id),
                    track_instance_id=str(item.track_instance_id),
                    epi=str(item.epi),
                    estado_instantaneo=str(item.estado_instantaneo),
                    estado_candidato=(
                        None if item.estado_candidato is None
                        else str(item.estado_candidato)
                    ),
                    estado_confirmado=(
                        None if item.estado_confirmado is None
                        else str(item.estado_confirmado)
                    ),
                    candidato_desde=(
                        None if item.candidato_desde is None
                        else float(item.candidato_desde)
                    ),
                    confirmado_desde=(
                        None if item.confirmado_desde is None
                        else float(item.confirmado_desde)
                    ),
                    ultima_observacao=float(item.ultima_observacao),
                    quantidade_observacoes_candidato=int(
                        item.quantidade_observacoes_candidato
                    ),
                    status_temporal=str(item.status_temporal),
                    atualizado_em=agora,
                )
            self._marcar_atualizacao()

    def limpar_estados_epi_temporais_camera(self, camera_id: int) -> None:
        with self._lock:
            camera_id = int(camera_id)
            remover = [
                chave for chave in self.estados_epi_temporais
                if chave[0] == camera_id
            ]
            for chave in remover:
                self.estados_epi_temporais.pop(chave, None)
            self._marcar_atualizacao()

    def atualizar_latencia_pose(self, latencia_pose_ms: Optional[float]) -> None:
        with self._lock:
            self.metricas_runtime.latencia_pose_ms = (
                None
                if latencia_pose_ms is None
                else float(latencia_pose_ms)
            )
            self._marcar_atualizacao()

    # --------------------------------------------------------
    # SNAPSHOT LEVE E THREAD-SAFE
    # --------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """
        Retorna projeção leve do estado operacional.

        Não usa deepcopy() e não inclui frames, imagens ou objetos
        de inferência pesados. Objetos globais são resumidos por
        quantidade e IDs de maquinários nesta etapa.
        """
        with self._lock:
            cameras = {
                camera_id: {
                    "camera_id": camera.camera_id,
                    "nome": camera.nome,
                    "tipo": camera.tipo,
                    "camera_uid": camera.camera_uid,
                    "status_identidade": camera.status_identidade,
                    "indice_runtime": camera.indice_runtime,
                    "status": camera.status,
                    "ativa": camera.ativa,
                    "ultimo_frame_em": camera.ultimo_frame_em,
                    "ultima_leitura_ok_em": camera.ultima_leitura_ok_em,
                    "falhas_consecutivas": camera.falhas_consecutivas,
                    "tracks_ativos": tuple(camera.tracks_ativos),
                }
                for camera_id, camera in self.cameras.items()
            }

            pessoas = {
                chave: {
                    "camera_id": pessoa.camera_id,
                    "track_id": pessoa.track_id,
                    "track_instance_id": pessoa.track_instance_id,
                    "ativo": pessoa.ativo,
                    "detectado_no_frame": pessoa.detectado_no_frame,
                    "frames_sem_deteccao": pessoa.frames_sem_deteccao,
                    "bbox": pessoa.bbox,
                    "confianca": pessoa.confianca,
                    "primeira_deteccao_em": _timestamp_iso(
                        pessoa.primeira_deteccao_em
                    ),
                    "ultima_deteccao_em": _timestamp_iso(
                        pessoa.ultima_deteccao_em
                    ),
                    "keypoints": {
                        nome: {
                            "indice": keypoint.indice,
                            "x": keypoint.x,
                            "y": keypoint.y,
                            "confianca": keypoint.confianca,
                            "confiavel": keypoint.confiavel,
                        }
                        for nome, keypoint in pessoa.keypoints.items()
                    },
                    "identidade": {
                        "conhecida": pessoa.identidade.conhecida,
                        "status_identidade": pessoa.identidade.status_identidade,
                        "status_processamento": pessoa.identidade.status_processamento,
                        "matricula": pessoa.identidade.matricula,
                        "nome": pessoa.identidade.nome,
                        "cargo": pessoa.identidade.cargo,
                        "confianca": pessoa.identidade.confianca,
                        "distancia_match": pessoa.identidade.distancia_match,
                        "metodo": pessoa.identidade.metodo,
                        "modelo": pessoa.identidade.modelo,
                        "tentativas": pessoa.identidade.tentativas,
                        "tentativas_validas": pessoa.identidade.tentativas_validas,
                        "ultima_tentativa_monotonica": pessoa.identidade.ultima_tentativa_monotonica,
                        "candidato_matricula": pessoa.identidade.candidato_matricula,
                        "confirmacoes_candidato": pessoa.identidade.confirmacoes_candidato,
                        "confirmacoes_desconhecido": pessoa.identidade.confirmacoes_desconhecido,
                        "candidato_conflito": pessoa.identidade.candidato_conflito,
                        "confirmacoes_conflito": pessoa.identidade.confirmacoes_conflito,
                        "job_pendente_id": pessoa.identidade.job_pendente_id,
                        "observacao_pendente_id": pessoa.identidade.observacao_pendente_id,
                        "motivo": pessoa.identidade.motivo,
                    },
                    "epis": {
                        epi: estado_epi.estado
                        for epi, estado_epi in pessoa.epis.items()
                    },
                }
                for chave, pessoa in self.pessoas.items()
            }

            associacoes_epi = {
                chave: tuple({
                    "detection_id": item.detection_id,
                    "camera_id": item.camera_id,
                    "classe_modelo": item.classe_modelo,
                    "epi": item.epi,
                    "tipo_deteccao": item.tipo_deteccao,
                    "bbox_epi": item.bbox_epi,
                    "confianca_deteccao": item.confianca_deteccao,
                    "status_associacao": item.status_associacao,
                    "track_id": item.track_id,
                    "track_instance_id": item.track_instance_id,
                    "score_assoc": item.score_assoc,
                    "score_segundo_candidato": item.score_segundo_candidato,
                    "score_ownership": item.score_ownership,
                    "componente_bbox": item.componente_bbox,
                    "componente_proximidade_corpo": item.componente_proximidade_corpo,
                    "componente_proximidade_keypoints": item.componente_proximidade_keypoints,
                    "componente_regiao_esperada": item.componente_regiao_esperada,
                    "distancia_corporal_normalizada": item.distancia_corporal_normalizada,
                    "distancia_regiao_esperada_normalizada": item.distancia_regiao_esperada_normalizada,
                    "regiao_corporal_mais_proxima": item.regiao_corporal_mais_proxima,
                    "regiao_esperada": item.regiao_esperada,
                    "compatibilidade_regiao_esperada": item.compatibilidade_regiao_esperada,
                    "metodo": item.metodo,
                    "metodo_regiao_esperada": item.metodo_regiao_esperada,
                    "qualidade_geometrica": item.qualidade_geometrica,
                    "candidatos": item.candidatos,
                } for item in itens)
                for chave, itens in self.associacoes_epi.items()
            }

            evidencias_sem_associacao = {
                camera_id: tuple({
                    "detection_id": item.detection_id,
                    "classe_modelo": item.classe_modelo,
                    "epi": item.epi,
                    "tipo_deteccao": item.tipo_deteccao,
                    "bbox_epi": item.bbox_epi,
                    "confianca_deteccao": item.confianca_deteccao,
                    "status_associacao": item.status_associacao,
                    "score_assoc": item.score_assoc,
                    "score_segundo_candidato": item.score_segundo_candidato,
                    "score_ownership": item.score_ownership,
                    "componente_bbox": item.componente_bbox,
                    "componente_proximidade_corpo": item.componente_proximidade_corpo,
                    "componente_proximidade_keypoints": item.componente_proximidade_keypoints,
                    "componente_regiao_esperada": item.componente_regiao_esperada,
                    "distancia_corporal_normalizada": item.distancia_corporal_normalizada,
                    "distancia_regiao_esperada_normalizada": item.distancia_regiao_esperada_normalizada,
                    "regiao_corporal_mais_proxima": item.regiao_corporal_mais_proxima,
                    "regiao_esperada": item.regiao_esperada,
                    "compatibilidade_regiao_esperada": item.compatibilidade_regiao_esperada,
                    "metodo": item.metodo,
                    "metodo_regiao_esperada": item.metodo_regiao_esperada,
                    "qualidade_geometrica": item.qualidade_geometrica,
                    "candidatos": item.candidatos,
                } for item in itens)
                for camera_id, itens in self.evidencias_epi_sem_associacao.items()
            }

            estados_epi_individuais = {
                chave: {
                    "camera_id": item.camera_id,
                    "track_id": item.track_id,
                    "track_instance_id": item.track_instance_id,
                    "epi": item.epi,
                    "estado": item.estado,
                    "qualidade_anatomica": item.qualidade_anatomica,
                    "metodo": item.metodo,
                    "motivos": item.motivos,
                    "atualizado_em": _timestamp_iso(item.atualizado_em),
                    "evidencias_positivas": tuple({
                        "detection_id": ev.detection_id,
                        "classe_modelo": ev.classe_modelo,
                        "tipo_deteccao": ev.tipo_deteccao,
                        "bbox_epi": ev.bbox_epi,
                        "confianca_deteccao": ev.confianca_deteccao,
                        "status_associacao": ev.status_associacao,
                        "score_ownership": ev.score_ownership,
                        "compatibilidade_regiao_esperada_etapa6": ev.compatibilidade_regiao_esperada_etapa6,
                        "compatibilidade_anatomica": ev.compatibilidade_anatomica,
                        "regiao_corporal_mais_proxima": ev.regiao_corporal_mais_proxima,
                        "regiao_esperada": ev.regiao_esperada,
                        "utilizavel": ev.utilizavel,
                        "posicao": ev.posicao,
                        "motivo": ev.motivo,
                    } for ev in item.evidencias_positivas),
                    "evidencias_negativas": tuple({
                        "detection_id": ev.detection_id,
                        "classe_modelo": ev.classe_modelo,
                        "tipo_deteccao": ev.tipo_deteccao,
                        "bbox_epi": ev.bbox_epi,
                        "confianca_deteccao": ev.confianca_deteccao,
                        "status_associacao": ev.status_associacao,
                        "compatibilidade_anatomica": ev.compatibilidade_anatomica,
                        "regiao_esperada": ev.regiao_esperada,
                        "utilizavel": ev.utilizavel,
                        "posicao": ev.posicao,
                        "motivo": ev.motivo,
                    } for ev in item.evidencias_negativas),
                    "evidencias_ambiguas": tuple({
                        "detection_id": ev.detection_id,
                        "classe_modelo": ev.classe_modelo,
                        "tipo_deteccao": ev.tipo_deteccao,
                        "status_associacao": ev.status_associacao,
                        "motivo": ev.motivo,
                    } for ev in item.evidencias_ambiguas),
                }
                for chave, item in self.estados_epi_individuais.items()
            }

            estados_epi_temporais = {
                chave: {
                    "camera_id": item.camera_id,
                    "track_id": item.track_id,
                    "track_instance_id": item.track_instance_id,
                    "epi": item.epi,
                    "estado_instantaneo": item.estado_instantaneo,
                    "estado_candidato": item.estado_candidato,
                    "estado_confirmado": item.estado_confirmado,
                    "candidato_desde": item.candidato_desde,
                    "confirmado_desde": item.confirmado_desde,
                    "ultima_observacao": item.ultima_observacao,
                    "quantidade_observacoes_candidato": item.quantidade_observacoes_candidato,
                    "status_temporal": item.status_temporal,
                    "atualizado_em": _timestamp_iso(item.atualizado_em),
                }
                for chave, item in self.estados_epi_temporais.items()
            }

            incidentes = {
                incidente_id: {
                    "incidente_id": item.incidente_id,
                    "ambiente_id": item.ambiente_id,
                    "ambiente_nome": item.ambiente_nome,
                    "camera_id": item.camera_id,
                    "camera_nome": item.camera_nome,
                    "track_id": item.track_id,
                    "track_instance_id": item.track_instance_id,
                    "epi": item.epi,
                    "tipo_irregularidade": item.tipo_irregularidade,
                    "estado_incidente": item.estado_incidente,
                    "motivo_encerramento": item.motivo_encerramento,
                    "matricula": item.matricula,
                    "nome": item.nome,
                    "cargo": item.cargo,
                    "status_identidade": item.status_identidade,
                    "iniciado_em": _timestamp_iso(item.iniciado_em),
                    "ultima_observacao_em": _timestamp_iso(item.ultima_observacao_em),
                    "ultima_evidencia_em": _timestamp_iso(item.ultima_evidencia_em),
                    "encerrado_em": _timestamp_iso(item.encerrado_em),
                    "quantidade_evidencias": len(item.evidencias),
                    "falhas_evidencia": tuple(item.falhas_evidencia),
                    "falhas_persistencia": tuple(item.falhas_persistencia),
                }
                for incidente_id, item in self.incidentes.items()
            }

            notificacoes = {
                incidente_id: {
                    "notificacao_id": item.notificacao_id,
                    "incidente_id": item.incidente_id,
                    "severidade": item.severidade,
                    "alerta_visual_ativo": item.alerta_visual_ativo,
                    "suspensa": item.suspensa,
                    "encerrada": item.encerrada,
                    "tempo_ativo_acumulado": item.tempo_ativo_acumulado,
                    "quantidade_audios": item.quantidade_audios,
                    "audio_em_fila": item.audio_em_fila,
                    "status_email": item.status_email,
                    "tentativas_email": item.tentativas_email,
                    "ultima_falha_audio": item.ultima_falha_audio,
                    "ultima_falha_email": item.ultima_falha_email,
                    "atualizado_em": _timestamp_iso(item.atualizado_em),
                }
                for incidente_id, item in self.notificacoes_incidentes.items()
            }

            metricas = {
                "fps_global": self.metricas_runtime.fps_global,
                "fps_por_camera": dict(
                    self.metricas_runtime.fps_por_camera
                ),
                "latencia_ppe_ms": (
                    self.metricas_runtime.latencia_ppe_ms
                ),
                "latencia_pose_ms": (
                    self.metricas_runtime.latencia_pose_ms
                ),
                "latencia_biometria_ms": (
                    self.metricas_runtime.latencia_biometria_ms
                ),
                "latencia_pipeline_ms": (
                    self.metricas_runtime.latencia_pipeline_ms
                ),
            }

            return {
                "fase_execucao": self.fase_execucao,
                "ambiente": {
                    "ambiente_id": self.ambiente.ambiente_id,
                    "nome": self.ambiente.nome,
                    "carregado": self.ambiente.carregado,
                    "calibrado": self.ambiente.calibrado,
                    "camera_ids": tuple(self.ambiente.camera_ids),
                    "cameras_associadas": tuple(
                        dict(camera)
                        for camera in self.ambiente.cameras_associadas
                    ),
                    "epis_obrigatorios": tuple(
                        self.ambiente.epis_obrigatorios
                    ),
                    "total_objetos_globais": len(
                        self.ambiente.objetos_globais
                    ),
                    "maquinarios": tuple(self.ambiente.maquinarios),
                },
                "cameras": cameras,
                "pessoas": pessoas,
                "associacoes_epi": associacoes_epi,
                "evidencias_epi_sem_associacao": evidencias_sem_associacao,
                "estados_epi_individuais": estados_epi_individuais,
                "estados_epi_temporais": estados_epi_temporais,
                "incidentes": incidentes,
                "notificacoes_incidentes": notificacoes,
                "metricas_runtime": metricas,
                "iniciado_em": _timestamp_iso(self.iniciado_em),
                "atualizado_em": _timestamp_iso(self.atualizado_em),
            }

    def _marcar_atualizacao(self) -> None:
        self.atualizado_em = _agora_utc()


def criar_estado_sistema_legado(config) -> EstadoSistema:
    """
    Cria o estado central a partir da configuração legada atual,
    sem alterar a persistência existente.
    """
    estado = EstadoSistema(
        fase_execucao=config.obter_estado_inicial()
    )

    estado.atualizar_ambiente_legado(
        nome=getattr(
            config,
            "NOME_AMBIENTE",
            "Ambiente Principal",
        ),
        calibrado=getattr(
            config,
            "AMBIENTE_CALIBRADO",
            False,
        ),
        epis_obrigatorios=getattr(
            config,
            "EPIS_OBRIGATORIOS",
            [],
        ),
        objetos_globais=getattr(
            config,
            "OBJETOS_GLOBAIS",
            {},
        ),
    )

    return estado
