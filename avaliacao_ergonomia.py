import math
import time


ESTADO_ADEQUADA = "ADEQUADA"
ESTADO_INADEQUADA = "INADEQUADA"
ESTADO_INDETERMINADA = "INDETERMINADA"

POSTURA_EM_PE = "EM_PE"
POSTURA_SENTADA = "SENTADA"
POSTURA_INDETERMINADA = "INDETERMINADA"

# Confirmação temporal: evita oscilações por keypoints instáveis.
TEMPO_CONFIRMAR_INADEQUADA_SEGUNDOS = 1.40
TEMPO_CONFIRMAR_ADEQUADA_SEGUNDOS = 0.90
TEMPO_CONFIRMAR_MODO_SEGUNDOS = 0.70
TEMPO_EXPIRAR_SEM_OBSERVACAO_SEGUNDOS = 1.8

# Tronco.
LIMITE_INCLINACAO_LATERAL_TRONCO_GRAUS = 28.0
LIMITE_ASSIMETRIA_OMBROS_GRAUS = 16.0

# Braços.
LIMITE_ELEVACAO_BRACO_GRAUS = 70.0

# Pernas / modo sentado-em pé.
ANGULO_JOELHO_SENTADO_MAX = 135.0
ANGULO_JOELHO_EM_PE_MIN = 145.0
ANGULO_JOELHO_FLEXAO_EXCESSIVA = 85.0

# Sinal complementar para aproximação/curvatura em direção à câmera.
# É deliberadamente conservador: sozinho não condena a postura.
RAZAO_TRONCO_CABECA_CURVADO_MAX = 1.15

# Refinamento postural.
LIMITE_TRONCO_LADO_FORTE_GRAUS = 24.0
LIMITE_TRONCO_DOIS_LADOS_GRAUS = 16.0
LIMITE_DESVIO_PESCOCO_GRAUS = 45.0
LIMITE_APOIO_CABECA_NORMALIZADO = 0.72

_estados_temporais = {}


def _valor(ponto, nome, padrao=None):
    if isinstance(ponto, dict):
        return ponto.get(nome, padrao)
    return getattr(ponto, nome, padrao)


def _ponto_confiavel(keypoints, nome):
    ponto = (keypoints or {}).get(nome)
    if ponto is None:
        return None

    if not bool(_valor(ponto, "confiavel", False)):
        return None

    x = _valor(ponto, "x")
    y = _valor(ponto, "y")
    if x is None or y is None:
        return None

    return (float(x), float(y))


def _media_pontos(*pontos):
    validos = [p for p in pontos if p is not None]
    if not validos:
        return None
    return (
        sum(p[0] for p in validos) / len(validos),
        sum(p[1] for p in validos) / len(validos),
    )


def _distancia(a, b):
    if a is None or b is None:
        return None
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _angulo_tres_pontos(a, b, c):
    if a is None or b is None or c is None:
        return None

    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])

    na = math.hypot(*ba)
    nc = math.hypot(*bc)
    if na <= 1e-6 or nc <= 1e-6:
        return None

    cosv = (ba[0] * bc[0] + ba[1] * bc[1]) / (na * nc)
    cosv = max(-1.0, min(1.0, cosv))
    return math.degrees(math.acos(cosv))


def _angulo_segmento_vertical(origem, destino):
    if origem is None or destino is None:
        return None
    dx = destino[0] - origem[0]
    dy = origem[1] - destino[1]
    if abs(dx) <= 1e-6 and abs(dy) <= 1e-6:
        return None
    return abs(math.degrees(math.atan2(dx, max(1e-6, dy))))


def _angulo_linha_horizontal(a, b):
    if a is None or b is None:
        return None
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if abs(dx) <= 1e-6:
        return 90.0
    return abs(math.degrees(math.atan2(dy, dx)))


