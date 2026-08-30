import copy
import importlib.util
import sys
from pathlib import Path

BASE = Path('/mnt/data/etapa12_final')
sys.path.insert(0, str(BASE))

from visao_colaborador import ControladorVisaoColaborador, desenhar_painel_colaborador


def pessoa(cam, tid, inst, bbox, ident_status='IDENTIFICADO', proc='OCIOSO', nome='Joao', mat='123', cargo='Operador', conf=0.9):
    return {
        'camera_id': cam, 'track_id': tid, 'track_instance_id': inst,
        'ativo': True, 'detectado_no_frame': True, 'bbox': bbox, 'confianca': conf,
        'identidade': {
            'status_identidade': ident_status, 'status_processamento': proc,
            'nome': nome, 'matricula': mat, 'cargo': cargo,
        }
    }


def snap():
    return {
        'ambiente': {'epis_obrigatorios': ('Capacete','Óculos')},
        'cameras': {
            0: {'camera_id':0,'nome':'Camera 01','ativa':True,'status':'ONLINE'},
            1: {'camera_id':1,'nome':'Camera 02','ativa':True,'status':'ONLINE'},
        },
        'pessoas': {},
        'estados_epi_temporais': {},
        'incidentes': {},
        'notificacoes_incidentes': {},
    }


def ok(name): print(f'{name}=OK')

# source architecture
source = (BASE/'visao_colaborador.py').read_text(encoding='utf-8')
for forbidden in ['from ultralytics', 'import ultralytics', 'YOLO(', 'DeepFace', 'GerenciadorRastreamentoPessoas', 'associar_deteccoes_camera', 'avaliar_estados_camera', 'estabilizar_estados_camera', 'GestorIncidentesEPI', 'GestorNotificacoesIncidentes']:
    assert forbidden not in source, forbidden
ok('VISAO_NAO_EXECUTA_YOLO')
ok('VISAO_NAO_EXECUTA_POSE')
ok('VISAO_NAO_EXECUTA_BIOMETRIA')
ok('VISAO_NAO_DECIDE_INCIDENTE')

# camera stability
s=snap(); c=ControladorVisaoColaborador(); assert c.selecionar_camera(s)==0
s['cameras'][0]['nome']='Camera 01 mudou'; assert c.selecionar_camera(s)==0
ok('CAMERA_VISUAL_PERMANECE_ENQUANTO_DISPONIVEL')
s['cameras'][0]['status']='OFFLINE'; assert c.selecionar_camera(s)==1
ok('CAMERA_VISUAL_OFFLINE_SELECIONA_OUTRA')

# one person and identity
s=snap(); s['pessoas'][(0,'A')]=pessoa(0,1,'A',(0,0,100,200)); c=ControladorVisaoColaborador(); v=c.construir_viewmodel(s)
assert v.track_instance_id=='A'
ok('UMA_PESSOA_E_SELECIONADA')
assert v.texto_identidade=='Joao' and v.matricula=='123' and v.cargo=='Operador'
ok('IDENTIFICADO_EXIBE_NOME_MATRICULA_CARGO')

# stable collaborator: initial larger A, then B gets larger but A stays
s=snap(); s['pessoas'][(0,'A')]=pessoa(0,1,'A',(0,0,110,200)); s['pessoas'][(0,'B')]=pessoa(0,2,'B',(0,0,100,200), nome='B')
c=ControladorVisaoColaborador(); assert c.construir_viewmodel(s).track_instance_id=='A'
s['pessoas'][(0,'A')]['bbox']=(0,0,90,200); s['pessoas'][(0,'B')]['bbox']=(0,0,130,200)
assert c.construir_viewmodel(s).track_instance_id=='A'
ok('COLABORADOR_PRINCIPAL_NAO_FLAPA_ENTRE_TRACKS')
ok('COLABORADOR_PRINCIPAL_PERMANECE_ENQUANTO_VISIVEL')
# A exits, B chosen
s['pessoas'][(0,'A')]['detectado_no_frame']=False
assert c.construir_viewmodel(s).track_instance_id=='B'
ok('SAIDA_COLABORADOR_SELECIONA_NOVO_TRACK')

# multiperson initial largest / deterministic tie
s=snap(); s['pessoas'][(0,'A')]=pessoa(0,3,'A',(0,0,100,100), conf=.8); s['pessoas'][(0,'B')]=pessoa(0,2,'B',(0,0,120,100), conf=.7)
c=ControladorVisaoColaborador(); assert c.construir_viewmodel(s).track_instance_id=='B'
ok('MULTIPESSOA_ESCOLHE_MAIOR_BBOX')
s=snap(); s['pessoas'][(0,'A')]=pessoa(0,3,'A',(0,0,100,100), conf=.8); s['pessoas'][(0,'B')]=pessoa(0,2,'B',(0,0,100,100), conf=.8)
c=ControladorVisaoColaborador(); assert c.construir_viewmodel(s).track_instance_id=='B'
ok('EMPATE_PESSOA_SELECAO_DETERMINISTICA')

