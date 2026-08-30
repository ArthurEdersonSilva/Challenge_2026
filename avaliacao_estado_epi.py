import math

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ESTADO_CORRETO = "CORRETO"
ESTADO_INCORRETO = "INCORRETO"
ESTADO_AUSENTE = "AUSENTE"
ESTADO_INDETERMINADO = "INDETERMINADO"

QUALIDADE_FORTE = "FORTE"
QUALIDADE_FALLBACK = "FALLBACK"
QUALIDADE_INSUFICIENTE = "INSUFICIENTE"

TIPO_PRESENCA = "PRESENCA"
TIPO_EVIDENCIA_NEGATIVA = "EVIDENCIA_NEGATIVA_MODELO"

ASSOCIADA = "ASSOCIADA"
AMBIGUA = "AMBIGUA"
NAO_ASSOCIADA = "NAO_ASSOCIADA"


@dataclass(frozen=True)
class EvidenciaSemanticaEPI:
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
class ResultadoEstadoEPIInstantaneo:
    camera_id: int
    track_id: int
    track_instance_id: str
    epi: str
    estado: str
    evidencias_positivas: Tuple[EvidenciaSemanticaEPI, ...] = field(default_factory=tuple)
    evidencias_negativas: Tuple[EvidenciaSemanticaEPI, ...] = field(default_factory=tuple)
    evidencias_ambiguas: Tuple[EvidenciaSemanticaEPI, ...] = field(default_factory=tuple)
    qualidade_anatomica: str = QUALIDADE_INSUFICIENTE
    metodo: str = "SEM_EVIDENCIA"
    motivos: Tuple[str, ...] = field(default_factory=tuple)


REGIAO_POR_EPI = {
    "Capacete": "cabeca",
    "Óculos": "olhos",
    "Máscara": "face",
    "Protetor auricular": "orelhas",
    "Protetor facial": "face",
    "Colete": "tronco",
    "Macacão de proteção": "corpo",
    "Cinto de segurança": "quadril_tronco",
    "Luvas": "maos",
    "Bota de segurança": "pes",
}


def _bbox_valida(bbox) -> bool:
    if bbox is None or len(bbox) != 4:
        return False
    try:
        x1, y1, x2, y2 = [float(v) for v in bbox]
    except (TypeError, ValueError):
        return False
    return x2 > x1 and y2 > y1


def _centro_bbox(bbox):
    x1, y1, x2, y2 = [float(v) for v in bbox]
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _ponto_em_bbox(ponto, bbox):
    x, y = float(ponto[0]), float(ponto[1])
    x1, y1, x2, y2 = [float(v) for v in bbox]
    return x1 <= x <= x2 and y1 <= y <= y2


def _intersecao_sobre_area_bbox(alvo, regiao) -> float:
    ax1, ay1, ax2, ay2 = [float(v) for v in alvo]
    bx1, by1, bx2, by2 = [float(v) for v in regiao]
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    area = max(1e-9, (ax2 - ax1) * (ay2 - ay1))
    return max(0.0, min(1.0, inter / area))


def _distancia_normalizada(ponto_a, ponto_b, bbox_pessoa) -> float:
    distancia = math.hypot(
        float(ponto_a[0]) - float(ponto_b[0]),
        float(ponto_a[1]) - float(ponto_b[1]),
    )
    altura = max(1.0, float(bbox_pessoa[3]) - float(bbox_pessoa[1]))
    return distancia / altura


def _kp(pessoa: dict, nome: str):
    item = (pessoa.get("keypoints") or {}).get(nome)
    if not item or not bool(item.get("confiavel", False)):
        return None
    x = item.get("x")
    y = item.get("y")
    if x is None or y is None:
        return None
    return (float(x), float(y))


def _bbox_de_pontos(pontos: Sequence[Tuple[float, float]], margem_x: float, margem_y: float):
    pontos = [p for p in pontos if p is not None]
    if not pontos:
        return None
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    return (
        min(xs) - margem_x,
        min(ys) - margem_y,
        max(xs) + margem_x,
        max(ys) + margem_y,
    )


def _bbox_toca_borda(bbox, frame_shape, lado: str, margem_relativa: float = 0.015) -> bool:
    if not frame_shape or len(frame_shape) < 2:
        return False
    altura_frame = float(frame_shape[0])
    largura_frame = float(frame_shape[1])
    x1, y1, x2, y2 = [float(v) for v in bbox]
    margem_x = max(2.0, largura_frame * margem_relativa)
    margem_y = max(2.0, altura_frame * margem_relativa)
    if lado == "topo":
        return y1 <= margem_y
    if lado == "base":
        return y2 >= altura_frame - margem_y
    if lado == "esquerda":
        return x1 <= margem_x
    if lado == "direita":
        return x2 >= largura_frame - margem_x
    return False


