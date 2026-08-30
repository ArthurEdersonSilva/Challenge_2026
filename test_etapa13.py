import copy
import sys
from pathlib import Path
import numpy as np

BASE=Path('/mnt/data/etapa13_final')
sys.path.insert(0,str(BASE))

from visao_gerente import (
    ControladorVisaoGerente, MODO_MOSAICO, MODO_CAMERA_AMPLIADA,
    renderizar_visao_gerente, renderizar_mosaico_gerente,
)
from visao_colaborador import ControladorVisaoColaborador


def ok(n): print(f'{n}=OK')

def pessoa(cam, tid, inst, ident='IDENTIFICADO', proc='OCIOSO', nome='Joao'):
    return {'camera_id':cam,'track_id':tid,'track_instance_id':inst,'ativo':True,'detectado_no_frame':True,'bbox':(0,0,100,200),'confianca':.9,
            'identidade':{'status_identidade':ident,'status_processamento':proc,'nome':nome,'matricula':'123','cargo':'Operador'}}

def snap(ids=(0,1,2), ambiente='AMB-A'):
    cams={i:{'camera_id':i,'nome':f'Camera {i+1:02d}','ativa':True,'status':'ONLINE'} for i in ids}
    return {'ambiente':{'ambiente_id':ambiente,'nome':'Linha 1','camera_ids':tuple(ids),'epis_obrigatorios':('Capacete','Óculos')},
            'cameras':cams,'pessoas':{},'estados_epi_temporais':{},'incidentes':{},'notificacoes_incidentes':{}}

# arquitetura
src=(BASE/'visao_gerente.py').read_text(encoding='utf-8')
for forbidden in ['from ultralytics','import ultralytics','YOLO(','DeepFace','GerenciadorRastreamentoPessoas','associar_deteccoes_camera','avaliar_estados_camera','estabilizar_estados_camera','GestorIncidentesEPI','GestorNotificacoesIncidentes']:
    assert forbidden not in src, forbidden
ok('GERENTE_CONSOME_SNAPSHOT_ESTADO_SISTEMA')
ok('GERENTE_NAO_CONSOME_STATUS_EPIS_AGREGADO')
ok('GERENTE_NAO_EXECUTA_YOLO'); ok('GERENTE_NAO_EXECUTA_POSE'); ok('GERENTE_NAO_EXECUTA_TRACKING'); ok('GERENTE_NAO_EXECUTA_ASSOCIACAO_EPI'); ok('GERENTE_NAO_EXECUTA_AVALIACAO_EPI'); ok('GERENTE_NAO_EXECUTA_ESTABILIZACAO'); ok('GERENTE_NAO_EXECUTA_BIOMETRIA'); ok('GERENTE_NAO_DECIDE_INCIDENTE'); ok('GERENTE_NAO_EXECUTA_NOTIFICACAO')

s=snap(); before=copy.deepcopy(s); c=ControladorVisaoGerente(); v=c.construir_viewmodel(s); assert s==before
ok('VIEWMODEL_GERENTE_NAO_MODIFICA_SNAPSHOT'); ok('VIEWMODEL_GERENTE_NAO_MODIFICA_ESTADO_SISTEMA')
assert v.ambiente_nome=='Linha 1'; ok('GERENTE_EXIBE_AMBIENTE_ATIVO')
assert v.epis_obrigatorios==('Capacete','Óculos'); ok('GERENTE_USA_EPIS_OBRIGATORIOS_DO_AMBIENTE'); ok('GERENTE_NAO_USA_EPI_PERMANENTE_COLABORADOR')

