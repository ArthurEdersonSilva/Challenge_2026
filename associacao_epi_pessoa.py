import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ASSOCIACAO_ASSOCIADA = "ASSOCIADA"
ASSOCIACAO_AMBIGUA = "AMBIGUA"
ASSOCIACAO_NAO_ASSOCIADA = "NAO_ASSOCIADA"

TIPO_PRESENCA = "PRESENCA"
TIPO_EVIDENCIA_NEGATIVA = "EVIDENCIA_NEGATIVA_MODELO"


@dataclass(frozen=True)
class DeteccaoEPINormalizada:
    detection_id: str
    camera_id: int
    classe_modelo: str
    epi: str
    tipo_deteccao: str
    bbox: Tuple[float, float, float, float]
    centro: Tuple[float, float]
    confianca: float


@dataclass(frozen=True)
class CandidaturaAssociacao:
    detection_id: str
    camera_id: int
    track_id: int
    track_instance_id: str
    # Score usado exclusivamente para resolver DE QUEM é a detecção.
    # Para presença física equivale ao score_ownership. Para classes
    # Without representa o score de localização da evidência negativa.
    score: float
    score_ownership: Optional[float]
    componente_bbox: float
    componente_proximidade_corpo: float
    componente_proximidade_keypoints: float
    componente_regiao_esperada: float
    distancia_corporal_normalizada: Optional[float]
    distancia_regiao_esperada_normalizada: Optional[float]
    regiao_corporal_mais_proxima: Optional[str]
    regiao_esperada: str
    compatibilidade_regiao_esperada: float
    metodo_ownership: str
    metodo_regiao_esperada: str
    qualidade_geometrica: str


@dataclass(frozen=True)
class ResultadoAssociacao:
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
    # Campos geométricos preservados para a ETAPA 7. Nenhum deles
    # representa CORRETO/INCORRETO/AUSENTE/INDETERMINADO.
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


REGIAO_PRIMARIA_POR_EPI = {
    "Capacete": "cabeca",
    "Óculos": "face",
    "Máscara": "face",
    "Protetor auricular": "orelhas",
    "Protetor facial": "face",
    "Colete": "tronco",
    "Macacão de proteção": "corpo",
    "Cinto de segurança": "quadril_tronco",
    "Luvas": "maos",
    "Bota de segurança": "pes",
}


KEYPOINT_PARA_REGIAO_CORPORAL = {
    "nariz": "cabeca_face",
    "olho_esquerdo": "cabeca_face",
    "olho_direito": "cabeca_face",
    "orelha_esquerda": "cabeca_face",
    "orelha_direita": "cabeca_face",
    "ombro_esquerdo": "tronco",
    "ombro_direito": "tronco",
    "cotovelo_esquerdo": "braco_esquerdo",
    "cotovelo_direito": "braco_direito",
    "punho_esquerdo": "mao_esquerda",
    "punho_direito": "mao_direita",
    "quadril_esquerdo": "quadril",
    "quadril_direito": "quadril",
    "joelho_esquerdo": "perna_esquerda",
    "joelho_direito": "perna_direita",
    "tornozelo_esquerdo": "pe_esquerdo",
    "tornozelo_direito": "pe_direito",
}


def _bbox_valida(bbox) -> bool:
    if bbox is None or len(bbox) != 4:
        return False
    x1, y1, x2, y2 = [float(v) for v in bbox]
    return x2 > x1 and y2 > y1