def _regiao_anatomica_avaliavel(pessoa: dict, epi: str, frame_shape=None):
    bbox = pessoa.get("bbox")
    if not _bbox_valida(bbox):
        return {
            "avaliavel": False,
            "qualidade": QUALIDADE_INSUFICIENTE,
            "metodo": "BBOX_INVALIDA",
            "regiao": REGIAO_POR_EPI.get(epi, "corpo"),
            "bbox": None,
            "pontos": tuple(),
            "motivo": "bbox da pessoa inválida",
        }

    bbox = tuple(float(v) for v in bbox)
    x1, y1, x2, y2 = bbox
    largura = max(1.0, x2 - x1)
    altura = max(1.0, y2 - y1)
    regiao = REGIAO_POR_EPI.get(epi, "corpo")

    nariz = _kp(pessoa, "nariz")
    olhos = [p for p in (_kp(pessoa, "olho_esquerdo"), _kp(pessoa, "olho_direito")) if p]
    orelhas = [p for p in (_kp(pessoa, "orelha_esquerda"), _kp(pessoa, "orelha_direita")) if p]
    ombros = [p for p in (_kp(pessoa, "ombro_esquerdo"), _kp(pessoa, "ombro_direito")) if p]
    quadris = [p for p in (_kp(pessoa, "quadril_esquerdo"), _kp(pessoa, "quadril_direito")) if p]
    punhos = [p for p in (_kp(pessoa, "punho_esquerdo"), _kp(pessoa, "punho_direito")) if p]
    tornozelos = [p for p in (_kp(pessoa, "tornozelo_esquerdo"), _kp(pessoa, "tornozelo_direito")) if p]

    qualidade = QUALIDADE_FORTE
    metodo = "KEYPOINTS"
    pontos = []
    regiao_bbox = None

    if regiao == "cabeca":
        pontos = ([nariz] if nariz else []) + olhos + orelhas

        # Para capacete, a região válida deve representar o TOPO da cabeça.
        # A versão anterior criava uma caixa muito ampla ao redor de olhos,
        # nariz e orelhas; por isso um capacete deslocado/de lado ainda podia
        # obter alta compatibilidade e virar CORRETO.
        pontos_face = olhos + orelhas + ([nariz] if nariz else [])
        if len(pontos_face) >= 2:
            xs_face = [p[0] for p in pontos_face]
            ys_face = [p[1] for p in pontos_face]
            centro_x_face = sum(xs_face) / len(xs_face)

            # Usa a largura facial observada quando possível e limita a região
            # do capacete horizontalmente ao eixo real da cabeça.
            largura_face = max(xs_face) - min(xs_face)
            if largura_face < 0.12 * largura:
                largura_face = 0.38 * largura

            meio_largura = max(0.20 * largura, 0.72 * largura_face)

            # O capacete deve ficar predominantemente acima dos olhos/orelhas.
            y_referencia = min(ys_face)
            topo = max(y1, y_referencia - 0.22 * altura)
            base = min(y1 + 0.30 * altura, y_referencia + 0.055 * altura)

            regiao_bbox = (
                max(x1, centro_x_face - meio_largura),
                topo,
                min(x2, centro_x_face + meio_largura),
                base,
            )
            metodo = "KEYPOINTS_CABECA_ESTRITO"
        elif not _bbox_toca_borda(bbox, frame_shape, "topo"):
            qualidade = QUALIDADE_FALLBACK
            metodo = "BBOX_FALLBACK_CABECA_ESTRITO"
            regiao_bbox = (
                x1 + 0.20 * largura,
                y1,
                x2 - 0.20 * largura,
                y1 + 0.22 * altura,
            )
        else:
            qualidade = QUALIDADE_INSUFICIENTE

    elif regiao == "olhos":
        pontos = olhos
        if len(olhos) >= 2:
            regiao_bbox = _bbox_de_pontos(olhos, 0.10 * largura, 0.035 * altura)
        elif len(olhos) == 1 and nariz:
            pontos = olhos + [nariz]
            regiao_bbox = _bbox_de_pontos(pontos, 0.10 * largura, 0.045 * altura)
        elif not _bbox_toca_borda(bbox, frame_shape, "topo"):
            qualidade = QUALIDADE_FALLBACK
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (x1 + 0.15 * largura, y1 + 0.08 * altura, x2 - 0.15 * largura, y1 + 0.22 * altura)
        else:
            qualidade = QUALIDADE_INSUFICIENTE

    elif regiao == "face":
        pontos = ([nariz] if nariz else []) + olhos + orelhas
        if len(pontos) >= 2:
            regiao_bbox = _bbox_de_pontos(pontos, 0.13 * largura, 0.10 * altura)
        elif not _bbox_toca_borda(bbox, frame_shape, "topo"):
            qualidade = QUALIDADE_FALLBACK
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (x1 + 0.10 * largura, y1 + 0.04 * altura, x2 - 0.10 * largura, y1 + 0.34 * altura)
        else:
            qualidade = QUALIDADE_INSUFICIENTE

    elif regiao == "orelhas":
        pontos = orelhas
        if len(orelhas) >= 1:
            regiao_bbox = _bbox_de_pontos(orelhas, 0.08 * largura, 0.055 * altura)
        elif len(olhos) >= 2 and not _bbox_toca_borda(bbox, frame_shape, "topo"):
            qualidade = QUALIDADE_FALLBACK
            metodo = "KEYPOINTS_FALLBACK"
            regiao_bbox = _bbox_de_pontos(olhos, 0.18 * largura, 0.08 * altura)
            pontos = olhos
        elif not _bbox_toca_borda(bbox, frame_shape, "topo"):
            qualidade = QUALIDADE_FALLBACK
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (x1 + 0.02 * largura, y1 + 0.05 * altura, x2 - 0.02 * largura, y1 + 0.30 * altura)
        else:
            qualidade = QUALIDADE_INSUFICIENTE

    elif regiao == "tronco":
        pontos = ombros + quadris
        if ombros and quadris:
            regiao_bbox = _bbox_de_pontos(pontos, 0.08 * largura, 0.06 * altura)
        elif not _bbox_toca_borda(bbox, frame_shape, "topo") and not _bbox_toca_borda(bbox, frame_shape, "base"):
            qualidade = QUALIDADE_FALLBACK
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (x1 + 0.08 * largura, y1 + 0.23 * altura, x2 - 0.08 * largura, y1 + 0.68 * altura)
        else:
            qualidade = QUALIDADE_INSUFICIENTE

    elif regiao == "quadril_tronco":
        pontos = ombros + quadris
        if quadris and (ombros or len(quadris) >= 2):
            regiao_bbox = _bbox_de_pontos(pontos or quadris, 0.10 * largura, 0.08 * altura)
        elif not _bbox_toca_borda(bbox, frame_shape, "base"):
            qualidade = QUALIDADE_FALLBACK
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (x1 + 0.08 * largura, y1 + 0.38 * altura, x2 - 0.08 * largura, y1 + 0.72 * altura)
        else:
            qualidade = QUALIDADE_INSUFICIENTE

    elif regiao == "maos":
        pontos = punhos
        if punhos:
            regiao_bbox = _bbox_de_pontos(punhos, 0.10 * largura, 0.08 * altura)
        elif not (_bbox_toca_borda(bbox, frame_shape, "esquerda") or _bbox_toca_borda(bbox, frame_shape, "direita")):
            qualidade = QUALIDADE_FALLBACK
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (x1 - 0.05 * largura, y1 + 0.28 * altura, x2 + 0.05 * largura, y1 + 0.72 * altura)
        else:
            qualidade = QUALIDADE_INSUFICIENTE

    elif regiao == "pes":
        pontos = tornozelos
        if tornozelos:
            regiao_bbox = _bbox_de_pontos(tornozelos, 0.11 * largura, 0.08 * altura)
            regiao_bbox = (
                regiao_bbox[0],
                regiao_bbox[1] - 0.02 * altura,
                regiao_bbox[2],
                regiao_bbox[3] + 0.08 * altura,
            )
        elif not _bbox_toca_borda(bbox, frame_shape, "base"):
            qualidade = QUALIDADE_FALLBACK
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (x1 - 0.04 * largura, y1 + 0.80 * altura, x2 + 0.04 * largura, y2 + 0.03 * altura)
        else:
            qualidade = QUALIDADE_INSUFICIENTE

    else:  # corpo / macacão
        pontos = ombros + quadris + tornozelos
        if ombros and quadris and tornozelos:
            regiao_bbox = _bbox_de_pontos(pontos, 0.08 * largura, 0.05 * altura)
        elif not (_bbox_toca_borda(bbox, frame_shape, "topo") or _bbox_toca_borda(bbox, frame_shape, "base")):
            qualidade = QUALIDADE_FALLBACK
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (x1 + 0.03 * largura, y1 + 0.05 * altura, x2 - 0.03 * largura, y2 - 0.03 * altura)
        else:
            qualidade = QUALIDADE_INSUFICIENTE

    if qualidade == QUALIDADE_INSUFICIENTE or not _bbox_valida(regiao_bbox):
        return {
            "avaliavel": False,
            "qualidade": QUALIDADE_INSUFICIENTE,
            "metodo": metodo,
            "regiao": regiao,
            "bbox": None,
            "pontos": tuple(pontos),
            "motivo": f"região {regiao} não avaliável com segurança neste frame",
        }

    return {
        "avaliavel": True,
        "qualidade": qualidade,
        "metodo": metodo,
        "regiao": regiao,
        "bbox": tuple(float(v) for v in regiao_bbox),
        "pontos": tuple(pontos),
        "referencias": {
            "nariz": nariz,
            "olhos": tuple(olhos),
            "orelhas": tuple(orelhas),
        },
        "motivo": None,
    }


