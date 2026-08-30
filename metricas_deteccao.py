from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Sequence, Tuple

CLASSES_BEST_PT: Tuple[str, ...] = (
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
)

IOU_PADRAO = 0.50
BACKGROUND = "__background__"


@dataclass(frozen=True)
class Caixa:
    classe_id: int
    xyxy: Tuple[float, float, float, float]
    confianca: Optional[float] = None
    identificador: Optional[str] = None


@dataclass(frozen=True)
class MatchDeteccao:
    pred_indice: int
    gt_indice: int
    iou: float


@dataclass
class ResultadoClasse:
    classe_id: int
    classe: str
    suporte: int
    tp: int
    fp: int
    fn: int
    precision: Optional[float]
    recall: Optional[float]
    f1: Optional[float]
    avaliavel: bool

    def como_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuditoriaImagem:
    matches: List[MatchDeteccao]
    predicoes_fp: List[int]
    ground_truth_fn: List[int]


@dataclass
class ResultadoAuditoria:
    por_classe: Dict[int, ResultadoClasse]
    matriz_confusao: List[List[int]]
    rotulos_matriz: List[str]

    def como_dict(self) -> dict:
        return {
            "por_classe": {str(k): v.como_dict() for k, v in self.por_classe.items()},
            "matriz_confusao": self.matriz_confusao,
            "rotulos_matriz": self.rotulos_matriz,
        }


def _validar_xyxy(xyxy: Sequence[float]) -> Tuple[float, float, float, float]:
    if len(xyxy) != 4:
        raise ValueError("Bounding box deve conter exatamente quatro coordenadas xyxy.")
    x1, y1, x2, y2 = map(float, xyxy)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Bounding box inválida: x2>x1 e y2>y1 são obrigatórios.")
    return x1, y1, x2, y2


def calcular_iou(a: Sequence[float], b: Sequence[float]) -> float:
    ax1, ay1, ax2, ay2 = _validar_xyxy(a)
    bx1, by1, bx2, by2 = _validar_xyxy(b)
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    uniao = area_a + area_b - inter
    if uniao <= 0.0:
        return 0.0
    return inter / uniao


def matching_mesma_classe(
    ground_truth: Sequence[Caixa],
    predicoes: Sequence[Caixa],
    iou_threshold: float = IOU_PADRAO,
) -> AuditoriaImagem:
    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("iou_threshold deve estar entre 0 e 1.")

    ordem_pred = sorted(
        range(len(predicoes)),
        key=lambda i: (
            -(predicoes[i].confianca if predicoes[i].confianca is not None else 0.0),
            i,
        ),
    )
    gt_usados = set()
    matches: List[MatchDeteccao] = []
    fp: List[int] = []

    for pi in ordem_pred:
        pred = predicoes[pi]
        candidatos: List[Tuple[float, int]] = []
        for gi, gt in enumerate(ground_truth):
            if gi in gt_usados or gt.classe_id != pred.classe_id:
                continue
            iou = calcular_iou(pred.xyxy, gt.xyxy)
            candidatos.append((iou, gi))
        if not candidatos:
            fp.append(pi)
            continue
        melhor_iou, melhor_gi = max(candidatos, key=lambda item: (item[0], -item[1]))
        if melhor_iou >= iou_threshold:
            gt_usados.add(melhor_gi)
            matches.append(MatchDeteccao(pi, melhor_gi, melhor_iou))
        else:
            fp.append(pi)

    fn = [gi for gi in range(len(ground_truth)) if gi not in gt_usados]
    matches.sort(key=lambda m: m.pred_indice)
    fp.sort()
    return AuditoriaImagem(matches=matches, predicoes_fp=fp, ground_truth_fn=fn)


