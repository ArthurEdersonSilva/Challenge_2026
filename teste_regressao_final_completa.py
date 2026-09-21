from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

TESTES = [
    # Regressão anterior
    "teste_cadastro_colaborador.py",
    "teste_consulta_detalhes_colaborador.py",
    "teste_monitoramento_colaborador.py",
    "teste_dashboard_gerencial.py",
    "teste_metadata_evidencias.py",
    "teste_dashboard_distribuicao_colaborador.py",
    "teste_dashboard_opcoes_filtros.py",
    "teste_filtros_paginacao_ambientes.py",
    "teste_http_api_sistema.py",
    "teste_integracao_monitoramento_estado_real.py",
    "teste_integracao_dashboard_gerencial_real.py",
    "teste_integracao_real_api_sistema.py",

    # Novos testes adicionados no fechamento
    "teste_http_ambientes_avancado.py",
    "teste_http_colaborador_captura.py",
    "teste_http_colaborador_imagem.py",
    "teste_setor_colaborador.py",
    "teste_remocao_colaborador.py",
    "teste_consulta_gerencial_colaboradores.py",
    "teste_monitoramento_preview_operador.py",
    "teste_monitoramento_ergonomia.py",
    "teste_bootstrap_api_runtime.py",
    "teste_http_evidencias_autorizacao_exportacao.py",

    # Testes físicos / câmera por último
    "teste_multiplas_cameras_ambiente.py",
    "teste_reconexao_ambiente.py",
]


def main() -> int:
    resultados = []

    print("=" * 72)
    print(" REGRESSÃO FINAL COMPLETA — CHALLENGE_2026")
    print("=" * 72)

    for indice, nome in enumerate(TESTES, start=1):
        caminho = BASE / nome

        print()
        print("=" * 72)
        print(f"[{indice:02d}/{len(TESTES):02d}] {nome}")
        print("=" * 72)

        if not caminho.exists():
            print(f"FALHA: arquivo não encontrado: {nome}")
            resultados.append((nome, "AUSENTE"))
            continue

        processo = subprocess.run(
            [sys.executable, str(caminho)],
            cwd=str(BASE),
        )

        status = "PASSOU" if processo.returncode == 0 else "FALHOU"
        resultados.append((nome, status))

    print()
    print("=" * 72)
    print(" RESUMO FINAL")
    print("=" * 72)

    falhas = []
    for nome, status in resultados:
        print(f"{status:8}  {nome}")
        if status != "PASSOU":
            falhas.append((nome, status))

    print()
    print(f"Total planejado : {len(TESTES)}")
    print(f"Passaram        : {sum(1 for _, s in resultados if s == 'PASSOU')}")
    print(f"Falharam/ausentes: {len(falhas)}")

    if falhas:
        print()
        print("RESULTADO_FINAL=FALHOU")
        return 1

    print()
    print("RESULTADO_FINAL=PASSOU")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