def _angulo_braco_vertical(ombro, cotovelo):
    if ombro is None or cotovelo is None:
        return None
    dx = cotovelo[0] - ombro[0]
    dy = cotovelo[1] - ombro[1]
    if abs(dx) <= 1e-6 and abs(dy) <= 1e-6:
        return None

    # 0 = braço caído para baixo; 90 = horizontal; 180 = para cima.
    ang = math.degrees(math.atan2(abs(dx), max(1e-6, cotovelo[1] - ombro[1])))
    if cotovelo[1] < ombro[1]:
        ang = 180.0 - ang
    return max(0.0, min(180.0, ang))


def _extrair(track):
    k = getattr(track, "keypoints", {}) or {}
    nomes = (
        "nariz",
        "olho_esquerdo", "olho_direito",
        "orelha_esquerda", "orelha_direita",
        "ombro_esquerdo", "ombro_direito",
        "cotovelo_esquerdo", "cotovelo_direito",
        "punho_esquerdo", "punho_direito",
        "quadril_esquerdo", "quadril_direito",
        "joelho_esquerdo", "joelho_direito",
        "tornozelo_esquerdo", "tornozelo_direito",
    )
    return {nome: _ponto_confiavel(k, nome) for nome in nomes}


def _detectar_modo(p, track=None):
    qe, qd = p["quadril_esquerdo"], p["quadril_direito"]
    je, jd = p["joelho_esquerdo"], p["joelho_direito"]
    te, td = p["tornozelo_esquerdo"], p["tornozelo_direito"]

    ombros = _media_pontos(
        p["ombro_esquerdo"],
        p["ombro_direito"],
    )
    quadris = _media_pontos(qe, qd)
    joelhos = _media_pontos(je, jd)

    metricas = {}
    votos_sentado = 0
    votos_em_pe = 0

    angulos = []
    ae = _angulo_tres_pontos(qe, je, te)
    ad = _angulo_tres_pontos(qd, jd, td)

    if ae is not None:
        angulos.append(ae)
    if ad is not None:
        angulos.append(ad)

    if angulos:
        angulo_medio = sum(angulos) / len(angulos)
        metricas["angulo_joelho_medio"] = round(angulo_medio, 1)

        if angulo_medio <= 130.0:
            votos_sentado += 3
        elif angulo_medio >= 150.0:
            votos_em_pe += 3

    if quadris is not None and joelhos is not None:
        dy_qj = abs(joelhos[1] - quadris[1])
        metricas["distancia_vertical_quadril_joelho"] = round(dy_qj, 1)

        largura_ombros = _distancia(
            p["ombro_esquerdo"],
            p["ombro_direito"],
        )
        if largura_ombros is not None and largura_ombros > 1.0:
            razao_qj = dy_qj / largura_ombros
            metricas["razao_quadril_joelho_ombros"] = round(razao_qj, 2)

            if razao_qj <= 1.35:
                votos_sentado += 2
            elif razao_qj >= 1.75:
                votos_em_pe += 2

    bbox = getattr(track, "bbox", None) if track is not None else None
    if bbox is not None and len(bbox) == 4:
        x1, y1, x2, y2 = [float(v) for v in bbox]
        largura_bbox = max(1.0, x2 - x1)
        altura_bbox = max(1.0, y2 - y1)
        razao_bbox = altura_bbox / largura_bbox
        metricas["razao_bbox_altura_largura"] = round(razao_bbox, 2)

        if razao_bbox >= 2.15:
            votos_em_pe += 2
        elif razao_bbox <= 1.75:
            votos_sentado += 2

    if quadris is not None and ombros is not None:
        comprimento_tronco = _distancia(ombros, quadris)
        largura_ombros = _distancia(
            p["ombro_esquerdo"],
            p["ombro_direito"],
        )
        if (
            comprimento_tronco is not None
            and largura_ombros is not None
            and largura_ombros > 1.0
        ):
            razao_tronco = comprimento_tronco / largura_ombros
            metricas["razao_tronco_ombros"] = round(razao_tronco, 2)

            if joelhos is None and razao_tronco <= 1.60:
                votos_sentado += 1

    metricas["votos_sentado"] = votos_sentado
    metricas["votos_em_pe"] = votos_em_pe

    if votos_sentado >= votos_em_pe + 2:
        return POSTURA_SENTADA, metricas

    if votos_em_pe >= votos_sentado + 2:
        return POSTURA_EM_PE, metricas

    if votos_sentado >= 2 and votos_sentado > votos_em_pe:
        return POSTURA_SENTADA, metricas

    if votos_em_pe >= 2 and votos_em_pe > votos_sentado:
        return POSTURA_EM_PE, metricas

    return POSTURA_INDETERMINADA, metricas