def _centro_bbox(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _expandir_bbox(bbox, fator: float):
    x1, y1, x2, y2 = bbox
    largura = max(1.0, x2 - x1)
    altura = max(1.0, y2 - y1)
    dx = largura * float(fator)
    dy = altura * float(fator)
    return (x1 - dx, y1 - dy, x2 + dx, y2 + dy)


def _intersecao_sobre_area_epi(bbox_epi, bbox_pessoa) -> float:
    ex1, ey1, ex2, ey2 = bbox_epi
    px1, py1, px2, py2 = bbox_pessoa
    ix1 = max(ex1, px1)
    iy1 = max(ey1, py1)
    ix2 = min(ex2, px2)
    iy2 = min(ey2, py2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    area_epi = max(1.0, (ex2 - ex1) * (ey2 - ey1))
    return max(0.0, min(1.0, inter / area_epi))


def _ponto_em_bbox(ponto, bbox) -> bool:
    x, y = ponto
    x1, y1, x2, y2 = bbox
    return x1 <= x <= x2 and y1 <= y <= y2


def _distancia_normalizada(ponto_a, ponto_b, bbox_pessoa) -> float:
    distancia = math.hypot(
        float(ponto_a[0]) - float(ponto_b[0]),
        float(ponto_a[1]) - float(ponto_b[1]),
    )
    altura = max(1.0, float(bbox_pessoa[3]) - float(bbox_pessoa[1]))
    return distancia / altura


def _distancia_ponto_bbox_normalizada(ponto, bbox, bbox_pessoa) -> float:
    x, y = float(ponto[0]), float(ponto[1])
    x1, y1, x2, y2 = [float(v) for v in bbox]
    dx = max(x1 - x, 0.0, x - x2)
    dy = max(y1 - y, 0.0, y - y2)
    distancia = math.hypot(dx, dy)
    altura = max(1.0, float(bbox_pessoa[3]) - float(bbox_pessoa[1]))
    return distancia / altura


def _keypoints_corporais_confiaveis(pessoa: dict):
    pontos = []
    for nome, kp in sorted((pessoa.get("keypoints") or {}).items()):
        if not kp or not bool(kp.get("confiavel", False)):
            continue
        x = kp.get("x")
        y = kp.get("y")
        if x is None or y is None:
            continue
        pontos.append((str(nome), (float(x), float(y))))
    return pontos


def _proximidade_keypoints_corpo(centro_epi, pessoa: dict, bbox_pessoa):
    pontos = _keypoints_corporais_confiaveis(pessoa)
    if not pontos:
        return 0.0, None, None

    melhor_nome = None
    melhor_distancia = None
    for nome, ponto in pontos:
        distancia = _distancia_normalizada(centro_epi, ponto, bbox_pessoa)
        if melhor_distancia is None or distancia < melhor_distancia:
            melhor_distancia = distancia
            melhor_nome = nome

    # 0.45 da altura da pessoa é uma tolerância de ownership, não uma
    # regra de uso correto. O objetivo é reconhecer EPI carregado junto
    # ao corpo sem exigir a região anatômica de utilização.
    componente = max(0.0, 1.0 - min(1.0, float(melhor_distancia) / 0.45))
    regiao = KEYPOINT_PARA_REGIAO_CORPORAL.get(melhor_nome, melhor_nome)
    return float(componente), regiao, float(melhor_distancia)


def _kp_valido(pessoa, nome):
    kp = (pessoa.get("keypoints") or {}).get(nome)
    if not kp or not bool(kp.get("confiavel", False)):
        return None
    x = kp.get("x")
    y = kp.get("y")
    if x is None or y is None:
        return None
    return (float(x), float(y))


def _bbox_de_pontos(pontos: Sequence[Tuple[float, float]], margem_x, margem_y):
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


def derivar_regiao_anatomica(pessoa: dict, epi: str):
    bbox = tuple(float(v) for v in pessoa["bbox"])
    x1, y1, x2, y2 = bbox
    largura = max(1.0, x2 - x1)
    altura = max(1.0, y2 - y1)
    regiao = REGIAO_PRIMARIA_POR_EPI.get(epi, "corpo")

    nariz = _kp_valido(pessoa, "nariz")
    olhos = [
        p for p in (
            _kp_valido(pessoa, "olho_esquerdo"),
            _kp_valido(pessoa, "olho_direito"),
        ) if p is not None
    ]
    orelhas = [
        p for p in (
            _kp_valido(pessoa, "orelha_esquerda"),
            _kp_valido(pessoa, "orelha_direita"),
        ) if p is not None
    ]
    ombros = [
        p for p in (
            _kp_valido(pessoa, "ombro_esquerdo"),
            _kp_valido(pessoa, "ombro_direito"),
        ) if p is not None
    ]
    quadris = [
        p for p in (
            _kp_valido(pessoa, "quadril_esquerdo"),
            _kp_valido(pessoa, "quadril_direito"),
        ) if p is not None
    ]
    punhos = [
        p for p in (
            _kp_valido(pessoa, "punho_esquerdo"),
            _kp_valido(pessoa, "punho_direito"),
        ) if p is not None
    ]
    tornozelos = [
        p for p in (
            _kp_valido(pessoa, "tornozelo_esquerdo"),
            _kp_valido(pessoa, "tornozelo_direito"),
        ) if p is not None
    ]

    metodo = "KEYPOINTS_E_BBOX"
    centros_referencia = []

    if regiao == "cabeca":
        pontos = ([nariz] if nariz else []) + olhos + orelhas
        if pontos:
            regiao_bbox = _bbox_de_pontos(pontos, 0.14 * largura, 0.10 * altura)
            centros_referencia = pontos
        else:
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (x1, y1, x2, y1 + 0.28 * altura)
    elif regiao == "face":
        pontos = ([nariz] if nariz else []) + olhos + orelhas
        if pontos:
            regiao_bbox = _bbox_de_pontos(pontos, 0.12 * largura, 0.09 * altura)
            centros_referencia = pontos
        else:
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (
                x1 + 0.10 * largura,
                y1 + 0.04 * altura,
                x2 - 0.10 * largura,
                y1 + 0.34 * altura,
            )
    elif regiao == "orelhas":
        pontos = orelhas or olhos or ([nariz] if nariz else [])
        if pontos:
            regiao_bbox = _bbox_de_pontos(pontos, 0.13 * largura, 0.10 * altura)
            centros_referencia = pontos
        else:
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (x1, y1 + 0.03 * altura, x2, y1 + 0.32 * altura)
    elif regiao == "tronco":
        pontos = ombros + quadris
        if len(ombros) >= 1 and len(quadris) >= 1:
            regiao_bbox = _bbox_de_pontos(pontos, 0.08 * largura, 0.05 * altura)
            centros_referencia = pontos
        else:
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (
                x1 + 0.08 * largura,
                y1 + 0.22 * altura,
                x2 - 0.08 * largura,
                y1 + 0.68 * altura,
            )
    elif regiao == "quadril_tronco":
        pontos = ombros + quadris
        if quadris:
            regiao_bbox = _bbox_de_pontos(pontos or quadris, 0.10 * largura, 0.08 * altura)
            centros_referencia = quadris
        else:
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (
                x1 + 0.08 * largura,
                y1 + 0.40 * altura,
                x2 - 0.08 * largura,
                y1 + 0.72 * altura,
            )
    elif regiao == "maos":
        if punhos:
            regiao_bbox = _bbox_de_pontos(punhos, 0.12 * largura, 0.10 * altura)
            centros_referencia = punhos
        else:
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (
                x1 - 0.08 * largura,
                y1 + 0.25 * altura,
                x2 + 0.08 * largura,
                y1 + 0.72 * altura,
            )
    elif regiao == "pes":
        if tornozelos:
            regiao_bbox = _bbox_de_pontos(tornozelos, 0.12 * largura, 0.08 * altura)
            centros_referencia = tornozelos
        else:
            metodo = "BBOX_FALLBACK"
            regiao_bbox = (
                x1 - 0.05 * largura,
                y1 + 0.78 * altura,
                x2 + 0.05 * largura,
                y2 + 0.05 * altura,
            )
    else:
        regiao_bbox = bbox
        centros_referencia = [_centro_bbox(bbox)]

    return {
        "nome": regiao,
        "bbox": tuple(float(v) for v in regiao_bbox),
        "pontos_referencia": tuple(centros_referencia),
        "metodo": metodo,
    }


def normalizar_deteccoes(
    camera_id: int,
    deteccoes_brutas: Iterable[dict],
    epis_obrigatorios: Iterable[str],
    mapa_presenca: Dict[str, str],
    mapa_ausencia: Dict[str, str],
) -> List[DeteccaoEPINormalizada]:
    obrigatorios = set(epis_obrigatorios or [])
    itens = []

    for det in deteccoes_brutas or []:
        classe = str(det.get("classe_modelo", ""))
        if classe in mapa_presenca:
            epi = mapa_presenca[classe]
            tipo = TIPO_PRESENCA
        elif classe in mapa_ausencia:
            epi = mapa_ausencia[classe]
            tipo = TIPO_EVIDENCIA_NEGATIVA
        else:
            continue

        if epi not in obrigatorios:
            continue

        bbox = det.get("bbox")
        if not _bbox_valida(bbox):
            continue

        bbox = tuple(float(v) for v in bbox)
        confianca = float(det.get("confianca", 0.0))
        itens.append((classe, epi, tipo, bbox, confianca))

    # Ordenação canônica torna a saída independente da ordem do YOLO.
    itens.sort(key=lambda x: (
        x[0], x[1], x[2],
        round(x[3][0], 4), round(x[3][1], 4),
        round(x[3][2], 4), round(x[3][3], 4),
        round(x[4], 6),
    ))

    saida = []
    for ordinal, (classe, epi, tipo, bbox, confianca) in enumerate(itens, start=1):
        id_bbox = "-".join(f"{v:.2f}" for v in bbox)
        detection_id = f"{int(camera_id)}:{classe}:{id_bbox}:{confianca:.4f}:{ordinal}"
        saida.append(
            DeteccaoEPINormalizada(
                detection_id=detection_id,
                camera_id=int(camera_id),
                classe_modelo=classe,
                epi=epi,
                tipo_deteccao=tipo,
                bbox=bbox,
                centro=_centro_bbox(bbox),
                confianca=confianca,
            )
        )
    return saida


def _score_candidatura(
    deteccao: DeteccaoEPINormalizada,
    pessoa: dict,
    expansao_bbox: float,
) -> Optional[CandidaturaAssociacao]:
    if not bool(pessoa.get("detectado_no_frame", False)):
        return None

    bbox_pessoa = pessoa.get("bbox")
    if not _bbox_valida(bbox_pessoa):
        return None
    bbox_pessoa = tuple(float(v) for v in bbox_pessoa)
    bbox_expandida = _expandir_bbox(bbox_pessoa, expansao_bbox)
    centro_epi = deteccao.centro

    # Geometria geral de ownership: independente da região esperada de uso.
    componente_bbox = _intersecao_sobre_area_epi(deteccao.bbox, bbox_expandida)
    distancia_corpo = _distancia_ponto_bbox_normalizada(
        centro_epi, bbox_expandida, bbox_pessoa
    )
    componente_proximidade_corpo = max(
        0.0, 1.0 - min(1.0, distancia_corpo / 0.30)
    )
    centro_na_bbox_expandida = 1.0 if _ponto_em_bbox(centro_epi, bbox_expandida) else 0.0
    (
        componente_proximidade_keypoints,
        regiao_corporal_mais_proxima,
        distancia_keypoint,
    ) = _proximidade_keypoints_corpo(centro_epi, pessoa, bbox_pessoa)

    if distancia_keypoint is None:
        metodo_ownership = "BBOX_FALLBACK"
        qualidade_geometrica = "FALLBACK"
        score_ownership = (
            0.70 * componente_bbox
            + 0.20 * componente_proximidade_corpo
            + 0.10 * centro_na_bbox_expandida
        )
        distancia_corporal_normalizada = float(distancia_corpo)
    else:
        metodo_ownership = "KEYPOINTS_E_BBOX"
        qualidade_geometrica = "FORTE"
        score_ownership = (
            0.45 * componente_bbox
            + 0.20 * componente_proximidade_corpo
            + 0.25 * componente_proximidade_keypoints
            + 0.10 * centro_na_bbox_expandida
        )
        distancia_corporal_normalizada = min(
            float(distancia_corpo), float(distancia_keypoint)
        )

    # Compatibilidade anatômica esperada é calculada e preservada para a
    # ETAPA 7, mas NÃO bloqueia nem domina o ownership de detecção positiva.
    regiao = derivar_regiao_anatomica(pessoa, deteccao.epi)
    regiao_bbox = regiao["bbox"]
    componente_regiao_esperada = _intersecao_sobre_area_epi(
        deteccao.bbox, regiao_bbox
    )
    centro_na_regiao = 1.0 if _ponto_em_bbox(centro_epi, regiao_bbox) else 0.0
    pontos_regiao = list(regiao["pontos_referencia"])
    if pontos_regiao:
        distancia_regiao = min(
            _distancia_normalizada(centro_epi, ponto, bbox_pessoa)
            for ponto in pontos_regiao
        )
    else:
        distancia_regiao = _distancia_normalizada(
            centro_epi, _centro_bbox(regiao_bbox), bbox_pessoa
        )
    componente_distancia_regiao = max(
        0.0, 1.0 - min(1.0, float(distancia_regiao) / 0.65)
    )
    compatibilidade_regiao_esperada = (
        0.65 * max(componente_regiao_esperada, centro_na_regiao)
        + 0.35 * componente_distancia_regiao
    )

    if deteccao.tipo_deteccao == TIPO_EVIDENCIA_NEGATIVA:
        # Without... é evidência negativa localizada, não objeto físico.
        # Aqui a região anatômica correspondente continua central.
        score = (
            0.55 * max(componente_regiao_esperada, centro_na_regiao)
            + 0.35 * componente_distancia_regiao
            + 0.10 * componente_bbox
        )
        score_ownership_saida = None
        metodo_associacao = str(regiao["metodo"])
    else:
        score = float(score_ownership)
        score_ownership_saida = float(score_ownership)
        metodo_associacao = metodo_ownership

    return CandidaturaAssociacao(
        detection_id=deteccao.detection_id,
        camera_id=deteccao.camera_id,
        track_id=int(pessoa["track_id"]),
        track_instance_id=str(pessoa["track_instance_id"]),
        score=float(score),
        score_ownership=score_ownership_saida,
        componente_bbox=float(componente_bbox),
        componente_proximidade_corpo=float(componente_proximidade_corpo),
        componente_proximidade_keypoints=float(componente_proximidade_keypoints),
        componente_regiao_esperada=float(componente_regiao_esperada),
        distancia_corporal_normalizada=distancia_corporal_normalizada,
        distancia_regiao_esperada_normalizada=float(distancia_regiao),
        regiao_corporal_mais_proxima=regiao_corporal_mais_proxima,
        regiao_esperada=str(regiao["nome"]),
        compatibilidade_regiao_esperada=float(compatibilidade_regiao_esperada),
        metodo_ownership=metodo_associacao,
        metodo_regiao_esperada=str(regiao["metodo"]),
        qualidade_geometrica=qualidade_geometrica,
    )


def _campos_geometricos(candidatura: Optional[CandidaturaAssociacao]):
    if candidatura is None:
        return {}
    return {
        "score_ownership": candidatura.score_ownership,
        "componente_bbox": candidatura.componente_bbox,
        "componente_proximidade_corpo": candidatura.componente_proximidade_corpo,
        "componente_proximidade_keypoints": candidatura.componente_proximidade_keypoints,
        "componente_regiao_esperada": candidatura.componente_regiao_esperada,
        "distancia_corporal_normalizada": candidatura.distancia_corporal_normalizada,
        "distancia_regiao_esperada_normalizada": candidatura.distancia_regiao_esperada_normalizada,
        "regiao_corporal_mais_proxima": candidatura.regiao_corporal_mais_proxima,
        "regiao_esperada": candidatura.regiao_esperada,
        "compatibilidade_regiao_esperada": candidatura.compatibilidade_regiao_esperada,
        "metodo": candidatura.metodo_ownership,
        "metodo_regiao_esperada": candidatura.metodo_regiao_esperada,
        "qualidade_geometrica": candidatura.qualidade_geometrica,
    }

def associar_deteccoes_camera(
    camera_id: int,
    deteccoes_brutas: Iterable[dict],
    pessoas: Iterable[dict],
    epis_obrigatorios: Iterable[str],
    mapa_presenca: Dict[str, str],
    mapa_ausencia: Dict[str, str],
    score_minimo: float = 0.45,
    margem_ambiguidade: float = 0.08,
    intersecao_minima: float = 0.05,
    expansao_bbox: float = 0.08,
) -> List[ResultadoAssociacao]:
    deteccoes = normalizar_deteccoes(
        camera_id=camera_id,
        deteccoes_brutas=deteccoes_brutas,
        epis_obrigatorios=epis_obrigatorios,
        mapa_presenca=mapa_presenca,
        mapa_ausencia=mapa_ausencia,
    )

    pessoas_validas = [
        p for p in (pessoas or [])
        if int(p.get("camera_id", -1)) == int(camera_id)
        and bool(p.get("detectado_no_frame", False))
    ]
    pessoas_validas.sort(
        key=lambda p: (str(p.get("track_instance_id", "")), int(p.get("track_id", 0)))
    )

    # Primeiro calcula TODAS as candidaturas. Nenhuma decisão é tomada
    # durante a iteração das detecções retornadas pelo YOLO.
    candidaturas_por_deteccao: Dict[str, List[CandidaturaAssociacao]] = {
        d.detection_id: [] for d in deteccoes
    }
    for deteccao in deteccoes:
        for pessoa in pessoas_validas:
            candidatura = _score_candidatura(
                deteccao,
                pessoa,
                expansao_bbox=expansao_bbox,
            )
            if candidatura is None:
                continue

            # Para presença física exigimos vínculo corporal geral, nunca
            # compatibilidade com a região de uso esperada. Isso permite
            # capacete na mão, colete carregado etc. seguirem ASSOCIADOS
            # ao proprietário para posterior avaliação semântica na ETAPA 7.
            if deteccao.tipo_deteccao == TIPO_PRESENCA:
                vinculo_bbox = candidatura.componente_bbox >= intersecao_minima
                vinculo_corporal_proximo = (
                    candidatura.componente_proximidade_corpo >= 0.85
                    and candidatura.componente_proximidade_keypoints >= 0.55
                )
                if not (vinculo_bbox or vinculo_corporal_proximo):
                    continue
            candidaturas_por_deteccao[deteccao.detection_id].append(candidatura)

    resultados = []
    for deteccao in deteccoes:
        candidaturas = candidaturas_por_deteccao[deteccao.detection_id]
        candidaturas.sort(
            key=lambda c: (-round(c.score, 12), c.track_instance_id, c.track_id)
        )

        candidatos_resumo = tuple(
            (c.track_instance_id, float(c.score)) for c in candidaturas
        )

        if not candidaturas or candidaturas[0].score < float(score_minimo):
            resultados.append(
                ResultadoAssociacao(
                    detection_id=deteccao.detection_id,
                    camera_id=deteccao.camera_id,
                    classe_modelo=deteccao.classe_modelo,
                    epi=deteccao.epi,
                    tipo_deteccao=deteccao.tipo_deteccao,
                    bbox_epi=deteccao.bbox,
                    confianca_deteccao=deteccao.confianca,
                    status_associacao=ASSOCIACAO_NAO_ASSOCIADA,
                    score_assoc=(candidaturas[0].score if candidaturas else None),
                    score_segundo_candidato=(
                        candidaturas[1].score if len(candidaturas) > 1 else None
                    ),
                    candidatos=candidatos_resumo,
                    **_campos_geometricos(candidaturas[0] if candidaturas else None),
                )
            )
            continue

        melhor = candidaturas[0]
        segundo = candidaturas[1] if len(candidaturas) > 1 else None

        if (
            segundo is not None
            and (melhor.score - segundo.score) <= float(margem_ambiguidade)
        ):
            resultados.append(
                ResultadoAssociacao(
                    detection_id=deteccao.detection_id,
                    camera_id=deteccao.camera_id,
                    classe_modelo=deteccao.classe_modelo,
                    epi=deteccao.epi,
                    tipo_deteccao=deteccao.tipo_deteccao,
                    bbox_epi=deteccao.bbox,
                    confianca_deteccao=deteccao.confianca,
                    status_associacao=ASSOCIACAO_AMBIGUA,
                    score_assoc=melhor.score,
                    score_segundo_candidato=segundo.score,
                    candidatos=candidatos_resumo,
                    **_campos_geometricos(melhor),
                )
            )
            continue

        resultados.append(
            ResultadoAssociacao(
                detection_id=deteccao.detection_id,
                camera_id=deteccao.camera_id,
                classe_modelo=deteccao.classe_modelo,
                epi=deteccao.epi,
                tipo_deteccao=deteccao.tipo_deteccao,
                bbox_epi=deteccao.bbox,
                confianca_deteccao=deteccao.confianca,
                status_associacao=ASSOCIACAO_ASSOCIADA,
                track_id=melhor.track_id,
                track_instance_id=melhor.track_instance_id,
                score_assoc=melhor.score,
                score_segundo_candidato=(segundo.score if segundo else None),
                candidatos=candidatos_resumo,
                **_campos_geometricos(melhor),
            )
        )

    # Saída também é canônica e não depende da ordem original do modelo.
    resultados.sort(key=lambda r: r.detection_id)
    return resultados
