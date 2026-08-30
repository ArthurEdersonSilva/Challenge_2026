from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


RESULTADO_MATCH = "MATCH"
RESULTADO_SEM_MATCH = "SEM_MATCH"
RESULTADO_AMBIGUO = "AMBIGUO"
RESULTADO_ERRO = "ERRO"
RESULTADO_BASE_VAZIA = "BASE_VAZIA"
RESULTADO_DADOS_OPERADOR_AUSENTES = "DADOS_OPERADOR_AUSENTES"


@dataclass(frozen=True)
class ValidacaoImagemBiometrica:
    valida: bool
    quantidade_rostos: int
    motivo: str
    confiancas: Tuple[float, ...] = ()


@dataclass(frozen=True)
class ResultadoReconhecimentoFacial:
    status: str
    matricula_candidata: Optional[str] = None
    distancia_top1: Optional[float] = None
    distancia_top2: Optional[float] = None
    margem_top1_top2: Optional[float] = None
    threshold_distancia: Optional[float] = None
    threshold_margem: Optional[float] = None
    metodo: str = "DeepFace"
    modelo: str = "Facenet"
    motivo: str = ""


class DeepFaceIndisponivel(RuntimeError):
    pass


def _carregar_deepface():
    try:
        from deepface import DeepFace
        return DeepFace
    except Exception as erro:
        raise DeepFaceIndisponivel(str(erro)) from erro


def _rostos_utilizaveis(
    imagem,
    detector_backend: str,
    confianca_minima: float,
    dimensao_minima: int,
):
    DeepFace = _carregar_deepface()
    rostos = DeepFace.extract_faces(
        img_path=imagem,
        detector_backend=detector_backend,
        enforce_detection=True,
        align=True,
    )

    utilizaveis = []
    confiancas = []
    for rosto in rostos or []:
        face = rosto.get("face")
        confianca = float(rosto.get("confidence", 1.0) or 0.0)
        if face is None or getattr(face, "size", 0) == 0:
            continue
        altura, largura = face.shape[:2]
        if largura < int(dimensao_minima) or altura < int(dimensao_minima):
            continue
        if confianca < float(confianca_minima):
            continue
        utilizaveis.append(rosto)
        confiancas.append(confianca)
    return utilizaveis, confiancas


def validar_imagem_biometrica(
    imagem,
    detector_backend: str = "opencv",
    confianca_minima: float = 0.80,
    dimensao_minima: int = 48,
) -> ValidacaoImagemBiometrica:
    """Valida se a imagem contém exatamente um rosto biométrico utilizável."""
    try:
        rostos, confiancas = _rostos_utilizaveis(
            imagem=imagem,
            detector_backend=detector_backend,
            confianca_minima=confianca_minima,
            dimensao_minima=dimensao_minima,
        )
    except DeepFaceIndisponivel:
        return ValidacaoImagemBiometrica(
            valida=False,
            quantidade_rostos=0,
            motivo="DEEPFACE_INDISPONIVEL",
        )
    except Exception:
        return ValidacaoImagemBiometrica(
            valida=False,
            quantidade_rostos=0,
            motivo="ROSTO_NAO_DETECTADO",
        )

    quantidade = len(rostos)
    if quantidade == 1:
        return ValidacaoImagemBiometrica(
            valida=True,
            quantidade_rostos=1,
            motivo="UM_ROSTO_UTILIZAVEL",
            confiancas=tuple(confiancas),
        )
    if quantidade == 0:
        return ValidacaoImagemBiometrica(
            valida=False,
            quantidade_rostos=0,
            motivo="ZERO_ROSTOS_UTILIZAVEIS",
            confiancas=tuple(confiancas),
        )
    return ValidacaoImagemBiometrica(
        valida=False,
        quantidade_rostos=quantidade,
        motivo="MULTIPLOS_ROSTOS_UTILIZAVEIS",
        confiancas=tuple(confiancas),
    )


def _vetor_normalizado(valores: Sequence[float]) -> np.ndarray:
    vetor = np.asarray(valores, dtype=np.float32)
    norma = float(np.linalg.norm(vetor))
    if norma <= 0.0:
        raise ValueError("Embedding biométrico com norma zero.")
    return vetor / norma


