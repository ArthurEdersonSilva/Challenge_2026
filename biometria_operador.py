from __future__ import annotations

from dataclasses import dataclass
import csv
import math
import os
import queue
import threading
import time
import uuid
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import cv2

from reconhecimento_facial import (
    RESULTADO_MATCH,
    RESULTADO_DADOS_OPERADOR_AUSENTES,
    ResultadoReconhecimentoFacial,
)


EVENTO_JOB_INICIADO = "JOB_INICIADO"
EVENTO_RESULTADO = "RESULTADO"


@dataclass(frozen=True)
class ResultadoCropFacial:
    utilizavel: bool
    crop: Optional[object]
    bbox_face: Optional[Tuple[int, int, int, int]]
    qualidade: float
    motivo: str


@dataclass(frozen=True)
class JobBiometria:
    job_id: str
    camera_id: int
    track_id: int
    track_instance_id: str
    observacao_id: str
    crop: object
    criado_monotonico: float


@dataclass(frozen=True)
class ResultadoJobBiometria:
    job_id: str
    camera_id: int
    track_id: int
    track_instance_id: str
    observacao_id: str
    reconhecimento: ResultadoReconhecimentoFacial
    matricula: Optional[str] = None
    nome: Optional[str] = None
    cargo: Optional[str] = None
    latencia_ms: Optional[float] = None


@dataclass(frozen=True)
class EventoBiometria:
    tipo: str
    job_id: str
    camera_id: int
    track_id: int
    track_instance_id: str
    observacao_id: str
    resultado: Optional[ResultadoJobBiometria] = None


class RepositorioOperadores:
    def __init__(self, caminho_csv: str):
        self.caminho_csv = caminho_csv
        self._assinatura = None
        self._dados: Dict[str, Dict[str, str]] = {}

    @staticmethod
    def _normalizar_matricula(valor) -> str:
        return str(valor or "").strip()

    def _assinatura_atual(self):
        try:
            stat = os.stat(self.caminho_csv)
            return (int(stat.st_size), int(stat.st_mtime_ns))
        except OSError:
            return None

    def _recarregar_se_necessario(self):
        assinatura = self._assinatura_atual()
        if assinatura == self._assinatura:
            return
        dados: Dict[str, Dict[str, str]] = {}
        if assinatura is not None:
            try:
                with open(self.caminho_csv, "r", encoding="utf-8") as arquivo:
                    reader = csv.DictReader(arquivo)
                    for linha in reader:
                        matricula = self._normalizar_matricula(
                            linha.get("Matricula", linha.get("Matrícula", ""))
                        )
                        if not matricula:
                            continue
                        dados[matricula] = {
                            "matricula": matricula,
                            "nome": str(linha.get("Nome", "")).strip(),
                            "cargo": str(linha.get("Cargo", "")).strip(),
                        }
            except Exception:
                dados = {}
        self._dados = dados
        self._assinatura = assinatura

    def buscar(self, matricula: str) -> Optional[Dict[str, str]]:
        self._recarregar_se_necessario()
        item = self._dados.get(self._normalizar_matricula(matricula))
        return None if item is None else dict(item)


def _kp_confiavel(pessoa: Dict, nome: str):
    kp = (pessoa.get("keypoints") or {}).get(nome)
    if not kp or not kp.get("confiavel"):
        return None
    x = kp.get("x")
    y = kp.get("y")
    if x is None or y is None:
        return None
    return float(x), float(y)


def _centro_face_keypoints(pessoa: Dict):
    pontos = []
    for nome in ("olho_esquerdo", "olho_direito", "nariz", "orelha_esquerda", "orelha_direita"):
        ponto = _kp_confiavel(pessoa, nome)
        if ponto is not None:
            pontos.append(ponto)
    if len(pontos) < 2:
        return None
    return (
        sum(p[0] for p in pontos) / len(pontos),
        sum(p[1] for p in pontos) / len(pontos),
    )