def _compatibilidade_bbox_regiao(bbox_epi, regiao_info, bbox_pessoa) -> float:
    regiao_bbox = regiao_info["bbox"]
    centro = _centro_bbox(bbox_epi)
    intersecao = _intersecao_sobre_area_bbox(bbox_epi, regiao_bbox)
    centro_na_regiao = 1.0 if _ponto_em_bbox(centro, regiao_bbox) else 0.0
    pontos = list(regiao_info.get("pontos") or [])
    if pontos:
        distancia = min(_distancia_normalizada(centro, p, bbox_pessoa) for p in pontos)
    else:
        distancia = _distancia_normalizada(centro, _centro_bbox(regiao_bbox), bbox_pessoa)
    proximidade = max(0.0, 1.0 - min(1.0, distancia / 0.30))
    return float(0.60 * max(intersecao, centro_na_regiao) + 0.40 * proximidade)



def _recortar_bbox_frame(frame, bbox, margem=0.0):
    if frame is None or not hasattr(frame, "shape") or len(frame.shape) < 2:
        return None, None

    if not _bbox_valida(bbox):
        return None, None

    altura_frame, largura_frame = frame.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in bbox]

    largura = max(1.0, x2 - x1)
    altura = max(1.0, y2 - y1)

    x1 -= margem * largura
    x2 += margem * largura
    y1 -= margem * altura
    y2 += margem * altura

    ix1 = max(0, min(largura_frame - 1, int(math.floor(x1))))
    iy1 = max(0, min(altura_frame - 1, int(math.floor(y1))))
    ix2 = max(ix1 + 1, min(largura_frame, int(math.ceil(x2))))
    iy2 = max(iy1 + 1, min(altura_frame, int(math.ceil(y2))))

    crop = frame[iy1:iy2, ix1:ix2]
    if crop is None or crop.size == 0:
        return None, None

    return crop, (ix1, iy1, ix2, iy2)


