import csv
import os
from datetime import datetime
from typing import Any, Dict, Optional

import config


def _caminho_incidentes() -> str:
    return str(
        getattr(
            config,
            "PATH_INCIDENTES_EPI_CSV",
            "incidentes_epi.csv",
        )
    )


def _timestamp_para_data_local(valor: str):
    texto = str(valor or "").strip()

    if not texto:
        return None

    try:
        # Compatibilidade com timestamps terminados em Z.
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"

        data = datetime.fromisoformat(texto)

        if data.tzinfo is not None:
            data = data.astimezone()

        return data.date()
    except Exception:
        return None


def contar_infracoes_hoje_por_ambiente(
    ambiente_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Conta incidentes de EPI ABERTOS hoje.

    A fonte é o CSV operacional da ETAPA 10:
    config.PATH_INCIDENTES_EPI_CSV.

    Conta cada incidente_id uma única vez e ignora eventos posteriores
    do mesmo incidente (evidência, identidade atualizada, encerramento etc.).
    """
    caminho = _caminho_incidentes()
    hoje = datetime.now().astimezone().date()

    if not os.path.exists(caminho):
        return {
            "sucesso": True,
            "erro": None,
            "data": hoje.isoformat(),
            "ambiente_id": ambiente_id,
            "quantidade": 0,
            "por_ambiente": {},
            "fonte": caminho,
        }

    incidentes_vistos = set()
    por_ambiente: Dict[str, int] = {}

    try:
        with open(
            caminho,
            mode="r",
            encoding="utf-8",
            newline="",
        ) as arquivo:
            reader = csv.DictReader(arquivo)

            for linha in reader:
                if str(linha.get("tipo_registro") or "").strip() != "ABERTURA":
                    continue

                data_registro = _timestamp_para_data_local(
                    linha.get("timestamp", "")
                )

                if data_registro != hoje:
                    continue

                ambiente_registro = str(
                    linha.get("ambiente_id") or ""
                ).strip()

                if ambiente_id is not None and ambiente_registro != str(ambiente_id):
                    continue

                incidente_id = str(
                    linha.get("incidente_id") or ""
                ).strip()

                # Se algum registro antigo não tiver incidente_id,
                # usa registro_id apenas para não colapsar linhas distintas.
                chave = incidente_id or str(
                    linha.get("registro_id") or ""
                ).strip()

                if not chave:
                    continue

                chave_composta = (
                    ambiente_registro,
                    chave,
                )

                if chave_composta in incidentes_vistos:
                    continue

                incidentes_vistos.add(chave_composta)
                por_ambiente[ambiente_registro] = (
                    por_ambiente.get(ambiente_registro, 0) + 1
                )

    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_LER_INCIDENTES",
            "detalhe": str(erro),
            "data": hoje.isoformat(),
            "ambiente_id": ambiente_id,
            "quantidade": 0,
            "por_ambiente": {},
            "fonte": caminho,
        }

    quantidade = (
        por_ambiente.get(str(ambiente_id), 0)
        if ambiente_id is not None
        else sum(por_ambiente.values())
    )

    return {
        "sucesso": True,
        "erro": None,
        "data": hoje.isoformat(),
        "ambiente_id": ambiente_id,
        "quantidade": quantidade,
        "por_ambiente": por_ambiente,
        "fonte": caminho,
    }