def extrair_crop_facial_pessoa(
    frame,
    pessoa: Dict,
    outras_pessoas: Iterable[Dict] = (),
    largura_minima: int = 64,
    altura_minima: int = 64,
    blur_variancia_minima: float = 25.0,
    brilho_minimo: float = 25.0,
    brilho_maximo: float = 235.0,
    padding_proporcional: float = 0.65,
) -> ResultadoCropFacial:
    if frame is None or getattr(frame, "size", 0) == 0:
        return ResultadoCropFacial(False, None, None, 0.0, "FRAME_INVALIDO")

    bbox_pessoa = pessoa.get("bbox")
    if not bbox_pessoa or len(bbox_pessoa) != 4:
        return ResultadoCropFacial(False, None, None, 0.0, "BBOX_PESSOA_AUSENTE")

    olhos = [
        ponto for ponto in (
            _kp_confiavel(pessoa, "olho_esquerdo"),
            _kp_confiavel(pessoa, "olho_direito"),
        ) if ponto is not None
    ]
    nariz = _kp_confiavel(pessoa, "nariz")
    orelhas = [
        ponto for ponto in (
            _kp_confiavel(pessoa, "orelha_esquerda"),
            _kp_confiavel(pessoa, "orelha_direita"),
        ) if ponto is not None
    ]

    pontos = olhos + ([nariz] if nariz is not None else []) + orelhas
    if len(pontos) < 2:
        return ResultadoCropFacial(False, None, None, 0.0, "KEYPOINTS_FACE_INSUFICIENTES")

    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    centro_x = sum(xs) / len(xs)
    centro_y = sum(ys) / len(ys)

    escala_x = max(xs) - min(xs)
    escala_y = max(ys) - min(ys)
    if len(olhos) == 2:
        distancia_olhos = math.hypot(
            olhos[0][0] - olhos[1][0],
            olhos[0][1] - olhos[1][1],
        )
    else:
        distancia_olhos = 0.0

    base = max(escala_x, escala_y * 1.6, distancia_olhos * 1.8, 24.0)
    largura_face = base * (1.0 + 2.0 * float(padding_proporcional))
    altura_face = largura_face * 1.20

    x1 = centro_x - largura_face / 2.0
    x2 = centro_x + largura_face / 2.0
    y1 = centro_y - altura_face * 0.45
    y2 = centro_y + altura_face * 0.55

    px1, py1, px2, py2 = [float(v) for v in bbox_pessoa]
    margem_pessoa_x = max(4.0, (px2 - px1) * 0.03)
    margem_pessoa_y = max(4.0, (py2 - py1) * 0.03)
    x1 = max(x1, px1 - margem_pessoa_x)
    x2 = min(x2, px2 + margem_pessoa_x)
    y1 = max(y1, py1 - margem_pessoa_y)
    y2 = min(y2, py2 + margem_pessoa_y)

    altura_frame, largura_frame = frame.shape[:2]
    ix1 = max(0, min(largura_frame, int(math.floor(x1))))
    iy1 = max(0, min(altura_frame, int(math.floor(y1))))
    ix2 = max(0, min(largura_frame, int(math.ceil(x2))))
    iy2 = max(0, min(altura_frame, int(math.ceil(y2))))

    if ix2 - ix1 < int(largura_minima) or iy2 - iy1 < int(altura_minima):
        return ResultadoCropFacial(False, None, (ix1, iy1, ix2, iy2), 0.0, "CROP_PEQUENO")

    for outra in outras_pessoas or ():
        if str(outra.get("track_instance_id")) == str(pessoa.get("track_instance_id")):
            continue
        centro_outra = _centro_face_keypoints(outra)
        if centro_outra is None:
            continue
        ox, oy = centro_outra
        if ix1 <= ox <= ix2 and iy1 <= oy <= iy2:
            return ResultadoCropFacial(
                False, None, (ix1, iy1, ix2, iy2), 0.0, "OUTRA_FACE_NO_CROP"
            )

    crop = frame[iy1:iy2, ix1:ix2].copy()
    if crop.size == 0:
        return ResultadoCropFacial(False, None, (ix1, iy1, ix2, iy2), 0.0, "CROP_VAZIO")

    cinza = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(cinza, cv2.CV_64F).var())
    brilho = float(cinza.mean())

    if blur < float(blur_variancia_minima):
        return ResultadoCropFacial(False, None, (ix1, iy1, ix2, iy2), 0.0, "CROP_DESFOCADO")
    if brilho < float(brilho_minimo) or brilho > float(brilho_maximo):
        return ResultadoCropFacial(False, None, (ix1, iy1, ix2, iy2), 0.0, "BRILHO_INADEQUADO")

    qualidade_blur = min(1.0, blur / max(float(blur_variancia_minima) * 4.0, 1.0))
    distancia_brilho = abs(brilho - 127.5) / 127.5
    qualidade_brilho = max(0.0, 1.0 - distancia_brilho)
    qualidade = 0.65 * qualidade_blur + 0.35 * qualidade_brilho

    return ResultadoCropFacial(
        True,
        crop,
        (ix1, iy1, ix2, iy2),
        float(max(0.0, min(1.0, qualidade))),
        "CROP_UTILIZAVEL",
    )


