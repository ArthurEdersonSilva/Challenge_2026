from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Optional

STATUS_NAO_EXECUTADA = "AVALIAÇÃO NÃO EXECUTADA"
MOTIVO_SEM_GT = "GROUND TRUTH NÃO DISPONÍVEL"


def resultado_nao_executado(motivo: str = MOTIVO_SEM_GT) -> Dict[str, Any]:
    return {
        "status": STATUS_NAO_EXECUTADA,
        "motivo": motivo,
        "metricas": None,
    }


def salvar_relatorios_avaliacao_real(
    resultado: Dict[str, Any],
    caminho_json: Optional[str] = None,
    caminho_csv: Optional[str] = None,
) -> Dict[str, str]:
    if resultado.get("status") != "AVALIAÇÃO EXECUTADA" or not resultado.get("metricas"):
        raise ValueError("Relatórios de métricas só podem ser gravados após avaliação real.")

    salvos: Dict[str, str] = {}
    if caminho_json:
        destino = Path(caminho_json)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        salvos["json"] = str(destino)

    if caminho_csv:
        destino = Path(caminho_csv)
        destino.parent.mkdir(parents=True, exist_ok=True)
        por_classe = resultado["metricas"].get("por_classe", {})
        with destino.open("w", encoding="utf-8", newline="") as arquivo:
            campos = [
                "classe_id", "classe", "suporte", "tp", "fp", "fn",
                "precision", "recall", "f1", "ap50", "avaliavel",
            ]
            writer = csv.DictWriter(arquivo, fieldnames=campos)
            writer.writeheader()
            for chave in sorted(por_classe, key=lambda x: int(x)):
                linha = dict(por_classe[chave])
                writer.writerow({campo: linha.get(campo) for campo in campos})
        salvos["csv"] = str(destino)
    return salvos
