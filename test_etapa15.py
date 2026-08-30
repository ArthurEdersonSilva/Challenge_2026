from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
BASE = Path(os.environ.get('ETAPA15_BASE_OPERACIONAL', HERE)).resolve()
sys.path.insert(0, str(HERE))

from avaliar_modelo_epi import DatasetInvalidoError, executar, validar_data_yaml, validar_ground_truth, _extrair_metricas_ultralytics
from metricas_deteccao import (
    BACKGROUND,
    CLASSES_BEST_PT,
    Caixa,
    calcular_iou,
    calcular_metricas_por_classe,
    construir_matriz_confusao,
    matching_mesma_classe,
)
from relatorio_avaliacao_epi import salvar_relatorios_avaliacao_real

EXPECTED_HASHES = {
    'main.py': '13bdb4342718a411280adb59ddc21184e6bb831938520a90cfef460c31da5eec',
    'estado_sistema.py': '447d04af31586a37dfa54c994241db16a6c2b3351bb6db2e693617dd9f842bf5',
    'metricas_runtime.py': '9378128969cb92714b509ddbda7ee2c3c8ede04a52914e9ab4d2d9f1ea3ceeb5',
    'visao_colaborador.py': '82bfec61309de9279eea7407c8fd2c9cf3c8928bc54a3dc1453c25025b7fc574',
    'visao_gerente.py': 'b7dc0cb64e26509c2c1c7db01168e86bb65132dd219d098d1618c2a274e04372',
}

EXPECTED_CLASSES = (
    'Ear Protectors','Face Shield','Full body suit','Glasses','Gloves','Helmet','Mask',
    'Safety Harness','Safety Shoes','Safety Vest','Without Ear Protectors','Without Face Shield',
    'Without Full body suit','Without Glass','Without Glove','Without Helmet','Without Mask',
    'Without Safety Harness','Without Safety Shoes','Without Safety Vest'
)