def _mascara_visual_epi(crop):
    if crop is None or crop.size == 0:
        return None

    if crop.shape[0] < 12 or crop.shape[1] < 12:
        return None

    cinza = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    cinza = cv2.GaussianBlur(cinza, (5, 5), 0)

    mediana = float(np.median(cinza))
    limiar_baixo = int(max(20, 0.66 * mediana))
    limiar_alto = int(min(255, max(limiar_baixo + 20, 1.33 * mediana)))
    bordas = cv2.Canny(cinza, limiar_baixo, limiar_alto)

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    saturacao = hsv[:, :, 1]
    valor = hsv[:, :, 2]

    limiar_sat = max(35, int(np.percentile(saturacao, 60)))
    mascara_cor = (
        (saturacao >= limiar_sat)
        & (valor >= 35)
    ).astype(np.uint8) * 255

    kernel = np.ones((3, 3), dtype=np.uint8)
    bordas = cv2.dilate(bordas, kernel, iterations=1)
    mascara_cor = cv2.morphologyEx(
        mascara_cor,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=1,
    )

    return cv2.bitwise_or(bordas, mascara_cor)


def _angulo_visual_dominante(mascara):
    if mascara is None:
        return None

    ys, xs = np.nonzero(mascara > 0)
    if len(xs) < 30:
        return None

    pontos = np.column_stack(
        (xs.astype(np.float32), ys.astype(np.float32))
    )

    _media, autovetores = cv2.PCACompute(
        pontos,
        mean=None,
        maxComponents=2,
    )

    if autovetores is None or len(autovetores) == 0:
        return None

    vx, vy = autovetores[0]
    angulo = math.degrees(
        math.atan2(float(vy), float(vx))
    )

    while angulo > 90.0:
        angulo -= 180.0

    while angulo < -90.0:
        angulo += 180.0

    return float(angulo)


def _assimetria_visual_horizontal(mascara, eixo_x):
    if mascara is None:
        return None

    h, w = mascara.shape[:2]

    if h < 10 or w < 10:
        return None

    eixo_x = int(round(float(eixo_x)))
    eixo_x = max(1, min(w - 2, eixo_x))

    raio = min(eixo_x, w - eixo_x)

    if raio < 6:
        return None

    esquerda = mascara[:, eixo_x - raio:eixo_x]
    direita = mascara[:, eixo_x:eixo_x + raio]
    direita = np.fliplr(direita)

    a = esquerda > 0
    b = direita > 0

    uniao = np.logical_or(a, b).sum()

    if uniao < 40:
        return None

    diferenca = np.logical_xor(a, b).sum()

    return float(
        diferenca / max(1, uniao)
    )


def _validacao_visual_capacete(
    frame,
    bbox_epi,
    regiao_info,
):
    referencias = regiao_info.get("referencias") or {}
    olhos = list(referencias.get("olhos") or [])
    nariz = referencias.get("nariz")

    if frame is None or len(olhos) < 2:
        return None, None

    crop, origem = _recortar_bbox_frame(
        frame,
        bbox_epi,
        margem=0.03,
    )

    if crop is None:
        return None, None

    mascara = _mascara_visual_epi(crop)

    if mascara is None:
        return None, None

    olhos = sorted(
        olhos,
        key=lambda p: p[0],
    )

    olho_e, olho_d = olhos[0], olhos[-1]

    dist_olhos = max(
        1.0,
        math.hypot(
            olho_d[0] - olho_e[0],
            olho_d[1] - olho_e[1],
        ),
    )

    centro_olhos_x = (
        olho_e[0] + olho_d[0]
    ) / 2.0

    face_frontal = True

    if nariz is not None:
        desvio_nariz = (
            abs(float(nariz[0]) - centro_olhos_x)
            / dist_olhos
        )

        face_frontal = (
            desvio_nariz <= 0.38
        )

    ox1, _oy1, _, _ = origem
    eixo_crop = centro_olhos_x - ox1

    angulo = _angulo_visual_dominante(
        mascara
    )

    if (
        angulo is not None
        and abs(angulo) >= 28.0
    ):
        return (
            "INCOMPATIVEL",
            (
                "capacete com inclinacao visual "
                f"incompativel ({angulo:.1f} graus)"
            ),
        )

    if face_frontal:
        assimetria = _assimetria_visual_horizontal(
            mascara,
            eixo_crop,
        )

        if (
            assimetria is not None
            and assimetria >= 0.58
        ):
            return (
                "INCOMPATIVEL",
                (
                    "capacete visualmente "
                    f"assimetrico/deslocado ({assimetria:.2f})"
                ),
            )

        h, _w = mascara.shape[:2]
        y_inicio = int(0.52 * h)
        faixa = mascara[y_inicio:, :]

        _ys, xs = np.nonzero(
            faixa > 0
        )

        if len(xs) >= 25:
            eixo = float(eixo_crop)

            esquerda = max(
                1.0,
                eixo - float(xs.min()),
            )

            direita = max(
                1.0,
                float(xs.max()) - eixo,
            )

            razao = (
                max(esquerda, direita)
                / max(1.0, min(esquerda, direita))
            )

            if razao >= 2.35:
                return (
                    "INCOMPATIVEL",
                    (
                        "aba/borda do capacete "
                        f"excessivamente lateral ({razao:.2f})"
                    ),
                )

    return None, None