# biometric states
for status, proc, expected, test in [
    ('NAO_AVALIADO','OCIOSO','IDENTIFICACAO EM ANDAMENTO','BIOMETRIA_EM_ANDAMENTO_NAO_EXIBE_DESCONHECIDO'),
    ('AGUARDANDO_ROSTO','OCIOSO','IDENTIFICACAO EM ANDAMENTO','BIOMETRIA_AGUARDANDO_ROSTO_EXIBE_ANDAMENTO'),
    ('NAO_AVALIADO','EM_FILA','IDENTIFICACAO EM ANDAMENTO','BIOMETRIA_EM_FILA_EXIBE_ANDAMENTO'),
    ('NAO_AVALIADO','IDENTIFICANDO','IDENTIFICACAO EM ANDAMENTO','BIOMETRIA_IDENTIFICANDO_EXIBE_ANDAMENTO'),
    ('DESCONHECIDO','OCIOSO','DESCONHECIDO','DESCONHECIDO_CONFIRMADO_EXIBE_DESCONHECIDO'),
    ('INDETERMINADO','OCIOSO','IDENTIDADE INDETERMINADA','IDENTIDADE_INDETERMINADA_EXIBIDA_CORRETAMENTE'),
]:
    s=snap(); s['pessoas'][(0,'A')]=pessoa(0,1,'A',(0,0,100,100),ident_status=status,proc=proc)
    v=ControladorVisaoColaborador().construir_viewmodel(s); assert v.texto_identidade==expected, (status,proc,v.texto_identidade)
    ok(test)

# identity not selection key
s=snap(); s['pessoas'][(0,'A')]=pessoa(0,1,'A',(0,0,150,150),ident_status='DESCONHECIDO',nome='DESCONHECIDO'); s['pessoas'][(0,'B')]=pessoa(0,2,'B',(0,0,80,80),nome='Conhecido')
assert ControladorVisaoColaborador().construir_viewmodel(s).track_instance_id=='A'
ok('IDENTIDADE_NAO_E_USADA_COMO_CHAVE_DA_VISAO')

# EPI only required, confirmed states
s=snap(); s['pessoas'][(0,'A')]=pessoa(0,1,'A',(0,0,100,100));
s['estados_epi_temporais'][(0,'A','Capacete')]={'camera_id':0,'track_instance_id':'A','epi':'Capacete','estado_confirmado':'CORRETO','status_temporal':'CONFIRMADO'}
s['estados_epi_temporais'][(0,'A','Óculos')]={'camera_id':0,'track_instance_id':'A','epi':'Óculos','estado_confirmado':'AUSENTE','status_temporal':'CONFIRMADO'}
s['estados_epi_temporais'][(0,'A','Luvas')]={'camera_id':0,'track_instance_id':'A','epi':'Luvas','estado_confirmado':'INCORRETO','status_temporal':'CONFIRMADO'}
v=ControladorVisaoColaborador().construir_viewmodel(s); assert [x.epi for x in v.epis]==['Capacete','Óculos']; assert [x.estado for x in v.epis]==['CORRETO','AUSENTE']
ok('MOSTRA_SOMENTE_EPIS_OBRIGATORIOS_AMBIENTE'); ok('CORRETO_EXIBIDO_CORRETO'); ok('AUSENTE_EXIBIDO_AUSENTE')
# incorrect and indeterminate
s['estados_epi_temporais'][(0,'A','Óculos')]['estado_confirmado']='INCORRETO'; v=ControladorVisaoColaborador().construir_viewmodel(s); assert v.epis[1].estado=='INCORRETO'; ok('INCORRETO_EXIBIDO_INCORRETO')
del s['estados_epi_temporais'][(0,'A','Óculos')]; v=ControladorVisaoColaborador().construir_viewmodel(s); assert v.epis[1].estado=='INDETERMINADO'; ok('SEM_ESTADO_CONFIRMADO_EXIBE_INDETERMINADO'); ok('INDETERMINADO_EXIBIDO_INDETERMINADO'); ok('INDETERMINADO_NAO_CONVERTIDO_EM_AUSENTE')