class GerenciadorBiometriaAssincrona:
    def __init__(
        self,
        reconhecedor_factory: Callable[[], object],
        caminho_dados_operadores: str,
        fila_maxima: int = 4,
        relogio: Callable[[], float] = time.monotonic,
    ):
        self._reconhecedor_factory = reconhecedor_factory
        self._repositorio = RepositorioOperadores(caminho_dados_operadores)
        self._fila: queue.Queue = queue.Queue(maxsize=max(1, int(fila_maxima)))
        self._eventos: queue.Queue = queue.Queue()
        self._relogio = relogio
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._worker,
            name="BiometriaWorker",
            daemon=True,
        )
        self._thread.start()

    def criar_job(
        self,
        camera_id: int,
        track_id: int,
        track_instance_id: str,
        observacao_id: str,
        crop,
        agora_monotonico: Optional[float] = None,
    ) -> JobBiometria:
        return JobBiometria(
            job_id=str(uuid.uuid4()),
            camera_id=int(camera_id),
            track_id=int(track_id),
            track_instance_id=str(track_instance_id),
            observacao_id=str(observacao_id),
            crop=crop.copy(),
            criado_monotonico=(
                self._relogio() if agora_monotonico is None else float(agora_monotonico)
            ),
        )

    def enfileirar(self, job: JobBiometria) -> bool:
        try:
            self._fila.put_nowait(job)
            return True
        except queue.Full:
            return False

    def obter_eventos(self, limite: int = 100) -> List[EventoBiometria]:
        saida = []
        for _ in range(max(0, int(limite))):
            try:
                saida.append(self._eventos.get_nowait())
            except queue.Empty:
                break
        return saida

    def _worker(self):
        try:
            reconhecedor = self._reconhecedor_factory()
        except Exception:
            reconhecedor = None

        while not self._stop.is_set():
            try:
                job = self._fila.get(timeout=0.1)
            except queue.Empty:
                continue

            if job is None:
                self._fila.task_done()
                break

            self._eventos.put(EventoBiometria(
                tipo=EVENTO_JOB_INICIADO,
                job_id=job.job_id,
                camera_id=job.camera_id,
                track_id=job.track_id,
                track_instance_id=job.track_instance_id,
                observacao_id=job.observacao_id,
            ))

            inicio = self._relogio()
            print(
                f"[BIOMETRIA] Worker iniciou job | cam={job.camera_id} "
                f"| track={job.track_id} | obs={job.observacao_id}"
            )
            if reconhecedor is None:
                reconhecimento = ResultadoReconhecimentoFacial(
                    status="ERRO",
                    motivo="RECONHECEDOR_INDISPONIVEL",
                )
            else:
                try:
                    reconhecimento = reconhecedor.identificar_rosto(job.crop)
                except Exception as erro:
                    print(
                        f"[BIOMETRIA] ERRO no reconhecimento | "
                        f"{type(erro).__name__}: {erro}"
                    )
                    reconhecimento = ResultadoReconhecimentoFacial(
                        status="ERRO",
                        motivo=f"FALHA_RECONHECIMENTO:{type(erro).__name__}",
                    )
            fim = self._relogio()

            matricula = None
            nome = None
            cargo = None
            if reconhecimento.status == RESULTADO_MATCH and reconhecimento.matricula_candidata:
                print(
                    f"[BIOMETRIA] Match facial recebido | "
                    f"matricula={reconhecimento.matricula_candidata}"
                )
                dados = self._repositorio.buscar(reconhecimento.matricula_candidata)
                if dados is None or not dados.get("nome"):
                    print(
                        f"[BIOMETRIA] Matricula sem dados no CSV: "
                        f"{reconhecimento.matricula_candidata}"
                    )
                    reconhecimento = ResultadoReconhecimentoFacial(
                        status=RESULTADO_DADOS_OPERADOR_AUSENTES,
                        matricula_candidata=reconhecimento.matricula_candidata,
                        distancia_top1=reconhecimento.distancia_top1,
                        distancia_top2=reconhecimento.distancia_top2,
                        margem_top1_top2=reconhecimento.margem_top1_top2,
                        threshold_distancia=reconhecimento.threshold_distancia,
                        threshold_margem=reconhecimento.threshold_margem,
                        metodo=reconhecimento.metodo,
                        modelo=reconhecimento.modelo,
                        motivo="MATRICULA_SEM_DADOS_OPERADOR",
                    )
                else:
                    matricula = dados["matricula"]
                    nome = dados["nome"]
                    cargo = dados.get("cargo") or "--"
                    print(
                        f"[BIOMETRIA] Operador localizado no CSV | "
                        f"{nome} | {matricula}"
                    )

            print(
                f"[BIOMETRIA] Job finalizado | status={reconhecimento.status} "
                f"| motivo={reconhecimento.motivo}"
            )

            resultado = ResultadoJobBiometria(
                job_id=job.job_id,
                camera_id=job.camera_id,
                track_id=job.track_id,
                track_instance_id=job.track_instance_id,
                observacao_id=job.observacao_id,
                reconhecimento=reconhecimento,
                matricula=matricula,
                nome=nome,
                cargo=cargo,
                latencia_ms=max(0.0, (fim - inicio) * 1000.0),
            )
            self._eventos.put(EventoBiometria(
                tipo=EVENTO_RESULTADO,
                job_id=job.job_id,
                camera_id=job.camera_id,
                track_id=job.track_id,
                track_instance_id=job.track_instance_id,
                observacao_id=job.observacao_id,
                resultado=resultado,
            ))
            self._fila.task_done()

    def encerrar(self):
        self._stop.set()
        try:
            self._fila.put_nowait(None)
        except queue.Full:
            pass
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
