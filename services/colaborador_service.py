from __future__ import annotations

import base64
import csv
import os
import tempfile
from typing import Any, Dict, List, Optional

import cv2

import config
from reconhecimento_facial import validar_imagem_biometrica


ARQUIVO_CSV = getattr(
    config,
    "PATH_DADOS_OPERADORES",
    os.path.join("banco_biometria", "dados_operadores.csv"),
)

PASTA_BIOMETRIA = getattr(
    config,
    "PATH_BANCO_BIOMETRIA",
    "banco_biometria",
)

CAMPOS_CSV = ("Matricula", "Nome", "Cargo", "Setor")


def _normalizar_matricula(matricula: Any) -> str:
    return str(matricula or "").strip()


def _normalizar_texto(valor: Any) -> str:
    return str(valor or "").strip()


def _matricula_valida_para_arquivo(matricula: str) -> bool:
    if not matricula or matricula in {".", ".."}:
        return False
    if os.path.basename(matricula) != matricula:
        return False
    if "/" in matricula or "\\" in matricula:
        return False
    return True


def _caminho_biometria(matricula: str) -> str:
    return os.path.join(PASTA_BIOMETRIA, f"{matricula}.jpg")


def _garantir_persistencia() -> None:
    os.makedirs(PASTA_BIOMETRIA, exist_ok=True)
    pasta_csv = os.path.dirname(os.path.abspath(ARQUIVO_CSV))
    os.makedirs(pasta_csv, exist_ok=True)


def _ler_linhas_csv() -> List[Dict[str, str]]:
    if not os.path.exists(ARQUIVO_CSV):
        return []

    linhas: List[Dict[str, str]] = []
    with open(ARQUIVO_CSV, mode="r", encoding="utf-8", newline="") as arquivo:
        reader = csv.DictReader(arquivo)
        for linha in reader:
            matricula = _normalizar_matricula(linha.get("Matricula"))
            if not matricula:
                continue
            linhas.append({
                "Matricula": matricula,
                "Nome": _normalizar_texto(linha.get("Nome")),
                "Cargo": _normalizar_texto(linha.get("Cargo")),
                # Compatibilidade legada: CSVs antigos não possuem a coluna Setor.
                "Setor": _normalizar_texto(linha.get("Setor")),
            })
    return linhas


def _criar_csv_temporario(linhas: List[Dict[str, str]]) -> str:
    _garantir_persistencia()
    pasta_csv = os.path.dirname(os.path.abspath(ARQUIVO_CSV))
    arquivo_temporario = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=".dados_operadores_",
        suffix=".csv",
        dir=pasta_csv,
        delete=False,
    )
    caminho_temporario = arquivo_temporario.name

    try:
        with arquivo_temporario:
            writer = csv.DictWriter(
                arquivo_temporario,
                fieldnames=list(CAMPOS_CSV),
            )
            writer.writeheader()
            for linha in linhas:
                writer.writerow({
                    "Matricula": _normalizar_matricula(linha.get("Matricula")),
                    "Nome": _normalizar_texto(linha.get("Nome")),
                    "Cargo": _normalizar_texto(linha.get("Cargo")),
                    "Setor": _normalizar_texto(linha.get("Setor")),
                })
            arquivo_temporario.flush()
            os.fsync(arquivo_temporario.fileno())
    except Exception:
        try:
            os.remove(caminho_temporario)
        except OSError:
            pass
        raise

    return caminho_temporario


def _criar_imagem_temporaria(matricula: str, imagem_biometrica) -> str:
    _garantir_persistencia()
    descritor, caminho_temporario = tempfile.mkstemp(
        prefix=f".{matricula}_",
        suffix=".jpg",
        dir=PASTA_BIOMETRIA,
    )
    os.close(descritor)

    try:
        sucesso = cv2.imwrite(caminho_temporario, imagem_biometrica)
        if not sucesso:
            raise OSError("cv2.imwrite retornou False.")
        if not os.path.exists(caminho_temporario) or os.path.getsize(caminho_temporario) <= 0:
            raise OSError("Arquivo biométrico temporário inválido.")
    except Exception:
        try:
            os.remove(caminho_temporario)
        except OSError:
            pass
        raise

    return caminho_temporario


def _remover_temporario(caminho: Optional[str]) -> None:
    if not caminho:
        return
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
    except OSError:
        pass


