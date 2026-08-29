import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import cv2


# Ordem oficial dos 17 keypoints COCO utilizados pelo YOLOv8 Pose.
NOMES_KEYPOINTS_COCO = (
    "nariz",
    "olho_esquerdo",
    "olho_direito",
    "orelha_esquerda",
    "orelha_direita",
    "ombro_esquerdo",
    "ombro_direito",
    "cotovelo_esquerdo",
    "cotovelo_direito",
    "punho_esquerdo",
    "punho_direito",
    "quadril_esquerdo",
    "quadril_direito",
    "joelho_esquerdo",
    "joelho_direito",
    "tornozelo_esquerdo",
    "tornozelo_direito",
)

ARESTAS_ESQUELETO_COCO = (
    (0, 1), (0, 2),
    (1, 3), (2, 4),
    (5, 6),
    (5, 7), (7, 9),
    (6, 8), (8, 10),
    (5, 11), (6, 12),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
)


@dataclass(frozen=True)
class KeypointPose:
    indice: int
    nome: str
    x: Optional[float]
    y: Optional[float]
    confianca: Optional[float]
    confiavel: bool


@dataclass
class DeteccaoPessoa:
    bbox: Tuple[float, float, float, float]
    confianca: float
    keypoints: Dict[str, KeypointPose]


@dataclass
class TrackPessoaRuntime:
    camera_id: int
    track_id: int
    track_instance_id: str
    bbox: Tuple[float, float, float, float]
    confianca: float
    keypoints: Dict[str, KeypointPose]
    primeira_deteccao_em: datetime
    ultima_deteccao_em: datetime
    frames_sem_deteccao: int = 0
    detectado_no_frame: bool = True


