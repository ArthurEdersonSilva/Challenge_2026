from dataclasses import dataclass
import time
from typing import Dict, Iterable, List, Optional, Tuple


ESTADO_CORRETO = "CORRETO"
ESTADO_INCORRETO = "INCORRETO"
ESTADO_AUSENTE = "AUSENTE"
ESTADO_INDETERMINADO = "INDETERMINADO"

ESTADOS_VALIDOS = {
    ESTADO_CORRETO,
    ESTADO_INCORRETO,
    ESTADO_AUSENTE,
    ESTADO_INDETERMINADO,
}


@dataclass(frozen=True)
class ResultadoEstadoEPITemporal:
    camera_id: int
    track_id: int
    track_instance_id: str
    epi: str
    estado_instantaneo: str
    estado_candidato: Optional[str]
    estado_confirmado: Optional[str]
    candidato_desde: Optional[float]
    confirmado_desde: Optional[float]
    ultima_observacao: float
    quantidade_observacoes_candidato: int
    status_temporal: str


def _agora_monotonico(agora_monotonico: Optional[float]) -> float:
    return time.monotonic() if agora_monotonico is None else float(agora_monotonico)


def _tempo_confirmacao(estado: str, tempos_confirmacao: Dict[str, float]) -> float:
    if estado not in tempos_confirmacao:
        raise ValueError(f"Tempo de confirmação não configurado para estado: {estado}")
    valor = float(tempos_confirmacao[estado])
    if valor < 0:
        raise ValueError(f"Tempo de confirmação inválido para {estado}: {valor}")
    return valor


def _validar_resultado_instantaneo(item) -> None:
    estado = str(item.estado)
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(f"Estado instantâneo inválido: {estado}")
    if not str(item.track_instance_id):
        raise ValueError("track_instance_id vazio em estado instantâneo")
    if not str(item.epi):
        raise ValueError("EPI vazio em estado instantâneo")