def _validacao_visual_oculos(
    frame,
    bbox_epi,
    regiao_info,
):
    referencias = regiao_info.get("referencias") or {}
    olhos = list(referencias.get("olhos") or [])

    if frame is None or len(olhos) < 2:
        return None, None

    crop, origem = _recortar_bbox_frame(
        frame,
        bbox_epi,
        margem=0.08,
    )

    if crop is None:
        return None, None

    mascara = _mascara_visual_epi(
        crop
    )

    if mascara is None:
        return None, None

    olhos = sorted(
        olhos,
        key=lambda p: p[0],
    )

    olho_e, olho_d = olhos[0], olhos[-1]

    dist_olhos = max(
        1.0,
        math.hypot(
            olho_d[0] - olho_e[0],
            olho_d[1] - olho_e[1],
        ),
    )

    angulo = _angulo_visual_dominante(
        mascara
    )

    if (
        angulo is not None
        and abs(angulo) >= 24.0
    ):
        return (
            "INCOMPATIVEL",
            (
                "oculos com inclinacao visual "
                f"incompativel ({angulo:.1f} graus)"
            ),
        )

    ox1, oy1, _, _ = origem

    pontos_crop = [
        (
            float(p[0]) - ox1,
            float(p[1]) - oy1,
        )
        for p in olhos
    ]

    h, w = mascara.shape[:2]

    raio = max(
        3,
        int(round(0.28 * dist_olhos)),
    )

    cobertura = []

    for px, py in pontos_crop:
        ix = int(round(px))
        iy = int(round(py))

        x1 = max(0, ix - raio)
        x2 = min(w, ix + raio + 1)
        y1 = max(0, iy - raio)
        y2 = min(h, iy + raio + 1)

        if x2 <= x1 or y2 <= y1:
            continue

        janela = mascara[
            y1:y2,
            x1:x2,
        ]

        cobertura.append(
            float(
                np.mean(janela > 0)
            )
        )

    if len(cobertura) == 2:
        maior = max(cobertura)
        menor = min(cobertura)

        if (
            maior >= 0.22
            and menor <= 0.07
        ):
            return (
                "INCOMPATIVEL",
                "oculos visualmente deslocado de um dos olhos",
            )

    return None, None


def _validacao_especifica_capacete(bbox_epi, regiao_info, bbox_pessoa, frame=None):
    """Retorna (estado, motivo) apenas quando há evidência geométrica forte.

    estado:
      - "INCOMPATIVEL": uso claramente incorreto
      - None: deixa a regra anatômica geral decidir
    """
    referencias = regiao_info.get("referencias") or {}
    olhos = list(referencias.get("olhos") or [])

    ex1, ey1, ex2, ey2 = [float(v) for v in bbox_epi]
    largura_epi = max(1.0, ex2 - ex1)
    altura_epi = max(1.0, ey2 - ey1)
    cx_epi, cy_epi = _centro_bbox(bbox_epi)

    px1, py1, px2, py2 = [float(v) for v in bbox_pessoa]
    altura_pessoa = max(1.0, py2 - py1)

    # Capacete quase "em pé"/girado produz uma caixa muito vertical.
    proporcao = largura_epi / altura_epi
    if proporcao < 0.82:
        return "INCOMPATIVEL", "capacete com orientação visual incompatível"

    if len(olhos) >= 2:
        olhos = sorted(olhos, key=lambda p: p[0])
        olho_e, olho_d = olhos[0], olhos[-1]

        dist_olhos = max(
            1.0,
            math.hypot(
                olho_d[0] - olho_e[0],
                olho_d[1] - olho_e[1],
            )
        )
        centro_olhos_x = (olho_e[0] + olho_d[0]) / 2.0
        linha_olhos_y = (olho_e[1] + olho_d[1]) / 2.0

        # Deslocamento lateral claro em relação ao eixo da face.
        if abs(cx_epi - centro_olhos_x) > 0.95 * dist_olhos:
            return "INCOMPATIVEL", "capacete deslocado lateralmente da cabeça"

        # Centro do capacete não deve ficar na altura/abaixo dos olhos.
        if cy_epi >= linha_olhos_y + 0.15 * dist_olhos:
            return "INCOMPATIVEL", "capacete abaixo da região esperada da cabeça"

        # A base do capacete pode chegar perto da linha dos olhos, mas não
        # descer claramente pela face.
        if ey2 > linha_olhos_y + 0.60 * dist_olhos:
            return "INCOMPATIVEL", "capacete avançando excessivamente sobre a face"

        # Muito estreito em relação à cabeça sugere objeto girado/deslocado.
        if largura_epi < 0.95 * dist_olhos:
            return "INCOMPATIVEL", "capacete estreito/desalinhado para a largura da cabeça"

    else:
        # Sem os dois olhos, só rejeita casos muito claros para não gerar
        # falso INCORRETO.
        rx1, ry1, rx2, ry2 = [float(v) for v in regiao_info["bbox"]]
        centro_regiao_x = (rx1 + rx2) / 2.0
        largura_regiao = max(1.0, rx2 - rx1)

        if abs(cx_epi - centro_regiao_x) > 0.60 * largura_regiao:
            return "INCOMPATIVEL", "capacete claramente deslocado da região da cabeça"

        if cy_epi > ry2 + 0.03 * altura_pessoa:
            return "INCOMPATIVEL", "capacete abaixo da região da cabeça"

    resultado_visual, motivo_visual = _validacao_visual_capacete(
        frame,
        bbox_epi,
        regiao_info,
    )

    if resultado_visual == "INCOMPATIVEL":
        return resultado_visual, motivo_visual

    return None, None