def calcular_metricas_por_classe(
    ground_truth_por_imagem: Sequence[Sequence[Caixa]],
    predicoes_por_imagem: Sequence[Sequence[Caixa]],
    classes: Sequence[str] = CLASSES_BEST_PT,
    iou_threshold: float = IOU_PADRAO,
) -> Dict[int, ResultadoClasse]:
    if len(ground_truth_por_imagem) != len(predicoes_por_imagem):
        raise ValueError("Ground truth e predições devem possuir a mesma quantidade de imagens.")

    suporte = [0] * len(classes)
    tp = [0] * len(classes)
    fp = [0] * len(classes)
    fn = [0] * len(classes)

    for gts, preds in zip(ground_truth_por_imagem, predicoes_por_imagem):
        for gt in gts:
            _validar_classe_id(gt.classe_id, classes)
            suporte[gt.classe_id] += 1
        for pred in preds:
            _validar_classe_id(pred.classe_id, classes)
        auditoria = matching_mesma_classe(gts, preds, iou_threshold=iou_threshold)
        for match in auditoria.matches:
            tp[preds[match.pred_indice].classe_id] += 1
        for pi in auditoria.predicoes_fp:
            fp[preds[pi].classe_id] += 1
        for gi in auditoria.ground_truth_fn:
            fn[gts[gi].classe_id] += 1

    resultados: Dict[int, ResultadoClasse] = {}
    for cid, nome in enumerate(classes):
        if suporte[cid] == 0:
            resultados[cid] = ResultadoClasse(
                cid, nome, 0, tp[cid], fp[cid], fn[cid], None, None, None, False
            )
            continue
        denom_precision = tp[cid] + fp[cid]
        precision = tp[cid] / denom_precision if denom_precision else 0.0
        recall = tp[cid] / (tp[cid] + fn[cid]) if (tp[cid] + fn[cid]) else 0.0
        f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        resultados[cid] = ResultadoClasse(
            cid, nome, suporte[cid], tp[cid], fp[cid], fn[cid], precision, recall, f1, True
        )
    return resultados


def construir_matriz_confusao(
    ground_truth_por_imagem: Sequence[Sequence[Caixa]],
    predicoes_por_imagem: Sequence[Sequence[Caixa]],
    classes: Sequence[str] = CLASSES_BEST_PT,
    iou_threshold: float = IOU_PADRAO,
) -> Tuple[List[List[int]], List[str]]:
    """Matriz [classe GT][classe predita], incluindo background no último índice.

    O pareamento espacial para a matriz é um-para-um e independe da classe para que
    confusões de classe sejam visíveis. O matching TP/FP/FN oficial da auditoria
    continua sendo estritamente por mesma classe em ``matching_mesma_classe``.
    """
    if len(ground_truth_por_imagem) != len(predicoes_por_imagem):
        raise ValueError("Ground truth e predições devem possuir a mesma quantidade de imagens.")
    n = len(classes)
    bg = n
    matriz = [[0 for _ in range(n + 1)] for _ in range(n + 1)]

    for gts, preds in zip(ground_truth_por_imagem, predicoes_por_imagem):
        for gt in gts:
            _validar_classe_id(gt.classe_id, classes)
        for pred in preds:
            _validar_classe_id(pred.classe_id, classes)

        pares: List[Tuple[float, int, int]] = []
        for gi, gt in enumerate(gts):
            for pi, pred in enumerate(preds):
                iou = calcular_iou(gt.xyxy, pred.xyxy)
                if iou >= iou_threshold:
                    pares.append((iou, gi, pi))
        pares.sort(key=lambda x: (-x[0], x[1], x[2]))
        gt_usados = set()
        pred_usadas = set()
        for _iou, gi, pi in pares:
            if gi in gt_usados or pi in pred_usadas:
                continue
            gt_usados.add(gi)
            pred_usadas.add(pi)
            matriz[gts[gi].classe_id][preds[pi].classe_id] += 1

        for gi, gt in enumerate(gts):
            if gi not in gt_usados:
                matriz[gt.classe_id][bg] += 1
        for pi, pred in enumerate(preds):
            if pi not in pred_usadas:
                matriz[bg][pred.classe_id] += 1

    return matriz, list(classes) + [BACKGROUND]


def auditar_deteccoes(
    ground_truth_por_imagem: Sequence[Sequence[Caixa]],
    predicoes_por_imagem: Sequence[Sequence[Caixa]],
    classes: Sequence[str] = CLASSES_BEST_PT,
    iou_threshold: float = IOU_PADRAO,
) -> ResultadoAuditoria:
    por_classe = calcular_metricas_por_classe(
        ground_truth_por_imagem, predicoes_por_imagem, classes, iou_threshold
    )
    matriz, rotulos = construir_matriz_confusao(
        ground_truth_por_imagem, predicoes_por_imagem, classes, iou_threshold
    )
    return ResultadoAuditoria(por_classe, matriz, rotulos)


def _validar_classe_id(classe_id: int, classes: Sequence[str]) -> None:
    if not isinstance(classe_id, int) or not 0 <= classe_id < len(classes):
        raise ValueError(f"classe_id inválido: {classe_id}")
