from __future__ import annotations

import unittest
from unittest.mock import patch

import api_sistema
import services.colaborador_consulta_service as service


COLABORADORES = {
    "sucesso": True,
    "erro": None,
    "quantidade": 3,
    "colaboradores": [
        {
            "matricula": "COL-001",
            "nome": "João Silva",
            "cargo": "Operador",
            "setor": "Produção",
            "biometria_cadastrada": True,
        },
        {
            "matricula": "COL-002",
            "nome": "Ana Souza",
            "cargo": "Técnica",
            "setor": "Corte",
            "biometria_cadastrada": True,
        },
        {
            "matricula": "COL-003",
            "nome": "Pedro Lima",
            "cargo": "Operador",
            "setor": "Produção",
            "biometria_cadastrada": False,
        },
    ],
}

AMBIENTES_MAP = {
    "COL-001": [
        {"ambiente_id": "AMB-1", "nome": "Soldagem"},
        {"ambiente_id": "AMB-2", "nome": "Produção 01"},
    ],
    "COL-002": [
        {"ambiente_id": "AMB-3", "nome": "Corte"},
    ],
    "COL-003": [
        {"ambiente_id": "AMB-2", "nome": "Produção 01"},
    ],
}

INFRACOES = {
    "sucesso": True,
    "erro": None,
    "fonte": "incidentes_epi.csv",
    "infracoes": [
        {
            "incidente_id": "INC-3",
            "evidencia_id": "EVI-3",
            "timestamp": "2026-09-19T14:32:00-03:00",
            "data": "2026-09-19",
            "horario": "14:32:00",
            "ambiente_id": "AMB-1",
            "ambiente_nome": "Soldagem",
            "camera_id": "CAM-1",
            "camera_nome": "CAM-1",
            "matricula": "COL-001",
            "nome": "João Silva",
            "cargo": "Operador",
            "epi": "Óculos",
            "tipo_irregularidade": "AUSENCIA_EPI",
            "infracao": "Sem Óculos",
        },
        {
            "incidente_id": "INC-2",
            "evidencia_id": "EVI-2",
            "timestamp": "2026-09-18T11:05:00-03:00",
            "data": "2026-09-18",
            "horario": "11:05:00",
            "ambiente_id": "AMB-2",
            "ambiente_nome": "Produção 01",
            "camera_id": "CAM-2",
            "camera_nome": "CAM-2",
            "matricula": "COL-001",
            "nome": "João Silva",
            "cargo": "Operador",
            "epi": "Capacete",
            "tipo_irregularidade": "AUSENCIA_EPI",
            "infracao": "Sem Capacete",
        },
        {
            "incidente_id": "INC-1",
            "evidencia_id": "EVI-1",
            "timestamp": "2026-09-17T09:20:00-03:00",
            "data": "2026-09-17",
            "horario": "09:20:00",
            "ambiente_id": "AMB-3",
            "ambiente_nome": "Corte",
            "camera_id": "CAM-3",
            "camera_nome": "CAM-3",
            "matricula": "COL-002",
            "nome": "Ana Souza",
            "cargo": "Técnica",
            "epi": "Luvas",
            "tipo_irregularidade": "AUSENCIA_EPI",
            "infracao": "Sem Luvas",
        },
        {
            "incidente_id": "INC-H",
            "evidencia_id": "EVI-H",
            "timestamp": "2026-01-10T08:00:00-03:00",
            "data": "2026-01-10",
            "horario": "08:00:00",
            "ambiente_id": "AMB-1",
            "ambiente_nome": "Soldagem",
            "camera_id": "CAM-1",
            "camera_nome": "CAM-1",
            "matricula": "COL-001",
            "nome": "João Silva",
            "cargo": "Operador",
            "epi": "Óculos",
            "tipo_irregularidade": "AUSENCIA_EPI",
            "infracao": "Sem Óculos",
        },
    ],
}


