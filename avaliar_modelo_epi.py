from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

from metricas_deteccao import (
    CLASSES_BEST_PT,
    Caixa,
    auditar_deteccoes,
)
from relatorio_avaliacao_epi import (
    MOTIVO_SEM_GT,
    STATUS_NAO_EXECUTADA,
    resultado_nao_executado,
    salvar_relatorios_avaliacao_real,
)

EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class DatasetInvalidoError(ValueError):
    pass


def _normalizar_names(names: Any) -> List[str]:
    if isinstance(names, list):
        return [str(x) for x in names]
    if isinstance(names, dict):
        try:
            return [str(names[i]) for i in range(len(names))]
        except (KeyError, TypeError):
            raise DatasetInvalidoError("names do data.yaml deve usar índices contínuos 0..N-1.")
    raise DatasetInvalidoError("Campo names ausente ou inválido no data.yaml.")


def validar_data_yaml(caminho_data: str) -> Dict[str, Any]:
    path = Path(caminho_data).expanduser().resolve()
    if not path.is_file():
        raise DatasetInvalidoError("GROUND TRUTH NÃO DISPONÍVEL")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise DatasetInvalidoError(f"data.yaml inválido: {exc}") from exc

    names = _normalizar_names(data.get("names"))
    if tuple(names) != CLASSES_BEST_PT:
        raise DatasetInvalidoError("As classes do dataset divergem do contrato exato de 20 classes do best.pt.")
    test_ref = data.get("test")
    if not test_ref:
        raise DatasetInvalidoError("Campo test ausente no data.yaml; ground truth de teste não disponível.")

    base = path.parent
    root = Path(data.get("path", "."))
    if not root.is_absolute():
        root = (base / root).resolve()
    test_path = Path(test_ref)
    if not test_path.is_absolute():
        test_path = (root / test_path).resolve()
    if not test_path.exists():
        raise DatasetInvalidoError("Diretório/lista de teste não existe; ground truth não disponível.")

    return {"path_data": path, "root": root, "test_path": test_path, "yaml": data}


def _listar_imagens(test_path: Path) -> List[Path]:
    if test_path.is_dir():
        return sorted(p for p in test_path.rglob("*") if p.suffix.lower() in EXTENSOES_IMAGEM)
    if test_path.is_file():
        base = test_path.parent
        imagens = []
        for linha in test_path.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha:
                continue
            p = Path(linha)
            if not p.is_absolute():
                p = (base / p).resolve()
            imagens.append(p)
        return imagens
    return []


def _caminho_label_para_imagem(imagem: Path) -> Path:
    partes = list(imagem.parts)
    for i in range(len(partes) - 1, -1, -1):
        if partes[i] == "images":
            partes[i] = "labels"
            return Path(*partes).with_suffix(".txt")
    return imagem.with_suffix(".txt")


def _ler_dimensoes_imagem(path: Path) -> Tuple[int, int]:
    try:
        from PIL import Image
    except Exception as exc:
        raise DatasetInvalidoError("Pillow é necessário para validar labels YOLO offline.") from exc
    with Image.open(path) as img:
        return int(img.width), int(img.height)


def ler_ground_truth_yolo(imagem: Path, classes: Sequence[str] = CLASSES_BEST_PT) -> List[Caixa]:
    if not imagem.is_file():
        raise DatasetInvalidoError(f"Imagem de teste inexistente: {imagem}")
    label = _caminho_label_para_imagem(imagem)
    if not label.exists():
        return []  # imagem negativa válida
    texto = label.read_text(encoding="utf-8").strip()
    if not texto:
        return []
    largura, altura = _ler_dimensoes_imagem(imagem)
    caixas: List[Caixa] = []
    for numero_linha, linha in enumerate(texto.splitlines(), 1):
        partes = linha.split()
        if len(partes) != 5:
            raise DatasetInvalidoError(f"Label malformada em {label}:{numero_linha}")
        try:
            cid = int(partes[0])
            xc, yc, w, h = map(float, partes[1:])
        except ValueError as exc:
            raise DatasetInvalidoError(f"Label malformada em {label}:{numero_linha}") from exc
        if not 0 <= cid < len(classes):
            raise DatasetInvalidoError(f"Classe inválida {cid} em {label}:{numero_linha}")
        if not all(0.0 <= v <= 1.0 for v in (xc, yc, w, h)) or w <= 0 or h <= 0:
            raise DatasetInvalidoError(f"Coordenadas YOLO inválidas em {label}:{numero_linha}")
        x1 = (xc - w / 2.0) * largura
        y1 = (yc - h / 2.0) * altura
        x2 = (xc + w / 2.0) * largura
        y2 = (yc + h / 2.0) * altura
        caixas.append(Caixa(cid, (x1, y1, x2, y2)))
    return caixas