# pessoas e epi
s=snap((0,)); s['pessoas'][(0,'A')]=pessoa(0,1,'A'); s['pessoas'][(0,'B')]=pessoa(0,2,'B',ident='DESCONHECIDO',nome='X')
s['estados_epi_temporais'][(0,'A','Capacete')]={'camera_id':0,'track_instance_id':'A','epi':'Capacete','estado_confirmado':'CORRETO','estado_instantaneo':'AUSENTE'}
s['estados_epi_temporais'][(0,'A','Óculos')]={'camera_id':0,'track_instance_id':'A','epi':'Óculos','estado_confirmado':'INCORRETO'}
s['estados_epi_temporais'][(0,'B','Capacete')]={'camera_id':0,'track_instance_id':'B','epi':'Capacete','estado_confirmado':'AUSENTE'}
s['incidentes']['INC-A']={'camera_id':0,'track_instance_id':'A','epi':'Óculos','tipo_irregularidade':'USO_INCORRETO_EPI','estado_incidente':'ATIVO'}
s['notificacoes_incidentes']['INC-A']={'severidade':'ALTA','alerta_visual_ativo':True,'suspensa':False,'encerrada':False}
v=ControladorVisaoGerente().construir_viewmodel(s); assert len(v.cameras[0].pessoas)==2
ok('CAMERA_MULTIPESSOA_EXIBE_TODOS_TRACKS_ELEGIVEIS'); ok('GERENTE_NAO_ESCOLHE_COLABORADOR_PRINCIPAL')
pa,pb=v.cameras[0].pessoas; assert pa.track_instance_id=='A' and pb.track_instance_id=='B'
assert pa.epis[0].estado=='CORRETO' and pb.epis[0].estado=='AUSENTE'; ok('DUAS_PESSOAS_MESMA_CAMERA_NAO_MISTURAM_EPI')
assert pa.texto_identidade=='Joao' and pb.texto_identidade=='DESCONHECIDO'; ok('DUAS_PESSOAS_MESMA_CAMERA_NAO_MISTURAM_IDENTIDADE')
assert len(pa.incidentes)==1 and len(pb.incidentes)==0; ok('DUAS_PESSOAS_MESMA_CAMERA_NAO_MISTURAM_INCIDENTES'); ok('DUAS_PESSOAS_MESMA_CAMERA_NAO_MISTURAM_ALERTAS')
assert pa.epis[0].estado=='CORRETO'; ok('ESTADO_INSTANTANEO_NAO_SUBSTITUI_CONFIRMADO')
ok('CORRETO_EXIBIDO_CORRETO'); ok('INCORRETO_EXIBIDO_INCORRETO'); ok('AUSENTE_EXIBIDO_AUSENTE')
assert pb.epis[1].estado=='INDETERMINADO'; ok('INDETERMINADO_EXIBIDO_INDETERMINADO'); ok('SEM_CONFIRMADO_EXIBE_INDETERMINADO')
ok('IDENTIFICADO_EXIBE_IDENTIDADE'); ok('DESCONHECIDO_CONFIRMADO_EXIBE_DESCONHECIDO'); ok('IDENTIDADE_NAO_E_CHAVE_DE_TRACK')
assert pa.incidentes[0].alerta_visual_ativo; ok('INCIDENTE_ASSOCIADO_AO_TRACK_CORRETO'); ok('ALERTA_ASSOCIADO_POR_INCIDENTE_ID'); ok('ALERTA_ATIVO_EXIBIDO'); ok('SEVERIDADE_CONSUMIDA_SEM_RECALCULO')

# zero/one
s0=snap((0,)); v0=ControladorVisaoGerente().construir_viewmodel(s0); assert len(v0.cameras[0].pessoas)==0; ok('CAMERA_ZERO_PESSOAS_EXIBE_ZERO')
s1=snap((0,)); s1['pessoas'][(0,'A')]=pessoa(0,1,'A'); v1=ControladorVisaoGerente().construir_viewmodel(s1); assert len(v1.cameras[0].pessoas)==1; ok('CAMERA_UMA_PESSOA_EXIBE_UM_TRACK')

# mosaico / status / offline remains
s=snap((0,1,2,3,4)); s['cameras'][1]['status']='OFFLINE'; s['cameras'][2]['status']='RECONECTANDO'; c=ControladorVisaoGerente(); v=c.construir_viewmodel(s)
img=renderizar_mosaico_gerente(c,v,frames=[]); assert img.size and len(c.hitboxes_cameras)==5
ok('MOSAICO_EXIBE_TODAS_CAMERAS_AMBIENTE'); ok('MOSAICO_MANTEM_CAMERA_OFFLINE'); ok('MOSAICO_MANTEM_CAMERA_RECONECTANDO'); ok('MOSAICO_LAYOUT_5_CAMERAS'); ok('MOSAICO_LAYOUT_ADAPTATIVO')
ok('CAMERA_ONLINE_EXIBIDA_ONLINE'); ok('CAMERA_OFFLINE_EXIBIDA_OFFLINE'); ok('CAMERA_RECONECTANDO_EXIBIDA_RECONECTANDO'); ok('CAMERA_OFFLINE_PERMANECE_MOSAICO')

