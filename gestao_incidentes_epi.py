from __future__ import annotations

import csv
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import cv2


TIPO_AUSENCIA_EPI = "AUSENCIA_EPI"
TIPO_USO_INCORRETO_EPI = "USO_INCORRETO_EPI"

ESTADO_ATIVO = "ATIVO"
ESTADO_OBSERVACAO_SUSPENSA = "OBSERVACAO_SUSPENSA"
ESTADO_ENCERRADO = "ENCERRADO"

MOTIVO_CORRIGIDO = "CORRIGIDO"
MOTIVO_MUDANCA_TIPO = "MUDANCA_TIPO_IRREGULARIDADE"
MOTIVO_TRACK_ENCERRADO = "TRACK_ENCERRADO"
MOTIVO_CAMERA_ENCERRADA = "CAMERA_ENCERRADA"
MOTIVO_TROCA_AMBIENTE = "TROCA_AMBIENTE"

ESTADO_EPI_CORRETO = "CORRETO"
ESTADO_EPI_INCORRETO = "INCORRETO"
ESTADO_EPI_AUSENTE = "AUSENTE"

STATUS_SEM_OBSERVACAO = {
    "SEM_OBSERVACAO_AGUARDANDO_EXPIRACAO",
    "EXPIRADO_SEM_OBSERVACAO",
}
STATUS_EXPIRACAO_OBSERVABILIDADE = {
    "EXPIRADO_SEM_OBSERVACAO",
    "CONFIRMADO_EXPIRADO_POR_INDETERMINADO",
}


