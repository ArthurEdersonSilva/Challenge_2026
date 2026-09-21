import uuid

from services.ambiente_service import (
    criar_ambiente,
    definir_roi,
    finalizar_ambiente,
    listar_ambientes_consulta,
    remover_ambiente,
)

CAMERA_1 = "8c086203-d10f-4782-b2b1-545996043e56"   # Integrated Webcam
CAMERA_2 = "94172bf6-4532-448f-87ab-26b6ba11993d"   # TESTE_CELULAR_FINAL


def nomes(resultado):
    return [item.get("nome") for item in resultado.get("ambientes", [])]


def main():
    sufixo = uuid.uuid4().hex[:6]
    nome_ativo = f"FILTRO_ATIVO_{sufixo}"
    nome_inativo = f"FILTRO_INATIVO_{sufixo}"

    ids = []

    try:
        a = criar_ambiente(
            nome_ativo,
            [CAMERA_1],
            epis_obrigatorios=["Capacete"],
            descricao="Ambiente ativo para teste de filtros",
        )
        assert a.get("sucesso"), a
        aid = a["ambiente"]["ambiente_id"]
        ids.append(aid)

        r = definir_roi(aid, CAMERA_1, 0.1, 0.1, 0.9, 0.9)
        assert r.get("sucesso"), r

        f = finalizar_ambiente(aid)
        assert f.get("sucesso"), f

        b = criar_ambiente(
            nome_inativo,
            [CAMERA_2],
            epis_obrigatorios=["Luvas"],
            descricao="Ambiente inativo para teste de filtros",
        )
        assert b.get("sucesso"), b
        bid = b["ambiente"]["ambiente_id"]
        ids.append(bid)

        busca = listar_ambientes_consulta(
            busca=nome_ativo,
            atualizar_status=False,
        )

        status_ativo = listar_ambientes_consulta(
            status="ATIVO",
            atualizar_status=False,
        )

        status_inativo = listar_ambientes_consulta(
            status="INATIVO",
            atualizar_status=False,
        )

        camera_1 = listar_ambientes_consulta(
            camera_uid=CAMERA_1,
            atualizar_status=False,
        )

        camera_2 = listar_ambientes_consulta(
            camera_uid=CAMERA_2,
            atualizar_status=False,
        )

        epi_capacete = listar_ambientes_consulta(
            epi="Capacete",
            atualizar_status=False,
        )

        epi_luvas = listar_ambientes_consulta(
            epi="Luvas",
            atualizar_status=False,
        )

        pagina_1 = listar_ambientes_consulta(
            pagina=1,
            por_pagina=1,
            atualizar_status=False,
        )

        passou = {
            "busca": nome_ativo in nomes(busca),
            "status_ativo": nome_ativo in nomes(status_ativo),
            "status_inativo": nome_inativo in nomes(status_inativo),
            "filtro_camera_1": nome_ativo in nomes(camera_1),
            "filtro_camera_2": nome_inativo in nomes(camera_2),
            "filtro_epi_capacete": nome_ativo in nomes(epi_capacete),
            "filtro_epi_luvas": nome_inativo in nomes(epi_luvas),
            "paginacao": (
                pagina_1.get("paginacao", {}).get("por_pagina") == 1
                and len(pagina_1.get("ambientes", [])) <= 1
                and pagina_1.get("paginacao", {}).get("total_itens", 0) >= 2
            ),
        }

        for chave, valor in passou.items():
            print(f"{chave}={valor}")

        print(
            "RESULTADO_FINAL=",
            "PASSOU" if all(passou.values()) else "FALHOU",
        )

    finally:
        for ambiente_id in ids:
            print(
                "LIMPEZA=",
                remover_ambiente(ambiente_id),
            )


if __name__ == "__main__":
    main()