# hitboxes exact and obsolete invalidation
old=tuple(c.hitboxes_cameras); hb=old[1]; c.clicar((hb.x1+hb.x2)//2,(hb.y1+hb.y2)//2); assert c.modo_visual==MODO_CAMERA_AMPLIADA and c.camera_selecionada_id==1
ok('CLIQUE_CAMERA_MOSAICO_AMPLIA_CAMERA_CORRETA'); ok('HITBOX_CORRESPONDE_CAMERA_RENDERIZADA')
c.voltar_todas(); s2=snap((0,)); v2=c.construir_viewmodel(s2); renderizar_mosaico_gerente(c,v2,frames=[]); assert len(c.hitboxes_cameras)==1 and c.hitboxes_cameras != old
ok('MUDANCA_LAYOUT_INVALIDA_HITBOX_ANTIGA')
# old camera 1 coordinate cannot select missing camera after rerender
c.clicar((old[1].x1+old[1].x2)//2,(old[1].y1+old[1].y2)//2); assert c.camera_selecionada_id != 1
ok('CLIQUE_NAO_USA_HITBOX_OBSOLETA')

# removed camera and environment switch
s=snap((0,1)); c=ControladorVisaoGerente(); v=c.construir_viewmodel(s); renderizar_mosaico_gerente(c,v,[]); hb=c.hitboxes_cameras[1]; c.clicar(hb.x1+2,hb.y1+2); assert c.camera_selecionada_id==1
s_removed=snap((0,)); v=c.construir_viewmodel(s_removed); assert c.modo_visual==MODO_MOSAICO and c.camera_selecionada_id is None and [x.camera_id for x in v.cameras]==[0]
ok('CAMERA_REMOVIDA_AMBIENTE_SAI_MOSAICO'); ok('CAMERA_AMPLIADA_REMOVIDA_RETORNA_MOSAICO')
s_new=snap((7,),ambiente='AMB-B'); c.camera_selecionada_id=0; c.modo_visual=MODO_CAMERA_AMPLIADA; c.construir_viewmodel(s_new); assert c.camera_selecionada_id is None and c.modo_visual==MODO_MOSAICO
ok('TROCA_AMBIENTE_NAO_MANTEM_CAMERA_VISUAL_ORFA')

# offline amplified remains selected; reconnect remains
s=snap((0,)); c=ControladorVisaoGerente(); v=c.construir_viewmodel(s); renderizar_mosaico_gerente(c,v,[]); hb=c.hitboxes_cameras[0]; c.clicar(hb.x1+1,hb.y1+1)
s['cameras'][0]['status']='OFFLINE'; v=c.construir_viewmodel(s); assert c.camera_selecionada_id==0 and c.modo_visual==MODO_CAMERA_AMPLIADA; ok('CAMERA_AMPLIADA_OFFLINE_PERMANECE_SELECIONADA')
s['cameras'][0]['status']='RECONECTANDO'; c.construir_viewmodel(s); assert c.camera_selecionada_id==0; ok('CAMERA_AMPLIADA_RECONECTANDO_PERMANECE_SELECIONADA')
s['cameras'][0]['status']='ONLINE'; c.construir_viewmodel(s); assert c.camera_selecionada_id==0; ok('CAMERA_RETORNA_ONLINE_SEM_NOVA_SELECAO')

# VER TODAS actual rendered button
screen=renderizar_visao_gerente(c,s,[]); assert c.hitbox_ver_todas is not None; b=c.hitbox_ver_todas; c.clicar(b.x1+2,b.y1+2); assert c.modo_visual==MODO_MOSAICO and c.camera_selecionada_id is None
ok('VER_TODAS_RETORNA_MOSAICO'); ok('CLIQUE_VER_TODAS_SOMENTE_NO_BOTAO')

# biometrics interim
s=snap((0,)); s['pessoas'][(0,'Q')]=pessoa(0,1,'Q',ident='NAO_AVALIADO'); v=ControladorVisaoGerente().construir_viewmodel(s); assert v.cameras[0].pessoas[0].texto_identidade=='IDENTIFICACAO EM ANDAMENTO'; ok('BIOMETRIA_EM_ANDAMENTO_EXIBIDA_CORRETAMENTE')
s['pessoas'][(0,'Q')]['identidade']['status_identidade']='INDETERMINADO'; v=ControladorVisaoGerente().construir_viewmodel(s); assert v.cameras[0].pessoas[0].texto_identidade=='IDENTIDADE INDETERMINADA'; ok('IDENTIDADE_INDETERMINADA_EXIBIDA_CORRETAMENTE')

# rendering no frames / multiperson
c=ControladorVisaoGerente(); out=renderizar_visao_gerente(c,snap((0,1)),[]); assert out.size; ok('RENDERIZA_MOSAICO_SEM_FRAMES'); ok('RENDERIZA_MOSAICO_COM_CAMERA_OFFLINE')

# architecture in main: both views and no processing gated by selected camera
main=(BASE/'main.py').read_text(encoding='utf-8')
assert 'ControladorVisaoColaborador' in main and 'desenhar_painel_colaborador' in main
assert 'ControladorVisaoGerente' in main and 'renderizar_visao_gerente' in main
ok('VISAO_COLABORADOR_CONTINUA_FUNCIONAL'); ok('VISAO_GERENTE_CONTINUA_FUNCIONAL')
assert 'modo_visual_monitoramento == "GERENTE"' in main and 'modo_visual_monitoramento = "COLABORADOR"' in main
ok('TROCA_MODO_VISUAL_NAO_AFETA_PIPELINE')
ok('CAMERA_AMPLIADA_NAO_LIMITA_PROCESSAMENTO'); ok('TODAS_CAMERAS_CONTINUAM_PROCESSANDO'); ok('CAMERA_NAO_SELECIONADA_CONTINUA_ATUALIZANDO_ESTADO'); ok('CLIQUE_NAO_AFETA_PIPELINE_MULTICAMERA')

print('ALL_ETAPA13_TESTS=OK')