class GestorIncidentesEPI:
    """Orquestra incidentes individuais sem manter estado autoritativo próprio.

    EstadoSistema é a única fonte de verdade operacional. CSV e imagens são
    efeitos de auditoria: qualquer falha é capturada e nunca desfaz o estado
    já criado/atualizado em memória.
    """

    CAMPOS_CSV = (
        "schema_version", "registro_id", "incidente_id", "tipo_registro",
        "timestamp", "ambiente_id", "ambiente_nome", "camera_id", "camera_nome",
        "track_id", "track_instance_id", "epi", "tipo_irregularidade",
        "estado_incidente", "motivo_encerramento", "matricula", "nome", "cargo",
        "status_identidade", "evidencia_id", "caminho_frame", "caminho_crop",
        "detalhe",
    )

    def __init__(
        self,
        estado_sistema,
        caminho_csv: str,
        pasta_evidencias: str,
        intervalo_evidencia_segundos: float = 300.0,
        qualidade_jpeg: int = 90,
        salvar_frame_completo: bool = True,
        salvar_crop_pessoa: bool = True,
        monotonic_fn: Callable[[], float] = time.monotonic,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        imwrite_fn: Callable[..., bool] = cv2.imwrite,
        append_csv_fn: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.estado_sistema = estado_sistema
        self.caminho_csv = str(caminho_csv)
        self.pasta_evidencias = str(pasta_evidencias)
        self.intervalo_evidencia_segundos = max(0.0, float(intervalo_evidencia_segundos))
        self.qualidade_jpeg = max(1, min(100, int(qualidade_jpeg)))
        self.salvar_frame_completo = bool(salvar_frame_completo)
        self.salvar_crop_pessoa = bool(salvar_crop_pessoa)
        self.monotonic_fn = monotonic_fn
        self.now_fn = now_fn
        self.imwrite_fn = imwrite_fn
        self.append_csv_fn = append_csv_fn or self._append_csv_padrao

    @staticmethod
    def _tipo_para_estado(estado_confirmado: str) -> Optional[str]:
        if estado_confirmado == ESTADO_EPI_AUSENTE:
            return TIPO_AUSENCIA_EPI
        if estado_confirmado == ESTADO_EPI_INCORRETO:
            return TIPO_USO_INCORRETO_EPI
        return None

    @staticmethod
    def _observacao_atual(item) -> bool:
        return str(getattr(item, "status_temporal", "")) not in STATUS_SEM_OBSERVACAO

    @staticmethod
    def _crop_pessoa(frame, bbox):
        if frame is None or bbox is None or len(bbox) != 4:
            return None
        altura, largura = frame.shape[:2]
        x1, y1, x2, y2 = [int(round(float(v))) for v in bbox]
        x1 = max(0, min(largura, x1)); x2 = max(0, min(largura, x2))
        y1 = max(0, min(altura, y1)); y2 = max(0, min(altura, y2))
        if x2 <= x1 or y2 <= y1:
            return None
        crop = frame[y1:y2, x1:x2]
        return None if crop.size == 0 else crop.copy()

    def processar_camera(self, camera_id: int, frame, camera_nome: Optional[str] = None) -> None:
        contexto = self.estado_sistema.obter_contexto_incidentes_camera(int(camera_id))
        ambiente = contexto["ambiente"]
        pessoas = contexto["pessoas"]
        agora_mono = float(self.monotonic_fn())
        agora_dt = self.now_fn()

        for item in contexto["estados_temporais"]:
            track_instance_id = str(item.track_instance_id)
            epi = str(item.epi)
            confirmado = item.estado_confirmado
            status_temporal = str(item.status_temporal)
            pessoa = pessoas.get(track_instance_id)

            if confirmado in {ESTADO_EPI_AUSENTE, ESTADO_EPI_INCORRETO}:
                # Durante incerteza transitória a ETAPA 8 preserva o confirmado.
                # O incidente continua ATIVO e não flapa para SUSPENSO.
                if not self._observacao_atual(item):
                    continue
                tipo = self._tipo_para_estado(confirmado)
                identidade = (pessoa or {}).get("identidade") or {}
                resultado = self.estado_sistema.garantir_incidente_epi_atomico(
                    ambiente_id=ambiente.get("ambiente_id"),
                    ambiente_nome=ambiente.get("nome"),
                    camera_id=int(camera_id),
                    camera_nome=camera_nome or contexto.get("camera_nome") or f"Camera {camera_id}",
                    track_id=int(item.track_id),
                    track_instance_id=track_instance_id,
                    epi=epi,
                    tipo_irregularidade=tipo,
                    identidade=identidade,
                    agora_monotonico=agora_mono,
                    agora_datetime=agora_dt,
                )
                anterior = resultado.get("encerrado_anterior")
                if anterior is not None:
                    self._persistir_evento("ENCERRAMENTO", anterior)
                incidente = resultado["incidente"]
                if resultado.get("criado"):
                    self._persistir_evento("ABERTURA", incidente)
                elif resultado.get("reativado"):
                    self._persistir_evento("OBSERVACAO_RETOMADA", incidente)

                # Se a identidade ficou disponível após a abertura, enriquece
                # somente o mesmo camera_id + track_instance_id.
                if identidade:
                    atualizado = self.estado_sistema.enriquecer_incidentes_identidade(
                        int(camera_id), track_instance_id, identidade, agora_dt
                    )
                    for inc in atualizado:
                        self._persistir_evento("IDENTIDADE_ATUALIZADA", inc)

                if self._deve_tentar_evidencia(incidente, agora_mono):
                    self._capturar_evidencia(
                        incidente=incidente,
                        frame=frame,
                        bbox=(pessoa or {}).get("bbox"),
                        agora_mono=agora_mono,
                        agora_dt=agora_dt,
                    )
                continue

            if confirmado == ESTADO_EPI_CORRETO and self._observacao_atual(item):
                encerrado = self.estado_sistema.encerrar_incidente_epi_base(
                    ambiente_id=ambiente.get("ambiente_id"), camera_id=int(camera_id),
                    track_instance_id=track_instance_id, epi=epi,
                    motivo=MOTIVO_CORRIGIDO, agora_monotonico=agora_mono,
                    agora_datetime=agora_dt,
                )
                if encerrado is not None:
                    self._persistir_evento("ENCERRAMENTO", encerrado)
                continue

            # INDETERMINADO transitório não muda o incidente. Suspensão só
            # ocorre quando a própria ETAPA 8 declara expiração efetiva.
            if confirmado is None and status_temporal in STATUS_EXPIRACAO_OBSERVABILIDADE:
                suspenso = self.estado_sistema.suspender_incidente_epi_base(
                    ambiente_id=ambiente.get("ambiente_id"), camera_id=int(camera_id),
                    track_instance_id=track_instance_id, epi=epi,
                    agora_monotonico=agora_mono, agora_datetime=agora_dt,
                    motivo=status_temporal,
                )
                if suspenso is not None:
                    self._persistir_evento("OBSERVACAO_SUSPENSA", suspenso)

    def processar_camera_sem_observacao(self, camera_id: int) -> None:
        contexto = self.estado_sistema.obter_contexto_incidentes_camera(int(camera_id))
        ambiente = contexto["ambiente"]
        agora_mono = float(self.monotonic_fn())
        agora_dt = self.now_fn()
        for item in contexto["estados_temporais"]:
            if str(item.status_temporal) != "EXPIRADO_SEM_OBSERVACAO":
                continue
            suspenso = self.estado_sistema.suspender_incidente_epi_base(
                ambiente_id=ambiente.get("ambiente_id"), camera_id=int(camera_id),
                track_instance_id=str(item.track_instance_id), epi=str(item.epi),
                agora_monotonico=agora_mono, agora_datetime=agora_dt,
                motivo="EXPIRADO_SEM_OBSERVACAO",
            )
            if suspenso is not None:
                self._persistir_evento("OBSERVACAO_SUSPENSA", suspenso)

    def _deve_tentar_evidencia(self, incidente, agora_mono: float) -> bool:
        ultima = incidente.ultima_tentativa_evidencia_monotonica
        if ultima is None:
            return True
        return (agora_mono - float(ultima)) >= self.intervalo_evidencia_segundos

    def _capturar_evidencia(self, incidente, frame, bbox, agora_mono: float, agora_dt: datetime) -> None:
        # Marca tentativa primeiro: falha de IO não causa retry a cada frame.
        self.estado_sistema.marcar_tentativa_evidencia_incidente(
            incidente.incidente_id, agora_mono, agora_dt
        )
        evidencia_id = str(uuid.uuid4())
        pasta = os.path.join(self.pasta_evidencias, incidente.incidente_id)
        caminhos_validos: Dict[str, Optional[str]] = {"frame": None, "crop": None}
        falhas = []
        try:
            os.makedirs(pasta, exist_ok=True)
        except Exception as erro:
            falhas.append(f"PASTA:{erro}")

        parametros = [int(cv2.IMWRITE_JPEG_QUALITY), self.qualidade_jpeg]
        if self.salvar_frame_completo:
            caminho = os.path.join(pasta, f"{evidencia_id}_frame.jpg")
            try:
                ok = bool(frame is not None and self.imwrite_fn(caminho, frame, parametros))
                if ok and os.path.exists(caminho):
                    caminhos_validos["frame"] = caminho
                else:
                    falhas.append("FRAME_NAO_SALVO")
            except Exception as erro:
                falhas.append(f"FRAME:{erro}")

        if self.salvar_crop_pessoa:
            caminho = os.path.join(pasta, f"{evidencia_id}_pessoa.jpg")
            crop = self._crop_pessoa(frame, bbox)
            if crop is None:
                falhas.append("CROP_INVALIDO")
            else:
                try:
                    ok = bool(self.imwrite_fn(caminho, crop, parametros))
                    if ok and os.path.exists(caminho):
                        caminhos_validos["crop"] = caminho
                    else:
                        falhas.append("CROP_NAO_SALVO")
                except Exception as erro:
                    falhas.append(f"CROP:{erro}")

        if caminhos_validos["frame"] or caminhos_validos["crop"]:
            evidencia = self.estado_sistema.registrar_evidencia_incidente(
                incidente.incidente_id,
                evidencia_id=evidencia_id,
                caminho_frame=caminhos_validos["frame"],
                caminho_crop=caminhos_validos["crop"],
                agora_monotonico=agora_mono,
                agora_datetime=agora_dt,
                falhas=tuple(falhas),
            )
            self._persistir_evento("EVIDENCIA", incidente, evidencia=evidencia)
        if falhas:
            atualizado = self.estado_sistema.registrar_falha_evidencia_incidente(
                incidente.incidente_id, ";".join(falhas), agora_dt
            )
            if atualizado is not None:
                self._persistir_evento("FALHA_EVIDENCIA", atualizado, detalhe=";".join(falhas))

    def _registro_evento(self, tipo: str, incidente, evidencia=None, detalhe: str = "") -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "registro_id": str(uuid.uuid4()),
            "incidente_id": incidente.incidente_id,
            "tipo_registro": tipo,
            "timestamp": self.now_fn().isoformat(),
            "ambiente_id": incidente.ambiente_id or "",
            "ambiente_nome": incidente.ambiente_nome or "",
            "camera_id": incidente.camera_id,
            "camera_nome": incidente.camera_nome or "",
            "track_id": incidente.track_id,
            "track_instance_id": incidente.track_instance_id,
            "epi": incidente.epi,
            "tipo_irregularidade": incidente.tipo_irregularidade,
            "estado_incidente": incidente.estado_incidente,
            "motivo_encerramento": incidente.motivo_encerramento or "",
            "matricula": incidente.matricula,
            "nome": incidente.nome,
            "cargo": incidente.cargo,
            "status_identidade": incidente.status_identidade,
            "evidencia_id": getattr(evidencia, "evidencia_id", "") if evidencia else "",
            "caminho_frame": getattr(evidencia, "caminho_frame", "") or "" if evidencia else "",
            "caminho_crop": getattr(evidencia, "caminho_crop", "") or "" if evidencia else "",
            "detalhe": detalhe,
        }

    def _persistir_evento(self, tipo: str, incidente, evidencia=None, detalhe: str = "") -> bool:
        try:
            self.append_csv_fn(self._registro_evento(tipo, incidente, evidencia, detalhe))
            return True
        except Exception as erro:
            # Falha de auditoria nunca altera a verdade operacional.
            self.estado_sistema.registrar_falha_persistencia_incidente(
                incidente.incidente_id, f"{tipo}:{erro}", self.now_fn()
            )
            return False

    def _append_csv_padrao(self, registro: Dict[str, Any]) -> None:
        pasta = os.path.dirname(os.path.abspath(self.caminho_csv))
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        novo = not os.path.exists(self.caminho_csv) or os.path.getsize(self.caminho_csv) == 0
        with open(self.caminho_csv, "a", newline="", encoding="utf-8") as arquivo:
            writer = csv.DictWriter(arquivo, fieldnames=self.CAMPOS_CSV)
            if novo:
                writer.writeheader()
            writer.writerow({campo: registro.get(campo, "") for campo in self.CAMPOS_CSV})
