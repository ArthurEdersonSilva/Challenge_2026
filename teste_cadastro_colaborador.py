import csv
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import services.colaborador_service as service
from reconhecimento_facial import ReconhecedorFacial


class TestCadastroColaborador(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.csv_path = os.path.join(self.base, "dados_operadores.csv")
        self.bio_dir = os.path.join(self.base, "biometria")
        os.makedirs(self.bio_dir, exist_ok=True)

        service.ARQUIVO_CSV = self.csv_path
        service.PASTA_BIOMETRIA = self.bio_dir

        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["Matricula", "Nome", "Cargo"],
            )
            writer.writeheader()
            writer.writerow({
                "Matricula": "557079",
                "Nome": "Arthur",
                "Cargo": "Operador",
            })

        self.imagem = np.full((120, 120, 3), 127, dtype=np.uint8)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def validacao_ok():
        return SimpleNamespace(
            valida=True,
            quantidade_rostos=1,
            motivo="UM_ROSTO_UTILIZAVEL",
            confiancas=(0.99,),
        )

    @staticmethod
    def validacao_sem_rosto():
        return SimpleNamespace(
            valida=False,
            quantidade_rostos=0,
            motivo="ZERO_ROSTOS_UTILIZAVEIS",
            confiancas=(),
        )

    @staticmethod
    def validacao_multiplos():
        return SimpleNamespace(
            valida=False,
            quantidade_rostos=2,
            motivo="MULTIPLOS_ROSTOS_UTILIZAVEIS",
            confiancas=(0.99, 0.98),
        )

    def test_01_compatibilidade_cadastro_antigo(self):
        r = service.obter_colaborador("557079")
        self.assertTrue(r["sucesso"])
        self.assertEqual(r["colaborador"]["nome"], "Arthur")
        self.assertEqual(r["colaborador"]["cargo"], "Operador")

    @patch("services.colaborador_service.validar_imagem_biometrica")
    def test_02_cadastro_valido(self, mock_validar):
        mock_validar.return_value = self.validacao_ok()

        r = service.cadastrar_colaborador(
            "999001",
            "Teste Cadastro",
            "Operador",
            self.imagem,
        )

        self.assertTrue(r["sucesso"])
        self.assertEqual(r["colaborador"]["matricula"], "999001")
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.bio_dir, "999001.jpg")
            )
        )

        consulta = service.obter_colaborador("999001")
        self.assertTrue(consulta["sucesso"])

    @patch("services.colaborador_service.validar_imagem_biometrica")
    def test_03_matricula_duplicada(self, mock_validar):
        mock_validar.return_value = self.validacao_ok()

        r = service.cadastrar_colaborador(
            "557079",
            "Outro Nome",
            "Outro Cargo",
            self.imagem,
        )

        self.assertFalse(r["sucesso"])
        self.assertEqual(r["erro"], "MATRICULA_JA_CADASTRADA")

    def test_04_campos_obrigatorios(self):
        r1 = service.cadastrar_colaborador(
            "",
            "Nome",
            "Cargo",
            self.imagem,
        )
        self.assertEqual(r1["erro"], "MATRICULA_OBRIGATORIA")

        r2 = service.cadastrar_colaborador(
            "999002",
            "",
            "Cargo",
            self.imagem,
        )
        self.assertEqual(r2["erro"], "NOME_OBRIGATORIO")

        r3 = service.cadastrar_colaborador(
            "999002",
            "Nome",
            "",
            self.imagem,
        )
        self.assertEqual(r3["erro"], "CARGO_OBRIGATORIO")

        r4 = service.cadastrar_colaborador(
            "999002",
            "Nome",
            "Cargo",
            None,
        )
        self.assertEqual(r4["erro"], "IMAGEM_BIOMETRICA_OBRIGATORIA")

    @patch("services.colaborador_service.validar_imagem_biometrica")
    def test_05_sem_rosto(self, mock_validar):
        mock_validar.return_value = self.validacao_sem_rosto()

        r = service.cadastrar_colaborador(
            "999003",
            "Sem Rosto",
            "Operador",
            self.imagem,
        )

        self.assertFalse(r["sucesso"])
        self.assertEqual(r["erro"], "BIOMETRIA_INVALIDA")
        self.assertEqual(
            r["motivo_biometria"],
            "ZERO_ROSTOS_UTILIZAVEIS",
        )

    @patch("services.colaborador_service.validar_imagem_biometrica")
    def test_06_multiplos_rostos(self, mock_validar):
        mock_validar.return_value = self.validacao_multiplos()

        r = service.cadastrar_colaborador(
            "999004",
            "Multiplos",
            "Operador",
            self.imagem,
        )

        self.assertFalse(r["sucesso"])
        self.assertEqual(r["erro"], "BIOMETRIA_INVALIDA")
        self.assertEqual(
            r["motivo_biometria"],
            "MULTIPLOS_ROSTOS_UTILIZAVEIS",
        )

    @patch("services.colaborador_service.validar_imagem_biometrica")
    def test_07_status_biometria(self, mock_validar):
        mock_validar.return_value = self.validacao_ok()

        service.cadastrar_colaborador(
            "999005",
            "Status Bio",
            "Operador",
            self.imagem,
        )

        r = service.obter_status_biometria("999005")
        self.assertTrue(r["sucesso"])
        self.assertTrue(r["biometria_cadastrada"])

    @patch("services.colaborador_service.validar_imagem_biometrica")
    def test_08_atualizar_biometria(self, mock_validar):
        mock_validar.return_value = self.validacao_ok()

        service.cadastrar_colaborador(
            "999006",
            "Atualiza Bio",
            "Operador",
            self.imagem,
        )

        caminho = os.path.join(self.bio_dir, "999006.jpg")
        tamanho_antes = os.path.getsize(caminho)

        nova = np.full((160, 160, 3), 200, dtype=np.uint8)
        r = service.atualizar_biometria_colaborador(
            "999006",
            nova,
        )

        self.assertTrue(r["sucesso"])
        self.assertTrue(r["biometria_cadastrada"])
        self.assertNotEqual(
            os.path.getsize(caminho),
            tamanho_antes,
        )

    @patch("services.colaborador_service.validar_imagem_biometrica")
    def test_09_editar_nome_cargo_preserva_matricula_biometria(self, mock_validar):
        mock_validar.return_value = self.validacao_ok()

        service.cadastrar_colaborador(
            "999007",
            "Nome Antigo",
            "Cargo Antigo",
            self.imagem,
        )

        caminho = os.path.join(self.bio_dir, "999007.jpg")
        self.assertTrue(os.path.isfile(caminho))

        r = service.editar_colaborador(
            "999007",
            nome="Nome Novo",
            cargo="Cargo Novo",
        )

        self.assertTrue(r["sucesso"])
        self.assertEqual(r["colaborador"]["matricula"], "999007")
        self.assertEqual(r["colaborador"]["nome"], "Nome Novo")
        self.assertEqual(r["colaborador"]["cargo"], "Cargo Novo")
        self.assertTrue(os.path.isfile(caminho))

    @patch("services.colaborador_service.validar_imagem_biometrica")
    def test_10_falha_csv_nao_deixa_biometria_orfa(self, mock_validar):
        mock_validar.return_value = self.validacao_ok()

        replace_real = os.replace
        chamadas = {"n": 0}

        def replace_controlado(origem, destino):
            chamadas["n"] += 1
            if chamadas["n"] == 2:
                raise OSError("falha simulada no CSV")
            return replace_real(origem, destino)

        with patch(
            "services.colaborador_service.os.replace",
            side_effect=replace_controlado,
        ):
            r = service.cadastrar_colaborador(
                "999008",
                "Rollback",
                "Operador",
                self.imagem,
            )

        self.assertFalse(r["sucesso"])
        self.assertEqual(r["erro"], "ERRO_SALVAR_COLABORADOR")
        self.assertFalse(
            os.path.exists(
                os.path.join(self.bio_dir, "999008.jpg")
            )
        )
        self.assertEqual(
            service.obter_colaborador("999008")["erro"],
            "COLABORADOR_NAO_ENCONTRADO",
        )

    @patch("services.colaborador_service.validar_imagem_biometrica")
    def test_11_nova_imagem_entra_na_base_do_reconhecedor(self, mock_validar):
        mock_validar.return_value = self.validacao_ok()

        r = service.cadastrar_colaborador(
            "999009",
            "Base Facial",
            "Operador",
            self.imagem,
        )
        self.assertTrue(r["sucesso"])

        reconhecedor = ReconhecedorFacial(
            db_path=self.bio_dir,
        )

        vetor = np.ones(128, dtype=np.float32)
        vetor = vetor / np.linalg.norm(vetor)

        with patch.object(
            reconhecedor,
            "_representar",
            return_value=vetor,
        ):
            reconhecedor.atualizar_base_se_necessario()

        self.assertIn("999009", reconhecedor._embeddings)

    def test_12_matricula_invalida_para_arquivo(self):
        r = service.cadastrar_colaborador(
            "../teste",
            "Nome",
            "Cargo",
            self.imagem,
        )
        self.assertFalse(r["sucesso"])
        self.assertEqual(r["erro"], "MATRICULA_INVALIDA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
