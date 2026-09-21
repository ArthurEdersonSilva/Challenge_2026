from __future__ import annotations

import base64
import csv
import json
import tempfile
import unittest
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import config

from services.evidencia_service import (
    listar_evidencias,
    listar_opcoes_filtros_evidencias,
    obter_detalhes_evidencia,
    obter_imagem_evidencia,
    exportar_evidencia,
)

from services.relatorio_service import (
    gerar_relatorio_geral,
    exportar_relatorio_pdf,
)

from services.dashboard_infracoes_service import (
    obter_dashboard_infracoes,
)


def _parse_timestamp_local(valor: str):
    texto = str(valor or "").strip()

    if not texto:
        return None

    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(texto)
    except Exception:
        return None

    if dt.tzinfo is not None:
        try:
            dt = dt.astimezone()
        except Exception:
            pass

    return dt


class DadosPersistidosMixin:
    @classmethod
    def setUpClass(cls):
        cls.csv_path = Path(
            str(
                getattr(
                    config,
                    "PATH_INCIDENTES_EPI_CSV",
                    "incidentes_epi.csv",
                )
            )
        )

        if not cls.csv_path.exists():
            raise AssertionError(
                f"CSV persistido não encontrado: {cls.csv_path}"
            )

        with cls.csv_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as arquivo:
            cls.eventos = list(csv.DictReader(arquivo))

        if not cls.eventos:
            raise AssertionError(
                "O CSV de incidentes existe, mas está vazio."
            )

        cls.aberturas = [
            item
            for item in cls.eventos
            if str(
                item.get("tipo_registro") or ""
            ).strip() == "ABERTURA"
            and str(
                item.get("incidente_id") or ""
            ).strip()
        ]

        cls.eventos_evidencia = [
            item
            for item in cls.eventos
            if str(
                item.get("tipo_registro") or ""
            ).strip() == "EVIDENCIA"
            and str(
                item.get("evidencia_id") or ""
            ).strip()
        ]

        if not cls.aberturas:
            raise AssertionError(
                "Nenhum registro ABERTURA encontrado no CSV real."
            )

        if not cls.eventos_evidencia:
            raise AssertionError(
                "Nenhum registro EVIDENCIA encontrado no CSV real."
            )

        datas_abertura = [
            _parse_timestamp_local(
                item.get("timestamp", "")
            )
            for item in cls.aberturas
        ]
        datas_abertura = [
            dt
            for dt in datas_abertura
            if dt is not None
        ]

        if not datas_abertura:
            raise AssertionError(
                "Nenhuma ABERTURA possui timestamp válido."
            )

        cls.data_inicio = min(
            datas_abertura
        ).date().isoformat()

        cls.data_fim = max(
            datas_abertura
        ).date().isoformat()

        cls.incidentes_unicos_periodo = {
            str(
                item.get("incidente_id") or ""
            ).strip()
            for item in cls.aberturas
            if (
                (dt := _parse_timestamp_local(
                    item.get("timestamp", "")
                ))
                is not None
                and cls.data_inicio
                <= dt.date().isoformat()
                <= cls.data_fim
            )
        }

        cls.evidencias_periodo = [
            item
            for item in cls.eventos_evidencia
            if (
                (dt := _parse_timestamp_local(
                    item.get("timestamp", "")
                ))
                is not None
                and cls.data_inicio
                <= dt.date().isoformat()
                <= cls.data_fim
            )
        ]

        # O próprio service resolve caminhos relativos a partir da raiz
        # em que o teste é executado. A suite usa o service para achar
        # uma evidência real cuja imagem ainda exista.
        consulta = listar_evidencias(
            data_inicio=cls.data_inicio,
            data_fim=cls.data_fim,
            pagina=1,
            por_pagina=200,
        )

        if not consulta.get("sucesso"):
            raise AssertionError(
                f"Falha ao listar evidências reais: {consulta}"
            )

        cls.evidencias_service = (
            consulta.get("evidencias") or []
        )

        cls.evidencia_com_imagem = next(
            (
                item
                for item in cls.evidencias_service
                if item.get("imagem_disponivel")
            ),
            None,
        )

        if cls.evidencia_com_imagem is None:
            raise AssertionError(
                "Há eventos EVIDENCIA no CSV, mas nenhuma imagem "
                "persistida foi encontrada pelos caminhos registrados."
            )

        cls.evidencia_identificada = next(
            (
                item
                for item in cls.evidencias_service
                if item.get("pessoa_identificada")
            ),
            None,
        )