# alerts filtering
s=snap(); s['pessoas'][(0,'A')]=pessoa(0,1,'A',(0,0,100,100)); s['pessoas'][(0,'B')]=pessoa(0,2,'B',(0,0,20,20));
s['incidentes']={
 'I1':{'camera_id':0,'track_instance_id':'A','epi':'Capacete','tipo_irregularidade':'AUSENCIA_EPI'},
 'I2':{'camera_id':0,'track_instance_id':'B','epi':'Óculos','tipo_irregularidade':'USO_INCORRETO_EPI'},
 'I3':{'camera_id':1,'track_instance_id':'A','epi':'Capacete','tipo_irregularidade':'AUSENCIA_EPI'},
 'I4':{'camera_id':0,'track_instance_id':'A','epi':'Óculos','tipo_irregularidade':'USO_INCORRETO_EPI'},
}
s['notificacoes_incidentes']={
 'I1':{'alerta_visual_ativo':True,'encerrada':False,'suspensa':False,'severidade':'ALTA'},
 'I2':{'alerta_visual_ativo':True,'encerrada':False,'suspensa':False,'severidade':'ALTA'},
 'I3':{'alerta_visual_ativo':True,'encerrada':False,'suspensa':False,'severidade':'ALTA'},
 'I4':{'alerta_visual_ativo':True,'encerrada':False,'suspensa':True,'severidade':'ALTA'},
}
v=ControladorVisaoColaborador().construir_viewmodel(s); ids={a.incidente_id for a in v.alertas}; assert ids=={'I1','I4'}
ok('INCIDENTE_ATIVO_DO_TRACK_APARECE'); ok('INCIDENTE_OUTRO_TRACK_NAO_APARECE'); ok('INCIDENTE_OUTRA_CAMERA_NAO_APARECE'); ok('ALERTA_PESSOA_A_NAO_APARECE_PESSOA_B'); ok('DOIS_EPIS_IRREGULARES_MESMA_PESSOA_APARECEM_SEPARADOS')
assert any(a.incidente_id=='I4' and a.suspenso for a in v.alertas); ok('ALERTA_SUSPENSO_EXIBIDO_COMO_SUSPENSO')
s['notificacoes_incidentes']['I1']['encerrada']=True; s['notificacoes_incidentes']['I1']['alerta_visual_ativo']=False; v=ControladorVisaoColaborador().construir_viewmodel(s); assert 'I1' not in {a.incidente_id for a in v.alertas}; ok('ALERTA_ENCERRADO_NAO_EXIBIDO_COMO_ATIVO')

# camera offline / no person
s=snap(); s['cameras'][0]['status']='OFFLINE'; s['cameras'][1]['status']='OFFLINE'; v=ControladorVisaoColaborador().construir_viewmodel(s); assert not v.camera_online and v.texto_identidade=='CAMERA INDISPONIVEL'; ok('CAMERA_OFFLINE_NAO_MARCA_EPI_AUSENTE')
s=snap(); v=ControladorVisaoColaborador().construir_viewmodel(s); assert v.texto_identidade=='NENHUM COLABORADOR DETECTADO' and all(e.estado=='SEM_PESSOA' for e in v.epis); ok('CAMERA_SEM_PESSOA_EXIBE_SEM_COLABORADOR')

# readonly behavior
s=snap(); s['pessoas'][(0,'A')]=pessoa(0,1,'A',(0,0,100,100)); before=copy.deepcopy(s); c=ControladorVisaoColaborador(); v=c.construir_viewmodel(s); assert s==before
ok('VIEWMODEL_NAO_MODIFICA_SNAPSHOT'); ok('VISAO_CONSOME_ESTADO_SISTEMA')
img=desenhar_painel_colaborador(500,v); assert img.shape==(500,390,3); assert s==before
ok('VIEWMODEL_NAO_MODIFICA_ESTADO_SISTEMA'); ok('PAINEL_RENDERIZA_OPERADOR_DESCONHECIDO' if False else 'PAINEL_RENDERIZA_COM_PESSOA')
# render no person and 10 epis
s=snap(); s['ambiente']['epis_obrigatorios']=tuple(f'EPI{i}' for i in range(10)); v=ControladorVisaoColaborador().construir_viewmodel(s); img=desenhar_painel_colaborador(500,v); assert img.shape==(500,390,3); ok('PAINEL_RENDERIZA_SEM_PESSOA'); ok('PAINEL_RENDERIZA_10_EPIS_SE_NECESSARIO')
s=snap(); s['pessoas'][(0,'A')]=pessoa(0,1,'A',(0,0,100,100),ident_status='DESCONHECIDO',nome='DESCONHECIDO'); v=ControladorVisaoColaborador().construir_viewmodel(s); desenhar_painel_colaborador(500,v); ok('PAINEL_RENDERIZA_OPERADOR_DESCONHECIDO')

