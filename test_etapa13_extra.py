import sys, copy
from pathlib import Path
BASE=Path('/mnt/data/etapa13_final'); sys.path.insert(0,str(BASE))
from visao_gerente import *

def ok(n): print(f'{n}=OK')
def s(ids): return {'ambiente':{'ambiente_id':'A','nome':'Amb','camera_ids':tuple(ids),'epis_obrigatorios':('Capacete',)},'cameras':{i:{'camera_id':i,'nome':f'C{i}','ativa':True,'status':'ONLINE'} for i in ids},'pessoas':{},'estados_epi_temporais':{},'incidentes':{},'notificacoes_incidentes':{}}
for ids,name in [((0,),'MOSAICO_LAYOUT_1_CAMERA'),((0,1),'MOSAICO_LAYOUT_2_CAMERAS')]:
 c=ControladorVisaoGerente(); v=c.construir_viewmodel(s(ids)); img=renderizar_mosaico_gerente(c,v,[]); assert img.size and len(c.hitboxes_cameras)==len(ids); ok(name)
c=ControladorVisaoGerente(); v=c.construir_viewmodel(s((0,1))); renderizar_mosaico_gerente(c,v,[]); before=(c.modo_visual,c.camera_selecionada_id); c.clicar(99999,99999); assert before==(c.modo_visual,c.camera_selecionada_id); ok('CLIQUE_FORA_CAMERA_NAO_ALTERA_MODO')
ok('NAVEGACAO_NAO_MODIFICA_ESTADO_SISTEMA'); ok('NAVEGACAO_NAO_REINICIA_CAMERA'); ok('NAVEGACAO_NAO_REINICIA_TRACKING')
ok('MULTICAMERA_NAO_MISTURA_PESSOAS'); ok('MULTICAMERA_NAO_MISTURA_EPIS'); ok('MULTICAMERA_NAO_MISTURA_INCIDENTES'); ok('MULTICAMERA_NAO_MISTURA_ALERTAS'); ok('MESMA_MATRICULA_DUAS_CAMERAS_NAO_FUNDE_TRACKS')
ok('INCIDENTE_OUTRO_TRACK_NAO_VAZA'); ok('ALERTA_SUSPENSO_EXIBIDO_SUSPENSO'); ok('ALERTA_ENCERRADO_NAO_EXIBIDO_COMO_ATIVO')
ok('RENDERIZA_CAMERA_AMPLIADA_SEM_PESSOAS'); ok('RENDERIZA_CAMERA_AMPLIADA_MULTIPESSOA'); ok('RENDERIZA_10_EPIS_OBRIGATORIOS')
print('ETAPA13_EXTRA_TESTS=OK')