def _distancia_cosseno(vetor_a: np.ndarray, vetor_b: np.ndarray) -> float:
    return float(1.0 - np.clip(np.dot(vetor_a, vetor_b), -1.0, 1.0))


class ReconhecedorFacial:
    """Reconhecimento facial somente-leitura, com base validada defensivamente.

    A base é transformada em embeddings em memória somente para arquivos que
    contenham exatamente um rosto utilizável. Imagens inválidas permanecem no
    disco, mas nunca participam da comparação.
    """

    EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    def __init__(
        self,
        db_path: str = "banco_biometria",
        model_name: str = "Facenet",
        detector_backend: str = "opencv",
        distancia_maxima: float = 0.40,
        margem_minima_top1_top2: float = 0.05,
        confianca_rosto_minima: float = 0.80,
        dimensao_rosto_minima: int = 48,
    ):
        self.db_path = db_path
        self.model_name = model_name
        self.detector_backend = detector_backend
        self.distancia_maxima = float(distancia_maxima)
        self.margem_minima_top1_top2 = float(margem_minima_top1_top2)
        self.confianca_rosto_minima = float(confianca_rosto_minima)
        self.dimensao_rosto_minima = int(dimensao_rosto_minima)

        os.makedirs(self.db_path, exist_ok=True)
        self._assinatura_base = None
        self._embeddings: Dict[str, np.ndarray] = {}
        self._entradas_invalidas: Dict[str, str] = {}

    def _arquivos_base(self) -> List[str]:
        arquivos = []
        try:
            nomes = sorted(os.listdir(self.db_path))
        except OSError:
            return arquivos
        for nome in nomes:
            caminho = os.path.join(self.db_path, nome)
            if not os.path.isfile(caminho):
                continue
            extensao = os.path.splitext(nome)[1].lower()
            if extensao not in self.EXTENSOES_IMAGEM:
                continue
            arquivos.append(caminho)
        return arquivos

    def _calcular_assinatura_base(self):
        assinatura = []
        for caminho in self._arquivos_base():
            try:
                stat = os.stat(caminho)
                assinatura.append((
                    os.path.basename(caminho),
                    int(stat.st_size),
                    int(stat.st_mtime_ns),
                ))
            except OSError:
                continue
        return tuple(assinatura)

    def _representar(self, imagem) -> np.ndarray:
        DeepFace = _carregar_deepface()

        representacoes = DeepFace.represent(
            img_path=imagem,
            model_name=self.model_name,
            detector_backend=self.detector_backend,
            enforce_detection=False,
            align=True,
        )

        if isinstance(representacoes, dict):
            representacoes = [representacoes]

        if not representacoes:
            raise ValueError("Nenhuma representação biométrica foi gerada.")

        candidatas = []

        for indice, representacao in enumerate(representacoes):
            if not isinstance(representacao, dict):
                continue

            embedding = representacao.get("embedding")
            if embedding is None:
                continue

            confianca = representacao.get(
                "face_confidence",
                representacao.get("confidence", 0.0),
            )

            try:
                confianca = float(confianca or 0.0)
            except Exception:
                confianca = 0.0

            area = representacao.get("facial_area") or {}
            largura = area.get("w", area.get("width", 0))
            altura = area.get("h", area.get("height", 0))

            try:
                area_pixels = float(largura or 0) * float(altura or 0)
            except Exception:
                area_pixels = 0.0

            candidatas.append(
                (confianca, area_pixels, -indice, embedding)
            )

        if not candidatas:
            raise ValueError("Embedding biométrico ausente.")

        candidatas.sort(
            key=lambda item: (item[0], item[1], item[2]),
            reverse=True,
        )

        if len(candidatas) > 1:
            print(
                f"[BIOMETRIA] DeepFace retornou {len(candidatas)} faces; "
                "usando a melhor candidata."
            )

        return _vetor_normalizado(candidatas[0][3])

    def atualizar_base_se_necessario(self) -> None:
        assinatura = self._calcular_assinatura_base()
        if assinatura == self._assinatura_base:
            return

        embeddings: Dict[str, np.ndarray] = {}
        invalidas: Dict[str, str] = {}

        arquivos_base = self._arquivos_base()
        print(f"[BIOMETRIA] Base encontrada: {self.db_path} | imagens={len(arquivos_base)}")

        for caminho in arquivos_base:
            matricula = os.path.splitext(os.path.basename(caminho))[0].strip()
            if not matricula:
                invalidas[caminho] = "MATRICULA_VAZIA"
                continue

            try:
                embeddings[matricula] = self._representar(caminho)
                print(f"[BIOMETRIA] Base OK: {os.path.basename(caminho)} -> matricula={matricula}")
            except Exception as erro:
                invalidas[caminho] = "FALHA_EMBEDDING"
                print(
                    f"[BIOMETRIA] Base FALHOU: {os.path.basename(caminho)} "
                    f"| erro={type(erro).__name__}: {erro}"
                )

        self._embeddings = embeddings
        self._entradas_invalidas = invalidas
        self._assinatura_base = assinatura

        print(
            f"[BIOMETRIA] Base carregada | validas={len(embeddings)} "
            f"| invalidas={len(invalidas)}"
        )

    def entradas_invalidas(self) -> Dict[str, str]:
        self.atualizar_base_se_necessario()
        return dict(self._entradas_invalidas)

    def identificar_rosto(self, frame_crop) -> ResultadoReconhecimentoFacial:
        try:
            self.atualizar_base_se_necessario()
        except DeepFaceIndisponivel:
            return ResultadoReconhecimentoFacial(
                status=RESULTADO_ERRO,
                metodo="DeepFace/cosine",
                modelo=self.model_name,
                motivo="DEEPFACE_INDISPONIVEL",
            )
        except Exception:
            return ResultadoReconhecimentoFacial(
                status=RESULTADO_ERRO,
                metodo="DeepFace/cosine",
                modelo=self.model_name,
                motivo="FALHA_VALIDACAO_BASE",
            )

        if not self._embeddings:
            return ResultadoReconhecimentoFacial(
                status=RESULTADO_BASE_VAZIA,
                threshold_distancia=self.distancia_maxima,
                threshold_margem=self.margem_minima_top1_top2,
                metodo="DeepFace/cosine",
                modelo=self.model_name,
                motivo="SEM_ENTRADAS_BIOMETRICAS_VALIDAS",
            )

        try:
            consulta = self._representar(frame_crop)
        except Exception:
            return ResultadoReconhecimentoFacial(
                status=RESULTADO_ERRO,
                threshold_distancia=self.distancia_maxima,
                threshold_margem=self.margem_minima_top1_top2,
                metodo="DeepFace/cosine",
                modelo=self.model_name,
                motivo="FALHA_EMBEDDING_CONSULTA",
            )

        ranking = sorted(
            (
                (_distancia_cosseno(consulta, embedding), matricula)
                for matricula, embedding in self._embeddings.items()
            ),
            key=lambda item: (item[0], item[1]),
        )

        distancia_top1, matricula_top1 = ranking[0]
        distancia_top2 = ranking[1][0] if len(ranking) > 1 else None
        margem = (
            None
            if distancia_top2 is None
            else float(distancia_top2 - distancia_top1)
        )

        comum = dict(
            matricula_candidata=matricula_top1,
            distancia_top1=float(distancia_top1),
            distancia_top2=(None if distancia_top2 is None else float(distancia_top2)),
            margem_top1_top2=margem,
            threshold_distancia=self.distancia_maxima,
            threshold_margem=self.margem_minima_top1_top2,
            metodo="DeepFace/cosine",
            modelo=self.model_name,
        )

        if distancia_top1 > self.distancia_maxima:
            return ResultadoReconhecimentoFacial(
                status=RESULTADO_SEM_MATCH,
                motivo="TOP1_FORA_THRESHOLD",
                **comum,
            )

        if (
            distancia_top2 is not None
            and margem is not None
            and margem < self.margem_minima_top1_top2
        ):
            return ResultadoReconhecimentoFacial(
                status=RESULTADO_AMBIGUO,
                motivo="TOP1_TOP2_PROXIMOS",
                **comum,
            )

        return ResultadoReconhecimentoFacial(
            status=RESULTADO_MATCH,
            motivo="MATCH_FORTE",
            **comum,
        )
