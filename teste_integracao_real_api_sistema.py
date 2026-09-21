from __future__ import annotations

import copy
import glob
import hashlib
import importlib
import os
import unittest

import config
from estado_sistema import criar_estado_sistema_legado


class TestIntegracaoRealAPISistema(unittest.TestCase):
    """
    Integração REAL da api_sistema.py usando Flask test_client.

    Usa as rotas HTTP reais e, por consequência, os services reais de:
    - Câmeras
    - Ambientes
    - Colaboradores
    - Monitoramento do Colaborador
    - Dashboard Gerencial

    Não usa mocks dos services.
    Não cria, edita ou remove dados.
    Não cadastra câmeras/ambientes/colaboradores.
    Não grava incidentes.
    Não altera biometria.

    A autenticação usa os cabeçalhos locais já definidos pela api_sistema.py:
        X-Perfil
        X-Matricula
    """

    @classmethod
    def setUpClass(cls):
        cls.api = importlib.import_module("api_sistema")

        if not hasattr(cls.api, "app"):
            raise AssertionError(
                "api_sistema.py deve expor a aplicação Flask como `app`."
            )

        if not hasattr(cls.api, "definir_estado_sistema"):
            raise AssertionError(
                "api_sistema.py deve expor definir_estado_sistema()."
            )

        cls.api.app.config.update(
            TESTING=True,
            PROPAGATE_EXCEPTIONS=False,
        )

        # EstadoSistema real, sem iniciar pipeline de IA/câmeras.
        cls.estado_sistema = criar_estado_sistema_legado(config)
        cls.estado_original = copy.deepcopy(
            cls.estado_sistema.snapshot()
        )

        cls.arquivos_monitorados = cls._arquivos_persistencia()
        cls.hashes_antes = cls._hashes(cls.arquivos_monitorados)

        cls.headers_gerencial = {
            "X-Perfil": "GERENCIAL",
        }

        cls.matricula_real = None

    def setUp(self):
        self.client = self.api.app.test_client()

        # Garante EstadoSistema real disponível em cada teste.
        self.api.definir_estado_sistema(
            self.estado_sistema
        )

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _arquivos_persistencia():
        caminhos = set()

        fixos = [
            os.path.join(
                "configuracoes",
                "cameras_registry.json",
            ),
            getattr(
                config,
                "PATH_DADOS_OPERADORES",
                os.path.join(
                    "banco_biometria",
                    "dados_operadores.csv",
                ),
            ),
            getattr(
                config,
                "PATH_INCIDENTES_EPI_CSV",
                "incidentes_epi.csv",
            ),
        ]

        for caminho in fixos:
            if caminho and os.path.isfile(caminho):
                caminhos.add(os.path.abspath(caminho))

        for caminho in glob.glob(
            os.path.join("ambientes", "*.json")
        ):
            if os.path.isfile(caminho):
                caminhos.add(os.path.abspath(caminho))

        return tuple(sorted(caminhos))

    @staticmethod
    def _hash_arquivo(caminho):
        sha = hashlib.sha256()

        with open(caminho, "rb") as arquivo:
            for bloco in iter(
                lambda: arquivo.read(1024 * 1024),
                b"",
            ):
                sha.update(bloco)

        return sha.hexdigest()

    @classmethod
    def _hashes(cls, caminhos):
        return {
            caminho: cls._hash_arquivo(caminho)
            for caminho in caminhos
            if os.path.isfile(caminho)
        }

    def _get_json(
        self,
        rota,
        headers=None,
        status_esperado=200,
    ):
        resposta = self.client.get(
            rota,
            headers=headers or {},
        )

        self.assertEqual(
            resposta.status_code,
            status_esperado,
            resposta.get_data(as_text=True),
        )

        dados = resposta.get_json()

        self.assertIsInstance(
            dados,
            dict,
            f"Resposta de {rota} não é JSON objeto.",
        )

        return dados

    @staticmethod
    def _buscar_chaves_sensiveis(valor):
        """
        Procura nomes de campos que não devem aparecer para OPERADOR.
        Não inspeciona valores/credenciais.
        """
        proibidas = {
            "senha",
            "password",
            "usuario",
            "username",
            "fonte",
            "url",
            "rtsp_url",
            "stream_url",
        }

        encontradas = set()

        def caminhar(obj):
            if isinstance(obj, dict):
                for chave, conteudo in obj.items():
                    chave_normalizada = str(chave).strip().lower()

                    if chave_normalizada in proibidas:
                        encontradas.add(chave_normalizada)

                    caminhar(conteudo)

            elif isinstance(obj, (list, tuple)):
                for item in obj:
                    caminhar(item)

        caminhar(valor)
        return encontradas

    # ============================================================
    # AUTENTICAÇÃO / PERMISSÕES
    # ============================================================

    def test_01_sem_autenticacao_retorna_401(self):
        dados = self._get_json(
            "/api/cameras",
            status_esperado=401,
        )

        self.assertFalse(dados["sucesso"])
        self.assertEqual(
            dados["erro"],
            "NAO_AUTENTICADO",
        )

    def test_02_operador_nao_acessa_rotas_gerenciais(self):
        headers = {
            "X-Perfil": "OPERADOR",
            "X-Matricula": "557079",
        }

        rotas = [
            "/api/cameras",
            "/api/ambientes",
            "/api/colaboradores",
            "/api/dashboard-gerencial",
        ]

        for rota in rotas:
            with self.subTest(rota=rota):
                dados = self._get_json(
                    rota,
                    headers=headers,
                    status_esperado=403,
                )

                self.assertFalse(dados["sucesso"])
                self.assertEqual(
                    dados["erro"],
                    "ACESSO_NEGADO",
                )

    # ============================================================
    # CÂMERAS REAIS
    # ============================================================

    def test_03_cameras_reais_via_http(self):
        dados = self._get_json(
            "/api/cameras",
            headers=self.headers_gerencial,
        )

        self.assertTrue(
            dados.get("sucesso"),
            dados,
        )
        self.assertIn("cameras", dados)
        self.assertIsInstance(
            dados["cameras"],
            list,
        )

        quantidade = dados.get("quantidade")
        if quantidade is not None:
            self.assertEqual(
                int(quantidade),
                len(dados["cameras"]),
            )

        for camera in dados["cameras"]:
            self.assertIn(
                "camera_uid",
                camera,
            )
            self.assertIn(
                "nome",
                camera,
            )
            self.assertIn(
                "tipo",
                camera,
            )

        # Se houver câmera cadastrada, valida também detalhe real.
        if dados["cameras"]:
            uid = dados["cameras"][0].get(
                "camera_uid"
            )

            if uid:
                detalhe = self._get_json(
                    f"/api/cameras/{uid}",
                    headers=self.headers_gerencial,
                )

                self.assertTrue(
                    detalhe.get("sucesso"),
                    detalhe,
                )

    # ============================================================
    # AMBIENTES REAIS
    # ============================================================

    def test_04_ambientes_reais_via_http(self):
        dados = self._get_json(
            "/api/ambientes?pagina=1&por_pagina=20",
            headers=self.headers_gerencial,
        )

        self.assertTrue(
            dados.get("sucesso"),
            dados,
        )
        self.assertIn(
            "ambientes",
            dados,
        )
        self.assertIsInstance(
            dados["ambientes"],
            list,
        )

        if "total" in dados:
            self.assertGreaterEqual(
                int(dados["total"]),
                len(dados["ambientes"]),
            )

        # Se houver ambiente, valida detalhe real.
        if dados["ambientes"]:
            ambiente_id = dados["ambientes"][0].get(
                "ambiente_id"
            )

            if ambiente_id:
                detalhe = self._get_json(
                    f"/api/ambientes/{ambiente_id}",
                    headers=self.headers_gerencial,
                )

                self.assertTrue(
                    detalhe.get("sucesso"),
                    detalhe,
                )

    # ============================================================
    # COLABORADORES REAIS
    # ============================================================

    def test_05_colaboradores_reais_via_http(self):
        dados = self._get_json(
            "/api/colaboradores?pagina=1&por_pagina=20",
            headers=self.headers_gerencial,
        )

        self.assertTrue(
            dados.get("sucesso"),
            dados,
        )
        self.assertIn(
            "colaboradores",
            dados,
        )
        self.assertIsInstance(
            dados["colaboradores"],
            list,
        )

        self.assertGreater(
            len(dados["colaboradores"]),
            0,
            "É necessário pelo menos um colaborador real cadastrado.",
        )

        colaborador = dados["colaboradores"][0]

        for campo in (
            "matricula",
            "nome",
            "cargo",
            "biometria_cadastrada",
        ):
            self.assertIn(
                campo,
                colaborador,
            )

        type(self).matricula_real = str(
            colaborador["matricula"]
        )

        detalhe = self._get_json(
            f"/api/colaboradores/{self.matricula_real}",
            headers=self.headers_gerencial,
        )

        self.assertTrue(
            detalhe.get("sucesso"),
            detalhe,
        )
        self.assertEqual(
            str(
                detalhe["colaborador"]["matricula"]
            ),
            self.matricula_real,
        )

    # ============================================================
    # MONITORAMENTO REAL
    # ============================================================

    def test_06_monitoramento_gerencial_com_estado_real(self):
        if not self.matricula_real:
            self.test_05_colaboradores_reais_via_http()

        dados = self._get_json(
            (
                "/api/monitoramento/colaboradores/"
                f"{self.matricula_real}"
            ),
            headers=self.headers_gerencial,
        )

        self.assertTrue(
            dados.get("sucesso"),
            dados,
        )
        self.assertIn(
            "colaborador",
            dados,
        )
        self.assertIn(
            "monitoramento",
            dados,
        )

        self.assertEqual(
            str(
                dados["colaborador"]["matricula"]
            ),
            self.matricula_real,
        )

        self.assertIn(
            dados["monitoramento"]["status_geral"],
            {
                "CONFORME",
                "NAO_CONFORME",
                "INDETERMINADO",
            },
        )

    def test_07_operador_acessa_apenas_o_proprio_monitoramento(self):
        if not self.matricula_real:
            self.test_05_colaboradores_reais_via_http()

        headers_operador = {
            "X-Perfil": "OPERADOR",
            "X-Matricula": self.matricula_real,
        }

        proprio = self._get_json(
            "/api/monitoramento/me",
            headers=headers_operador,
        )

        self.assertTrue(
            proprio.get("sucesso"),
            proprio,
        )
        self.assertEqual(
            str(
                proprio["colaborador"]["matricula"]
            ),
            self.matricula_real,
        )

        # A resposta do operador não deve expor configuração/credencial
        # administrativa da câmera.
        chaves_sensiveis = self._buscar_chaves_sensiveis(
            proprio
        )
        self.assertEqual(
            chaves_sensiveis,
            set(),
            (
                "Monitoramento do OPERADOR expôs campos sensíveis: "
                f"{sorted(chaves_sensiveis)}"
            ),
        )

        outra_matricula = "__OUTRO_COLABORADOR__"

        if outra_matricula == self.matricula_real:
            outra_matricula = "__OUTRO_COLABORADOR_2__"

        negado = self._get_json(
            (
                "/api/monitoramento/colaboradores/"
                f"{outra_matricula}"
            ),
            headers=headers_operador,
            status_esperado=403,
        )

        self.assertFalse(
            negado["sucesso"]
        )
        self.assertEqual(
            negado["erro"],
            "ACESSO_NEGADO",
        )

    def test_08_monitoramento_sem_estado_retorna_503(self):
        self.api.definir_estado_sistema(None)

        dados = self._get_json(
            "/api/monitoramento/colaboradores/557079",
            headers=self.headers_gerencial,
            status_esperado=503,
        )

        self.assertFalse(
            dados["sucesso"]
        )
        self.assertEqual(
            dados["erro"],
            "ESTADO_SISTEMA_INDISPONIVEL",
        )

    # ============================================================
    # DASHBOARD REAL
    # ============================================================

    def test_09_dashboard_gerencial_real_via_http(self):
        dados = self._get_json(
            "/api/dashboard-gerencial",
            headers=self.headers_gerencial,
        )

        self.assertTrue(
            dados.get("sucesso"),
            dados,
        )

        for campo in (
            "resumo",
            "alertas",
            "ambientes_com_mais_infracoes",
            "serie_temporal",
            "status_cameras",
            "periodo",
        ):
            self.assertIn(
                campo,
                dados,
            )

        resumo = dados["resumo"]

        for campo in (
            "cameras_total",
            "cameras_online",
            "cameras_offline",
            "ambientes_total",
            "ambientes_ativos",
            "ambientes_com_problema",
            "ambientes_inativos",
            "colaboradores_total",
            "infracoes_periodo",
        ):
            self.assertIn(
                campo,
                resumo,
            )

        self.assertEqual(
            resumo["cameras_online"]
            + resumo["cameras_offline"],
            resumo["cameras_total"],
        )

    # ============================================================
    # PRESERVAÇÃO DO ESTADO / PERSISTÊNCIA
    # ============================================================

    def test_10_estado_sistema_real_permanece_inalterado(self):
        atual = self.estado_sistema.snapshot()

        self.assertEqual(
            atual,
            self.estado_original,
            "As chamadas HTTP alteraram o EstadoSistema real.",
        )

    def test_11_persistencia_real_permanece_inalterada(self):
        hashes_depois = self._hashes(
            self.arquivos_monitorados
        )

        self.assertEqual(
            self.hashes_antes,
            hashes_depois,
            (
                "As chamadas HTTP de integração alteraram "
                "arquivo persistente do projeto."
            ),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