def _validacao_especifica_oculos(bbox_epi, regiao_info, frame=None):
    """Validação geométrica específica para óculos de segurança."""
    referencias = regiao_info.get("referencias") or {}
    olhos = list(referencias.get("olhos") or [])

    if len(olhos) < 2:
        return None, None

    olhos = sorted(olhos, key=lambda p: p[0])
    olho_e, olho_d = olhos[0], olhos[-1]

    dist_olhos = max(
        1.0,
        math.hypot(
            olho_d[0] - olho_e[0],
            olho_d[1] - olho_e[1],
        )
    )
    centro_olhos_x = (olho_e[0] + olho_d[0]) / 2.0
    linha_olhos_y = (olho_e[1] + olho_d[1]) / 2.0

    ex1, ey1, ex2, ey2 = [float(v) for v in bbox_epi]
    largura_epi = max(1.0, ex2 - ex1)
    altura_epi = max(1.0, ey2 - ey1)
    cx_epi, cy_epi = _centro_bbox(bbox_epi)

    # Óculos corretos precisam acompanhar a linha dos olhos.
    if abs(cy_epi - linha_olhos_y) > 0.60 * dist_olhos:
        return "INCOMPATIVEL", "óculos fora da linha dos olhos"

    if abs(cx_epi - centro_olhos_x) > 0.65 * dist_olhos:
        return "INCOMPATIVEL", "óculos deslocado lateralmente dos olhos"

    # A caixa precisa abranger visualmente os dois olhos.
    tolerancia_x = 0.28 * dist_olhos
    if ex1 > olho_e[0] + tolerancia_x or ex2 < olho_d[0] - tolerancia_x:
        return "INCOMPATIVEL", "óculos não cobre adequadamente os dois olhos"

    # Óculos normalmente formam uma caixa predominantemente horizontal.
    if largura_epi / altura_epi < 1.35:
        return "INCOMPATIVEL", "orientação dos óculos incompatível com uso correto"

    resultado_visual, motivo_visual = _validacao_visual_oculos(
        frame,
        bbox_epi,
        regiao_info,
    )

    if resultado_visual == "INCOMPATIVEL":
        return resultado_visual, motivo_visual

    return None, None


def _validacao_especifica_epi(epi, bbox_epi, regiao_info, bbox_pessoa, frame=None):
    if str(epi) == "Capacete":
        return _validacao_especifica_capacete(
            bbox_epi,
            regiao_info,
            bbox_pessoa,
            frame=frame,
        )

    if str(epi) == "Óculos":
        return _validacao_especifica_oculos(
            bbox_epi,
            regiao_info,
            frame=frame,
        )

    return None, None


def _evidencia_from_assoc(
    assoc,
    epi,
    regiao_info,
    bbox_pessoa,
    compatibilidade_correto_min: float,
    compatibilidade_incorreto_max: float,
    negativa_utilizavel_min: float,
    frame=None,
):
    bbox_epi = tuple(float(v) for v in assoc.bbox_epi)
    compatibilidade = _compatibilidade_bbox_regiao(
        bbox_epi,
        regiao_info,
        bbox_pessoa,
    )
    tipo = str(assoc.tipo_deteccao)

    motivo_especifico = None

    if tipo == TIPO_PRESENCA:
        resultado_especifico, motivo_especifico = _validacao_especifica_epi(
            epi=epi,
            bbox_epi=bbox_epi,
            regiao_info=regiao_info,
            bbox_pessoa=bbox_pessoa,
            frame=frame,
        )

        if resultado_especifico == "INCOMPATIVEL":
            compatibilidade = min(
                compatibilidade,
                float(compatibilidade_incorreto_max),
            )

    if tipo == TIPO_PRESENCA:
        if compatibilidade >= float(compatibilidade_correto_min):
            posicao = "COMPATIVEL"
            utilizavel = True
            motivo = "evidência positiva na região anatômica esperada"
        elif compatibilidade <= float(compatibilidade_incorreto_max):
            posicao = "INCOMPATIVEL"
            utilizavel = True
            motivo = (
                motivo_especifico
                or "evidência positiva fora da região anatômica esperada"
            )
        else:
            posicao = "INDETERMINADA"
            utilizavel = False
            motivo = "compatibilidade anatômica intermediária"
    else:
        if compatibilidade >= float(negativa_utilizavel_min):
            posicao = "NEGATIVA_LOCALIZADA"
            utilizavel = True
            motivo = "evidência negativa localizada na região anatômica esperada"
        else:
            posicao = "NEGATIVA_NAO_UTILIZAVEL"
            utilizavel = False
            motivo = "evidência negativa sem localização anatômica suficiente"

    return EvidenciaSemanticaEPI(
        detection_id=str(assoc.detection_id),
        classe_modelo=str(assoc.classe_modelo),
        tipo_deteccao=tipo,
        bbox_epi=bbox_epi,
        confianca_deteccao=float(assoc.confianca_deteccao),
        status_associacao=str(assoc.status_associacao),
        score_ownership=(None if assoc.score_ownership is None else float(assoc.score_ownership)),
        compatibilidade_regiao_esperada_etapa6=(
            None
            if assoc.compatibilidade_regiao_esperada is None
            else float(assoc.compatibilidade_regiao_esperada)
        ),
        compatibilidade_anatomica=compatibilidade,
        regiao_corporal_mais_proxima=(
            None
            if assoc.regiao_corporal_mais_proxima is None
            else str(assoc.regiao_corporal_mais_proxima)
        ),
        regiao_esperada=str(regiao_info["regiao"]),
        utilizavel=utilizavel,
        posicao=posicao,
        motivo=motivo,
    )


