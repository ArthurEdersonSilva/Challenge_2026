from __future__ import annotations

import csv
import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import services.colaborador_service as colaborador_service


class TestConsultaDetalhesColaborador(unittest.TestCase):
    """
    Testes da etapa Consulta + Detalhes de Colaborador.

    Contratos esperados nesta etapa:

    consultar_colaboradores(
        busca=None,
        pagina=1,
        por_pagina=20,
    ) -> {
        "sucesso": bool,
        "erro": str | None,
        "total": int,
        "pagina": int,
        "por_pagina": int,
        "total_paginas": int,
        "colaboradores": list[dict],
    }

    obter_detalhes_colaborador(matricula) -> {
        "sucesso": bool,
        "erro": str | None,
        "colaborador": dict | None,
    }

    Campos mínimos de cada colaborador:
    - matricula
    - nome
    - cargo
    - setor
    - biometria_cadastrada

    Estes testes NÃO alteram os dados reais do projeto.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.raiz = self.temp_dir.name

        self.pasta_biometria = os.path.join(self.raiz, "banco_biometria")
        self.arquivo_csv = os.path.join(
            self.pasta_biometria,
            "dados_operadores.csv",
        )

        os.makedirs(self.pasta_biometria, exist_ok=True)

        with open(
            self.arquivo_csv,
            mode="w",
            encoding="utf-8",
            newline="",
        ) as arquivo:
            writer = csv.DictWriter(
                arquivo,
                fieldnames=["Matricula", "Nome", "Cargo"],
            )
            writer.writeheader()
            writer.writerows([
                {
                    "Matricula": "100001",
                    "Nome": "Arthur Silva",
                    "Cargo": "Operador",
                },
                {
                    "Matricula": "100002",
                    "Nome": "Beatriz Souza",
                    "Cargo": "Supervisora",
                },
                {
                    "Matricula": "200003",
                    "Nome": "Carlos Lima",
                    "Cargo": "Operador",
                },
            ])

        self._criar_biometria("100001")
        self._criar_biometria("100002")
        # 200003 fica propositalmente sem biometria.

        self.patch_csv = patch.object(
            colaborador_service,
            "ARQUIVO_CSV",
            self.arquivo_csv,
        )
        self.patch_biometria = patch.object(
            colaborador_service,
            "PASTA_BIOMETRIA",
            self.pasta_biometria,
        )

        self.patch_csv.start()
        self.patch_biometria.start()

    def tearDown(self):
        self.patch_biometria.stop()
        self.patch_csv.stop()
        self.temp_dir.cleanup()

    def _criar_biometria(self, matricula: str) -> str:
        caminho = os.path.join(
            self.pasta_biometria,
            f"{matricula}.jpg",
        )

        imagem = np.zeros((64, 64, 3), dtype=np.uint8)
        imagem[:, :] = (120, 120, 120)

        sucesso = cv2.imwrite(caminho, imagem)
        self.assertTrue(sucesso)

        return caminho

    @staticmethod
    def _hash_arquivo(caminho: str) -> str:
        sha = hashlib.sha256()
        with open(caminho, "rb") as arquivo:
            for bloco in iter(lambda: arquivo.read(8192), b""):
                sha.update(bloco)
        return sha.hexdigest()

    def _consultar(self, **kwargs):
        funcao = getattr(
            colaborador_service,
            "consultar_colaboradores",
            None,
        )
        self.assertIsNotNone(
            funcao,
            "Função consultar_colaboradores ainda não foi implementada.",
        )
        return funcao(**kwargs)

    def _detalhes(self, matricula: str):
        funcao = getattr(
            colaborador_service,
            "obter_detalhes_colaborador",
            None,
        )
        self.assertIsNotNone(
            funcao,
            "Função obter_detalhes_colaborador ainda não foi implementada.",
        )
        return funcao(matricula)

    def test_01_consulta_exibe_dados_essenciais(self):
        resultado = self._consultar()

        self.assertTrue(resultado["sucesso"])
        self.assertIsNone(resultado["erro"])
        self.assertEqual(resultado["total"], 3)

        colaboradores = resultado["colaboradores"]
        self.assertEqual(len(colaboradores), 3)

        por_matricula = {
            item["matricula"]: item
            for item in colaboradores
        }

        self.assertEqual(
            por_matricula["100001"],
            {
                "matricula": "100001",
                "nome": "Arthur Silva",
                "cargo": "Operador",
                "setor": None,
                "biometria_cadastrada": True,
            },
        )

        self.assertEqual(
            por_matricula["200003"],
            {
                "matricula": "200003",
                "nome": "Carlos Lima",
                "cargo": "Operador",
                "setor": None,
                "biometria_cadastrada": False,
            },
        )

    def test_02_busca_por_nome_sem_diferenciar_maiusculas(self):
        resultado = self._consultar(busca="beatriz")

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["total"], 1)
        self.assertEqual(
            resultado["colaboradores"][0]["matricula"],
            "100002",
        )

    def test_03_busca_por_matricula(self):
        resultado = self._consultar(busca="200003")

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["total"], 1)
        self.assertEqual(
            resultado["colaboradores"][0]["nome"],
            "Carlos Lima",
        )

    def test_04_busca_por_cargo(self):
        resultado = self._consultar(busca="Operador")

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["total"], 2)

        matriculas = {
            item["matricula"]
            for item in resultado["colaboradores"]
        }

        self.assertEqual(
            matriculas,
            {"100001", "200003"},
        )

    def test_05_busca_sem_resultado(self):
        resultado = self._consultar(busca="NAO_EXISTE")

        self.assertTrue(resultado["sucesso"])
        self.assertIsNone(resultado["erro"])
        self.assertEqual(resultado["total"], 0)
        self.assertEqual(resultado["colaboradores"], [])

    def test_06_detalhes_exibem_dados_corretos(self):
        resultado = self._detalhes("100001")

        self.assertTrue(resultado["sucesso"])
        self.assertIsNone(resultado["erro"])

        colaborador = resultado["colaborador"]

        self.assertEqual(colaborador["matricula"], "100001")
        self.assertEqual(colaborador["nome"], "Arthur Silva")
        self.assertEqual(colaborador["cargo"], "Operador")
        self.assertTrue(colaborador["biometria_cadastrada"])

    def test_07_detalhes_colaborador_inexistente(self):
        resultado = self._detalhes("999999")

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(
            resultado["erro"],
            "COLABORADOR_NAO_ENCONTRADO",
        )
        self.assertIsNone(resultado["colaborador"])

    def test_08_consulta_preserva_biometria(self):
        caminho = os.path.join(
            self.pasta_biometria,
            "100001.jpg",
        )

        hash_antes = self._hash_arquivo(caminho)
        tamanho_antes = os.path.getsize(caminho)

        resultado = self._consultar(busca="Arthur")

        self.assertTrue(resultado["sucesso"])
        self.assertTrue(os.path.isfile(caminho))

        hash_depois = self._hash_arquivo(caminho)
        tamanho_depois = os.path.getsize(caminho)

        self.assertEqual(hash_antes, hash_depois)
        self.assertEqual(tamanho_antes, tamanho_depois)

    def test_09_detalhes_preservam_biometria(self):
        caminho = os.path.join(
            self.pasta_biometria,
            "100002.jpg",
        )

        hash_antes = self._hash_arquivo(caminho)

        resultado = self._detalhes("100002")

        self.assertTrue(resultado["sucesso"])
        self.assertTrue(os.path.isfile(caminho))
        self.assertEqual(
            hash_antes,
            self._hash_arquivo(caminho),
        )

    def test_10_colaborador_sem_biometria_continua_sem_biometria(self):
        caminho = os.path.join(
            self.pasta_biometria,
            "200003.jpg",
        )

        self.assertFalse(os.path.exists(caminho))

        consulta = self._consultar(busca="200003")
        detalhes = self._detalhes("200003")

        self.assertTrue(consulta["sucesso"])
        self.assertTrue(detalhes["sucesso"])

        self.assertFalse(
            consulta["colaboradores"][0]["biometria_cadastrada"]
        )
        self.assertFalse(
            detalhes["colaborador"]["biometria_cadastrada"]
        )
        self.assertFalse(os.path.exists(caminho))


if __name__ == "__main__":
    unittest.main(verbosity=2)