def listar_colaboradores() -> Dict[str, Any]:
    if not os.path.exists(ARQUIVO_CSV):
        return {
            "sucesso": True,
            "erro": None,
            "quantidade": 0,
            "colaboradores": [],
        }

    colaboradores: List[Dict[str, Any]] = []
    try:
        linhas = _ler_linhas_csv()
        for linha in linhas:
            matricula = linha["Matricula"]
            setor = _normalizar_texto(linha.get("Setor"))
            colaboradores.append({
                "matricula": matricula,
                "nome": linha["Nome"],
                "cargo": linha["Cargo"],
                "setor": setor or None,
                "biometria_cadastrada": os.path.isfile(
                    _caminho_biometria(matricula)
                ),
            })
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_LISTAR_COLABORADORES",
            "detalhe": str(erro),
            "quantidade": 0,
            "colaboradores": [],
        }

    colaboradores.sort(
        key=lambda item: (
            str(item.get("nome", "")).casefold(),
            str(item.get("matricula", "")).casefold(),
        )
    )

    return {
        "sucesso": True,
        "erro": None,
        "quantidade": len(colaboradores),
        "colaboradores": colaboradores,
    }


def obter_colaborador(matricula: str) -> Dict[str, Any]:
    matricula = _normalizar_matricula(matricula)

    if not matricula:
        return {
            "sucesso": False,
            "erro": "MATRICULA_OBRIGATORIA",
            "colaborador": None,
        }

    resultado = listar_colaboradores()

    if not resultado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": resultado.get("erro"),
            "detalhe": resultado.get("detalhe"),
            "colaborador": None,
        }

    for colaborador in resultado.get("colaboradores", []):
        if colaborador.get("matricula") == matricula:
            return {
                "sucesso": True,
                "erro": None,
                "colaborador": colaborador,
            }

    return {
        "sucesso": False,
        "erro": "COLABORADOR_NAO_ENCONTRADO",
        "matricula": matricula,
        "colaborador": None,
    }



