from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Tuple
import math

import cv2
import numpy as np

from visao_colaborador import _apresentar_identidade

MODO_MOSAICO = "MOSAICO"
MODO_CAMERA_AMPLIADA = "CAMERA_AMPLIADA"

CAMERA_ONLINE = "ONLINE"
CAMERA_OFFLINE = "OFFLINE"
CAMERA_RECONECTANDO = "RECONECTANDO"

ESTADO_CORRETO = "CORRETO"
ESTADO_INCORRETO = "INCORRETO"
ESTADO_AUSENTE = "AUSENTE"
ESTADO_INDETERMINADO = "INDETERMINADO"


@dataclass(frozen=True)
class EPIViewModelGerente:
    epi: str
    estado: str
    status_temporal: str = ""


@dataclass(frozen=True)
class IncidenteViewModelGerente:
    incidente_id: str
    epi: str
    tipo_irregularidade: str
    estado_incidente: str
    severidade: str
    alerta_visual_ativo: bool
    suspenso: bool


@dataclass(frozen=True)
class PessoaViewModelGerente:
    camera_id: int
    track_id: Optional[int]
    track_instance_id: str
    status_identidade: str
    texto_identidade: str
    nome: str
    matricula: str
    cargo: str
    epis: Tuple[EPIViewModelGerente, ...] = field(default_factory=tuple)
    incidentes: Tuple[IncidenteViewModelGerente, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CameraViewModelGerente:
    camera_id: int
    nome: str
    status: str
    ativa: bool
    pessoas: Tuple[PessoaViewModelGerente, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MetricasViewModelGerente:
    fps_global: Optional[float]
    fps_por_camera: Dict[int, Optional[float]]
    latencia_ppe_ms: Optional[float]
    latencia_pose_ms: Optional[float]
    latencia_biometria_ms: Optional[float]
    latencia_pipeline_ms: Optional[float]


@dataclass(frozen=True)
class ViewModelGerente:
    ambiente_id: Optional[str]
    ambiente_nome: str
    epis_obrigatorios: Tuple[str, ...]
    modo_visual: str
    camera_selecionada_id: Optional[int]
    cameras: Tuple[CameraViewModelGerente, ...]
    metricas: MetricasViewModelGerente


@dataclass(frozen=True)
class HitboxCamera:
    camera_id: int
    x1: int
    y1: int
    x2: int
    y2: int

    def contem(self, x: int, y: int) -> bool:
        return self.x1 <= x < self.x2 and self.y1 <= y < self.y2


@dataclass(frozen=True)
class HitboxBotao:
    x1: int
    y1: int
    x2: int
    y2: int

    def contem(self, x: int, y: int) -> bool:
        return self.x1 <= x < self.x2 and self.y1 <= y < self.y2


class ControladorVisaoGerente:
    """Estado local de navegação. Nunca altera EstadoSistema ou snapshot."""

    def __init__(self):
        self.modo_visual = MODO_MOSAICO
        self.camera_selecionada_id: Optional[int] = None
        self.hitboxes_cameras: Tuple[HitboxCamera, ...] = ()
        self.hitbox_ver_todas: Optional[HitboxBotao] = None
        self._ambiente_id_atual: Optional[str] = None

    def sincronizar_ambiente(self, snapshot: Dict[str, Any]) -> Tuple[int, ...]:
        ambiente = snapshot.get("ambiente", {}) or {}
        ambiente_id = ambiente.get("ambiente_id")
        camera_ids = tuple(int(v) for v in (ambiente.get("camera_ids", ()) or ()))

        if self._ambiente_id_atual != ambiente_id:
            self._ambiente_id_atual = ambiente_id
            if self.camera_selecionada_id not in camera_ids:
                self.modo_visual = MODO_MOSAICO
                self.camera_selecionada_id = None
            self.hitboxes_cameras = ()
            self.hitbox_ver_todas = None

        if self.camera_selecionada_id is not None and self.camera_selecionada_id not in camera_ids:
            self.modo_visual = MODO_MOSAICO
            self.camera_selecionada_id = None
            self.hitboxes_cameras = ()
            self.hitbox_ver_todas = None

        return camera_ids

    def construir_viewmodel(self, snapshot: Dict[str, Any]) -> ViewModelGerente:
        camera_ids = self.sincronizar_ambiente(snapshot)
        ambiente = snapshot.get("ambiente", {}) or {}
        cameras_snapshot = snapshot.get("cameras", {}) or {}
        epis_obrigatorios = tuple(str(v) for v in (ambiente.get("epis_obrigatorios", ()) or ()))

        cameras = []
        for camera_id in camera_ids:
            cam = cameras_snapshot.get(camera_id, {}) or {}
            pessoas = _construir_pessoas_camera(snapshot, camera_id, epis_obrigatorios)
            cameras.append(CameraViewModelGerente(
                camera_id=camera_id,
                nome=str(cam.get("nome") or f"Camera {camera_id}"),
                status=str(cam.get("status") or CAMERA_OFFLINE),
                ativa=bool(cam.get("ativa", True)),
                pessoas=pessoas,
            ))

        metricas_snapshot = snapshot.get("metricas_runtime", {}) or snapshot.get("metricas", {}) or {}
        fps_por_camera = {
            int(camera_id): (None if valor is None else float(valor))
            for camera_id, valor in (metricas_snapshot.get("fps_por_camera", {}) or {}).items()
        }
        metricas = MetricasViewModelGerente(
            fps_global=_float_ou_none(metricas_snapshot.get("fps_global")),
            fps_por_camera=fps_por_camera,
            latencia_ppe_ms=_float_ou_none(metricas_snapshot.get("latencia_ppe_ms")),
            latencia_pose_ms=_float_ou_none(metricas_snapshot.get("latencia_pose_ms")),
            latencia_biometria_ms=_float_ou_none(metricas_snapshot.get("latencia_biometria_ms")),
            latencia_pipeline_ms=_float_ou_none(metricas_snapshot.get("latencia_pipeline_ms")),
        )

        return ViewModelGerente(
            ambiente_id=None if ambiente.get("ambiente_id") is None else str(ambiente.get("ambiente_id")),
            ambiente_nome=str(ambiente.get("nome") or "--"),
            epis_obrigatorios=epis_obrigatorios,
            modo_visual=self.modo_visual,
            camera_selecionada_id=self.camera_selecionada_id,
            cameras=tuple(cameras),
            metricas=metricas,
        )

    def clicar(self, x: int, y: int) -> None:
        if self.modo_visual == MODO_CAMERA_AMPLIADA:
            if self.hitbox_ver_todas is not None and self.hitbox_ver_todas.contem(x, y):
                self.modo_visual = MODO_MOSAICO
                self.camera_selecionada_id = None
                self.hitboxes_cameras = ()
                self.hitbox_ver_todas = None
            return

        for hitbox in self.hitboxes_cameras:
            if hitbox.contem(x, y):
                self.modo_visual = MODO_CAMERA_AMPLIADA
                self.camera_selecionada_id = hitbox.camera_id
                self.hitboxes_cameras = ()
                self.hitbox_ver_todas = None
                return

    def voltar_todas(self) -> None:
        self.modo_visual = MODO_MOSAICO
        self.camera_selecionada_id = None
        self.hitboxes_cameras = ()
        self.hitbox_ver_todas = None


def _float_ou_none(valor):
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _formatar_metrica(valor: Optional[float], sufixo: str, casas: int = 1) -> str:
    if valor is None:
        return "--"
    return f"{float(valor):.{casas}f} {sufixo}".strip()


def _pessoa_elegivel(pessoa: Dict[str, Any], camera_id: int) -> bool:
    return (
        int(pessoa.get("camera_id", -1)) == int(camera_id)
        and bool(pessoa.get("ativo"))
        and bool(pessoa.get("detectado_no_frame"))
        and bool(pessoa.get("track_instance_id"))
    )


def _buscar_estado_temporal(estados: Dict[Any, Dict[str, Any]], camera_id: int, track_instance_id: str, epi: str):
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


def _construir_pessoas_camera(snapshot: Dict[str, Any], camera_id: int, epis_obrigatorios: Tuple[str, ...]):
    pessoas_snapshot = snapshot.get("pessoas", {}) or {}
    temporais = snapshot.get("estados_epi_temporais", {}) or {}
    incidentes = snapshot.get("incidentes", {}) or {}
    notificacoes = snapshot.get("notificacoes_incidentes", {}) or {}

    pessoas = []
    for pessoa in pessoas_snapshot.values():
        if not _pessoa_elegivel(pessoa, camera_id):
            continue

        track_instance_id = str(pessoa.get("track_instance_id"))
        identidade = pessoa.get("identidade", {}) or {}
        status_identidade, texto_identidade, nome, matricula, cargo = _apresentar_identidade(identidade)

        epis = []
        for epi in epis_obrigatorios:
            item = _buscar_estado_temporal(temporais, camera_id, track_instance_id, epi)
            if item is None:
                estado = ESTADO_INDETERMINADO
                status_temporal = "SEM_ESTADO_CONFIRMADO"
            else:
                estado = str(item.get("estado_confirmado") or ESTADO_INDETERMINADO)
                if estado not in {ESTADO_CORRETO, ESTADO_INCORRETO, ESTADO_AUSENTE, ESTADO_INDETERMINADO}:
                    estado = ESTADO_INDETERMINADO
                status_temporal = str(item.get("status_temporal") or "")
            epis.append(EPIViewModelGerente(epi=epi, estado=estado, status_temporal=status_temporal))

        incs = []
        for incidente_id, incidente in incidentes.items():
            if int(incidente.get("camera_id", -1)) != camera_id:
                continue
            if str(incidente.get("track_instance_id")) != track_instance_id:
                continue
            notif = notificacoes.get(incidente_id, {}) or {}
            incs.append(IncidenteViewModelGerente(
                incidente_id=str(incidente_id),
                epi=str(incidente.get("epi") or "EPI"),
                tipo_irregularidade=str(incidente.get("tipo_irregularidade") or ""),
                estado_incidente=str(incidente.get("estado_incidente") or ""),
                severidade=str(notif.get("severidade") or "ALTA"),
                alerta_visual_ativo=bool(notif.get("alerta_visual_ativo")) and not bool(notif.get("encerrada")),
                suspenso=bool(notif.get("suspensa")),
            ))
        incs.sort(key=lambda i: (not i.alerta_visual_ativo, i.suspenso, i.epi, i.incidente_id))

        pessoas.append(PessoaViewModelGerente(
            camera_id=camera_id,
            track_id=int(pessoa.get("track_id")) if pessoa.get("track_id") is not None else None,
            track_instance_id=track_instance_id,
            status_identidade=status_identidade,
            texto_identidade=texto_identidade,
            nome=nome,
            matricula=matricula,
            cargo=cargo,
            epis=tuple(epis),
            incidentes=tuple(incs),
        ))

    pessoas.sort(key=lambda p: ((p.track_id if p.track_id is not None else 10**9), p.track_instance_id))
    return tuple(pessoas)


def _frame_por_camera(frames: Iterable[Tuple[Any, np.ndarray]]) -> Dict[int, np.ndarray]:
    saida = {}
    for camera, frame in frames or ():
        try:
            saida[int(camera.camera_id)] = frame
        except Exception:
            continue
    return saida


def _cor_status_camera(status: str):
    if status == CAMERA_ONLINE:
        return (0, 200, 0)
    if status == CAMERA_RECONECTANDO:
        return (0, 165, 255)
    return (0, 0, 255)


def _cor_epi(estado: str):
    return {
        ESTADO_CORRETO: (0, 200, 0),
        ESTADO_INCORRETO: (0, 165, 255),
        ESTADO_AUSENTE: (0, 0, 255),
        ESTADO_INDETERMINADO: (150, 150, 150),
    }.get(estado, (150, 150, 150))


def _texto_epi(estado: str):
    return {
        ESTADO_CORRETO: "CORRETO",
        ESTADO_INCORRETO: "INCORRETO",
        ESTADO_AUSENTE: "AUSENTE",
        ESTADO_INDETERMINADO: "INDETERMINADO",
    }.get(estado, "INDETERMINADO")


def _celula_camera(camera: CameraViewModelGerente, frame: Optional[np.ndarray], largura: int, altura: int, fps: Optional[float] = None) -> np.ndarray:
    if frame is not None and camera.status == CAMERA_ONLINE:
        img = cv2.resize(frame, (largura, altura))
    else:
        img = np.zeros((altura, largura, 3), dtype=np.uint8)
        img[:] = (22, 22, 22)
        msg = "RECONECTANDO..." if camera.status == CAMERA_RECONECTANDO else "CAMERA INDISPONIVEL"
        cv2.putText(img, msg, (20, altura // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.55, _cor_status_camera(camera.status), 2, cv2.LINE_AA)

    cv2.rectangle(img, (0, 0), (largura, 48), (25, 25, 25), -1)
    cv2.putText(img, camera.nome[:26], (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(img, camera.status, (12, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.35, _cor_status_camera(camera.status), 1, cv2.LINE_AA)
    fps_txt = _formatar_metrica(fps, "FPS") if camera.status == CAMERA_ONLINE else "--"
    cv2.putText(img, fps_txt, (105, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (190, 190, 190), 1, cv2.LINE_AA)
    cv2.putText(img, f"Pessoas: {len(camera.pessoas)}", (largura - 115, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (210, 210, 210), 1, cv2.LINE_AA)
    alertas = sum(1 for p in camera.pessoas for i in p.incidentes if i.alerta_visual_ativo)
    if alertas:
        cv2.putText(img, f"Alertas: {alertas}", (largura - 115, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (0, 0, 255), 1, cv2.LINE_AA)
    return img


def renderizar_mosaico_gerente(controlador: ControladorVisaoGerente, view: ViewModelGerente, frames, largura_total: int = 1200) -> np.ndarray:
    cameras = view.cameras
    altura_cabecalho = 38
    qtd = max(1, len(cameras))
    if qtd == 1:
        colunas = 1
    elif qtd <= 4:
        colunas = 2
    else:
        colunas = 3
    linhas = max(1, math.ceil(qtd / colunas))
    largura = max(300, largura_total // colunas)
    altura = int(largura * 0.66)
    frames_map = _frame_por_camera(frames)

    celulas = []
    hitboxes = []
    for idx in range(linhas * colunas):
        linha = idx // colunas
        coluna = idx % colunas
        if idx < len(cameras):
            camera = cameras[idx]
            celula = _celula_camera(
                camera,
                frames_map.get(camera.camera_id),
                largura,
                altura,
                fps=view.metricas.fps_por_camera.get(camera.camera_id),
            )
            hitboxes.append(HitboxCamera(
                camera_id=camera.camera_id,
                x1=coluna * largura,
                y1=altura_cabecalho + linha * altura,
                x2=(coluna + 1) * largura,
                y2=altura_cabecalho + (linha + 1) * altura,
            ))
        else:
            celula = np.zeros((altura, largura, 3), dtype=np.uint8)
        celulas.append(celula)

    linhas_img = []
    for linha in range(linhas):
        ini = linha * colunas
        linhas_img.append(np.hstack(celulas[ini:ini + colunas]))
    mosaico = np.vstack(linhas_img)
    cabecalho = np.zeros((altura_cabecalho, mosaico.shape[1], 3), dtype=np.uint8)
    cabecalho[:] = (28, 28, 28)
    cv2.putText(cabecalho, f"AMBIENTE: {view.ambiente_nome}"[:80], (14, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
    mosaico = np.vstack((cabecalho, mosaico))

    # Substitui integralmente as hitboxes anteriores pelo layout deste frame.
    controlador.hitboxes_cameras = tuple(hitboxes)
    controlador.hitbox_ver_todas = None
    return mosaico


def _painel_pessoas(camera: CameraViewModelGerente, altura: int, ambiente_nome: str, largura: int = 420, metricas: Optional[MetricasViewModelGerente] = None) -> np.ndarray:
    painel = np.zeros((altura, largura, 3), dtype=np.uint8)
    painel[:] = (28, 28, 28)

    def texto(msg, x, y, escala=0.34, cor=(240, 240, 240), esp=1):
        cv2.putText(painel, str(msg), (x, y), cv2.FONT_HERSHEY_SIMPLEX, escala, cor, esp, cv2.LINE_AA)

    texto("VISAO DO GERENTE", 14, 26, 0.48, (255, 255, 255), 2)
    texto(f"Ambiente: {ambiente_nome}"[:45], 14, 48, 0.32, (180, 180, 180), 1)
    texto(f"{camera.nome} - {camera.status}"[:45], 14, 70, 0.38, _cor_status_camera(camera.status), 1)
    texto(f"Colaboradores monitorados: {len(camera.pessoas)}", 14, 92, 0.33, (180, 180, 180))
    if metricas is not None:
        texto(
            f"FPS global: {_formatar_metrica(metricas.fps_global, 'FPS')}",
            14, 112, 0.29, (170, 170, 170)
        )
        texto(
            f"PPE {_formatar_metrica(metricas.latencia_ppe_ms, 'ms')} | Pose {_formatar_metrica(metricas.latencia_pose_ms, 'ms')}",
            14, 130, 0.27, (170, 170, 170)
        )
        texto(
            f"Biom {_formatar_metrica(metricas.latencia_biometria_ms, 'ms')} | Pipeline {_formatar_metrica(metricas.latencia_pipeline_ms, 'ms')}",
            14, 148, 0.27, (170, 170, 170)
        )
        cv2.line(painel, (14, 160), (largura - 14, 160), (80, 80, 80), 1)
        y = 184
    else:
        cv2.line(painel, (14, 104), (largura - 14, 104), (80, 80, 80), 1)
        y = 128

    if not camera.pessoas:
        texto("NENHUM COLABORADOR DETECTADO", 14, y, 0.36, (150, 150, 150))
        return painel

    max_pessoas = 4
    for pessoa in camera.pessoas[:max_pessoas]:
        if y > altura - 80:
            break
        texto(f"Track {pessoa.track_id if pessoa.track_id is not None else '--'}", 14, y, 0.35, (200, 200, 200), 2); y += 19
        texto(pessoa.texto_identidade[:45], 14, y, 0.34, (255, 255, 255), 1); y += 19
        for epi in pessoa.epis:
            if y > altura - 55:
                break
            cor = _cor_epi(epi.estado)
            texto(epi.epi[:20], 24, y, 0.29, cor, 1)
            status = _texto_epi(epi.estado)
            texto(status, 205, y, 0.27, cor, 1)
            y += 16
        ativos = [i for i in pessoa.incidentes if i.alerta_visual_ativo]
        if pessoa.incidentes and y <= altura - 55:
            texto(f"Incidentes: {len(pessoa.incidentes)} | Alertas ativos: {len(ativos)}", 24, y, 0.26, (170, 170, 170), 1)
            y += 16
        for inc in ativos[:2]:
            if y > altura - 55:
                break
            msg = f"ALERTA {inc.severidade}: {inc.epi}"
            if inc.suspenso:
                msg += " (SUSPENSO)"
            texto(msg[:50], 24, y, 0.27, (0, 165, 255) if inc.suspenso else (0, 0, 255), 1)
            y += 17
        y += 8
        cv2.line(painel, (14, y), (largura - 14, y), (60, 60, 60), 1)
        y += 14

    if len(camera.pessoas) > max_pessoas and y < altura - 20:
        texto(f"+ {len(camera.pessoas) - max_pessoas} colaboradores", 14, y, 0.31, (160, 160, 160))
    return painel


def renderizar_camera_ampliada(controlador: ControladorVisaoGerente, view: ViewModelGerente, frames, largura_frame: int = 900, altura_frame: int = 650) -> np.ndarray:
    camera = next((c for c in view.cameras if c.camera_id == view.camera_selecionada_id), None)
    if camera is None:
        controlador.voltar_todas()
        return renderizar_mosaico_gerente(controlador, controlador.construir_viewmodel({
            "ambiente": {"ambiente_id": view.ambiente_id, "nome": view.ambiente_nome, "camera_ids": (), "epis_obrigatorios": view.epis_obrigatorios},
            "cameras": {}, "pessoas": {}, "estados_epi_temporais": {}, "incidentes": {}, "notificacoes_incidentes": {}
        }), frames, largura_total=largura_frame)

    frames_map = _frame_por_camera(frames)
    frame = frames_map.get(camera.camera_id)
    imagem = _celula_camera(
        camera,
        frame,
        largura_frame,
        altura_frame,
        fps=view.metricas.fps_por_camera.get(camera.camera_id),
    )
    painel = _painel_pessoas(camera, altura_frame, view.ambiente_nome, metricas=view.metricas)
    tela = np.hstack((imagem, painel))

    botao_largura = 155
    botao_altura = 38
    x2 = tela.shape[1] - 18
    x1 = x2 - botao_largura
    y1 = 12
    y2 = y1 + botao_altura
    cv2.rectangle(tela, (x1, y1), (x2, y2), (70, 70, 70), -1)
    cv2.rectangle(tela, (x1, y1), (x2, y2), (180, 180, 180), 1)
    cv2.putText(tela, "VER TODAS", (x1 + 22, y1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    controlador.hitboxes_cameras = ()
    controlador.hitbox_ver_todas = HitboxBotao(x1=x1, y1=y1, x2=x2, y2=y2)
    return tela


def renderizar_visao_gerente(controlador: ControladorVisaoGerente, snapshot: Dict[str, Any], frames) -> np.ndarray:
    view = controlador.construir_viewmodel(snapshot)
    if view.modo_visual == MODO_CAMERA_AMPLIADA and view.camera_selecionada_id is not None:
        return renderizar_camera_ampliada(controlador, view, frames)
    return renderizar_mosaico_gerente(controlador, view, frames)
