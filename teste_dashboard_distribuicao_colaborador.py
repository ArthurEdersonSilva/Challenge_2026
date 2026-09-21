from services.dashboard_infracoes_service import obter_dashboard_infracoes


def main():
    resultado = obter_dashboard_infracoes()

    print("SUCESSO=", resultado.get("sucesso"))

    if not resultado.get("sucesso"):
        print("ERRO=", resultado.get("erro"))
        raise SystemExit(1)

    existe = "infracoes_por_colaborador" in resultado
    print("CAMPO_EXISTE=", existe)

    dados = resultado.get("infracoes_por_colaborador")

    tipo_lista = isinstance(dados, list)
    print("TIPO_LISTA=", tipo_lista)

    estrutura_ok = True

    if dados:
        obrigatorios = {
            "matricula",
            "nome",
            "cargo",
            "ambiente_principal",
            "ambientes",
            "infracoes",
            "ultima_ocorrencia",
            "percentual_total",
        }

        faltando = obrigatorios - set(dados[0].keys())
        estrutura_ok = not faltando

        print("PRIMEIRO_REGISTRO=", dados[0])
        print("CAMPOS_FALTANDO=", sorted(faltando))

    print("ESTRUTURA_OK=", estrutura_ok)

    passou = (
        existe
        and tipo_lista
        and estrutura_ok
    )

    print(
        "RESULTADO_FINAL=",
        "PASSOU" if passou else "FALHOU"
    )

    raise SystemExit(0 if passou else 1)


if __name__ == "__main__":
    main()