def ok(name, cond):
    if not cond:
        raise AssertionError(name)
    print(f'{name}=OK')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assert_raises(exc, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except exc:
        return True
    return False


def make_dataset(root: Path, names=EXPECTED_CLASSES, with_gt=True, malformed=False, invalid_class=False):
    images = root / 'images' / 'test'
    labels = root / 'labels' / 'test'
    images.mkdir(parents=True)
    labels.mkdir(parents=True)
    Image.new('RGB', (100, 100)).save(images / 'a.jpg')
    if with_gt:
        if malformed:
            text = '5 0.5 0.5\n'
        elif invalid_class:
            text = '99 0.5 0.5 0.4 0.4\n'
        else:
            text = '5 0.5 0.5 0.4 0.4\n'
        (labels / 'a.txt').write_text(text, encoding='utf-8')
    data = root / 'data.yaml'
    data.write_text('path: .\ntest: images/test\nnames:\n' + ''.join(f'  {i}: "{n}"\n' for i,n in enumerate(names)), encoding='utf-8')
    return data


def main():
    # IoU
    ok('IOU_CAIXAS_IDENTICAS_IGUAL_1', abs(calcular_iou((0,0,10,10),(0,0,10,10))-1.0) < 1e-12)
    ok('IOU_SEM_INTERSECAO_IGUAL_0', calcular_iou((0,0,10,10),(20,20,30,30)) == 0.0)
    expected = 25/175
    ok('IOU_INTERSECAO_PARCIAL_CORRETA', abs(calcular_iou((0,0,10,10),(5,5,15,15))-expected) < 1e-12)
    ok('IOU_CAIXA_INVALIDA_REJEITADA', assert_raises(ValueError, calcular_iou, (0,0,0,1),(0,0,1,1)))

    # Matching same class deterministic one-to-one
    gt = [Caixa(5,(0,0,10,10)), Caixa(5,(20,20,30,30))]
    pred = [Caixa(5,(0,0,10,10),0.9), Caixa(5,(0,0,10,10),0.8), Caixa(5,(20,20,29,29),0.7)]
    audit = matching_mesma_classe(gt,pred)
    ok('MATCH_MESMA_CLASSE_IOU_050_E_TP', len(audit.matches)==2)
    low = matching_mesma_classe([Caixa(5,(0,0,10,10))],[Caixa(5,(9,9,19,19),0.9)])
    ok('MATCH_MESMA_CLASSE_IOU_ABAIXO_050_E_FP_FN', low.predicoes_fp==[0] and low.ground_truth_fn==[0])
    wrong = matching_mesma_classe([Caixa(5,(0,0,10,10))],[Caixa(15,(0,0,10,10),0.9)])
    ok('MATCH_CLASSE_DIFERENTE_NAO_E_TP', not wrong.matches and wrong.predicoes_fp==[0] and wrong.ground_truth_fn==[0])
    ok('GROUND_TRUTH_SO_PODE_SER_ASSOCIADO_UMA_VEZ', sum(m.gt_indice==0 for m in audit.matches)==1)
    ok('DETECCAO_DUPLICADA_GERA_FP', audit.predicoes_fp==[1])
    ok('GROUND_TRUTH_NAO_DETECTADO_GERA_FN', matching_mesma_classe([Caixa(5,(0,0,10,10))],[]).ground_truth_fn==[0])
    ok('DETECCAO_SEM_GROUND_TRUTH_GERA_FP', matching_mesma_classe([],[Caixa(5,(0,0,10,10),.9)]).predicoes_fp==[0])

    # Class contract
    ok('CONTRATO_20_CLASSES_EXATAS', CLASSES_BEST_PT==EXPECTED_CLASSES and len(CLASSES_BEST_PT)==20)
    ok('GLASSES_NAO_VIRA_GLASS', CLASSES_BEST_PT[3]=='Glasses')
    ok('GLOVES_NAO_VIRA_GLOVE', CLASSES_BEST_PT[4]=='Gloves')
    ok('WITHOUT_GLASS_PRESERVADO', CLASSES_BEST_PT[13]=='Without Glass')
    ok('WITHOUT_GLOVE_PRESERVADO', CLASSES_BEST_PT[14]=='Without Glove')
    ok('SAFETY_SHOES_PRESENTE', CLASSES_BEST_PT[8]=='Safety Shoes')
    ok('WITHOUT_SAFETY_SHOES_PRESENTE', CLASSES_BEST_PT[18]=='Without Safety Shoes')
    ok('WITHOUT_SAO_CLASSES_INDEPENDENTES', CLASSES_BEST_PT.index('Helmet') != CLASSES_BEST_PT.index('Without Helmet'))

    # Metrics
    gts = [[Caixa(5,(0,0,10,10)), Caixa(5,(20,20,30,30))]]
    preds = [[Caixa(5,(0,0,10,10),.9), Caixa(5,(40,40,50,50),.8)]]
    metrics = calcular_metricas_por_classe(gts,preds)
    helmet = metrics[5]
    ok('PRECISION_CALCULO_CORRETO', helmet.precision==0.5)
    ok('RECALL_CALCULO_CORRETO', helmet.recall==0.5)
    ok('F1_CALCULO_CORRETO', helmet.f1==0.5)
    ok('FP_FN_POR_CLASSE_CORRETOS', (helmet.tp,helmet.fp,helmet.fn)==(1,1,1))
    ok('CLASSE_SEM_GT_MARCADA_NAO_AVALIAVEL', metrics[3].avaliavel is False and metrics[3].precision is None and metrics[3].recall is None and metrics[3].f1 is None)
    no_pred = calcular_metricas_por_classe([[Caixa(5,(0,0,10,10))]],[[]])[5]
    ok('SEM_PREDICAO_COM_GT_E_DESEMPENHO_ZERO', no_pred.precision==0.0 and no_pred.recall==0.0 and no_pred.f1==0.0)
    no_gt = calcular_metricas_por_classe([[]],[[Caixa(5,(0,0,10,10),.9)]])[5]
    ok('SEM_GT_CLASSE_NAO_INVENTA_RECALL', no_gt.recall is None and no_gt.avaliavel is False and no_gt.fp==1)

    # Confusion matrix with background
    matrix, labels = construir_matriz_confusao([[Caixa(5,(0,0,10,10))]], [[Caixa(5,(0,0,10,10),.9)]])
    ok('MATRIZ_DIAGONAL_PARA_CLASSIFICACAO_CORRETA', matrix[5][5]==1 and labels[-1]==BACKGROUND)
    matrix2,_ = construir_matriz_confusao([[Caixa(5,(0,0,10,10))]], [[Caixa(15,(0,0,10,10),.9)]])
    ok('CONFUSAO_HELMET_WITHOUT_HELMET_REGISTRADA', matrix2[5][15]==1)
    matrix3,_ = construir_matriz_confusao([[Caixa(3,(0,0,10,10))]], [[Caixa(13,(0,0,10,10),.9)]])
    ok('CONFUSAO_GLASSES_WITHOUT_GLASS_REGISTRADA', matrix3[3][13]==1)
    bg=20
    matrix4,_=construir_matriz_confusao([[Caixa(5,(0,0,10,10))]],[[]])
    ok('GT_SEM_PREDICAO_VAI_PARA_BACKGROUND', matrix4[5][bg]==1)
    matrix5,_=construir_matriz_confusao([[]],[[Caixa(5,(0,0,10,10),.9)]])
    ok('PREDICAO_SEM_GT_VEM_DE_BACKGROUND', matrix5[bg][5]==1)
    matrix6,_=construir_matriz_confusao([[Caixa(5,(0,0,10,10))]], [[Caixa(5,(0,0,10,10),.9),Caixa(5,(0,0,10,10),.8)]])
    ok('MATRIZ_NAO_DUPLICA_GT', matrix6[5][5]==1 and matrix6[bg][5]==1)

    # Dataset validations
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        ok('DATASET_INEXISTENTE_FALHA_EXPLICITAMENTE', assert_raises(DatasetInvalidoError, validar_data_yaml, str(td/'missing.yaml')))
        data=make_dataset(td/'valid')
        info=validar_ground_truth(str(data))
        ok('DATASET_VALIDO_COM_GT_E_ACEITO', info['total_gt']==1)

    with tempfile.TemporaryDirectory() as td:
        td=Path(td); data=make_dataset(td/'negative', with_gt=False)
        ok('IMAGEM_SEM_LABEL_NEGATIVA_E_ACEITA_NA_LEITURA', validar_data_yaml(str(data))['test_path'].exists())
        ok('TEST_SEM_GROUND_TRUTH_NAO_PRODUZ_METRICAS_FICTICIAS', assert_raises(DatasetInvalidoError, validar_ground_truth, str(data)))

    with tempfile.TemporaryDirectory() as td:
        td=Path(td); data=make_dataset(td/'badlabel', malformed=True)
        ok('LABEL_MALFORMADA_FALHA', assert_raises(DatasetInvalidoError, validar_ground_truth, str(data)))
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); data=make_dataset(td/'badclass', invalid_class=True)
        ok('LABEL_REFERENCIA_CLASSE_INVALIDA_FALHA', assert_raises(DatasetInvalidoError, validar_ground_truth, str(data)))
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); names=list(EXPECTED_CLASSES); names[5]='Capacete'; data=make_dataset(td/'badnames', names=names)
        ok('CLASSES_DATASET_DIVERGENTES_DO_BEST_PT_FALHAM', assert_raises(DatasetInvalidoError, validar_data_yaml, str(data)))

    # Ultralytics result parsing: AP@0.5 must use box.ap50, not mAP50-95.
    class FakeBox:
        ap50=[0.91,0.82]
        p=[0.88,0.77]
        r=[0.86,0.75]
        ap_class_index=[5,15]
        map50=0.865
        maps=[0.51]*20  # deliberadamente diferente de AP50
    class FakeVal:
        box=FakeBox()
    parsed=_extrair_metricas_ultralytics(FakeVal())
    ok('AP50_POR_CLASSE_LIDO_CORRETAMENTE', parsed['por_classe']['5']['ap50']==0.91 and parsed['por_classe']['15']['ap50']==0.82)
    ok('MAP50_GERAL_LIDO_CORRETAMENTE', parsed['map50']==0.865)
    ok('CLASSE_SEM_SUPORTE_NAO_RECEBE_AP50_ULTRALYTICS', parsed['por_classe']['3']['ap50'] is None)

    # No fabrication / no dataset
    result = executar(caminho_data=None)
    ok('SEM_DATASET_NAO_GERA_MAP', result['metricas'] is None and 'map' not in result)
    ok('SEM_DATASET_NAO_GERA_PRECISION', result['metricas'] is None)
    ok('SEM_DATASET_NAO_GERA_RECALL', result['metricas'] is None)
    ok('SEM_DATASET_NAO_GERA_F1', result['metricas'] is None)
    ok('SEM_DATASET_NAO_GERA_FP_FN', result['metricas'] is None)
    ok('RESULTADO_NAO_E_PREENCHIDO_COM_META_DO_CHALLENGE', '0.75' not in json.dumps(result) and '0.80' not in json.dumps(result))
    ok('STATUS_SEM_DATASET_EXPLICITO', result['status']=='AVALIAÇÃO NÃO EXECUTADA' and result['motivo']=='GROUND TRUTH NÃO DISPONÍVEL')

    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'fake.json'
        ok('SEM_GT_NAO_GERA_RELATORIO_FICTICIO', assert_raises(ValueError, salvar_relatorios_avaliacao_real, result, str(out), None) and not out.exists())

    # CLI exact current behavior
    proc=subprocess.run([sys.executable,str(HERE/'avaliar_modelo_epi.py')],capture_output=True,text=True)
    lines=[x.strip() for x in proc.stdout.splitlines() if x.strip()]
    ok('CLI_SEM_DATASET_TERMINA_EXPLICITAMENTE', lines==['AVALIAÇÃO NÃO EXECUTADA','GROUND TRUTH NÃO DISPONÍVEL'])

    # Architecture separation by imports/references
    src=(HERE/'avaliar_modelo_epi.py').read_text(encoding='utf-8') + (HERE/'metricas_deteccao.py').read_text(encoding='utf-8') + (HERE/'relatorio_avaliacao_epi.py').read_text(encoding='utf-8')
    tree=ast.parse(src)
    imported=[]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module: imported.append(node.module)
    forbidden=['main','estado_sistema','metricas_runtime','visao_colaborador','visao_gerente','rastreamento_pessoas','associacao_epi_pessoa','avaliacao_estado_epi','estabilizacao_temporal_epi','biometria_operador','reconhecimento_facial','gestao_incidentes_epi','gestao_notificacoes_incidentes','notificacoes']
    for module in forbidden:
        ok(f'AVALIACAO_NAO_IMPORTA_{module.upper()}', not any(x==module or x.startswith(module+'.') for x in imported))
    ok('AVALIACAO_NAO_ACESSA_ESTADO_SISTEMA', 'EstadoSistema' not in src)
    ok('AVALIACAO_NAO_ALTERA_METRICAS_RUNTIME', 'metricas_runtime' not in imported)
    ok('AVALIACAO_NAO_EXECUTA_POSE', 'modelo_pose' not in src and 'yolov8n-pose' not in src)
    ok('AVALIACAO_NAO_EXECUTA_TRACKING', 'processar_camera' not in src)
    ok('AVALIACAO_NAO_EXECUTA_DEEPFACE', 'DeepFace' not in src)
    ok('AVALIACAO_NAO_EXECUTA_ASSOCIACAO_EPI_PESSOA', 'associacao_epi_pessoa' not in imported)
    ok('AVALIACAO_NAO_EXECUTA_AVALIACAO_ANATOMICA', 'avaliacao_estado_epi' not in imported)
    ok('AVALIACAO_NAO_EXECUTA_ESTABILIZACAO', 'estabilizacao_temporal_epi' not in imported)
    ok('AVALIACAO_NAO_CRIA_INCIDENTE', 'gestao_incidentes_epi' not in imported)
    ok('AVALIACAO_NAO_ENVIA_NOTIFICACAO', 'gestao_notificacoes_incidentes' not in imported and 'notificacoes' not in imported)

    # Protected base exact hashes
    for name, expected in EXPECTED_HASHES.items():
        label={
            'main.py':'MAIN_BYTE_IDENTICAL',
            'estado_sistema.py':'ESTADO_SISTEMA_BYTE_IDENTICAL',
            'metricas_runtime.py':'METRICAS_RUNTIME_BYTE_IDENTICAL',
            'visao_colaborador.py':'VISAO_COLABORADOR_BYTE_IDENTICAL',
            'visao_gerente.py':'VISAO_GERENTE_BYTE_IDENTICAL',
        }[name]
        ok(label, sha(BASE/name)==expected)

    ok('ALL_ETAPA15_TESTS', True)

if __name__=='__main__':
    main()