@dataclass
class ResultadoPoseCamera:
    camera_id: int
    tracks: List[TrackPessoaRuntime] = field(default_factory=list)
    latencia_pose_ms: float = 0.0


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def calcular_iou_bbox(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    intersecao = iw * ih

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    uniao = area_a + area_b - intersecao

    if uniao <= 0.0:
        return 0.0

    return intersecao / uniao


def _centro_bbox(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _distancia_centros_relativa(a, b) -> float:
    ax, ay = _centro_bbox(a)
    bx, by = _centro_bbox(b)
    distancia = math.hypot(ax - bx, ay - by)

    aw = max(1.0, a[2] - a[0])
    ah = max(1.0, a[3] - a[1])
    bw = max(1.0, b[2] - b[0])
    bh = max(1.0, b[3] - b[1])
    escala = max(1.0, (math.hypot(aw, ah) + math.hypot(bw, bh)) / 2.0)

    return distancia / escala


class RastreadorCamera:
    """
    Rastreador temporal EXCLUSIVO de uma câmera.

    Nenhum estado interno é compartilhado com outras câmeras. Os IDs
    numéricos são monotônicos durante a vida deste objeto e não são
    reciclados. Cada nascimento também recebe track_instance_id UUID,
    que identifica de forma inequívoca aquele ciclo de vida do track.
    """

    def __init__(
        self,
        camera_id: int,
        iou_minimo: float = 0.25,
        distancia_centro_maxima: float = 0.80,
        max_frames_sem_deteccao: int = 12,
    ):
        self.camera_id = int(camera_id)
        self.iou_minimo = float(iou_minimo)
        self.distancia_centro_maxima = float(distancia_centro_maxima)
        self.max_frames_sem_deteccao = int(max_frames_sem_deteccao)
        self._tracks: Dict[int, TrackPessoaRuntime] = {}
        self._proximo_track_id = 1

    def _novo_track(self, deteccao: DeteccaoPessoa) -> TrackPessoaRuntime:
        agora = _agora_utc()
        track_id = self._proximo_track_id
        self._proximo_track_id += 1

        track = TrackPessoaRuntime(
            camera_id=self.camera_id,
            track_id=track_id,
            track_instance_id=str(uuid.uuid4()),
            bbox=deteccao.bbox,
            confianca=deteccao.confianca,
            keypoints=deteccao.keypoints,
            primeira_deteccao_em=agora,
            ultima_deteccao_em=agora,
            frames_sem_deteccao=0,
            detectado_no_frame=True,
        )
        self._tracks[track_id] = track
        return track

    def atualizar(self, deteccoes: List[DeteccaoPessoa]) -> List[TrackPessoaRuntime]:
        for track in self._tracks.values():
            track.detectado_no_frame = False

        candidatos = []
        for track_id, track in self._tracks.items():
            for indice_deteccao, deteccao in enumerate(deteccoes):
                iou = calcular_iou_bbox(track.bbox, deteccao.bbox)
                distancia = _distancia_centros_relativa(track.bbox, deteccao.bbox)

                if (
                    iou >= self.iou_minimo
                    or distancia <= self.distancia_centro_maxima
                ):
                    # IoU é a evidência primária. A distância de centro
                    # apenas ajuda em deslocamentos entre frames.
                    score = iou - (0.15 * distancia)
                    candidatos.append(
                        (score, iou, -distancia, track_id, indice_deteccao)
                    )

        candidatos.sort(reverse=True)
        tracks_usados = set()
        deteccoes_usadas = set()

        for _, _, _, track_id, indice_deteccao in candidatos:
            if track_id in tracks_usados or indice_deteccao in deteccoes_usadas:
                continue

            track = self._tracks.get(track_id)
            if track is None:
                continue

            deteccao = deteccoes[indice_deteccao]
            agora = _agora_utc()

            track.bbox = deteccao.bbox
            track.confianca = deteccao.confianca
            track.keypoints = deteccao.keypoints
            track.ultima_deteccao_em = agora
            track.frames_sem_deteccao = 0
            track.detectado_no_frame = True

            tracks_usados.add(track_id)
            deteccoes_usadas.add(indice_deteccao)

        for indice_deteccao, deteccao in enumerate(deteccoes):
            if indice_deteccao not in deteccoes_usadas:
                novo = self._novo_track(deteccao)
                tracks_usados.add(novo.track_id)

        encerrar = []
        for track_id, track in self._tracks.items():
            if not track.detectado_no_frame:
                track.frames_sem_deteccao += 1
                if track.frames_sem_deteccao > self.max_frames_sem_deteccao:
                    encerrar.append(track_id)

        for track_id in encerrar:
            self._tracks.pop(track_id, None)

        return list(self._tracks.values())

    def encerrar_todos(self) -> None:
        self._tracks.clear()
        # _proximo_track_id NÃO volta para 1. Isso impede reciclagem
        # de track_id dentro deste processo para a mesma câmera.


class GerenciadorRastreamentoPessoas:
    """
    Mantém um RastreadorCamera independente para cada camera_id.
    """

    def __init__(
        self,
        modelo_pose,
        confianca_pose: float,
        confianca_keypoint: float,
        tamanho_imagem: int,
        iou_tracking: float,
        distancia_centro_tracking: float,
        max_frames_sem_deteccao: int,
        device,
    ):
        self.modelo_pose = modelo_pose
        self.device = device
        self.confianca_pose = float(confianca_pose)
        self.confianca_keypoint = float(confianca_keypoint)
        self.tamanho_imagem = int(tamanho_imagem)
        self.iou_tracking = float(iou_tracking)
        self.distancia_centro_tracking = float(distancia_centro_tracking)
        self.max_frames_sem_deteccao = int(max_frames_sem_deteccao)
        self._rastreadores: Dict[int, RastreadorCamera] = {}

    def _obter_rastreador(self, camera_id: int) -> RastreadorCamera:
        camera_id = int(camera_id)
        rastreador = self._rastreadores.get(camera_id)
        if rastreador is None:
            rastreador = RastreadorCamera(
                camera_id=camera_id,
                iou_minimo=self.iou_tracking,
                distancia_centro_maxima=self.distancia_centro_tracking,
                max_frames_sem_deteccao=self.max_frames_sem_deteccao,
            )
            self._rastreadores[camera_id] = rastreador
        return rastreador

    def _extrair_deteccoes(self, resultado) -> List[DeteccaoPessoa]:
        deteccoes = []

        boxes = getattr(resultado, "boxes", None)
        keypoints_resultado = getattr(resultado, "keypoints", None)

        if boxes is None or keypoints_resultado is None:
            return deteccoes

        xyxy = getattr(boxes, "xyxy", None)
        confs = getattr(boxes, "conf", None)
        xy = getattr(keypoints_resultado, "xy", None)
        conf_kpts = getattr(keypoints_resultado, "conf", None)

        if xyxy is None or xy is None:
            return deteccoes

        total = min(len(xyxy), len(xy))

        for indice in range(total):
            bbox_tensor = xyxy[indice]
            bbox_valores = bbox_tensor.detach().cpu().tolist()
            if len(bbox_valores) < 4:
                continue

            confianca_pessoa = 1.0
            if confs is not None and indice < len(confs):
                confianca_pessoa = float(confs[indice].detach().cpu().item())

            xy_pessoa = xy[indice].detach().cpu().tolist()
            conf_pessoa = None
            if conf_kpts is not None and indice < len(conf_kpts):
                conf_pessoa = conf_kpts[indice].detach().cpu().tolist()

            keypoints = {}
            for indice_kpt, nome in enumerate(NOMES_KEYPOINTS_COCO):
                x = None
                y = None
                confianca = None

                if indice_kpt < len(xy_pessoa):
                    ponto = xy_pessoa[indice_kpt]
                    if len(ponto) >= 2:
                        x = float(ponto[0])
                        y = float(ponto[1])

                if conf_pessoa is not None and indice_kpt < len(conf_pessoa):
                    confianca = float(conf_pessoa[indice_kpt])

                confiavel = bool(
                    x is not None
                    and y is not None
                    and confianca is not None
                    and confianca >= self.confianca_keypoint
                )

                keypoints[nome] = KeypointPose(
                    indice=indice_kpt,
                    nome=nome,
                    x=x,
                    y=y,
                    confianca=confianca,
                    confiavel=confiavel,
                )

            deteccoes.append(
                DeteccaoPessoa(
                    bbox=(
                        float(bbox_valores[0]),
                        float(bbox_valores[1]),
                        float(bbox_valores[2]),
                        float(bbox_valores[3]),
                    ),
                    confianca=confianca_pessoa,
                    keypoints=keypoints,
                )
            )

        return deteccoes

    def processar_camera(self, camera_id: int, frame) -> ResultadoPoseCamera:
        inicio = time.perf_counter()

        resultados = self.modelo_pose.predict(
            source=frame,
            conf=self.confianca_pose,
            imgsz=self.tamanho_imagem,
            device=self.device,
            verbose=False,
        )

        deteccoes = []
        if resultados:
            deteccoes = self._extrair_deteccoes(resultados[0])

        rastreador = self._obter_rastreador(camera_id)
        tracks = rastreador.atualizar(deteccoes)

        latencia_ms = (time.perf_counter() - inicio) * 1000.0
        return ResultadoPoseCamera(
            camera_id=int(camera_id),
            tracks=tracks,
            latencia_pose_ms=latencia_ms,
        )

    def marcar_camera_sem_frame(self, camera_id: int) -> List[TrackPessoaRuntime]:
        rastreador = self._rastreadores.get(int(camera_id))
        if rastreador is None:
            return []
        return rastreador.atualizar([])

    def encerrar_camera(self, camera_id: int) -> None:
        rastreador = self._rastreadores.get(int(camera_id))
        if rastreador is not None:
            rastreador.encerrar_todos()


def desenhar_pose_debug(frame, tracks: List[TrackPessoaRuntime]):
    saida = frame.copy()

    for track in tracks:
        if not track.detectado_no_frame:
            continue

        x1, y1, x2, y2 = [int(round(v)) for v in track.bbox]
        cv2.rectangle(saida, (x1, y1), (x2, y2), (255, 255, 255), 2)
        cv2.putText(
            saida,
            f"Pessoa #{track.track_id}",
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        pontos_por_indice = {}
        for keypoint in track.keypoints.values():
            if not keypoint.confiavel:
                continue
            if keypoint.x is None or keypoint.y is None:
                continue

            ponto = (int(round(keypoint.x)), int(round(keypoint.y)))
            pontos_por_indice[keypoint.indice] = ponto
            cv2.circle(saida, ponto, 3, (255, 255, 255), -1)

        for origem, destino in ARESTAS_ESQUELETO_COCO:
            if origem in pontos_por_indice and destino in pontos_por_indice:
                cv2.line(
                    saida,
                    pontos_por_indice[origem],
                    pontos_por_indice[destino],
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

    return saida
