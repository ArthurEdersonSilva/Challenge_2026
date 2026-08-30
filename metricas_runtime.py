from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict, Iterable, Optional
import time

CAMERA_ONLINE = "ONLINE"
CAMERA_OFFLINE = "OFFLINE"
CAMERA_RECONECTANDO = "RECONECTANDO"


@dataclass(frozen=True)
class SnapshotMetricasRuntime:
    fps_global: Optional[float]
    fps_por_camera: Dict[int, Optional[float]]
    latencia_ppe_ms: Optional[float]
    latencia_pose_ms: Optional[float]
    latencia_biometria_ms: Optional[float]
    latencia_pipeline_ms: Optional[float]


class GestorMetricasRuntime:
    """Agregador leve de métricas reais de runtime.

    Mantém somente janelas efêmeras para suavização. A fonte publicada
    continua sendo EstadoSistema.metricas_runtime.
    """

    def __init__(
        self,
        relogio: Callable[[], float] = time.perf_counter,
        janela_fps_segundos: float = 2.0,
        max_amostras_latencia: int = 30,
    ):
        self._relogio = relogio
        self._janela_fps_segundos = max(0.25, float(janela_fps_segundos))
        self._max_amostras_latencia = max(1, int(max_amostras_latencia))
        self._ambiente_id = None
        self._camera_ids = set()
        self._frames_por_camera: Dict[int, Deque[float]] = {}
        self._ciclos_pipeline: Deque[float] = deque()
        self._latencias = {
            "ppe": deque(maxlen=self._max_amostras_latencia),
            "pose": deque(maxlen=self._max_amostras_latencia),
            "biometria": deque(maxlen=self._max_amostras_latencia),
            "pipeline": deque(maxlen=self._max_amostras_latencia),
        }

    def agora(self) -> float:
        return float(self._relogio())

    def sincronizar_ambiente(self, ambiente_id, camera_ids: Iterable[int]) -> None:
        camera_ids = {int(v) for v in (camera_ids or ())}
        mudou = self._ambiente_id != ambiente_id
        if mudou:
            self._ambiente_id = ambiente_id
            self._camera_ids = set(camera_ids)
            self._frames_por_camera = {camera_id: deque() for camera_id in camera_ids}
            self._ciclos_pipeline.clear()
            for fila in self._latencias.values():
                fila.clear()
            return

        removidas = set(self._camera_ids) - camera_ids
        for camera_id in removidas:
            self._frames_por_camera.pop(camera_id, None)
        for camera_id in camera_ids:
            self._frames_por_camera.setdefault(camera_id, deque())
        self._camera_ids = set(camera_ids)

    def atualizar_status_camera(self, camera_id: int, status: str) -> None:
        camera_id = int(camera_id)
        if camera_id not in self._camera_ids:
            return
        if str(status) != CAMERA_ONLINE:
            self._frames_por_camera[camera_id] = deque()

    def registrar_frame_real(self, camera_id: int, status: str, instante: Optional[float] = None) -> None:
        camera_id = int(camera_id)
        if camera_id not in self._camera_ids:
            return
        if str(status) != CAMERA_ONLINE:
            self.atualizar_status_camera(camera_id, status)
            return
        instante = self.agora() if instante is None else float(instante)
        fila = self._frames_por_camera.setdefault(camera_id, deque())
        fila.append(instante)
        self._podar_tempos(fila, instante)

    def registrar_ciclo_pipeline(self, instante: Optional[float] = None) -> None:
        instante = self.agora() if instante is None else float(instante)
        self._ciclos_pipeline.append(instante)
        self._podar_tempos(self._ciclos_pipeline, instante)

    def registrar_latencia_ppe(self, valor_ms: Optional[float]) -> None:
        self._registrar_latencia("ppe", valor_ms)

    def registrar_latencia_pose(self, valor_ms: Optional[float]) -> None:
        self._registrar_latencia("pose", valor_ms)

    def registrar_latencia_biometria(self, valor_ms: Optional[float]) -> None:
        # None significa que nenhum job biométrico real terminou.
        self._registrar_latencia("biometria", valor_ms)

    def registrar_latencia_pipeline(self, valor_ms: Optional[float]) -> None:
        self._registrar_latencia("pipeline", valor_ms)

    def snapshot(self, status_cameras: Dict[int, str], instante: Optional[float] = None) -> SnapshotMetricasRuntime:
        instante = self.agora() if instante is None else float(instante)
        self._podar_tempos(self._ciclos_pipeline, instante)

        fps_por_camera: Dict[int, Optional[float]] = {}
        for camera_id in sorted(self._camera_ids):
            status = str((status_cameras or {}).get(camera_id, CAMERA_OFFLINE))
            if status != CAMERA_ONLINE:
                self.atualizar_status_camera(camera_id, status)
                fps_por_camera[camera_id] = None
                continue
            fila = self._frames_por_camera.setdefault(camera_id, deque())
            self._podar_tempos(fila, instante)
            fps_por_camera[camera_id] = self._calcular_fps(fila)

        return SnapshotMetricasRuntime(
            fps_global=self._calcular_fps(self._ciclos_pipeline),
            fps_por_camera=fps_por_camera,
            latencia_ppe_ms=self._media("ppe"),
            latencia_pose_ms=self._media("pose"),
            latencia_biometria_ms=self._media("biometria"),
            latencia_pipeline_ms=self._media("pipeline"),
        )

    def _registrar_latencia(self, nome: str, valor_ms: Optional[float]) -> None:
        if valor_ms is None:
            return
        valor = float(valor_ms)
        if valor < 0:
            return
        self._latencias[nome].append(valor)

    def _media(self, nome: str) -> Optional[float]:
        fila = self._latencias[nome]
        if not fila:
            return None
        return float(sum(fila) / len(fila))

    def _podar_tempos(self, fila: Deque[float], agora: float) -> None:
        limite = float(agora) - self._janela_fps_segundos
        while fila and fila[0] < limite:
            fila.popleft()

    @staticmethod
    def _calcular_fps(fila: Deque[float]) -> Optional[float]:
        if len(fila) < 2:
            return None
        duracao = float(fila[-1]) - float(fila[0])
        if duracao <= 0:
            return None
        return float((len(fila) - 1) / duracao)