def _centro_cabeca(p):
    pontos = [
        p.get("nariz"),
        p.get("olho_esquerdo"),
        p.get("olho_direito"),
        p.get("orelha_esquerda"),
        p.get("orelha_direita"),
    ]
    return _media_pontos(*pontos)



def _classificar_vista(p):
    """
    Classifica aproximadamente a vista da pessoa:
    - LATERAL: ombros projetados quase sobrepostos.
    - FRONTAL_OBLIQUA: largura aparente dos ombros maior.

    É apenas uma regra geométrica; não altera tracking nem pose.
    """
    oe = p.get("ombro_esquerdo")
    od = p.get("ombro_direito")
    qe = p.get("quadril_esquerdo")
    qd = p.get("quadril_direito")

    ombros = _media_pontos(oe, od)
    quadris = _media_pontos(qe, qd)

    largura_ombros = _distancia(oe, od)
    comprimento_tronco = _distancia(ombros, quadris)

    if (
        largura_ombros is None
        or comprimento_tronco is None
        or comprimento_tronco <= 1.0
    ):
        return "INDETERMINADA", {}

    razao = largura_ombros / comprimento_tronco

    if razao <= 0.62:
        vista = "LATERAL"
    else:
        vista = "FRONTAL_OBLIQUA"

    return vista, {
        "vista": vista,
        "razao_ombros_tronco": round(razao, 2),
    }


def _avaliar_tronco_por_lados(p):
    pares = (
        ("esquerdo", p.get("quadril_esquerdo"), p.get("ombro_esquerdo")),
        ("direito", p.get("quadril_direito"), p.get("ombro_direito")),
    )

    angulos = []
    metricas = {}

    for lado, quadril, ombro in pares:
        angulo = _angulo_segmento_vertical(quadril, ombro)
        if angulo is None:
            continue
        angulos.append(angulo)
        metricas[f"inclinacao_tronco_{lado}"] = round(angulo, 1)

    if not angulos:
        return False, metricas, 0

    maior = max(angulos)
    metricas["maior_inclinacao_tronco_lado"] = round(maior, 1)

    # Uma inclinação muito forte em um lado já é evidência suficiente.
    if maior >= LIMITE_TRONCO_LADO_FORTE_GRAUS:
        return True, metricas, len(angulos)

    # Quando os dois lados estão disponíveis, ambos precisam concordar
    # para uma inclinação moderada ser considerada problema.
    if (
        len(angulos) >= 2
        and min(angulos) >= LIMITE_TRONCO_DOIS_LADOS_GRAUS
    ):
        return True, metricas, len(angulos)

    return False, metricas, len(angulos)


def _avaliar_cabeca_pescoco(p):
    ombros = _media_pontos(
        p.get("ombro_esquerdo"),
        p.get("ombro_direito"),
    )
    quadris = _media_pontos(
        p.get("quadril_esquerdo"),
        p.get("quadril_direito"),
    )
    cabeca = _centro_cabeca(p)

    metricas = {}
    problemas = []

    if ombros is None or quadris is None or cabeca is None:
        return False, problemas, metricas, 0

    angulo = _angulo_tres_pontos(quadris, ombros, cabeca)
    if angulo is None:
        return False, problemas, metricas, 0

    desvio = abs(180.0 - angulo)
    metricas["desvio_pescoco_graus"] = round(desvio, 1)

    # Só considera pescoço inadequado quando a flexão/projeção é realmente forte.
    if desvio >= LIMITE_DESVIO_PESCOCO_GRAUS:
        problemas.append(("Cabeca/Pescoco", "FLEXAO OU PROJECAO EXCESSIVA"))
        return True, problemas, metricas, 1

    return False, problemas, metricas, 1