class TestEvidenciaService(
    DadosPersistidosMixin,
    unittest.TestCase,
):
    def test_01_listar_evidencias_reais(self):
        resultado = listar_evidencias(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            pagina=1,
            por_pagina=20,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertGreater(
            resultado["total"],
            0,
        )
        self.assertLessEqual(
            len(resultado["evidencias"]),
            20,
        )
        self.assertEqual(
            resultado["paginacao"]["pagina"],
            1,
        )

    def test_02_busca_por_evidencia_id_real(self):
        evidencia_id = self.evidencia_com_imagem[
            "evidencia_id"
        ]

        resultado = listar_evidencias(
            busca=evidencia_id,
            pagina=1,
            por_pagina=20,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertGreaterEqual(
            resultado["total"],
            1,
        )

        ids = {
            item["evidencia_id"]
            for item in resultado["evidencias"]
        }

        self.assertIn(
            evidencia_id,
            ids,
        )

    def test_03_filtros_ambiente_epi_e_data(self):
        amostra = self.evidencia_com_imagem

        ambiente = (
            amostra.get("ambiente_id")
            or amostra.get("ambiente_nome")
        )
        epi = amostra.get("epi")
        data = amostra.get("data")

        resultado = listar_evidencias(
            data_inicio=data,
            data_fim=data,
            ambiente=ambiente,
            epi=epi,
            pagina=1,
            por_pagina=200,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertGreaterEqual(
            resultado["total"],
            1,
        )

        for item in resultado["evidencias"]:
            self.assertEqual(
                item["data"],
                data,
            )
            self.assertEqual(
                str(item["epi"]).casefold(),
                str(epi).casefold(),
            )

            candidatos = {
                str(
                    item.get("ambiente_id") or ""
                ).casefold(),
                str(
                    item.get("ambiente_nome") or ""
                ).casefold(),
            }

            self.assertIn(
                str(ambiente).casefold(),
                candidatos,
            )

    def test_04_filtro_colaborador_quando_houver_identificado(self):
        if self.evidencia_identificada is None:
            self.skipTest(
                "Nenhuma evidência persistida possui colaborador identificado."
            )

        matricula = self.evidencia_identificada[
            "matricula"
        ]

        resultado = listar_evidencias(
            colaborador=matricula,
            pagina=1,
            por_pagina=200,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertGreaterEqual(
            resultado["total"],
            1,
        )

        for item in resultado["evidencias"]:
            self.assertEqual(
                item["matricula"],
                matricula,
            )

    def test_05_paginacao_real(self):
        resultado = listar_evidencias(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            pagina=1,
            por_pagina=1,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado["paginacao"]["por_pagina"],
            1,
        )
        self.assertLessEqual(
            len(resultado["evidencias"]),
            1,
        )

    def test_06_periodo_invalido(self):
        resultado = listar_evidencias(
            data_inicio="2099-01-02",
            data_fim="2099-01-01",
        )

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(
            resultado["erro"],
            "PERIODO_INVALIDO",
        )

    def test_07_opcoes_de_filtro_reais(self):
        resultado = listar_opcoes_filtros_evidencias()

        self.assertTrue(resultado["sucesso"])
        self.assertIsInstance(
            resultado["ambientes"],
            list,
        )
        self.assertIsInstance(
            resultado["colaboradores"],
            list,
        )
        self.assertIsInstance(
            resultado["epis"],
            list,
        )

        epi = self.evidencia_com_imagem["epi"]

        self.assertIn(
            epi,
            resultado["epis"],
        )

    def test_08_detalhes_evidencia_real(self):
        evidencia_id = self.evidencia_com_imagem[
            "evidencia_id"
        ]

        resultado = obter_detalhes_evidencia(
            evidencia_id
        )

        self.assertTrue(resultado["sucesso"])

        evidencia = resultado["evidencia"]

        self.assertEqual(
            evidencia["evidencia_id"],
            evidencia_id,
        )
        self.assertTrue(
            evidencia["imagem_disponivel"]
        )
        self.assertTrue(
            evidencia["historico_incidente"]
        )

    def test_09_imagem_real_em_base64(self):
        amostra = self.evidencia_com_imagem

        tipo = (
            "frame"
            if amostra.get("frame_disponivel")
            else "crop"
        )

        resultado = obter_imagem_evidencia(
            amostra["evidencia_id"],
            tipo=tipo,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertTrue(
            resultado["imagem_base64"]
        )

        bruto = base64.b64decode(
            resultado["imagem_base64"],
            validate=True,
        )

        self.assertGreater(
            len(bruto),
            100,
        )
        self.assertGreater(
            resultado["largura"] or 0,
            0,
        )
        self.assertGreater(
            resultado["altura"] or 0,
            0,
        )

    def test_10_exportar_evidencia_zip_sem_alterar_original(self):
        evidencia_id = self.evidencia_com_imagem[
            "evidencia_id"
        ]

        with tempfile.TemporaryDirectory() as pasta:
            resultado = exportar_evidencia(
                evidencia_id,
                pasta,
            )

            self.assertTrue(resultado["sucesso"])

            arquivo = Path(
                resultado["arquivo"]
            )

            self.assertTrue(
                arquivo.exists()
            )
            self.assertEqual(
                arquivo.suffix.lower(),
                ".zip",
            )

            with zipfile.ZipFile(
                arquivo,
                "r",
            ) as pacote:
                nomes = pacote.namelist()

                self.assertIn(
                    "metadata.json",
                    nomes,
                )

                imagens = [
                    nome
                    for nome in nomes
                    if nome.lower().endswith(
                        (".jpg", ".jpeg", ".png")
                    )
                ]

                self.assertGreaterEqual(
                    len(imagens),
                    1,
                )

                metadata = json.loads(
                    pacote.read(
                        "metadata.json"
                    ).decode("utf-8")
                )

                self.assertEqual(
                    metadata["evidencia_id"],
                    evidencia_id,
                )

    def test_11_evidencia_inexistente(self):
        resultado = obter_detalhes_evidencia(
            "EVIDENCIA_QUE_NAO_EXISTE"
        )

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(
            resultado["erro"],
            "EVIDENCIA_NAO_ENCONTRADA",
        )


class TestRelatorioService(
    DadosPersistidosMixin,
    unittest.TestCase,
):
    def test_20_relatorio_geral_consistente_com_csv_real(self):
        resultado = gerar_relatorio_geral(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
        )

        self.assertTrue(resultado["sucesso"])

        indicadores = resultado[
            "indicadores"
        ]

        self.assertEqual(
            indicadores[
                "total_infracoes"
            ]["atual"],
            len(
                self.incidentes_unicos_periodo
            ),
        )

        self.assertEqual(
            indicadores[
                "total_evidencias"
            ]["atual"],
            len(
                self.evidencias_periodo
            ),
        )

        soma_ambientes = sum(
            item["infracoes"]
            for item in resultado[
                "infracoes_por_ambiente"
            ]
        )

        self.assertEqual(
            soma_ambientes,
            indicadores[
                "total_infracoes"
            ]["atual"],
        )

        soma_epis = sum(
            item["infracoes"]
            for item in resultado[
                "infracoes_por_epi"
            ]
        )

        self.assertEqual(
            soma_epis,
            indicadores[
                "total_infracoes"
            ]["atual"],
        )

    def test_21_relatorio_filtrado_por_ambiente_real(self):
        abertura = self.aberturas[0]

        ambiente = (
            abertura.get("ambiente_id")
            or abertura.get("ambiente_nome")
        )

        esperado = {
            str(
                item.get("incidente_id") or ""
            ).strip()
            for item in self.aberturas
            if (
                str(
                    item.get("ambiente_id") or ""
                ).strip().casefold()
                == str(ambiente).strip().casefold()
                or str(
                    item.get("ambiente_nome") or ""
                ).strip().casefold()
                == str(ambiente).strip().casefold()
            )
            and (
                (dt := _parse_timestamp_local(
                    item.get("timestamp", "")
                ))
                is not None
                and self.data_inicio
                <= dt.date().isoformat()
                <= self.data_fim
            )
        }

        resultado = gerar_relatorio_geral(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            ambiente=ambiente,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado[
                "indicadores"
            ][
                "total_infracoes"
            ]["atual"],
            len(esperado),
        )

    def test_22_relatorio_filtrado_por_epi_real(self):
        epi = str(
            self.aberturas[0].get("epi")
            or ""
        ).strip()

        esperado = {
            str(
                item.get("incidente_id") or ""
            ).strip()
            for item in self.aberturas
            if str(
                item.get("epi") or ""
            ).strip().casefold()
            == epi.casefold()
            and (
                (dt := _parse_timestamp_local(
                    item.get("timestamp", "")
                ))
                is not None
                and self.data_inicio
                <= dt.date().isoformat()
                <= self.data_fim
            )
        }

        resultado = gerar_relatorio_geral(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            epi=epi,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado[
                "indicadores"
            ][
                "total_infracoes"
            ]["atual"],
            len(esperado),
        )

    def test_23_serie_temporal_e_resumos(self):
        resultado = gerar_relatorio_geral(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            granularidade="DIARIO",
        )

        self.assertTrue(resultado["sucesso"])
        self.assertIsInstance(
            resultado["serie_temporal"],
            list,
        )
        self.assertIsInstance(
            resultado["resumo_por_ambiente"],
            list,
        )
        self.assertIsInstance(
            resultado["resumo_por_colaborador"],
            list,
        )

    def test_24_exportar_pdf_real(self):
        with tempfile.TemporaryDirectory() as pasta:
            resultado = exportar_relatorio_pdf(
                pasta,
                data_inicio=self.data_inicio,
                data_fim=self.data_fim,
            )

            self.assertTrue(resultado["sucesso"])

            arquivo = Path(
                resultado["arquivo"]
            )

            self.assertTrue(
                arquivo.exists()
            )
            self.assertEqual(
                arquivo.suffix.lower(),
                ".pdf",
            )

            bruto = arquivo.read_bytes()

            self.assertTrue(
                bruto.startswith(
                    b"%PDF-"
                )
            )
            self.assertGreater(
                len(bruto),
                200,
            )

    def test_25_periodo_invalido_relatorio(self):
        resultado = gerar_relatorio_geral(
            data_inicio="2099-01-02",
            data_fim="2099-01-01",
        )

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(
            resultado["erro"],
            "PERIODO_INVALIDO",
        )


class TestDashboardInfracoesService(
    DadosPersistidosMixin,
    unittest.TestCase,
):
    def test_30_dashboard_consistente_com_relatorio(self):
        relatorio = gerar_relatorio_geral(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
        )

        dashboard = obter_dashboard_infracoes(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            limite_recentes=5,
        )

        self.assertTrue(relatorio["sucesso"])
        self.assertTrue(dashboard["sucesso"])

        self.assertEqual(
            dashboard["indicadores"],
            relatorio["indicadores"],
        )

        self.assertEqual(
            dashboard[
                "infracoes_por_ambiente"
            ],
            relatorio[
                "infracoes_por_ambiente"
            ],
        )

        self.assertEqual(
            dashboard[
                "infracoes_por_epi"
            ],
            relatorio[
                "infracoes_por_epi"
            ],
        )

    def test_31_limite_e_ordem_ocorrencias_recentes(self):
        dashboard = obter_dashboard_infracoes(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            limite_recentes=3,
        )

        self.assertTrue(dashboard["sucesso"])

        recentes = dashboard[
            "ocorrencias_recentes"
        ]

        self.assertLessEqual(
            len(recentes),
            3,
        )

        timestamps = [
            item.get("timestamp") or ""
            for item in recentes
        ]

        self.assertEqual(
            timestamps,
            sorted(
                timestamps,
                reverse=True,
            ),
        )

    def test_32_filtro_ambiente_deve_valer_para_ocorrencias_recentes(self):
        abertura = self.aberturas[0]

        ambiente = (
            abertura.get("ambiente_id")
            or abertura.get("ambiente_nome")
        )

        dashboard = obter_dashboard_infracoes(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            ambiente=ambiente,
            limite_recentes=200,
        )

        self.assertTrue(dashboard["sucesso"])

        for item in dashboard[
            "ocorrencias_recentes"
        ]:
            candidatos = {
                str(
                    item.get("ambiente_id") or ""
                ).strip().casefold(),
                str(
                    item.get("ambiente_nome") or ""
                ).strip().casefold(),
            }

            self.assertIn(
                str(ambiente).strip().casefold(),
                candidatos,
                "O filtro de ambiente do dashboard "
                "não foi aplicado às ocorrências recentes.",
            )

    def test_33_filtro_epi_deve_valer_para_ocorrencias_recentes(self):
        epi = str(
            self.aberturas[0].get("epi")
            or ""
        ).strip()

        dashboard = obter_dashboard_infracoes(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            epi=epi,
            limite_recentes=200,
        )

        self.assertTrue(dashboard["sucesso"])

        for item in dashboard[
            "ocorrencias_recentes"
        ]:
            self.assertEqual(
                str(
                    item.get("epi") or ""
                ).strip().casefold(),
                epi.casefold(),
                "O filtro de EPI do dashboard "
                "não foi aplicado às ocorrências recentes.",
            )

    def test_34_campos_dashboard(self):
        dashboard = obter_dashboard_infracoes(
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            limite_recentes=5,
        )

        self.assertTrue(dashboard["sucesso"])
        self.assertIn(
            "indicadores",
            dashboard,
        )
        self.assertIn(
            "serie_temporal",
            dashboard,
        )
        self.assertIn(
            "infracoes_por_ambiente",
            dashboard,
        )
        self.assertIn(
            "infracoes_por_epi",
            dashboard,
        )
        self.assertIn(
            "estado_incidentes_historico",
            dashboard,
        )
        self.assertIn(
            "ocorrencias_recentes",
            dashboard,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
