from __future__ import annotations

import csv
import os
import tempfile
import unittest
from unittest.mock import patch

import api_sistema
import services.colaborador_service as service


class TestRemocaoColaboradorService(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.bio_dir = os.path.join(self.base, "banco_biometria")
        self.csv_path = os.path.join(self.bio_dir, "dados_operadores.csv")
        os.makedirs(self.bio_dir, exist_ok=True)

        self.patch_csv = patch.object(service, "ARQUIVO_CSV", self.csv_path)
        self.patch_bio = patch.object(service, "PASTA_BIOMETRIA", self.bio_dir)
        self.patch_csv.start()
        self.patch_bio.start()

        with open(self.csv_path, "w", encoding="utf-8", newline="") as arquivo:
            writer = csv.DictWriter(
                arquivo,
                fieldnames=["Matricula", "Nome", "Cargo", "Setor"],
            )
            writer.writeheader()
            writer.writerow({
                "Matricula": "557079",
                "Nome": "Arthur",
                "Cargo": "Operador",
                "Setor": "Produção",
            })
            writer.writerow({
                "Matricula": "900001",
                "Nome": "Sem Foto",
                "Cargo": "Operador",
                "Setor": "Qualidade",
            })

        self.bio_path = os.path.join(self.bio_dir, "557079.jpg")
        with open(self.bio_path, "wb") as arquivo:
            arquivo.write(b"JPEG_TESTE")

    def tearDown(self):
        self.patch_bio.stop()
        self.patch_csv.stop()
        self.tmp.cleanup()

    def _matriculas_csv(self):
        with open(self.csv_path, "r", encoding="utf-8", newline="") as arquivo:
            return [linha["Matricula"] for linha in csv.DictReader(arquivo)]

    def test_01_remove_csv_e_biometria(self):
        resultado = service.remover_colaborador("557079")

        self.assertTrue(resultado["sucesso"], resultado)
        self.assertTrue(resultado["biometria_removida"])
        self.assertTrue(resultado["historico_preservado"])
        self.assertNotIn("557079", self._matriculas_csv())
        self.assertFalse(os.path.exists(self.bio_path))
        self.assertIn("900001", self._matriculas_csv())

    def test_02_remove_sem_biometria_tambem_funciona(self):
        resultado = service.remover_colaborador("900001")

        self.assertTrue(resultado["sucesso"], resultado)
        self.assertFalse(resultado["biometria_removida"])
        self.assertNotIn("900001", self._matriculas_csv())
        self.assertIn("557079", self._matriculas_csv())
        self.assertTrue(os.path.isfile(self.bio_path))

    def test_03_colaborador_inexistente_nao_altera_persistencia(self):
        antes = self._matriculas_csv()
        resultado = service.remover_colaborador("NAO_EXISTE")

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(resultado["erro"], "COLABORADOR_NAO_ENCONTRADO")
        self.assertEqual(antes, self._matriculas_csv())
        self.assertTrue(os.path.isfile(self.bio_path))

    def test_04_falha_ao_remover_biometria_restaura_csv(self):
        remover_real = os.remove
        bio_abs = os.path.abspath(self.bio_path)

        def remover_com_falha(caminho):
            if os.path.abspath(str(caminho)) == bio_abs:
                raise PermissionError("falha simulada ao remover biometria")
            return remover_real(caminho)

        with patch.object(service.os, "remove", side_effect=remover_com_falha):
            resultado = service.remover_colaborador("557079")

        self.assertFalse(resultado["sucesso"], resultado)
        self.assertEqual(resultado["erro"], "ERRO_REMOVER_COLABORADOR")
        self.assertTrue(resultado["rollback_sucesso"], resultado)
        self.assertIn("557079", self._matriculas_csv())
        self.assertTrue(os.path.isfile(self.bio_path))


class TestRemocaoColaboradorHTTP(unittest.TestCase):
    def setUp(self):
        api_sistema.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
        self.client = api_sistema.app.test_client()
        self.headers = {"X-Perfil": "GERENCIAL"}

    @staticmethod
    def _detalhe_ok(matricula="557079"):
        return {
            "sucesso": True,
            "erro": None,
            "colaborador": {
                "matricula": matricula,
                "nome": "Arthur",
                "cargo": "Operador",
                "setor": "Produção",
            },
        }

    @staticmethod
    def _ambientes(ambientes):
        return {
            "sucesso": True,
            "erro": None,
            "ambientes": ambientes,
            "paginacao": {
                "pagina": 1,
                "por_pagina": 100,
                "total_itens": len(ambientes),
                "total_paginas": 1 if ambientes else 0,
            },
        }

    def test_05_operador_bloqueado_403(self):
        resposta = self.client.delete(
            "/api/colaboradores/557079",
            headers={"X-Perfil": "OPERADOR", "X-Matricula": "557079"},
        )

        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(resposta.get_json()["erro"], "ACESSO_NEGADO")

    def test_06_colaborador_inexistente_404(self):
        with patch.object(
            api_sistema,
            "obter_detalhes_colaborador",
            return_value={
                "sucesso": False,
                "erro": "COLABORADOR_NAO_ENCONTRADO",
                "colaborador": None,
            },
        ):
            resposta = self.client.delete(
                "/api/colaboradores/NAO_EXISTE",
                headers=self.headers,
            )

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.get_json()["erro"], "COLABORADOR_NAO_ENCONTRADO")

    def test_07_colaborador_vinculado_retorna_409_e_nao_remove(self):
        with (
            patch.object(api_sistema, "obter_detalhes_colaborador", return_value=self._detalhe_ok()),
            patch.object(
                api_sistema,
                "listar_ambientes_consulta",
                return_value=self._ambientes([
                    {"ambiente_id": "AMB-1", "nome": "Produção 01"}
                ]),
            ),
            patch.object(
                api_sistema,
                "obter_colaboradores_vinculados",
                return_value={
                    "sucesso": True,
                    "erro": None,
                    "ambiente_id": "AMB-1",
                    "colaboradores": [
                        {"matricula": "557079", "nome": "Arthur"}
                    ],
                    "quantidade": 1,
                    "matriculas_ausentes": [],
                },
            ),
            patch.object(api_sistema, "remover_colaborador") as mock_remover,
        ):
            resposta = self.client.delete(
                "/api/colaboradores/557079",
                headers=self.headers,
            )

        self.assertEqual(resposta.status_code, 409)
        dados = resposta.get_json()
        self.assertEqual(dados["erro"], "COLABORADOR_POSSUI_VINCULOS")
        self.assertEqual(dados["quantidade_vinculos"], 1)
        self.assertEqual(dados["vinculos"][0]["ambiente_id"], "AMB-1")
        mock_remover.assert_not_called()

    def test_08_sem_vinculo_remove_200(self):
        retorno_remocao = {
            "sucesso": True,
            "erro": None,
            "matricula": "557079",
            "colaborador_removido": self._detalhe_ok()["colaborador"],
            "biometria_removida": True,
            "historico_preservado": True,
        }

        with (
            patch.object(api_sistema, "obter_detalhes_colaborador", return_value=self._detalhe_ok()),
            patch.object(
                api_sistema,
                "listar_ambientes_consulta",
                return_value=self._ambientes([
                    {"ambiente_id": "AMB-1", "nome": "Produção 01"}
                ]),
            ),
            patch.object(
                api_sistema,
                "obter_colaboradores_vinculados",
                return_value={
                    "sucesso": True,
                    "erro": None,
                    "ambiente_id": "AMB-1",
                    "colaboradores": [],
                    "quantidade": 0,
                    "matriculas_ausentes": [],
                },
            ),
            patch.object(api_sistema, "remover_colaborador", return_value=retorno_remocao) as mock_remover,
        ):
            resposta = self.client.delete(
                "/api/colaboradores/557079",
                headers=self.headers,
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.get_json()["sucesso"])
        mock_remover.assert_called_once_with("557079")

    def test_09_falha_ao_verificar_vinculos_retorna_500_e_nao_remove(self):
        with (
            patch.object(api_sistema, "obter_detalhes_colaborador", return_value=self._detalhe_ok()),
            patch.object(
                api_sistema,
                "listar_ambientes_consulta",
                return_value={
                    "sucesso": False,
                    "erro": "ERRO_LISTAR_AMBIENTES",
                    "ambientes": [],
                },
            ),
            patch.object(api_sistema, "remover_colaborador") as mock_remover,
        ):
            resposta = self.client.delete(
                "/api/colaboradores/557079",
                headers=self.headers,
            )

        self.assertEqual(resposta.status_code, 500)
        self.assertEqual(
            resposta.get_json()["erro"],
            "ERRO_VERIFICAR_VINCULOS_COLABORADOR",
        )
        mock_remover.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