def validar_ground_truth(caminho_data: str) -> Dict[str, Any]:
    info = validar_data_yaml(caminho_data)
    imagens = _listar_imagens(info["test_path"])
    if not imagens:
        raise DatasetInvalidoError("Conjunto test não contém imagens; ground truth não disponível.")
    gts = [ler_ground_truth_yolo(imagem) for imagem in imagens]
    total_gt = sum(len(x) for x in gts)
    if total_gt == 0:
        raise DatasetInvalidoError("Conjunto test não contém nenhuma anotação de ground truth.")
    info["imagens"] = imagens
    info["ground_truth"] = gts
    info["total_gt"] = total_gt
    return info


def _nomes_modelo(modelo: Any) -> Tuple[str, ...]:
    names = getattr(modelo, "names", None)
    if isinstance(names, dict):
        return tuple(str(names[i]) for i in range(len(names)))
    if isinstance(names, list):
        return tuple(str(x) for x in names)
    return ()


def _extrair_metricas_ultralytics(resultado_val: Any) -> Dict[str, Any]:
    box = getattr(resultado_val, "box", None)
    if box is None:
        raise RuntimeError("Ultralytics não retornou métricas de detecção box.")
    ap50 = list(getattr(box, "ap50", []) or [])
    precision = list(getattr(box, "p", []) or [])
    recall = list(getattr(box, "r", []) or [])
    class_ids = list(getattr(box, "ap_class_index", []) or [])
    map50 = getattr(box, "map50", None)
    por_id: Dict[int, Dict[str, Optional[float]]] = {}
    for pos, cid_raw in enumerate(class_ids):
        cid = int(cid_raw)
        por_id[cid] = {
            "ap50": float(ap50[pos]) if pos < len(ap50) else None,
            "precision_ultralytics": float(precision[pos]) if pos < len(precision) else None,
            "recall_ultralytics": float(recall[pos]) if pos < len(recall) else None,
        }
    saida: Dict[str, Any] = {"map50": float(map50) if map50 is not None else None, "por_classe": {}}
    for cid, nome in enumerate(CLASSES_BEST_PT):
        valores = por_id.get(cid, {})
        saida["por_classe"][str(cid)] = {
            "classe_id": cid,
            "classe": nome,
            "ap50": valores.get("ap50"),
            "precision_ultralytics": valores.get("precision_ultralytics"),
            "recall_ultralytics": valores.get("recall_ultralytics"),
        }
    return saida


def _predizer_para_auditoria(modelo: Any, imagens: Sequence[Path], conf_auditoria: float) -> List[List[Caixa]]:
    todas: List[List[Caixa]] = []
    for imagem in imagens:
        resultados = modelo.predict(source=str(imagem), conf=conf_auditoria, verbose=False)
        caixas_imagem: List[Caixa] = []
        if resultados:
            boxes = getattr(resultados[0], "boxes", None)
            if boxes is not None:
                xyxy = boxes.xyxy.cpu().tolist()
                cls = boxes.cls.cpu().tolist()
                conf = boxes.conf.cpu().tolist()
                for coords, cid, score in zip(xyxy, cls, conf):
                    caixas_imagem.append(Caixa(int(cid), tuple(map(float, coords)), float(score)))
        todas.append(caixas_imagem)
    return todas