def _avaliar_apoio_cabeca_mao(p):
    cabeca = _centro_cabeca(p)
    if cabeca is None:
        return False, [], {}, 0

    largura_ombros = _distancia(
        p.get("ombro_esquerdo"),
        p.get("ombro_direito"),
    )

    ombros = _media_pontos(
        p.get("ombro_esquerdo"),
        p.get("ombro_direito"),
    )
    quadris = _media_pontos(
        p.get("quadril_esquerdo"),
        p.get("quadril_direito"),
    )
    comprimento_tronco = _distancia(ombros, quadris)

    escala = largura_ombros
    if escala is None or escala <= 1.0:
        escala = comprimento_tronco
    if escala is None or escala <= 1.0:
        return False, [], {}, 0

    distancias = []
    for punho in (p.get("punho_esquerdo"), p.get("punho_direito")):
        d = _distancia(punho, cabeca)
        if d is not None:
            distancias.append(d / escala)

    if not distancias:
        return False, [], {}, 0

    menor = min(distancias)
    metricas = {"mao_cabeca_normalizado": round(menor, 2)}

    if menor <= LIMITE_APOIO_CABECA_NORMALIZADO:
        return (
            True,
            [("Cabeca/Pescoco", "APOIO PROLONGADO NA MAO")],
            metricas,
            1,
        )

    return False, [], metricas, 1


def _avaliar_tronco(p, modo):
    oe, od = p["ombro_esquerdo"], p["ombro_direito"]
    qe, qd = p["quadril_esquerdo"], p["quadril_direito"]

    ombros = _media_pontos(oe, od)
    quadris = _media_pontos(qe, qd)

    problemas = []
    metricas = {}
    sinais_avaliados = 0

    vista, metricas_vista = _classificar_vista(p)
    metricas.update(metricas_vista)

    # Inclinação central.
    lateral_central = _angulo_segmento_vertical(quadris, ombros)
    if lateral_central is not None:
        metricas["inclinacao_tronco_central"] = round(lateral_central, 1)
        sinais_avaliados += 1

    # Inclinação calculada lado a lado.
    ruim_lados, metricas_lados, avaliados_lados = _avaliar_tronco_por_lados(p)
    metricas.update(metricas_lados)
    sinais_avaliados += avaliados_lados

    maior_lado = metricas_lados.get("maior_inclinacao_tronco_lado")

    if vista == "LATERAL":
        # Em vista lateral/oblíqua, a projeção ombro-quadril é a principal
        # evidência de flexão para frente.
        valor = maior_lado
        if valor is None:
            valor = lateral_central

        if valor is not None and valor >= 22.0:
            problemas.append(("Tronco", "INCLINACAO EXCESSIVA"))

    elif vista == "FRONTAL_OBLIQUA":
        # Em vista frontal, não tentamos inferir profundidade com um único
        # deslocamento. Apenas inclinação lateral forte é considerada.
        if (
            lateral_central is not None
            and lateral_central >= LIMITE_INCLINACAO_LATERAL_TRONCO_GRAUS
        ):
            problemas.append(("Tronco", "INCLINACAO EXCESSIVA"))

    else:
        # Sem vista definida, exige evidência mais forte.
        if ruim_lados and maior_lado is not None and maior_lado >= 30.0:
            problemas.append(("Tronco", "INCLINACAO EXCESSIVA"))

    # Assimetria fica somente como métrica de diagnóstico.
    assimetria = _angulo_linha_horizontal(oe, od)
    if assimetria is not None:
        metricas["assimetria_ombros"] = round(assimetria, 1)

    return bool(problemas), problemas, metricas, sinais_avaliados

def _avaliar_bracos(p):
    pares = (
        (p["ombro_esquerdo"], p["cotovelo_esquerdo"], p["punho_esquerdo"]),
        (p["ombro_direito"], p["cotovelo_direito"], p["punho_direito"]),
    )

    avaliados = 0
    elevado = False
    angulos = []

    for ombro, cotovelo, punho in pares:
        ang = _angulo_braco_vertical(ombro, cotovelo)
        if ang is not None:
            avaliados += 1
            angulos.append(ang)
            if ang >= LIMITE_ELEVACAO_BRACO_GRAUS:
                elevado = True

        # Evidência forte adicional.
        if ombro is not None and punho is not None and punho[1] < ombro[1]:
            elevado = True

    metricas = {}
    if angulos:
        metricas["maior_elevacao_braco"] = round(max(angulos), 1)

    problemas = []
    if elevado:
        problemas.append(("Bracos", "ELEVACAO EXCESSIVA"))

    return elevado, problemas, metricas, avaliados


