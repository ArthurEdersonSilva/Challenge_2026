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

# Referências biométricas oficiais. A frontal mantém o nome legado
# <matricula>.jpg para não quebrar cadastros e integrações existentes.
BIOMETRIA_REFERENCIAS = ("frontal", "esquerda", "direita")
BIOMETRIA_SUFIXOS = {
    "frontal": "",
    "esquerda": "__esquerda",
    "direita": "__direita",
}


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


def _caminho_biometria(
    matricula: str,
    referencia: str = "frontal",
) -> str:
    referencia = str(referencia or "frontal").strip().lower()
    if referencia not in BIOMETRIA_SUFIXOS:
        raise ValueError("REFERENCIA_BIOMETRICA_INVALIDA")

    sufixo = BIOMETRIA_SUFIXOS[referencia]
    return os.path.join(PASTA_BIOMETRIA, f"{matricula}{sufixo}.jpg")


def _caminhos_biometria(matricula: str) -> Dict[str, str]:
    return {
        referencia: _caminho_biometria(matricula, referencia)
        for referencia in BIOMETRIA_REFERENCIAS
    }


def _status_referencias_biometricas(matricula: str) -> Dict[str, Any]:
    caminhos = _caminhos_biometria(matricula)
    capturas = {
        referencia: os.path.isfile(caminho)
        for referencia, caminho in caminhos.items()
    }
    quantidade = sum(1 for existe in capturas.values() if existe)

    return {
        "capturas": capturas,
        "quantidade_biometrias": quantidade,
        "biometria_cadastrada": bool(capturas["frontal"]),
        "biometria_multirreferencia": all(capturas.values()),
    }