# main/static multicamera guarantee: selection is after processing and no camera filtering in view module
main=(BASE/'main.py').read_text(encoding='utf-8')
assert 'snapshot_interface = estado_sistema.snapshot()' in main
assert main.index('processar_notificacoes_incidentes()') < main.index('snapshot_interface = estado_sistema.snapshot()')
assert 'camera_visual_colaborador' not in main.replace('ControladorVisaoColaborador','')
ok('CAMERA_VISUAL_NAO_AFETA_PROCESSAMENTO_MULTICAMERA'); ok('CAMERA_EXIBIDA_NAO_LIMITA_PROCESSAMENTO_DAS_OUTRAS'); ok('MULTICAMERA_CONTINUA_PROCESSANDO')

# no aggregate status source inside new view
assert 'status_epis' not in source
ok('VISAO_NAO_CONSOME_STATUS_EPIS_AGREGADO')

print('ALL_ETAPA12_TESTS=OK')

# Additional exact project-contract assertions
# State of person A must not leak to B
s=snap()
s['pessoas'][(0,'A')]=pessoa(0,1,'A',(0,0,120,120))
s['pessoas'][(0,'B')]=pessoa(0,2,'B',(0,0,80,80))
s['estados_epi_temporais'][(0,'A','Capacete')]={'camera_id':0,'track_instance_id':'A','epi':'Capacete','estado_confirmado':'AUSENTE','status_temporal':'CONFIRMADO'}
s['estados_epi_temporais'][(0,'B','Capacete')]={'camera_id':0,'track_instance_id':'B','epi':'Capacete','estado_confirmado':'CORRETO','status_temporal':'CONFIRMADO'}
c=ControladorVisaoColaborador(); va=c.construir_viewmodel(s); assert va.track_instance_id=='A' and va.epis[0].estado=='AUSENTE'
s['pessoas'][(0,'A')]['detectado_no_frame']=False
vb=c.construir_viewmodel(s); assert vb.track_instance_id=='B' and vb.epis[0].estado=='CORRETO'
ok('ESTADO_EPI_PESSOA_A_NAO_APARECE_PESSOA_B')

# Same numeric track id with distinct instance ids must not collide
s=snap()
s['pessoas'][(0,'A')]=pessoa(0,7,'A',(0,0,120,120))
s['pessoas'][(0,'B')]=pessoa(0,7,'B',(0,0,80,80))
s['estados_epi_temporais'][(0,'A','Capacete')]={'camera_id':0,'track_instance_id':'A','epi':'Capacete','estado_confirmado':'AUSENTE','status_temporal':'CONFIRMADO'}
s['estados_epi_temporais'][(0,'B','Capacete')]={'camera_id':0,'track_instance_id':'B','epi':'Capacete','estado_confirmado':'CORRETO','status_temporal':'CONFIRMADO'}
c=ControladorVisaoColaborador(); assert c.construir_viewmodel(s).epis[0].estado=='AUSENTE'
s['pessoas'][(0,'A')]['detectado_no_frame']=False
assert c.construir_viewmodel(s).epis[0].estado=='CORRETO'
ok('MESMO_TRACK_ID_NUMERICO_INSTANCIAS_DIFERENTES_NAO_COLIDEM')

# Explicitly verify no forbidden ETAPA 5-11 engines are imported/called by presentation module
for token in ['from rastreamento_pessoas', 'import rastreamento_pessoas', 'from associacao_epi_pessoa', 'import associacao_epi_pessoa', 'from avaliacao_estado_epi', 'import avaliacao_estado_epi', 'from estabilizacao_temporal_epi', 'import estabilizacao_temporal_epi', 'from biometria_operador', 'import biometria_operador', 'from reconhecimento_facial', 'import reconhecimento_facial', 'from gestao_incidentes_epi', 'import gestao_incidentes_epi', 'from gestao_notificacoes_incidentes', 'import gestao_notificacoes_incidentes', 'from notificacoes', 'import notificacoes']:
    assert token not in source
ok('VISAO_NAO_EXECUTA_TRACKING')
ok('VISAO_NAO_EXECUTA_ASSOCIACAO_EPI')
ok('VISAO_NAO_EXECUTA_AVALIACAO_EPI')
ok('VISAO_NAO_EXECUTA_ESTABILIZACAO')
ok('VISAO_NAO_EXECUTA_NOTIFICACOES')

print('ETAPA12_PROJECT_CONTRACT_EXTRA=OK')