def _evidencia_sem_avaliacao(assoc, regiao_esperada: str) -> EvidenciaSemanticaEPI:
    return EvidenciaSemanticaEPI(
        detection_id=str(assoc.detection_id),
        classe_modelo=str(assoc.classe_modelo),
        tipo_deteccao=str(assoc.tipo_deteccao),
        bbox_epi=tuple(float(v) for v in assoc.bbox_epi),
        confianca_deteccao=float(assoc.confianca_deteccao),
        status_associacao=str(assoc.status_associacao),
        score_ownership=(None if assoc.score_ownership is None else float(assoc.score_ownership)),
        compatibilidade_regiao_esperada_etapa6=(
            None if assoc.compatibilidade_regiao_esperada is None
            else float(assoc.compatibilidade_regiao_esperada)
        ),
        compatibilidade_anatomica=None,
        regiao_corporal_mais_proxima=(
            None if assoc.regiao_corporal_mais_proxima is None
            else str(assoc.regiao_corporal_mais_proxima)
        ),
        regiao_esperada=str(regiao_esperada),
        utilizavel=False,
        posicao="INDETERMINADA",
        motivo="região anatômica não avaliável no frame atual",
    )


def _evidencia_ambigua(assoc) -> EvidenciaSemanticaEPI:
    return EvidenciaSemanticaEPI(
        detection_id=str(assoc.detection_id),
        classe_modelo=str(assoc.classe_modelo),
        tipo_deteccao=str(assoc.tipo_deteccao),
        bbox_epi=tuple(float(v) for v in assoc.bbox_epi),
        confianca_deteccao=float(assoc.confianca_deteccao),
        status_associacao=str(assoc.status_associacao),
        score_ownership=(None if assoc.score_ownership is None else float(assoc.score_ownership)),
        compatibilidade_regiao_esperada_etapa6=(
            None if assoc.compatibilidade_regiao_esperada is None
            else float(assoc.compatibilidade_regiao_esperada)
        ),
        regiao_corporal_mais_proxima=(
            None if assoc.regiao_corporal_mais_proxima is None
            else str(assoc.regiao_corporal_mais_proxima)
        ),
        regiao_esperada=(None if assoc.regiao_esperada is None else str(assoc.regiao_esperada)),
        utilizavel=False,
        posicao="AMBIGUA",
        motivo="associação ambígua da ETAPA 6",
    )