def executar_avaliacao_real(
    caminho_modelo: str,
    caminho_data: str,
    conf_auditoria: float = 0.001,
) -> Dict[str, Any]:
    dataset = validar_ground_truth(caminho_data)
    modelo_path = Path(caminho_modelo).expanduser().resolve()
    if not modelo_path.is_file():
        raise FileNotFoundError(f"Modelo não encontrado: {modelo_path}")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Ultralytics não está instalado no ambiente de avaliação offline.") from exc

    modelo = YOLO(str(modelo_path))
    if _nomes_modelo(modelo) != CLASSES_BEST_PT:
        raise RuntimeError("As classes carregadas do best.pt divergem do contrato de 20 classes.")

    resultado_val = modelo.val(data=str(dataset["path_data"]), split="test", verbose=False)
    metricas_ultra = _extrair_metricas_ultralytics(resultado_val)

    predicoes = _predizer_para_auditoria(modelo, dataset["imagens"], conf_auditoria)
    auditoria = auditar_deteccoes(dataset["ground_truth"], predicoes)
    auditoria_dict = auditoria.como_dict()

    por_classe = auditoria_dict["por_classe"]
    for cid, linha in por_classe.items():
        ultra = metricas_ultra["por_classe"][cid]
        if not linha["avaliavel"]:
            linha["ap50"] = None
            linha["precision_ultralytics"] = None
            linha["recall_ultralytics"] = None
        else:
            linha["ap50"] = ultra["ap50"]
            linha["precision_ultralytics"] = ultra["precision_ultralytics"]
            linha["recall_ultralytics"] = ultra["recall_ultralytics"]

    return {
        "status": "AVALIAÇÃO EXECUTADA",
        "modelo": str(modelo_path),
        "data_yaml": str(dataset["path_data"]),
        "imagens_test": len(dataset["imagens"]),
        "instancias_ground_truth": dataset["total_gt"],
        "metricas": {
            "map50_ultralytics": metricas_ultra["map50"],
            "por_classe": por_classe,
            "matriz_confusao": auditoria_dict["matriz_confusao"],
            "rotulos_matriz": auditoria_dict["rotulos_matriz"],
            "iou_threshold_auditoria": 0.50,
            "conf_auditoria_offline": conf_auditoria,
        },
    }


def executar(
    caminho_modelo: str = "best.pt",
    caminho_data: Optional[str] = None,
    conf_auditoria: float = 0.001,
    saida_json: Optional[str] = None,
    saida_csv: Optional[str] = None,
) -> Dict[str, Any]:
    if not caminho_data:
        return resultado_nao_executado()
    try:
        resultado = executar_avaliacao_real(caminho_modelo, caminho_data, conf_auditoria)
    except DatasetInvalidoError:
        return resultado_nao_executado()
    salvar_relatorios_avaliacao_real(resultado, saida_json, saida_csv)
    return resultado


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Avaliação offline do detector de EPI best.pt.")
    parser.add_argument("--model", default="best.pt", help="Caminho para o arquivo best.pt.")
    parser.add_argument("--data", default=None, help="Caminho para data.yaml real com split test e ground truth.")
    parser.add_argument("--conf-auditoria", type=float, default=0.001, help="Confiança mínima apenas da auditoria offline.")
    parser.add_argument("--json", dest="saida_json", default=None, help="Salvar relatório JSON após avaliação real.")
    parser.add_argument("--csv", dest="saida_csv", default=None, help="Salvar relatório CSV após avaliação real.")
    return parser


def main() -> int:
    args = _parser().parse_args()
    resultado = executar(args.model, args.data, args.conf_auditoria, args.saida_json, args.saida_csv)
    if resultado["status"] == STATUS_NAO_EXECUTADA:
        print(STATUS_NAO_EXECUTADA)
        print(MOTIVO_SEM_GT)
        return 2
    metricas = resultado["metricas"]
    print("AVALIAÇÃO EXECUTADA")
    print(f"mAP@0.5 (Ultralytics): {metricas['map50_ultralytics']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