def _normalizar_imagens_biometricas(
    imagem_biometrica=None,
    imagens_biometricas: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    imagens: Dict[str, Any] = {}

    if isinstance(imagens_biometricas, dict):
        for referencia in BIOMETRIA_REFERENCIAS:
            imagem = imagens_biometricas.get(referencia)
            if imagem is not None:
                imagens[referencia] = imagem

    # Compatibilidade total com o contrato antigo: imagem_biometrica é frontal.
    if imagem_biometrica is not None and "frontal" not in imagens:
        imagens["frontal"] = imagem_biometrica

    return imagens


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
            status_biometria = _status_referencias_biometricas(matricula)
            colaboradores.append({
                "matricula": matricula,
                "nome": linha["Nome"],
                "cargo": linha["Cargo"],
                "setor": setor or None,
                **status_biometria,
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

def validar_captura_facial(
    imagem,
    referencia: str = "frontal",
) -> Dict[str, Any]:
    """Valida uma captura biométrica sem alterar os thresholds do reconhecimento.

    O cadastro legado já aceitava a detecção facial com confiança mínima 0.0
    depois que um detector realmente localizava exatamente um rosto. Aqui
    preservamos essa regra e usamos fallback de detector apenas quando o
    OpenCV não consegue localizar o rosto, principalmente nas referências
    laterais.
    """
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
            "referencia": referencia,
        }

    referencia = str(referencia or "frontal").strip().lower()
    if referencia not in BIOMETRIA_REFERENCIAS:
        referencia = "frontal"

    detector_preferido = str(
        getattr(config, "BIOMETRIA_DETECTOR_BACKEND", "opencv") or "opencv"
    ).strip().lower()

    # Primeiro tenta o detector configurado. Para fotos laterais, usa SSD
    # como fallback leve e RetinaFace somente como último recurso.
    backends = [detector_preferido]
    if referencia in {"esquerda", "direita"}:
        backends.extend(["ssd", "retinaface"])
    else:
        backends.append("ssd")

    backends_unicos = []
    for backend in backends:
        if backend and backend not in backends_unicos:
            backends_unicos.append(backend)

    dimensao_minima = int(
        getattr(config, "BIOMETRIA_DIMENSAO_ROSTO_MINIMA", 48)
    )

    tentativas = []
    ultimo_resultado = None

    for backend in backends_unicos:
        try:
            validacao = validar_imagem_biometrica(
                imagem=imagem,
                detector_backend=backend,
                # Regra do cadastro legado: depois de um detector achar
                # exatamente um rosto, não bloquear por score arbitrário.
                confianca_minima=0.0,
                dimensao_minima=dimensao_minima,
            )
        except Exception as erro:
            tentativas.append({
                "detector": backend,
                "motivo": "ERRO_VALIDAR_BIOMETRIA",
                "detalhe": str(erro),
            })
            continue

        motivo = str(getattr(validacao, "motivo", "") or "BIOMETRIA_INVALIDA")
        quantidade = int(getattr(validacao, "quantidade_rostos", 0) or 0)
        confiancas = [
            float(valor)
            for valor in (getattr(validacao, "confiancas", ()) or ())
        ]

        ultimo_resultado = {
            "sucesso": bool(getattr(validacao, "valida", False)),
            "erro": None,
            "captura_valida": bool(getattr(validacao, "valida", False)),
            "quantidade_rostos": quantidade,
            "motivo": motivo,
            "confiancas": confiancas,
            "detector_backend": backend,
            "referencia": referencia,
        }

        tentativas.append({
            "detector": backend,
            "motivo": motivo,
            "quantidade_rostos": quantidade,
        })

        if ultimo_resultado["sucesso"]:
            ultimo_resultado["tentativas"] = tentativas
            return ultimo_resultado

        # Se algum detector realmente encontrou mais de um rosto, não
        # tentamos contornar isso com outro detector. A captura deve ser refeita.
        if motivo == "MULTIPLOS_ROSTOS_UTILIZAVEIS":
            ultimo_resultado["erro"] = motivo
            ultimo_resultado["tentativas"] = tentativas
            return ultimo_resultado

    if ultimo_resultado is not None:
        motivo = ultimo_resultado.get("motivo") or "BIOMETRIA_INVALIDA"
        erros_conhecidos = {
            "DEEPFACE_INDISPONIVEL",
            "ROSTO_NAO_DETECTADO",
            "ZERO_ROSTOS_UTILIZAVEIS",
            "MULTIPLOS_ROSTOS_UTILIZAVEIS",
        }
        ultimo_resultado["erro"] = (
            motivo if motivo in erros_conhecidos else "BIOMETRIA_INVALIDA"
        )
        ultimo_resultado["tentativas"] = tentativas
        return ultimo_resultado

    return {
        "sucesso": False,
        "erro": "ERRO_VALIDAR_BIOMETRIA",
        "captura_valida": False,
        "quantidade_rostos": 0,
        "motivo": "ERRO_VALIDAR_BIOMETRIA",
        "confiancas": [],
        "referencia": referencia,
        "tentativas": tentativas,
    }


def cadastrar_colaborador(
    matricula: str,
    nome: str,
    cargo: str,
    imagem_biometrica=None,
    setor: Optional[str] = None,
    imagens_biometricas: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Cadastra colaborador com uma ou três referências biométricas.

    Compatibilidade:
    - fluxo legado: imagem_biometrica -> salva somente <matricula>.jpg;
    - fluxo novo: imagens_biometricas com frontal/esquerda/direita -> salva
      as três referências, todas associadas à mesma matrícula pelo
      reconhecimento_facial.py.

    Se uma referência lateral for enviada, as duas laterais passam a ser
    obrigatórias para evitar cadastro multirreferência incompleto.
    """
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

    imagens = _normalizar_imagens_biometricas(
        imagem_biometrica=imagem_biometrica,
        imagens_biometricas=imagens_biometricas,
    )

    frontal = imagens.get("frontal")
    if frontal is None or getattr(frontal, "size", 0) == 0:
        return {
            "sucesso": False,
            "erro": "IMAGEM_BIOMETRICA_OBRIGATORIA",
            "referencia": "frontal",
            "colaborador": None,
        }

    possui_esquerda = (
        imagens.get("esquerda") is not None
        and getattr(imagens.get("esquerda"), "size", 0) > 0
    )
    possui_direita = (
        imagens.get("direita") is not None
        and getattr(imagens.get("direita"), "size", 0) > 0
    )

    if possui_esquerda != possui_direita:
        return {
            "sucesso": False,
            "erro": "CAPTURAS_BIOMETRICAS_INCOMPLETAS",
            "capturas_necessarias": list(BIOMETRIA_REFERENCIAS),
            "colaborador": None,
        }

    referencias_salvar = (
        list(BIOMETRIA_REFERENCIAS)
        if possui_esquerda and possui_direita
        else ["frontal"]
    )

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

    caminhos_finais = {
        referencia: _caminho_biometria(matricula, referencia)
        for referencia in referencias_salvar
    }

    existentes = [
        referencia
        for referencia, caminho in caminhos_finais.items()
        if os.path.exists(caminho)
    ]
    if existentes:
        return {
            "sucesso": False,
            "erro": "BIOMETRIA_JA_EXISTENTE",
            "matricula": matricula,
            "referencias_existentes": existentes,
            "colaborador": None,
        }

    validacoes: Dict[str, Dict[str, Any]] = {}
    for referencia in referencias_salvar:
        imagem = imagens.get(referencia)
        if imagem is None or getattr(imagem, "size", 0) == 0:
            return {
                "sucesso": False,
                "erro": "CAPTURA_BIOMETRICA_AUSENTE",
                "referencia": referencia,
                "colaborador": None,
            }

        validacao = validar_captura_facial(
            imagem,
            referencia=referencia,
        )
        validacoes[referencia] = validacao

        if not validacao.get("sucesso"):
            return {
                "sucesso": False,
                "erro": "BIOMETRIA_INVALIDA",
                "referencia": referencia,
                "motivo_biometria": validacao.get("erro") or validacao.get("motivo"),
                "validacao_biometria": validacao,
                "validacoes_biometricas": validacoes,
                "colaborador": None,
            }

    caminhos_temporarios: Dict[str, str] = {}
    caminhos_promovidos: List[str] = []
    caminho_csv_temporario = None

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

        # Primeiro prepara todos os arquivos temporários. Nada oficial é
        # alterado até todas as imagens e o CSV estarem prontos.
        for referencia in referencias_salvar:
            caminhos_temporarios[referencia] = _criar_imagem_temporaria(
                f"{matricula}_{referencia}",
                imagens[referencia],
            )

        caminho_csv_temporario = _criar_csv_temporario(linhas)

        # Promove as referências biométricas e, por último, o CSV.
        for referencia in referencias_salvar:
            temporario = caminhos_temporarios.pop(referencia)
            final = caminhos_finais[referencia]
            os.replace(temporario, final)
            caminhos_promovidos.append(final)

        os.replace(caminho_csv_temporario, ARQUIVO_CSV)
        caminho_csv_temporario = None

    except Exception as erro:
        for temporario in caminhos_temporarios.values():
            _remover_temporario(temporario)
        _remover_temporario(caminho_csv_temporario)

        for caminho in caminhos_promovidos:
            try:
                if os.path.exists(caminho):
                    os.remove(caminho)
            except OSError:
                pass

        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_COLABORADOR",
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
        "referencias_biometricas": referencias_salvar,
        "validacoes_biometricas": validacoes,
    }


def obter_status_biometria(matricula: str) -> Dict[str, Any]:
    matricula = _normalizar_matricula(matricula)

    if not matricula:
        return {
            "sucesso": False,
            "erro": "MATRICULA_OBRIGATORIA",
            "matricula": None,
            "biometria_cadastrada": False,
            "quantidade_biometrias": 0,
            "biometria_multirreferencia": False,
            "capturas": {},
        }

    colaborador = obter_colaborador(matricula)

    if not colaborador.get("sucesso"):
        return {
            "sucesso": False,
            "erro": colaborador.get("erro"),
            "matricula": matricula,
            "biometria_cadastrada": False,
            "quantidade_biometrias": 0,
            "biometria_multirreferencia": False,
            "capturas": {},
        }

    status = _status_referencias_biometricas(matricula)

    return {
        "sucesso": True,
        "erro": None,
        "matricula": matricula,
        **status,
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

    status = _status_referencias_biometricas(matricula)

    return {
        "sucesso": True,
        "erro": None,
        "matricula": matricula,
        **status,
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
    """Remove o colaborador e todas as referências biométricas da matrícula."""
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
    caminhos_biometria = _caminhos_biometria(matricula)
    existentes = {
        referencia: caminho
        for referencia, caminho in caminhos_biometria.items()
        if os.path.isfile(caminho)
    }

    caminho_csv_novo = None
    caminho_csv_backup = None
    csv_substituido = False
    backups_biometria: Dict[str, tuple[str, str]] = {}

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

        caminho_csv_backup = _criar_csv_temporario(linhas)
        caminho_csv_novo = _criar_csv_temporario(linhas_restantes)

        # Retira as biometrias oficiais do caminho reconhecido sem apagá-las
        # ainda. Isso permite rollback completo se o CSV falhar.
        for referencia, caminho_original in existentes.items():
            descritor, caminho_backup = tempfile.mkstemp(
                prefix=f".{matricula}_{referencia}_remocao_",
                suffix=".jpg.bak",
                dir=PASTA_BIOMETRIA,
            )
            os.close(descritor)
            os.remove(caminho_backup)
            os.replace(caminho_original, caminho_backup)
            backups_biometria[referencia] = (caminho_original, caminho_backup)

        os.replace(caminho_csv_novo, ARQUIVO_CSV)
        caminho_csv_novo = None
        csv_substituido = True

        # Commit: CSV novo já está ativo; agora os backups biométricos podem
        # ser apagados definitivamente.
        for _, caminho_backup in backups_biometria.values():
            if os.path.exists(caminho_backup):
                os.remove(caminho_backup)
        backups_biometria.clear()

    except Exception as erro:
        _remover_temporario(caminho_csv_novo)

        rollback_sucesso = True
        detalhes_rollback = []

        for caminho_original, caminho_backup in backups_biometria.values():
            try:
                if os.path.exists(caminho_backup):
                    os.replace(caminho_backup, caminho_original)
            except Exception as erro_rollback:
                rollback_sucesso = False
                detalhes_rollback.append(str(erro_rollback))

        if csv_substituido and caminho_csv_backup:
            try:
                os.replace(caminho_csv_backup, ARQUIVO_CSV)
                caminho_csv_backup = None
            except Exception as erro_rollback:
                rollback_sucesso = False
                detalhes_rollback.append(str(erro_rollback))

        _remover_temporario(caminho_csv_backup)

        return {
            "sucesso": False,
            "erro": "ERRO_REMOVER_COLABORADOR",
            "detalhe": str(erro),
            "rollback_sucesso": rollback_sucesso,
            "rollback_detalhe": "; ".join(detalhes_rollback) or None,
            "matricula": matricula,
        }

    _remover_temporario(caminho_csv_backup)

    return {
        "sucesso": True,
        "erro": None,
        "matricula": matricula,
        "colaborador_removido": colaborador_removido,
        "biometria_removida": bool(existentes),
        "quantidade_biometrias_removidas": len(existentes),
        "referencias_biometricas_removidas": list(existentes.keys()),
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
            "referencia": "frontal",
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