def avaliar_estado_epi_pessoa(
    pessoa: dict,
    epi: str,
    associacoes_pessoa: Iterable,
    evidencias_sem_associacao: Iterable,
    frame_shape=None,
    frame=None,
    compatibilidade_correto_min: float = 0.60,
    compatibilidade_incorreto_max: float = 0.30,
    negativa_utilizavel_min: float = 0.55,
) -> ResultadoEstadoEPIInstantaneo:
    camera_id = int(pessoa["camera_id"])
    track_id = int(pessoa["track_id"])
    track_instance_id = str(pessoa["track_instance_id"])

    if not bool(pessoa.get("detectado_no_frame", False)):
        raise ValueError("Pessoa não detectada no frame atual não deve receber estado instantâneo")

    regiao_info = _regiao_anatomica_avaliavel(
        pessoa,
        epi,
        frame_shape=frame_shape,
    )

    ambiguas = []
    for assoc in evidencias_sem_associacao or []:
        if str(assoc.epi) != str(epi):
            continue
        if str(assoc.status_associacao) != AMBIGUA:
            continue

        # A ETAPA 6 resolve AMBIGUA exclusivamente pela disputa entre o
        # melhor e o segundo melhor candidato, já ordenados deterministicamente
        # em assoc.candidatos. A ETAPA 7 preserva esse contrato: candidatos
        # posteriores são diagnósticos da associação, mas não participantes da
        # ambiguidade e, portanto, não recebem esta evidência semântica.
        candidatos_disputa = tuple(
            str(item[0])
            for item in tuple(assoc.candidatos or ())[:2]
        )
        if track_instance_id in candidatos_disputa:
            ambiguas.append(_evidencia_ambigua(assoc))
    ambiguas.sort(key=lambda e: e.detection_id)

    if not regiao_info["avaliavel"]:
        positivas = []
        negativas = []
        for assoc in associacoes_pessoa or []:
            if str(assoc.epi) != str(epi):
                continue
            if str(assoc.status_associacao) != ASSOCIADA:
                continue
            if str(assoc.track_instance_id) != track_instance_id:
                continue
            evidencia = _evidencia_sem_avaliacao(assoc, regiao_info["regiao"])
            if evidencia.tipo_deteccao == TIPO_PRESENCA:
                positivas.append(evidencia)
            elif evidencia.tipo_deteccao == TIPO_EVIDENCIA_NEGATIVA:
                negativas.append(evidencia)
        positivas.sort(key=lambda e: e.detection_id)
        negativas.sort(key=lambda e: e.detection_id)
        return ResultadoEstadoEPIInstantaneo(
            camera_id=camera_id,
            track_id=track_id,
            track_instance_id=track_instance_id,
            epi=str(epi),
            estado=ESTADO_INDETERMINADO,
            evidencias_positivas=tuple(positivas),
            evidencias_negativas=tuple(negativas),
            evidencias_ambiguas=tuple(ambiguas),
            qualidade_anatomica=QUALIDADE_INSUFICIENTE,
            metodo=str(regiao_info["metodo"]),
            motivos=(str(regiao_info["motivo"]),),
        )

    positivas = []
    negativas = []
    bbox_pessoa = tuple(float(v) for v in pessoa["bbox"])

    for assoc in associacoes_pessoa or []:
        if str(assoc.epi) != str(epi):
            continue
        if str(assoc.status_associacao) != ASSOCIADA:
            continue
        if str(assoc.track_instance_id) != track_instance_id:
            continue
        evidencia = _evidencia_from_assoc(
            assoc,
            epi,
            regiao_info,
            bbox_pessoa,
            compatibilidade_correto_min,
            compatibilidade_incorreto_max,
            negativa_utilizavel_min,
            frame=frame,
        )
        if evidencia.tipo_deteccao == TIPO_PRESENCA:
            positivas.append(evidencia)
        elif evidencia.tipo_deteccao == TIPO_EVIDENCIA_NEGATIVA:
            negativas.append(evidencia)

    positivas.sort(key=lambda e: e.detection_id)
    negativas.sort(key=lambda e: e.detection_id)

    positivas_corretas = [e for e in positivas if e.utilizavel and e.posicao == "COMPATIVEL"]
    positivas_incorretas = [e for e in positivas if e.utilizavel and e.posicao == "INCOMPATIVEL"]
    positivas_indeterminadas = [e for e in positivas if not e.utilizavel]
    negativas_validas = [e for e in negativas if e.utilizavel]

    motivos = []
    estado = ESTADO_INDETERMINADO

    # Associação ambígua relevante impede inferência pela detecção ambígua.
    # Se não houver outra evidência individual inequívoca, o estado permanece
    # INDETERMINADO.
    if ambiguas and not (positivas_corretas or positivas_incorretas or negativas_validas):
        motivos.append("há evidência relevante com associação AMBIGUA")
        estado = ESTADO_INDETERMINADO

    elif positivas_corretas and negativas_validas:
        motivos.append("conflito entre evidência positiva corretamente posicionada e evidência negativa válida")
        estado = ESTADO_INDETERMINADO

    elif positivas_corretas:
        motivos.append("evidência positiva associada e compatível com a região anatômica esperada")
        estado = ESTADO_CORRETO

    elif positivas_incorretas:
        if negativas_validas:
            motivos.append("EPI pertence à pessoa, está fora da região de uso e há evidência negativa coerente")
        else:
            motivos.append("EPI pertence à pessoa, mas está fora da região anatômica esperada")
        estado = ESTADO_INCORRETO

    elif negativas_validas:
        motivos.append("evidência negativa associada e anatomicamente utilizável, sem evidência positiva válida")
        estado = ESTADO_AUSENTE

    else:
        if positivas_indeterminadas:
            motivos.append("evidência positiva com compatibilidade anatômica insuficiente")
        elif ambiguas:
            motivos.append("há evidência relevante com associação AMBIGUA")
        else:
            motivos.append("sem evidência positiva ou negativa suficiente no frame atual")
        estado = ESTADO_INDETERMINADO

    return ResultadoEstadoEPIInstantaneo(
        camera_id=camera_id,
        track_id=track_id,
        track_instance_id=track_instance_id,
        epi=str(epi),
        estado=estado,
        evidencias_positivas=tuple(positivas),
        evidencias_negativas=tuple(negativas),
        evidencias_ambiguas=tuple(ambiguas),
        qualidade_anatomica=str(regiao_info["qualidade"]),
        metodo=str(regiao_info["metodo"]),
        motivos=tuple(motivos),
    )


def avaliar_estados_camera(
    camera_id: int,
    pessoas: Iterable[dict],
    associacoes_por_track: Dict[Tuple[int, str], Iterable],
    evidencias_sem_associacao: Iterable,
    epis_obrigatorios: Iterable[str],
    frame_shape=None,
    frame=None,
    compatibilidade_correto_min: float = 0.60,
    compatibilidade_incorreto_max: float = 0.30,
    negativa_utilizavel_min: float = 0.55,
) -> List[ResultadoEstadoEPIInstantaneo]:
    camera_id = int(camera_id)
    epis = sorted({str(epi) for epi in (epis_obrigatorios or [])})
    pessoas_validas = [
        pessoa for pessoa in (pessoas or [])
        if int(pessoa.get("camera_id", -1)) == camera_id
        and bool(pessoa.get("detectado_no_frame", False))
    ]
    pessoas_validas.sort(
        key=lambda p: (str(p.get("track_instance_id", "")), int(p.get("track_id", 0)))
    )

    resultados = []
    for pessoa in pessoas_validas:
        track_instance_id = str(pessoa["track_instance_id"])
        associacoes = list(
            associacoes_por_track.get((camera_id, track_instance_id), []) or []
        )
        for epi in epis:
            resultados.append(
                avaliar_estado_epi_pessoa(
                    pessoa=pessoa,
                    epi=epi,
                    associacoes_pessoa=associacoes,
                    evidencias_sem_associacao=evidencias_sem_associacao,
                    frame_shape=frame_shape,
                    frame=frame,
                    compatibilidade_correto_min=compatibilidade_correto_min,
                    compatibilidade_incorreto_max=compatibilidade_incorreto_max,
                    negativa_utilizavel_min=negativa_utilizavel_min,
                )
            )

    resultados.sort(
        key=lambda r: (r.camera_id, r.track_instance_id, r.epi)
    )
    return resultados