def consultar_colaboradores(
    busca: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 20,
    setor: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Consulta colaboradores cadastrados com busca textual e paginação.

    A busca é case-insensitive e considera matrícula, nome, cargo e setor.
    O filtro de setor é opcional e case-insensitive, por igualdade.
    Esta função é somente-leitura e não altera CSV nem biometria.
    """
    try:
        pagina = int(pagina)
        por_pagina = int(por_pagina)
    except (TypeError, ValueError):
        return {
            "sucesso": False,
            "erro": "PAGINACAO_INVALIDA",
            "total": 0,
            "pagina": 1,
            "por_pagina": 20,
            "total_paginas": 0,
            "colaboradores": [],
        }

    if pagina < 1:
        return {
            "sucesso": False,
            "erro": "PAGINA_INVALIDA",
            "total": 0,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_paginas": 0,
            "colaboradores": [],
        }

    if por_pagina < 1:
        return {
            "sucesso": False,
            "erro": "POR_PAGINA_INVALIDO",
            "total": 0,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_paginas": 0,
            "colaboradores": [],
        }

    resultado = listar_colaboradores()

    if not resultado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": resultado.get("erro") or "ERRO_LISTAR_COLABORADORES",
            "detalhe": resultado.get("detalhe"),
            "total": 0,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_paginas": 0,
            "colaboradores": [],
        }

    colaboradores = list(resultado.get("colaboradores", []))
    termo = _normalizar_texto(busca).casefold()

    if termo:
        colaboradores = [
            colaborador
            for colaborador in colaboradores
            if (
                termo in str(colaborador.get("matricula", "")).casefold()
                or termo in str(colaborador.get("nome", "")).casefold()
                or termo in str(colaborador.get("cargo", "")).casefold()
                or termo in str(colaborador.get("setor") or "").casefold()
            )
        ]

    setor_normalizado = _normalizar_texto(setor).casefold()
    if setor_normalizado:
        colaboradores = [
            colaborador
            for colaborador in colaboradores
            if str(colaborador.get("setor") or "").casefold() == setor_normalizado
        ]

    total = len(colaboradores)
    total_paginas = (
        (total + por_pagina - 1) // por_pagina
        if total > 0
        else 0
    )

    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina

    return {
        "sucesso": True,
        "erro": None,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total_paginas": total_paginas,
        "colaboradores": colaboradores[inicio:fim],
    }


def obter_detalhes_colaborador(matricula: str) -> Dict[str, Any]:
    """
    Retorna matrícula, nome, cargo e status da biometria do colaborador.

    Esta função é somente-leitura e não modifica o arquivo biométrico.
    """
    resultado = obter_colaborador(matricula)

    if not resultado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": resultado.get("erro"),
            "detalhe": resultado.get("detalhe"),
            "colaborador": None,
        }

    return {
        "sucesso": True,
        "erro": None,
        "colaborador": dict(resultado["colaborador"]),
    }

def validar_captura_facial(imagem) -> Dict[str, Any]:
    if (
        imagem is None
        or getattr(imagem, "size", 0) == 0
        or not hasattr(imagem, "shape")
    ):
        return {
            "sucesso": False,
            "erro": "IMAGEM_INVALIDA",
            "captura_valida": False,
            "quantidade_rostos": 0,
            "motivo": "IMAGEM_INVALIDA",
            "confiancas": [],
        }

    try:
        validacao = validar_imagem_biometrica(
            imagem=imagem,
            detector_backend=getattr(
                config,
                "BIOMETRIA_DETECTOR_BACKEND",
                "opencv",
            ),
            confianca_minima=float(
                getattr(
                    config,
                    "BIOMETRIA_CONFIANCA_ROSTO_MINIMA",
                    0.80,
                )
            ),
            dimensao_minima=int(
                getattr(
                    config,
                    "BIOMETRIA_DIMENSAO_ROSTO_MINIMA",
                    48,
                )
            ),
        )
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_VALIDAR_BIOMETRIA",
            "detalhe": str(erro),
            "captura_valida": False,
            "quantidade_rostos": 0,
            "motivo": "ERRO_VALIDAR_BIOMETRIA",
            "confiancas": [],
        }

    motivo = str(getattr(validacao, "motivo", "") or "BIOMETRIA_INVALIDA")
    quantidade = int(getattr(validacao, "quantidade_rostos", 0) or 0)
    confiancas = [
        float(valor)
        for valor in (getattr(validacao, "confiancas", ()) or ())
    ]

    if bool(getattr(validacao, "valida", False)):
        return {
            "sucesso": True,
            "erro": None,
            "captura_valida": True,
            "quantidade_rostos": quantidade,
            "motivo": motivo,
            "confiancas": confiancas,
        }

    erros_conhecidos = {
        "DEEPFACE_INDISPONIVEL",
        "ROSTO_NAO_DETECTADO",
        "ZERO_ROSTOS_UTILIZAVEIS",
        "MULTIPLOS_ROSTOS_UTILIZAVEIS",
    }

    return {
        "sucesso": False,
        "erro": motivo if motivo in erros_conhecidos else "BIOMETRIA_INVALIDA",
        "captura_valida": False,
        "quantidade_rostos": quantidade,
        "motivo": motivo,
        "confiancas": confiancas,
    }


def cadastrar_colaborador(
    matricula: str,
    nome: str,
    cargo: str,
    imagem_biometrica,
    setor: Optional[str] = None,
) -> Dict[str, Any]:
    matricula = _normalizar_matricula(matricula)
    nome = _normalizar_texto(nome)
    cargo = _normalizar_texto(cargo)
    setor = _normalizar_texto(setor)

    if not matricula:
        return {"sucesso": False, "erro": "MATRICULA_OBRIGATORIA", "colaborador": None}

    if not _matricula_valida_para_arquivo(matricula):
        return {"sucesso": False, "erro": "MATRICULA_INVALIDA", "colaborador": None}

    if not nome:
        return {"sucesso": False, "erro": "NOME_OBRIGATORIO", "colaborador": None}

    if not cargo:
        return {"sucesso": False, "erro": "CARGO_OBRIGATORIO", "colaborador": None}

    if imagem_biometrica is None or getattr(imagem_biometrica, "size", 0) == 0:
        return {
            "sucesso": False,
            "erro": "IMAGEM_BIOMETRICA_OBRIGATORIA",
            "colaborador": None,
        }

    consulta = obter_colaborador(matricula)

    if consulta.get("sucesso"):
        return {
            "sucesso": False,
            "erro": "MATRICULA_JA_CADASTRADA",
            "matricula": matricula,
            "colaborador": consulta.get("colaborador"),
        }

    if consulta.get("erro") not in {"COLABORADOR_NAO_ENCONTRADO"}:
        return {
            "sucesso": False,
            "erro": consulta.get("erro") or "ERRO_LISTAR_COLABORADORES",
            "detalhe": consulta.get("detalhe"),
            "colaborador": None,
        }

    caminho_final_biometria = _caminho_biometria(matricula)

    if os.path.exists(caminho_final_biometria):
        return {
            "sucesso": False,
            "erro": "BIOMETRIA_JA_EXISTENTE",
            "matricula": matricula,
            "colaborador": None,
        }

    validacao = validar_captura_facial(imagem_biometrica)

    if not validacao.get("sucesso"):
        return {
            "sucesso": False,
            "erro": "BIOMETRIA_INVALIDA",
            "motivo_biometria": validacao.get("erro") or validacao.get("motivo"),
            "validacao_biometria": validacao,
            "colaborador": None,
        }

    caminho_imagem_temporaria = None
    caminho_csv_temporario = None
    imagem_promovida = False

    try:
        linhas = _ler_linhas_csv()

        for linha in linhas:
            if _normalizar_matricula(linha.get("Matricula")) == matricula:
                return {
                    "sucesso": False,
                    "erro": "MATRICULA_JA_CADASTRADA",
                    "matricula": matricula,
                    "colaborador": None,
                }

        linhas.append({
            "Matricula": matricula,
            "Nome": nome,
            "Cargo": cargo,
            "Setor": setor,
        })

        caminho_imagem_temporaria = _criar_imagem_temporaria(
            matricula,
            imagem_biometrica,
        )
        caminho_csv_temporario = _criar_csv_temporario(linhas)

        os.replace(caminho_imagem_temporaria, caminho_final_biometria)
        imagem_promovida = True
        caminho_imagem_temporaria = None

        os.replace(caminho_csv_temporario, ARQUIVO_CSV)
        caminho_csv_temporario = None

    except Exception as erro:
        _remover_temporario(caminho_imagem_temporaria)
        _remover_temporario(caminho_csv_temporario)

        if imagem_promovida:
            try:
                if os.path.exists(caminho_final_biometria):
                    os.remove(caminho_final_biometria)
            except OSError:
                pass

        return {
            "sucesso": False,
            "erro": (
                "ERRO_SALVAR_COLABORADOR"
                if imagem_promovida
                else "ERRO_SALVAR_BIOMETRIA"
            ),
            "detalhe": str(erro),
            "colaborador": None,
        }

    resultado = obter_colaborador(matricula)

    if not resultado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": "ERRO_CONFIRMAR_CADASTRO",
            "detalhe": resultado.get("erro"),
            "colaborador": None,
        }

    return {
        "sucesso": True,
        "erro": None,
        "colaborador": resultado["colaborador"],
    }


def obter_status_biometria(matricula: str) -> Dict[str, Any]:
    matricula = _normalizar_matricula(matricula)

    if not matricula:
        return {
            "sucesso": False,
            "erro": "MATRICULA_OBRIGATORIA",
            "matricula": None,
            "biometria_cadastrada": False,
        }

    colaborador = obter_colaborador(matricula)

    if not colaborador.get("sucesso"):
        return {
            "sucesso": False,
            "erro": colaborador.get("erro"),
            "matricula": matricula,
            "biometria_cadastrada": False,
        }

    return {
        "sucesso": True,
        "erro": None,
        "matricula": matricula,
        "biometria_cadastrada": os.path.isfile(_caminho_biometria(matricula)),
    }


def atualizar_biometria_colaborador(
    matricula: str,
    imagem_biometrica,
) -> Dict[str, Any]:
    matricula = _normalizar_matricula(matricula)

    if not matricula:
        return {
            "sucesso": False,
            "erro": "MATRICULA_OBRIGATORIA",
            "matricula": None,
            "biometria_cadastrada": False,
        }

    if not _matricula_valida_para_arquivo(matricula):
        return {
            "sucesso": False,
            "erro": "MATRICULA_INVALIDA",
            "matricula": matricula,
            "biometria_cadastrada": False,
        }

    colaborador = obter_colaborador(matricula)

    if not colaborador.get("sucesso"):
        return {
            "sucesso": False,
            "erro": colaborador.get("erro"),
            "matricula": matricula,
            "biometria_cadastrada": False,
        }

    if imagem_biometrica is None or getattr(imagem_biometrica, "size", 0) == 0:
        return {
            "sucesso": False,
            "erro": "IMAGEM_BIOMETRICA_OBRIGATORIA",
            "matricula": matricula,
            "biometria_cadastrada": False,
        }

    validacao = validar_captura_facial(imagem_biometrica)

    if not validacao.get("sucesso"):
        return {
            "sucesso": False,
            "erro": "BIOMETRIA_INVALIDA",
            "motivo_biometria": validacao.get("erro") or validacao.get("motivo"),
            "validacao_biometria": validacao,
            "matricula": matricula,
            "biometria_cadastrada": os.path.isfile(
                _caminho_biometria(matricula)
            ),
        }

    caminho_temporario = None
    caminho_final = _caminho_biometria(matricula)

    try:
        caminho_temporario = _criar_imagem_temporaria(
            matricula,
            imagem_biometrica,
        )
        os.replace(caminho_temporario, caminho_final)
        caminho_temporario = None
    except Exception as erro:
        _remover_temporario(caminho_temporario)
        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_BIOMETRIA",
            "detalhe": str(erro),
            "matricula": matricula,
            "biometria_cadastrada": os.path.isfile(caminho_final),
        }

    return {
        "sucesso": True,
        "erro": None,
        "matricula": matricula,
        "biometria_cadastrada": True,
    }


def editar_colaborador(
    matricula: str,
    nome: Optional[str] = None,
    cargo: Optional[str] = None,
    setor: Optional[str] = None,
) -> Dict[str, Any]:
    matricula = _normalizar_matricula(matricula)

    if not matricula:
        return {
            "sucesso": False,
            "erro": "MATRICULA_OBRIGATORIA",
            "colaborador": None,
        }

    atual = obter_colaborador(matricula)

    if not atual.get("sucesso"):
        return {
            "sucesso": False,
            "erro": atual.get("erro"),
            "colaborador": None,
        }

    nome_novo = None if nome is None else _normalizar_texto(nome)
    cargo_novo = None if cargo is None else _normalizar_texto(cargo)
    # Setor é opcional. String vazia remove o setor e volta a retornar null.
    setor_novo = None if setor is None else _normalizar_texto(setor)

    if nome is not None and not nome_novo:
        return {
            "sucesso": False,
            "erro": "NOME_INVALIDO",
            "colaborador": None,
        }

    if cargo is not None and not cargo_novo:
        return {
            "sucesso": False,
            "erro": "CARGO_INVALIDO",
            "colaborador": None,
        }

    if nome is None and cargo is None and setor is None:
        return {
            "sucesso": True,
            "erro": None,
            "colaborador": atual["colaborador"],
        }

    caminho_temporario = None

    try:
        linhas = _ler_linhas_csv()
        encontrou = False

        for linha in linhas:
            if _normalizar_matricula(linha.get("Matricula")) != matricula:
                continue

            encontrou = True

            if nome_novo is not None:
                linha["Nome"] = nome_novo

            if cargo_novo is not None:
                linha["Cargo"] = cargo_novo

            if setor_novo is not None or setor is not None:
                linha["Setor"] = setor_novo or ""

            break

        if not encontrou:
            return {
                "sucesso": False,
                "erro": "COLABORADOR_NAO_ENCONTRADO",
                "colaborador": None,
            }

        caminho_temporario = _criar_csv_temporario(linhas)
        os.replace(caminho_temporario, ARQUIVO_CSV)
        caminho_temporario = None

    except Exception as erro:
        _remover_temporario(caminho_temporario)
        return {
            "sucesso": False,
            "erro": "ERRO_ATUALIZAR_COLABORADOR",
            "detalhe": str(erro),
            "colaborador": None,
        }

    atualizado = obter_colaborador(matricula)

    if not atualizado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": "ERRO_CONFIRMAR_ATUALIZACAO",
            "detalhe": atualizado.get("erro"),
            "colaborador": None,
        }

    return {
        "sucesso": True,
        "erro": None,
        "colaborador": atualizado["colaborador"],
    }



def remover_colaborador(matricula: str) -> Dict[str, Any]:
    """
    Remove o cadastro do colaborador e sua biometria oficial.

    Regras:
    - não verifica vínculos com ambientes; essa proteção é feita pela camada
      HTTP, que já possui acesso ao ambiente_service sem criar dependência
      circular entre services;
    - não remove incidentes, evidências ou históricos externos;
    - a matrícula é imutável e usada apenas para localizar o cadastro;
    - se a remoção da biometria falhar após a troca do CSV, o CSV anterior é
      restaurado para evitar um estado parcial.
    """
    matricula = _normalizar_matricula(matricula)

    if not matricula:
        return {
            "sucesso": False,
            "erro": "MATRICULA_OBRIGATORIA",
            "matricula": None,
        }

    if not _matricula_valida_para_arquivo(matricula):
        return {
            "sucesso": False,
            "erro": "MATRICULA_INVALIDA",
            "matricula": matricula,
        }

    atual = obter_colaborador(matricula)
    if not atual.get("sucesso"):
        return {
            "sucesso": False,
            "erro": atual.get("erro") or "COLABORADOR_NAO_ENCONTRADO",
            "detalhe": atual.get("detalhe"),
            "matricula": matricula,
        }

    colaborador_removido = dict(atual.get("colaborador") or {})
    caminho_biometria = _caminho_biometria(matricula)
    biometria_existia = os.path.isfile(caminho_biometria)

    caminho_csv_novo = None
    caminho_csv_backup = None
    csv_substituido = False

    try:
        linhas = _ler_linhas_csv()
        linhas_restantes = [
            linha
            for linha in linhas
            if _normalizar_matricula(linha.get("Matricula")) != matricula
        ]

        if len(linhas_restantes) == len(linhas):
            return {
                "sucesso": False,
                "erro": "COLABORADOR_NAO_ENCONTRADO",
                "matricula": matricula,
            }

        # Mantém uma cópia transacional do estado anterior do CSV.
        caminho_csv_backup = _criar_csv_temporario(linhas)
        caminho_csv_novo = _criar_csv_temporario(linhas_restantes)

        os.replace(caminho_csv_novo, ARQUIVO_CSV)
        caminho_csv_novo = None
        csv_substituido = True

        if biometria_existia:
            os.remove(caminho_biometria)

    except Exception as erro:
        _remover_temporario(caminho_csv_novo)

        rollback_sucesso = True
        rollback_detalhe = None

        if csv_substituido and caminho_csv_backup:
            try:
                os.replace(caminho_csv_backup, ARQUIVO_CSV)
                caminho_csv_backup = None
            except Exception as erro_rollback:
                rollback_sucesso = False
                rollback_detalhe = str(erro_rollback)

        _remover_temporario(caminho_csv_backup)

        return {
            "sucesso": False,
            "erro": "ERRO_REMOVER_COLABORADOR",
            "detalhe": str(erro),
            "rollback_sucesso": rollback_sucesso,
            "rollback_detalhe": rollback_detalhe,
            "matricula": matricula,
        }

    _remover_temporario(caminho_csv_backup)

    return {
        "sucesso": True,
        "erro": None,
        "matricula": matricula,
        "colaborador_removido": colaborador_removido,
        "biometria_removida": biometria_existia,
        "historico_preservado": True,
    }

def obter_imagem_colaborador(matricula: str) -> Dict[str, Any]:
    """
    Retorna a imagem biométrica cadastrada do colaborador em Base64.

    Esta função é somente-leitura. Não altera CSV, biometria ou embeddings.
    """
    matricula = _normalizar_matricula(matricula)

    if not matricula:
        return {
            "sucesso": False,
            "erro": "MATRICULA_OBRIGATORIA",
            "matricula": None,
            "imagem_disponivel": False,
        }

    if not _matricula_valida_para_arquivo(matricula):
        return {
            "sucesso": False,
            "erro": "MATRICULA_INVALIDA",
            "matricula": matricula,
            "imagem_disponivel": False,
        }

    colaborador = obter_colaborador(matricula)
    if not colaborador.get("sucesso"):
        return {
            "sucesso": False,
            "erro": colaborador.get("erro") or "COLABORADOR_NAO_ENCONTRADO",
            "matricula": matricula,
            "imagem_disponivel": False,
        }

    caminho = _caminho_biometria(matricula)
    if not os.path.isfile(caminho):
        return {
            "sucesso": False,
            "erro": "IMAGEM_COLABORADOR_NAO_ENCONTRADA",
            "matricula": matricula,
            "imagem_disponivel": False,
        }

    try:
        with open(caminho, "rb") as arquivo:
            dados = arquivo.read()

        if not dados:
            return {
                "sucesso": False,
                "erro": "IMAGEM_COLABORADOR_NAO_ENCONTRADA",
                "matricula": matricula,
                "imagem_disponivel": False,
            }

        imagem = cv2.imread(caminho)
        altura = None
        largura = None
        if imagem is not None and getattr(imagem, "size", 0) > 0:
            altura, largura = imagem.shape[:2]

        return {
            "sucesso": True,
            "erro": None,
            "matricula": matricula,
            "mime_type": "image/jpeg",
            "largura": largura,
            "altura": altura,
            "imagem_disponivel": True,
            "imagem_base64": base64.b64encode(dados).decode("ascii"),
        }

    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_LER_IMAGEM_COLABORADOR",
            "detalhe": str(erro),
            "matricula": matricula,
            "imagem_disponivel": False,
        }