def _avaliar_pernas(p, modo):
    qe, qd = p["quadril_esquerdo"], p["quadril_direito"]
    je, jd = p["joelho_esquerdo"], p["joelho_direito"]
    te, td = p["tornozelo_esquerdo"], p["tornozelo_direito"]

    angulos = []
    for a, b, c in ((qe, je, te), (qd, jd, td)):
        ang = _angulo_tres_pontos(a, b, c)
        if ang is not None:
            angulos.append(ang)

    if not angulos:
        return False, [], {}, 0

    menor = min(angulos)
    metricas = {"menor_angulo_joelho": round(menor, 1)}

    # Flexão do joelho é normal para quem está sentado.
    if modo == POSTURA_SENTADA:
        return False, [], metricas, len(angulos)

    if modo == POSTURA_EM_PE and menor <= ANGULO_JOELHO_FLEXAO_EXCESSIVA:
        return True, [("Pernas", "FLEXAO EXCESSIVA")], metricas, len(angulos)

    return False, [], metricas, len(angulos)


def _avaliar_instantaneo(track):
    p = _extrair(track)
    modo, metricas_modo = _detectar_modo(p, track)

    tronco_ruim, problemas_tronco, mt, aval_tronco = _avaliar_tronco(p, modo)
    pescoco_ruim, problemas_pescoco, mn, aval_pescoco = _avaliar_cabeca_pescoco(p)
    apoio_ruim, problemas_apoio, ma, aval_apoio = _avaliar_apoio_cabeca_mao(p)
    bracos_ruins, problemas_bracos, mb, aval_bracos = _avaliar_bracos(p)
    pernas_ruins, problemas_pernas, mp, aval_pernas = _avaliar_pernas(p, modo)

    # Pescoço isolado pode variar bastante conforme rotação da cabeça/câmera.
    # Só entra como problema final se for muito forte ou vier acompanhado
    # de outra evidência postural.
    problema_base = (
        tronco_ruim
        or apoio_ruim
        or bracos_ruins
        or pernas_ruins
    )

    incluir_pescoco = pescoco_ruim and (
        problema_base
        or mn.get("desvio_pescoco_graus", 0.0) >= 55.0
    )

    listas = [
        problemas_tronco,
        problemas_apoio,
        problemas_bracos,
        problemas_pernas,
    ]
    if incluir_pescoco:
        listas.append(problemas_pescoco)

    problemas = []
    vistos = set()

    for lista in listas:
        for regiao, descricao in lista:
            chave = (regiao, descricao)
            if chave not in vistos:
                vistos.add(chave)
                problemas.append({
                    "regiao": regiao,
                    "descricao": descricao,
                })

    metricas = {
        "modo_postura": modo,
        **metricas_modo,
        **mt,
        **mn,
        **ma,
        **mb,
        **mp,
    }

    total_avaliavel = (
        aval_tronco
        + aval_pescoco
        + aval_apoio
        + aval_bracos
        + aval_pernas
    )

    tem_problema = bool(problemas)

    if total_avaliavel < 3:
        estado = ESTADO_INDETERMINADA
    elif tem_problema:
        estado = ESTADO_INADEQUADA
    else:
        estado = ESTADO_ADEQUADA

    return {
        "estado_instantaneo": estado,
        "problemas_instantaneos": problemas,
        "metricas": metricas,
        "modo_postura": modo,
    }

def _assinatura_problemas(problemas):
    return tuple(
        sorted(
            (
                str(p.get("regiao", "")),
                str(p.get("descricao", "")),
            )
            for p in problemas
        )
    )