def estabilizar_estado_epi(
    estado_instantaneo,
    estado_anterior: Optional[ResultadoEstadoEPITemporal],
    tempos_confirmacao: Dict[str, float],
    tolerancia_indeterminado_segundos: float,
    expiracao_indeterminado_segundos: float,
    agora_monotonico: Optional[float] = None,
) -> ResultadoEstadoEPITemporal:
    """Atualiza um único estado temporal usando somente o estado instantâneo.

    A função não interpreta geometria, não executa inferência e não conhece
    incidentes. Toda duração usa relógio monotônico e pode ser injetada em
    testes por ``agora_monotonico``.
    """
    _validar_resultado_instantaneo(estado_instantaneo)
    agora = _agora_monotonico(agora_monotonico)

    tolerancia_indeterminado_segundos = float(tolerancia_indeterminado_segundos)
    expiracao_indeterminado_segundos = float(expiracao_indeterminado_segundos)
    if tolerancia_indeterminado_segundos < 0:
        raise ValueError("Tolerância de INDETERMINADO não pode ser negativa")
    if expiracao_indeterminado_segundos < tolerancia_indeterminado_segundos:
        raise ValueError(
            "Expiração de INDETERMINADO deve ser >= tolerância de INDETERMINADO"
        )

    camera_id = int(estado_instantaneo.camera_id)
    track_id = int(estado_instantaneo.track_id)
    track_instance_id = str(estado_instantaneo.track_instance_id)
    epi = str(estado_instantaneo.epi)
    instantaneo = str(estado_instantaneo.estado)

    if estado_anterior is not None:
        if (
            int(estado_anterior.camera_id) != camera_id
            or str(estado_anterior.track_instance_id) != track_instance_id
            or str(estado_anterior.epi) != epi
        ):
            raise ValueError("Estado temporal anterior pertence a outra chave operacional")
        if agora < float(estado_anterior.ultima_observacao):
            raise ValueError("Tempo monotônico regressivo na estabilização de EPI")

    if estado_anterior is None:
        if instantaneo == ESTADO_INDETERMINADO:
            return ResultadoEstadoEPITemporal(
                camera_id=camera_id,
                track_id=track_id,
                track_instance_id=track_instance_id,
                epi=epi,
                estado_instantaneo=instantaneo,
                estado_candidato=ESTADO_INDETERMINADO,
                estado_confirmado=None,
                candidato_desde=agora,
                confirmado_desde=None,
                ultima_observacao=agora,
                quantidade_observacoes_candidato=1,
                status_temporal="INDETERMINADO_SEM_CONFIRMADO",
            )

        return ResultadoEstadoEPITemporal(
            camera_id=camera_id,
            track_id=track_id,
            track_instance_id=track_instance_id,
            epi=epi,
            estado_instantaneo=instantaneo,
            estado_candidato=instantaneo,
            estado_confirmado=None,
            candidato_desde=agora,
            confirmado_desde=None,
            ultima_observacao=agora,
            quantidade_observacoes_candidato=1,
            status_temporal="CANDIDATO_INICIADO",
        )

    confirmado = estado_anterior.estado_confirmado
    confirmado_desde = estado_anterior.confirmado_desde

    if instantaneo == ESTADO_INDETERMINADO:
        if estado_anterior.estado_candidato == ESTADO_INDETERMINADO:
            candidato_desde = estado_anterior.candidato_desde
            quantidade = estado_anterior.quantidade_observacoes_candidato + 1
        else:
            candidato_desde = agora
            quantidade = 1

        duracao_indeterminado = 0.0 if candidato_desde is None else agora - candidato_desde

        if confirmado is None:
            status = "INDETERMINADO_SEM_CONFIRMADO"
        elif duracao_indeterminado < tolerancia_indeterminado_segundos:
            status = "INDETERMINADO_CURTO_PRESERVA_CONFIRMADO"
        elif duracao_indeterminado < expiracao_indeterminado_segundos:
            status = "INDETERMINADO_AGUARDANDO_EXPIRACAO"
        else:
            confirmado = None
            confirmado_desde = None
            status = "CONFIRMADO_EXPIRADO_POR_INDETERMINADO"

        return ResultadoEstadoEPITemporal(
            camera_id=camera_id,
            track_id=track_id,
            track_instance_id=track_instance_id,
            epi=epi,
            estado_instantaneo=instantaneo,
            estado_candidato=ESTADO_INDETERMINADO,
            estado_confirmado=confirmado,
            candidato_desde=candidato_desde,
            confirmado_desde=confirmado_desde,
            ultima_observacao=agora,
            quantidade_observacoes_candidato=quantidade,
            status_temporal=status,
        )

    if estado_anterior.estado_candidato == instantaneo:
        candidato_desde = estado_anterior.candidato_desde
        quantidade = estado_anterior.quantidade_observacoes_candidato + 1
    else:
        candidato_desde = agora
        quantidade = 1

    if candidato_desde is None:
        candidato_desde = agora

    if confirmado == instantaneo:
        status = "CONFIRMADO_MANTIDO"
    else:
        tempo_minimo = _tempo_confirmacao(instantaneo, tempos_confirmacao)
        duracao_candidato = agora - candidato_desde
        if duracao_candidato >= tempo_minimo:
            confirmado = instantaneo
            confirmado_desde = agora
            status = "NOVO_ESTADO_CONFIRMADO"
        elif confirmado is None:
            status = "CANDIDATO_AGUARDANDO_CONFIRMACAO"
        else:
            status = "TRANSICAO_AGUARDANDO_CONFIRMACAO"

    return ResultadoEstadoEPITemporal(
        camera_id=camera_id,
        track_id=track_id,
        track_instance_id=track_instance_id,
        epi=epi,
        estado_instantaneo=instantaneo,
        estado_candidato=instantaneo,
        estado_confirmado=confirmado,
        candidato_desde=candidato_desde,
        confirmado_desde=confirmado_desde,
        ultima_observacao=agora,
        quantidade_observacoes_candidato=quantidade,
        status_temporal=status,
    )


