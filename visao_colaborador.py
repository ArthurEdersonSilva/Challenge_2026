from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np


CAMERA_ONLINE = "ONLINE"

ESTADO_CORRETO = "CORRETO"
ESTADO_INCORRETO = "INCORRETO"
ESTADO_AUSENTE = "AUSENTE"
ESTADO_INDETERMINADO = "INDETERMINADO"

IDENTIDADE_IDENTIFICADO = "IDENTIFICADO"
IDENTIDADE_DESCONHECIDO = "DESCONHECIDO"
IDENTIDADE_NAO_AVALIADO = "NAO_AVALIADO"
IDENTIDADE_AGUARDANDO_ROSTO = "AGUARDANDO_ROSTO"
IDENTIDADE_INDETERMINADO = "INDETERMINADO"

PROCESSAMENTO_EM_FILA = "EM_FILA"
PROCESSAMENTO_IDENTIFICANDO = "IDENTIFICANDO"


@dataclass(frozen=True)
class EPIViewModel:
    epi: str
    estado: str
    status_temporal: str = ""


@dataclass(frozen=True)
class AlertaViewModel:
    incidente_id: str
    epi: str
    tipo_irregularidade: str
    severidade: str
    suspenso: bool


@dataclass(frozen=True)
class ViewModelColaborador:
    camera_id: Optional[int]
    camera_nome: str
    camera_online: bool
    track_id: Optional[int]
    track_instance_id: Optional[str]
    pessoas_detectadas: int
    status_identidade: str
    texto_identidade: str
    nome: str
    matricula: str
    cargo: str
    epis: Tuple[EPIViewModel, ...] = field(default_factory=tuple)
    alertas: Tuple[AlertaViewModel, ...] = field(default_factory=tuple)