def _estabilizar(chave, instantaneo, agora):
    anterior = _estados_temporais.get(chave)

    if anterior is None:
        anterior = {
            "estado_confirmado": ESTADO_INDETERMINADA,
            "problemas_confirmados": [],
            "modo_confirmado": POSTURA_INDETERMINADA,
            "candidato_estado": instantaneo["estado_instantaneo"],
            "candidato_problemas": instantaneo["problemas_instantaneos"],
            "candidato_desde": agora,
            "candidato_modo": instantaneo["modo_postura"],
            "modo_desde": agora,
            "ultima_observacao": agora,
            "metricas": instantaneo["metricas"],
        }
        _estados_temporais[chave] = anterior

    estado_inst = instantaneo["estado_instantaneo"]
    problemas_inst = instantaneo["problemas_instantaneos"]
    modo_inst = instantaneo["modo_postura"]

    if modo_inst != POSTURA_INDETERMINADA:
        if anterior["candidato_modo"] != modo_inst:
            anterior["candidato_modo"] = modo_inst
            anterior["modo_desde"] = agora
        elif agora - anterior["modo_desde"] >= TEMPO_CONFIRMAR_MODO_SEGUNDOS:
            anterior["modo_confirmado"] = modo_inst

    mudou_estado = anterior["candidato_estado"] != estado_inst
    mudou_problema = (
        _assinatura_problemas(anterior["candidato_problemas"])
        != _assinatura_problemas(problemas_inst)
    )

    if mudou_estado or mudou_problema:
        anterior["candidato_estado"] = estado_inst
        anterior["candidato_problemas"] = list(problemas_inst)
        anterior["candidato_desde"] = agora

    anterior["ultima_observacao"] = agora
    anterior["metricas"] = instantaneo["metricas"]

    if estado_inst == ESTADO_INDETERMINADA:
        return anterior

    limite = (
        TEMPO_CONFIRMAR_INADEQUADA_SEGUNDOS
        if estado_inst == ESTADO_INADEQUADA
        else TEMPO_CONFIRMAR_ADEQUADA_SEGUNDOS
    )

    if agora - anterior["candidato_desde"] >= limite:
        anterior["estado_confirmado"] = estado_inst
        anterior["problemas_confirmados"] = list(problemas_inst)

    return anterior


def atualizar_ergonomia_camera(camera_id, tracks, agora=None):
    if agora is None:
        agora = time.monotonic()

    camera_id = int(camera_id)
    observados = set()

    for track in tracks or []:
        if not getattr(track, "detectado_no_frame", False):
            continue

        track_instance_id = str(getattr(track, "track_instance_id", ""))
        if not track_instance_id:
            continue

        chave = (camera_id, track_instance_id)
        observados.add(chave)
        instantaneo = _avaliar_instantaneo(track)
        _estabilizar(chave, instantaneo, agora)

    remover = []
    for chave, estado in _estados_temporais.items():
        if chave[0] != camera_id or chave in observados:
            continue
        if agora - estado.get("ultima_observacao", agora) >= TEMPO_EXPIRAR_SEM_OBSERVACAO_SEGUNDOS:
            remover.append(chave)

    for chave in remover:
        _estados_temporais.pop(chave, None)


def obter_estado_ergonomia(camera_id, track_instance_id):
    chave = (int(camera_id), str(track_instance_id))
    estado = _estados_temporais.get(chave)

    if estado is None:
        return {
            "estado": ESTADO_INDETERMINADA,
            "problemas": [],
            "modo": POSTURA_INDETERMINADA,
            "metricas": {},
        }

    return {
        "estado": str(estado.get("estado_confirmado", ESTADO_INDETERMINADA)),
        "problemas": list(estado.get("problemas_confirmados", [])),
        "modo": str(estado.get("modo_confirmado", POSTURA_INDETERMINADA)),
        "metricas": dict(estado.get("metricas", {})),
    }


def limpar_ergonomia_camera(camera_id):
    camera_id = int(camera_id)
    remover = [chave for chave in _estados_temporais if chave[0] == camera_id]
    for chave in remover:
        _estados_temporais.pop(chave, None)