def estabilizar_estados_camera(
    camera_id: int,
    estados_instantaneos: Iterable,
    estados_anteriores: Dict[Tuple[int, str, str], ResultadoEstadoEPITemporal],
    tempos_confirmacao: Dict[str, float],
    tolerancia_indeterminado_segundos: float,
    expiracao_indeterminado_segundos: float,
    agora_monotonico: Optional[float] = None,
) -> List[ResultadoEstadoEPITemporal]:
    """Estabiliza deterministicamente todos os estados instantâneos da câmera."""
    camera_id = int(camera_id)
    agora = _agora_monotonico(agora_monotonico)
    resultados = []
    chaves = set()

    itens = list(estados_instantaneos or [])
    itens.sort(key=lambda item: (str(item.track_instance_id), str(item.epi)))

    for item in itens:
        if int(item.camera_id) != camera_id:
            raise ValueError(
                f"Estado instantâneo com camera_id inconsistente: lote={camera_id}, estado={item.camera_id}"
            )
        chave = (camera_id, str(item.track_instance_id), str(item.epi))
        if chave in chaves:
            raise ValueError(f"Estado instantâneo duplicado para estabilização: {chave}")
        chaves.add(chave)
        resultados.append(
            estabilizar_estado_epi(
                estado_instantaneo=item,
                estado_anterior=estados_anteriores.get(chave),
                tempos_confirmacao=tempos_confirmacao,
                tolerancia_indeterminado_segundos=tolerancia_indeterminado_segundos,
                expiracao_indeterminado_segundos=expiracao_indeterminado_segundos,
                agora_monotonico=agora,
            )
        )

    resultados.sort(key=lambda item: (item.camera_id, item.track_instance_id, item.epi))
    return resultados


def expirar_estado_sem_observacao(
    estado_anterior: ResultadoEstadoEPITemporal,
    expiracao_sem_observacao_segundos: float,
    agora_monotonico: Optional[float] = None,
) -> ResultadoEstadoEPITemporal:
    """Expira estado temporal quando a câmera/track deixa de fornecer observação."""
    agora = _agora_monotonico(agora_monotonico)
    limite = float(expiracao_sem_observacao_segundos)
    if limite < 0:
        raise ValueError("Expiração sem observação não pode ser negativa")
    if agora < float(estado_anterior.ultima_observacao):
        raise ValueError("Tempo monotônico regressivo na expiração de EPI")

    if agora - float(estado_anterior.ultima_observacao) < limite:
        # O intervalo cego nunca conta como persistência de um candidato.
        # Um estado já confirmado pode sobreviver brevemente à perda de
        # observação, mas qualquer confirmação em andamento deve recomeçar
        # quando uma nova observação válida chegar.
        return ResultadoEstadoEPITemporal(
            camera_id=estado_anterior.camera_id,
            track_id=estado_anterior.track_id,
            track_instance_id=estado_anterior.track_instance_id,
            epi=estado_anterior.epi,
            estado_instantaneo=estado_anterior.estado_instantaneo,
            estado_candidato=None,
            estado_confirmado=estado_anterior.estado_confirmado,
            candidato_desde=None,
            confirmado_desde=estado_anterior.confirmado_desde,
            ultima_observacao=estado_anterior.ultima_observacao,
            quantidade_observacoes_candidato=0,
            status_temporal="SEM_OBSERVACAO_AGUARDANDO_EXPIRACAO",
        )

    return ResultadoEstadoEPITemporal(
        camera_id=estado_anterior.camera_id,
        track_id=estado_anterior.track_id,
        track_instance_id=estado_anterior.track_instance_id,
        epi=estado_anterior.epi,
        estado_instantaneo=estado_anterior.estado_instantaneo,
        estado_candidato=None,
        estado_confirmado=None,
        candidato_desde=None,
        confirmado_desde=None,
        ultima_observacao=estado_anterior.ultima_observacao,
        quantidade_observacoes_candidato=0,
        status_temporal="EXPIRADO_SEM_OBSERVACAO",
    )