class TestConsultaGerencialService(unittest.TestCase):
    def setUp(self):
        self.p1 = patch.object(service, "listar_colaboradores", return_value=COLABORADORES)
        self.p2 = patch.object(service, "_carregar_infracoes", return_value=INFRACOES)
        self.p3 = patch.object(service, "_mapa_ambientes_por_matricula", return_value=(AMBIENTES_MAP, True))
        self.p1.start(); self.p2.start(); self.p3.start()
        self.addCleanup(self.p1.stop); self.addCleanup(self.p2.stop); self.addCleanup(self.p3.stop)

    def test_01_consulta_monta_indicadores_e_linhas(self):
        r = service.consultar_colaboradores_gerencial(
            data_inicio="2026-09-01", data_fim="2026-09-30"
        )
        self.assertTrue(r["sucesso"])
        self.assertEqual(r["resumo"]["colaboradores_cadastrados"], 3)
        self.assertEqual(r["resumo"]["com_infracoes_periodo"], 2)
        self.assertEqual(r["resumo"]["sem_infracoes_periodo"], 1)
        self.assertEqual(r["resumo"]["total_infracoes_periodo"], 3)
        self.assertEqual(r["colaboradores"][0]["matricula"], "COL-001")
        self.assertEqual(r["colaboradores"][0]["infracoes_periodo"], 2)

    def test_02_filtro_setor(self):
        r = service.consultar_colaboradores_gerencial(
            data_inicio="2026-09-01", data_fim="2026-09-30", setor="produção"
        )
        self.assertEqual(r["resumo"]["colaboradores_cadastrados"], 2)
        self.assertEqual({i["matricula"] for i in r["colaboradores"]}, {"COL-001", "COL-003"})

    def test_03_filtro_ambiente_considera_vinculo(self):
        r = service.consultar_colaboradores_gerencial(
            data_inicio="2026-09-01", data_fim="2026-09-30", ambiente="AMB-2"
        )
        self.assertEqual(r["resumo"]["colaboradores_cadastrados"], 2)
        por_matricula = {i["matricula"]: i for i in r["colaboradores"]}
        self.assertEqual(por_matricula["COL-001"]["infracoes_periodo"], 1)
        self.assertEqual(por_matricula["COL-003"]["infracoes_periodo"], 0)

    def test_04_situacao_com_infracoes(self):
        r = service.consultar_colaboradores_gerencial(
            data_inicio="2026-09-01", data_fim="2026-09-30", situacao_infracoes="COM_INFRACOES"
        )
        self.assertEqual({i["matricula"] for i in r["colaboradores"]}, {"COL-001", "COL-002"})

    def test_05_situacao_sem_infracoes(self):
        r = service.consultar_colaboradores_gerencial(
            data_inicio="2026-09-01", data_fim="2026-09-30", situacao_infracoes="SEM_INFRACOES"
        )
        self.assertEqual([i["matricula"] for i in r["colaboradores"]], ["COL-003"])

    def test_06_periodo_invalido(self):
        r = service.consultar_colaboradores_gerencial(
            data_inicio="2026-10-01", data_fim="2026-09-01"
        )
        self.assertFalse(r["sucesso"])
        self.assertEqual(r["erro"], "PERIODO_INVALIDO")

    def test_07_detalhe_monta_historico_total_e_por_epi(self):
        with patch.object(
            service,
            "obter_detalhes_colaborador",
            return_value={"sucesso": True, "erro": None, "colaborador": COLABORADORES["colaboradores"][0]},
        ), patch.object(
            service,
            "obter_status_biometria",
            return_value={"sucesso": True, "erro": None, "biometria_cadastrada": True},
        ):
            r = service.obter_detalhes_colaborador_gerencial(
                "COL-001", data_inicio="2026-09-01", data_fim="2026-09-30"
            )
        self.assertTrue(r["sucesso"])
        self.assertEqual(r["indicadores"]["infracoes_periodo"], 2)
        self.assertEqual(r["indicadores"]["total_historico_infracoes"], 3)
        self.assertEqual(r["indicadores"]["ambientes_vinculados"], 2)
        self.assertEqual(len(r["historico_infracoes"]), 2)
        por_epi = {i["epi"]: i["infracoes"] for i in r["infracoes_por_epi"]}
        self.assertEqual(por_epi["Óculos"], 1)
        self.assertEqual(por_epi["Capacete"], 1)


class TestConsultaGerencialHTTP(unittest.TestCase):
    def setUp(self):
        self.client = api_sistema.app.test_client()
        self.headers = {"X-Perfil": "GERENCIAL"}

    def test_08_operador_bloqueado(self):
        r = self.client.get(
            "/api/colaboradores/consulta-gerencial",
            headers={"X-Perfil": "OPERADOR", "X-Matricula": "COL-001"},
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.get_json()["erro"], "ACESSO_NEGADO")

    def test_09_consulta_encaminha_filtros(self):
        retorno = {"sucesso": True, "erro": None, "colaboradores": []}
        with patch.object(api_sistema, "consultar_colaboradores_gerencial", return_value=retorno) as func:
            r = self.client.get(
                "/api/colaboradores/consulta-gerencial?data_inicio=2026-09-01&data_fim=2026-09-30&setor=Producao&ambiente=AMB-1&situacao_infracoes=COM_INFRACOES&busca=joao&pagina=2&por_pagina=10",
                headers=self.headers,
            )
        self.assertEqual(r.status_code, 200)
        kwargs = func.call_args.kwargs
        self.assertEqual(kwargs["data_inicio"], "2026-09-01")
        self.assertEqual(kwargs["data_fim"], "2026-09-30")
        self.assertEqual(kwargs["setor"], "Producao")
        self.assertEqual(kwargs["ambiente"], "AMB-1")
        self.assertEqual(kwargs["situacao_infracoes"], "COM_INFRACOES")
        self.assertEqual(kwargs["busca"], "joao")
        self.assertEqual(kwargs["pagina"], 2)
        self.assertEqual(kwargs["por_pagina"], 10)

    def test_10_filtros_200(self):
        retorno = {"sucesso": True, "erro": None, "setores": [], "ambientes": [], "situacoes_infracoes": []}
        with patch.object(api_sistema, "listar_opcoes_filtros_colaboradores", return_value=retorno):
            r = self.client.get(
                "/api/colaboradores/consulta-gerencial/filtros",
                headers=self.headers,
            )
        self.assertEqual(r.status_code, 200)

    def test_11_detalhes_gerenciais_200(self):
        retorno = {"sucesso": True, "erro": None, "colaborador": {"matricula": "COL-001"}}
        with patch.object(api_sistema, "obter_detalhes_colaborador_gerencial", return_value=retorno) as func:
            r = self.client.get(
                "/api/colaboradores/COL-001/detalhes-gerenciais?data_inicio=2026-09-01&data_fim=2026-09-30&limite_historico=8",
                headers=self.headers,
            )
        self.assertEqual(r.status_code, 200)
        kwargs = func.call_args.kwargs
        self.assertEqual(kwargs["matricula"], "COL-001")
        self.assertEqual(kwargs["limite_historico"], 8)

    def test_12_colaborador_inexistente_404(self):
        retorno = {"sucesso": False, "erro": "COLABORADOR_NAO_ENCONTRADO", "colaborador": None}
        with patch.object(api_sistema, "obter_detalhes_colaborador_gerencial", return_value=retorno):
            r = self.client.get(
                "/api/colaboradores/NAO-EXISTE/detalhes-gerenciais",
                headers=self.headers,
            )
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