class ControladorVisaoColaborador:
    """
    Estado exclusivamente local da camada de apresentação.

    Não executa inferência e não modifica EstadoSistema/snapshot.
    Mantém câmera e colaborador selecionados enquanto permanecem elegíveis.
    """

    def __init__(self):
        self.camera_visual_colaborador: Optional[int] = None
        self.track_instance_visual_colaborador: Optional[str] = None

    @staticmethod
    def _camera_online(camera: Dict[str, Any]) -> bool:
        return bool(camera.get("ativa", True)) and str(camera.get("status")) == CAMERA_ONLINE

    @staticmethod
    def _pessoa_elegivel(pessoa: Dict[str, Any], camera_id: int) -> bool:
        if int(pessoa.get("camera_id", -1)) != int(camera_id):
            return False
        if not bool(pessoa.get("ativo")) or not bool(pessoa.get("detectado_no_frame")):
            return False
        bbox = pessoa.get("bbox")
        if not isinstance(bbox, (tuple, list)) or len(bbox) != 4:
            return False
        try:
            x1, y1, x2, y2 = (float(v) for v in bbox)
        except (TypeError, ValueError):
            return False
        return x2 > x1 and y2 > y1

    @staticmethod
    def _area_bbox(pessoa: Dict[str, Any]) -> float:
        x1, y1, x2, y2 = (float(v) for v in pessoa["bbox"])
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

    def selecionar_camera(self, snapshot: Dict[str, Any]) -> Optional[int]:
        cameras = snapshot.get("cameras", {}) or {}

        if self.camera_visual_colaborador is not None:
            atual = cameras.get(self.camera_visual_colaborador)
            if atual is not None and self._camera_online(atual):
                return self.camera_visual_colaborador

        online = sorted(
            int(camera_id)
            for camera_id, camera in cameras.items()
            if self._camera_online(camera)
        )
        self.camera_visual_colaborador = online[0] if online else None
        self.track_instance_visual_colaborador = None
        return self.camera_visual_colaborador

    def selecionar_colaborador(
        self,
        snapshot: Dict[str, Any],
        camera_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        if camera_id is None:
            self.track_instance_visual_colaborador = None
            return None

        pessoas = [
            pessoa
            for pessoa in (snapshot.get("pessoas", {}) or {}).values()
            if self._pessoa_elegivel(pessoa, camera_id)
        ]

        if self.track_instance_visual_colaborador is not None:
            for pessoa in pessoas:
                if str(pessoa.get("track_instance_id")) == self.track_instance_visual_colaborador:
                    return pessoa

        if not pessoas:
            self.track_instance_visual_colaborador = None
            return None

        pessoas.sort(
            key=lambda pessoa: (
                -self._area_bbox(pessoa),
                -float(pessoa.get("confianca") or 0.0),
                int(pessoa.get("track_id") or 0),
                str(pessoa.get("track_instance_id") or ""),
            )
        )
        selecionada = pessoas[0]
        self.track_instance_visual_colaborador = str(selecionada.get("track_instance_id"))
        return selecionada

    def construir_viewmodel(self, snapshot: Dict[str, Any]) -> ViewModelColaborador:
        camera_id = self.selecionar_camera(snapshot)
        cameras = snapshot.get("cameras", {}) or {}
        camera = cameras.get(camera_id, {}) if camera_id is not None else {}
        pessoa = self.selecionar_colaborador(snapshot, camera_id)

        pessoas_detectadas = 0
        if camera_id is not None:
            pessoas_detectadas = sum(
                1
                for item in (snapshot.get("pessoas", {}) or {}).values()
                if self._pessoa_elegivel(item, camera_id)
            )

        epis_obrigatorios = tuple(
            snapshot.get("ambiente", {}).get("epis_obrigatorios", ()) or ()
        )

        if pessoa is None:
            epis = tuple(
                EPIViewModel(epi=str(epi), estado="SEM_PESSOA")
                for epi in epis_obrigatorios
            )
            return ViewModelColaborador(
                camera_id=camera_id,
                camera_nome=str(camera.get("nome") or (f"Camera {camera_id}" if camera_id is not None else "--")),
                camera_online=bool(camera_id is not None and self._camera_online(camera)),
                track_id=None,
                track_instance_id=None,
                pessoas_detectadas=pessoas_detectadas,
                status_identidade=IDENTIDADE_NAO_AVALIADO,
                texto_identidade="NENHUM COLABORADOR DETECTADO" if camera_id is not None else "CAMERA INDISPONIVEL",
                nome="--",
                matricula="--",
                cargo="--",
                epis=epis,
                alertas=(),
            )

        identidade = pessoa.get("identidade", {}) or {}
        status_identidade, texto_identidade, nome, matricula, cargo = _apresentar_identidade(identidade)
        track_instance_id = str(pessoa.get("track_instance_id"))

        temporais = snapshot.get("estados_epi_temporais", {}) or {}
        epis = []
        for epi in epis_obrigatorios:
            estado_item = _buscar_estado_temporal(temporais, int(camera_id), track_instance_id, str(epi))
            if estado_item is None:
                estado = ESTADO_INDETERMINADO
                status_temporal = "SEM_ESTADO_CONFIRMADO"
            else:
                estado = str(estado_item.get("estado_confirmado") or ESTADO_INDETERMINADO)
                if estado not in {ESTADO_CORRETO, ESTADO_INCORRETO, ESTADO_AUSENTE, ESTADO_INDETERMINADO}:
                    estado = ESTADO_INDETERMINADO
                status_temporal = str(estado_item.get("status_temporal") or "")
            epis.append(EPIViewModel(epi=str(epi), estado=estado, status_temporal=status_temporal))

        alertas = _obter_alertas(snapshot, int(camera_id), track_instance_id)

        return ViewModelColaborador(
            camera_id=int(camera_id),
            camera_nome=str(camera.get("nome") or f"Camera {camera_id}"),
            camera_online=self._camera_online(camera),
            track_id=int(pessoa.get("track_id")) if pessoa.get("track_id") is not None else None,
            track_instance_id=track_instance_id,
            pessoas_detectadas=pessoas_detectadas,
            status_identidade=status_identidade,
            texto_identidade=texto_identidade,
            nome=nome,
            matricula=matricula,
            cargo=cargo,
            epis=tuple(epis),
            alertas=alertas,
        )


def _apresentar_identidade(identidade: Dict[str, Any]):
    status = str(identidade.get("status_identidade") or IDENTIDADE_NAO_AVALIADO)
    processamento = str(identidade.get("status_processamento") or "OCIOSO")

    if status == IDENTIDADE_IDENTIFICADO:
        nome = str(identidade.get("nome") or "DESCONHECIDO")
        matricula = str(identidade.get("matricula") or "--")
        cargo = str(identidade.get("cargo") or "--")
        return status, nome, nome, matricula, cargo

    if status == IDENTIDADE_DESCONHECIDO:
        return status, "DESCONHECIDO", "DESCONHECIDO", "--", "--"

    if processamento in {PROCESSAMENTO_EM_FILA, PROCESSAMENTO_IDENTIFICANDO} or status in {
        IDENTIDADE_NAO_AVALIADO,
        IDENTIDADE_AGUARDANDO_ROSTO,
    }:
        return status, "IDENTIFICACAO EM ANDAMENTO", "--", "--", "--"

    if status == IDENTIDADE_INDETERMINADO:
        return status, "IDENTIDADE INDETERMINADA", "--", "--", "--"

    return status, "IDENTIFICACAO EM ANDAMENTO", "--", "--", "--"


def _buscar_estado_temporal(
    estados: Dict[Any, Dict[str, Any]],
    camera_id: int,
    track_instance_id: str,
    epi: str,
) -> Optional[Dict[str, Any]]:
    chave = (camera_id, track_instance_id, epi)
    item = estados.get(chave)
    if item is not None:
        return item
    for candidato in estados.values():
        if (
            int(candidato.get("camera_id", -1)) == camera_id
            and str(candidato.get("track_instance_id")) == track_instance_id
            and str(candidato.get("epi")) == epi
        ):
            return candidato
    return None


def _obter_alertas(
    snapshot: Dict[str, Any],
    camera_id: int,
    track_instance_id: str,
) -> Tuple[AlertaViewModel, ...]:
    incidentes = snapshot.get("incidentes", {}) or {}
    notificacoes = snapshot.get("notificacoes_incidentes", {}) or {}
    alertas = []

    for incidente_id, incidente in incidentes.items():
        if int(incidente.get("camera_id", -1)) != camera_id:
            continue
        if str(incidente.get("track_instance_id")) != track_instance_id:
            continue

        notificacao = notificacoes.get(incidente_id)
        if not notificacao or not bool(notificacao.get("alerta_visual_ativo")):
            continue
        if bool(notificacao.get("encerrada")):
            continue

        alertas.append(
            AlertaViewModel(
                incidente_id=str(incidente_id),
                epi=str(incidente.get("epi") or "EPI"),
                tipo_irregularidade=str(incidente.get("tipo_irregularidade") or ""),
                severidade=str(notificacao.get("severidade") or "ALTA"),
                suspenso=bool(notificacao.get("suspensa")),
            )
        )

    alertas.sort(key=lambda item: (item.suspenso, item.epi, item.incidente_id))
    return tuple(alertas)


def _texto_epi(estado: str) -> str:
    return {
        ESTADO_CORRETO: "CORRETO",
        ESTADO_INCORRETO: "USO INCORRETO",
        ESTADO_AUSENTE: "AUSENTE",
        ESTADO_INDETERMINADO: "INDETERMINADO",
        "SEM_PESSOA": "--",
    }.get(estado, "INDETERMINADO")


def _cor_epi(estado: str):
    return {
        ESTADO_CORRETO: (0, 200, 0),
        ESTADO_INCORRETO: (0, 165, 255),
        ESTADO_AUSENTE: (0, 0, 255),
        ESTADO_INDETERMINADO: (150, 150, 150),
        "SEM_PESSOA": (100, 100, 100),
    }.get(estado, (150, 150, 150))


def desenhar_painel_colaborador(altura: int, view: ViewModelColaborador, largura: int = 390) -> np.ndarray:
    painel = np.zeros((max(altura, 1), largura, 3), dtype=np.uint8)
    painel[:] = (28, 28, 28)

    def texto(msg, x, y, escala=0.38, cor=(255, 255, 255), espessura=1):
        cv2.putText(painel, str(msg), (x, y), cv2.FONT_HERSHEY_SIMPLEX, escala, cor, espessura, cv2.LINE_AA)

    texto("VISAO DO COLABORADOR", 16, 28, 0.52, (255, 255, 255), 2)
    cv2.line(painel, (16, 40), (largura - 16, 40), (80, 80, 80), 1)

    texto("CAMERA ATUAL", 16, 62, 0.32, (160, 160, 160))
    cor_camera = (0, 200, 0) if view.camera_online else (0, 0, 255)
    texto(view.camera_nome if view.camera_id is not None else "INDISPONIVEL", 16, 83, 0.42, cor_camera, 2)

    texto("IDENTIFICACAO", 16, 108, 0.32, (160, 160, 160))
    texto(view.texto_identidade[:43], 16, 130, 0.39, (255, 255, 255), 1)
    y = 151
    if view.status_identidade == IDENTIDADE_IDENTIFICADO:
        texto(f"Matricula: {view.matricula}"[:43], 16, y, 0.32, (210, 210, 210)); y += 18
        texto(f"Cargo: {view.cargo}"[:43], 16, y, 0.32, (210, 210, 210)); y += 20
    else:
        y += 8

    cv2.line(painel, (16, y), (largura - 16, y), (80, 80, 80), 1)
    y += 24
    texto("EPIs OBRIGATORIOS", 16, y, 0.32, (160, 160, 160)); y += 24

    for item in view.epis:
        if y > altura - 95:
            break
        cor = _cor_epi(item.estado)
        texto(item.epi[:22], 16, y, 0.35, cor, 2)
        status = _texto_epi(item.estado)
        tamanho, _ = cv2.getTextSize(status, cv2.FONT_HERSHEY_SIMPLEX, 0.30, 1)
        texto(status, largura - tamanho[0] - 16, y, 0.30, cor, 1)
        y += 22

    y += 4
    if y < altura - 55:
        cv2.line(painel, (16, y), (largura - 16, y), (80, 80, 80), 1)
        y += 22
        texto("ALERTAS", 16, y, 0.32, (160, 160, 160)); y += 22

        if not view.alertas:
            texto("Nenhum alerta ativo", 16, y, 0.34, (130, 130, 130))
        else:
            for alerta in view.alertas:
                if y > altura - 10:
                    break
                if alerta.suspenso:
                    msg = f"{alerta.epi}: OBSERVACAO SUSPENSA"
                    cor = (0, 165, 255)
                elif alerta.tipo_irregularidade == "AUSENCIA_EPI":
                    msg = f"{alerta.epi}: AUSENTE"
                    cor = (0, 0, 255)
                else:
                    msg = f"{alerta.epi}: USO INCORRETO"
                    cor = (0, 165, 255)
                texto(msg[:45], 16, y, 0.31, cor, 1)
                y += 20

    return painel
