from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
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

@dataclass
class IdentidadePessoa:
    conhecida: bool = False
    matricula: str = "--"
    nome: str = "DESCONHECIDO"
    cargo: str = "--"
    confianca: Optional[float] = None
    identificada_em: Optional[datetime] = None
    ultima_confirmacao_em: Optional[datetime] = None


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
    metodo: Optional[str] = None
    candidatos: Tuple[Tuple[str, float], ...] = field(default_factory=tuple)


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


@dataclass
class EstadoIncidente:
    incidente_id: Optional[str] = None
    ambiente_id: Optional[str] = None
    camera_id: Optional[int] = None
    track_id: Optional[int] = None
    matricula: str = "--"
    nome: str = "DESCONHECIDO"
    cargo: str = "--"
    epi: Optional[str] = None
    tipo_ocorrencia: Optional[str] = None
    severidade: Optional[str] = None
    ativo: bool = False
    iniciado_em: Optional[datetime] = None
    ultima_deteccao_em: Optional[datetime] = None
    ultima_evidencia_em: Optional[datetime] = None
    caminho_ultima_evidencia: Optional[str] = None


@dataclass
class EstadoNotificacao:
    notificacao_id: Optional[str] = None
    incidente_id: Optional[str] = None
    tipo: Optional[str] = None
    ativa: bool = False
    inicio: Optional[datetime] = None
    ultimo_audio: Optional[datetime] = None
    email_enviado: bool = False
    atualizado_em: Optional[datetime] = None


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
                self.cameras.clear()

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
    ) -> None:
        """
        Atualiza a projeção operacional dos tracks de uma câmera.

        A chave interna usa camera_id + track_instance_id. O track_id
        continua disponível para exibição/uso local, mas não é usado
        sozinho como identidade durável do ciclo de vida.
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
                self.pessoas.pop(chave, None)
                self.associacoes_epi.pop(chave, None)

            self.evidencias_epi_sem_associacao.pop(camera_id, None)

            camera = self.cameras.get(camera_id)
            if camera is not None:
                camera.tracks_ativos = []

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

            # Remove somente o estado anterior desta câmera.
            remover = [
                chave for chave in self.associacoes_epi
                if chave[0] == camera_id
            ]
            for chave in remover:
                self.associacoes_epi.pop(chave, None)

            por_track: Dict[Tuple[int, str], List[EstadoAssociacaoEPI]] = {}
            sem_associacao: List[EstadoAssociacaoEPI] = []

            for assoc in associacoes or []:
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
                    score_assoc=(
                        None if assoc.score_assoc is None
                        else float(assoc.score_assoc)
                    ),
                    score_segundo_candidato=(
                        None if assoc.score_segundo_candidato is None
                        else float(assoc.score_segundo_candidato)
                    ),
                    metodo=(None if assoc.metodo is None else str(assoc.metodo)),
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
                        "matricula": pessoa.identidade.matricula,
                        "nome": pessoa.identidade.nome,
                        "cargo": pessoa.identidade.cargo,
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
                    "metodo": item.metodo,
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
                    "candidatos": item.candidatos,
                } for item in itens)
                for camera_id, itens in self.evidencias_epi_sem_associacao.items()
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
