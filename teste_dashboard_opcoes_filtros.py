import csv
from pathlib import Path

import config

from services.dashboard_infracoes_service import (
    listar_opcoes_filtros_dashboard,
)


def main():
    resultado = listar_opcoes_filtros_dashboard()

    print("SUCESSO=", resultado.get("sucesso"))

    if not resultado.get("sucesso"):
        print("ERRO=", resultado.get("erro"))
        raise SystemExit(1)

    campos = {
        "ambientes",
        "colaboradores",
        "epis",
        "tipos_irregularidade",
        "epi_infracao",
    }

    campos_ok = campos.issubset(resultado.keys())
    print("CAMPOS_OK=", campos_ok)

    tipos_ok = all(
        isinstance(resultado[campo], list)
        for campo in campos
    )
    print("TIPOS_OK=", tipos_ok)

    csv_path = Path(
        str(
            getattr(
                config,
                "PATH_INCIDENTES_EPI_CSV",
                "incidentes_epi.csv",
            )
        )
    )

    with csv_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as arquivo:
        eventos = list(csv.DictReader(arquivo))

    aberturas = [
        item
        for item in eventos
        if str(
            item.get("tipo_registro") or ""
        ).strip() == "ABERTURA"
    ]

    epis_csv = {
        str(item.get("epi") or "").strip()
        for item in aberturas
        if str(item.get("epi") or "").strip()
    }

    tipos_csv = {
        str(
            item.get("tipo_irregularidade") or ""
        ).strip()
        for item in aberturas
        if str(
            item.get("tipo_irregularidade") or ""
        ).strip()
    }

    ambientes_csv = {
        str(
            item.get("ambiente_id")
            or item.get("ambiente_nome")
            or ""
        ).strip()
        for item in aberturas
        if (
            item.get("ambiente_id")
            or item.get("ambiente_nome")
        )
    }

    epis_service = set(resultado["epis"])
    tipos_service = set(
        resultado["tipos_irregularidade"]
    )
    ambientes_service = {
        str(
            item.get("ambiente_id")
            or item.get("nome")
            or ""
        ).strip()
        for item in resultado["ambientes"]
    }

    epis_ok = epis_csv.issubset(epis_service)
    tipos_irregularidade_ok = tipos_csv.issubset(
        tipos_service
    )
    ambientes_ok = ambientes_csv.issubset(
        ambientes_service
    )

    print("EPIS_OK=", epis_ok)
    print(
        "TIPOS_IRREGULARIDADE_OK=",
        tipos_irregularidade_ok,
    )
    print("AMBIENTES_OK=", ambientes_ok)
    print(
        "QTD_AMBIENTES=",
        len(resultado["ambientes"]),
    )
    print(
        "QTD_COLABORADORES=",
        len(resultado["colaboradores"]),
    )
    print(
        "QTD_EPIS=",
        len(resultado["epis"]),
    )
    print(
        "QTD_TIPOS_IRREGULARIDADE=",
        len(resultado["tipos_irregularidade"]),
    )

    passou = all(
        (
            campos_ok,
            tipos_ok,
            epis_ok,
            tipos_irregularidade_ok,
            ambientes_ok,
        )
    )

    print(
        "RESULTADO_FINAL=",
        "PASSOU" if passou else "FALHOU",
    )

    raise SystemExit(0 if passou else 1)


if __name__ == "__main__":
    main()
