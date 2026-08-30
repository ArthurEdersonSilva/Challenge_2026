import copy
import importlib.util
import sys
from pathlib import Path

BASE = Path('/mnt/data/etapa14_final')
sys.path.insert(0, str(BASE))

from metricas_runtime import GestorMetricasRuntime
from estado_sistema import EstadoSistema, EstadoAmbiente, CAMERA_ONLINE, CAMERA_OFFLINE, CAMERA_RECONECTANDO
from visao_gerente import ControladorVisaoGerente


class FakeClock:
    def __init__(self, value=0.0):
        self.value = float(value)
    def __call__(self):
        return self.value
    def advance(self, dt):
        self.value += float(dt)
        return self.value


def ok(name, cond=True):
    if not cond:
        raise AssertionError(name)
    print(f'{name}=OK')


clock = FakeClock()
g = GestorMetricasRuntime(relogio=clock, janela_fps_segundos=2.0, max_amostras_latencia=3)
g.sincronizar_ambiente('A', [1,2])
s0 = g.snapshot({1: CAMERA_ONLINE, 2: CAMERA_ONLINE})
ok('METRICAS_INICIAIS_SAO_NONE', s0.fps_global is None and all(v is None for v in s0.fps_por_camera.values()) and s0.latencia_ppe_ms is None and s0.latencia_pose_ms is None and s0.latencia_biometria_ms is None and s0.latencia_pipeline_ms is None)
ok('METRICAS_NAO_INVENTAM_ZERO', all(v is None for v in [s0.fps_global, s0.latencia_ppe_ms, s0.latencia_pose_ms, s0.latencia_biometria_ms, s0.latencia_pipeline_ms]))

# FPS real por câmera: apenas registrar_frame_real conta.
g.registrar_frame_real(1, CAMERA_ONLINE, clock())
clock.advance(0.1); g.registrar_frame_real(1, CAMERA_ONLINE, clock())
clock.advance(0.1); g.registrar_frame_real(1, CAMERA_ONLINE, clock())
s = g.snapshot({1: CAMERA_ONLINE, 2: CAMERA_ONLINE}, clock())
ok('FPS_CAMERA_USA_FRAMES_REAIS', abs(s.fps_por_camera[1] - 10.0) < 1e-9)
ok('FPS_CAMERA_ISOLADO_POR_CAMERA_ID', s.fps_por_camera[2] is None)

# FPS global é ciclo do pipeline, não soma de câmeras.
g.registrar_ciclo_pipeline(clock())
clock.advance(0.2); g.registrar_ciclo_pipeline(clock())
clock.advance(0.2); g.registrar_ciclo_pipeline(clock())
s = g.snapshot({1: CAMERA_ONLINE, 2: CAMERA_ONLINE}, clock())
ok('FPS_GLOBAL_MEDE_CICLOS_PIPELINE', abs(s.fps_global - 5.0) < 1e-9)
ok('FPS_GLOBAL_NAO_SOMA_FPS_CAMERAS', s.fps_global != sum(v or 0 for v in s.fps_por_camera.values()))

# Latências reais em ms e média móvel.
g.registrar_latencia_ppe(12.0); g.registrar_latencia_ppe(18.0)
g.registrar_latencia_pose(20.0); g.registrar_latencia_pose(40.0)
g.registrar_latencia_pipeline(50.0); g.registrar_latencia_pipeline(70.0)
s = g.snapshot({1: CAMERA_ONLINE, 2: CAMERA_ONLINE}, clock())
ok('LATENCIA_PPE_MEDIDA_EM_MS', s.latencia_ppe_ms == 15.0)
ok('LATENCIA_POSE_MEDIDA_EM_MS', s.latencia_pose_ms == 30.0)
ok('LATENCIA_PIPELINE_MEDIDA_EM_MS', s.latencia_pipeline_ms == 60.0)

# Biometria: None não cria nem zera amostra.
g2 = GestorMetricasRuntime(relogio=clock)
g2.sincronizar_ambiente('A', [1])
g2.registrar_latencia_biometria(None)
ok('LATENCIA_BIOMETRIA_SO_ATUALIZA_QUANDO_EXECUTADA', g2.snapshot({1: CAMERA_ONLINE}).latencia_biometria_ms is None)
g2.registrar_latencia_biometria(33.0)
g2.registrar_latencia_biometria(None)
ok('BIOMETRIA_FRAME_SEM_JOB_NAO_ESCREVE_ZERO', g2.snapshot({1: CAMERA_ONLINE}).latencia_biometria_ms == 33.0)

# Relógio monotônico/injetável.
before = clock()
clock.advance(0.25)
ok('MEDICAO_USA_RELOGIO_MONOTONICO', g.agora() == before + 0.25)
g.registrar_latencia_ppe(-1)
ok('METRICA_NEGATIVA_NUNCA_E_PUBLICADA', g.snapshot({1: CAMERA_ONLINE, 2: CAMERA_ONLINE}).latencia_ppe_ms >= 0)

# Offline/reconectando nunca publicam FPS fictício.
g3 = GestorMetricasRuntime(relogio=clock)
g3.sincronizar_ambiente('A', [1])
g3.registrar_frame_real(1, CAMERA_ONLINE, clock()); clock.advance(.1); g3.registrar_frame_real(1, CAMERA_ONLINE, clock())
ok('CAMERA_OFFLINE_NAO_PUBLICA_FPS_FALSO', g3.snapshot({1: CAMERA_OFFLINE}).fps_por_camera[1] is None)
g3.registrar_frame_real(1, CAMERA_RECONECTANDO, clock())
ok('CAMERA_RECONECTANDO_NAO_GERA_FRAME_FICTICIO', g3.snapshot({1: CAMERA_RECONECTANDO}).fps_por_camera[1] is None)
# Reconexão começa janela limpa: primeiro frame ainda None.
g3.registrar_frame_real(1, CAMERA_ONLINE, clock())
ok('CAMERA_RECONEXAO_REINICIA_JANELA_FPS', g3.snapshot({1: CAMERA_ONLINE}).fps_por_camera[1] is None)

# Troca de ambiente remove câmera antiga e zera janelas específicas.
g3.sincronizar_ambiente('B', [7])
s = g3.snapshot({7: CAMERA_ONLINE})
ok('TROCA_AMBIENTE_REMOVE_METRICAS_CAMERAS_ANTIGAS', set(s.fps_por_camera) == {7})
ok('TROCA_AMBIENTE_INICIA_JANELAS_LIMPAS', s.fps_por_camera[7] is None and s.fps_global is None)

# EstadoSistema é a fonte publicada.
estado = EstadoSistema('MONITORAMENTO', EstadoAmbiente(ambiente_id='A', nome='A', carregado=True, camera_ids=[1]))
estado.registrar_camera(1, 'CAM 01', 'usb', status=CAMERA_ONLINE)
metricas = g2.snapshot({1: CAMERA_ONLINE})
estado.publicar_metricas_runtime(metricas.fps_global, metricas.fps_por_camera, metricas.latencia_ppe_ms, metricas.latencia_pose_ms, metricas.latencia_biometria_ms, metricas.latencia_pipeline_ms)
snap = estado.snapshot()
ok('METRICAS_PUBLICADAS_NO_ESTADO_SISTEMA', snap['metricas_runtime']['latencia_biometria_ms'] == 33.0)
ok('SNAPSHOT_EXPOE_METRICAS_RUNTIME', set(['fps_global','fps_por_camera','latencia_ppe_ms','latencia_pose_ms','latencia_biometria_ms','latencia_pipeline_ms']).issubset(snap['metricas_runtime']))
ok('GESTOR_METRICAS_NAO_VIRA_FONTE_DE_VERDADE_PARA_UI', 'GestorMetricasRuntime' not in (BASE/'visao_gerente.py').read_text())

# Troca ambiente no EstadoSistema limpa fps por câmera da própria fonte publicada.
estado.publicar_metricas_runtime(5.0, {1: 9.0}, 10, 20, 30, 40)
estado.ativar_ambiente_perfil('B','B',True,[],[],{})
ok('ESTADOSISTEMA_TROCA_AMBIENTE_LIMPA_FPS_CAMERA', estado.snapshot()['metricas_runtime']['fps_por_camera'] == {})

# Visão gerente consome somente snapshot de métricas.
ctrl = ControladorVisaoGerente()
snap_ui = {
    'ambiente': {'ambiente_id':'A','nome':'Area','camera_ids':(1,), 'epis_obrigatorios':()},
    'cameras': {1:{'nome':'CAM 01','status':'ONLINE','ativa':True}},
    'pessoas': {}, 'estados_epi_temporais': {}, 'incidentes': {}, 'notificacoes_incidentes': {},
    'metricas_runtime': {'fps_global':8.5,'fps_por_camera':{1:9.5},'latencia_ppe_ms':40.0,'latencia_pose_ms':30.0,'latencia_biometria_ms':25.0,'latencia_pipeline_ms':80.0}
}
vm = ctrl.construir_viewmodel(copy.deepcopy(snap_ui))
ok('VISAO_GERENTE_CONSOME_METRICAS_DO_SNAPSHOT', vm.metricas.fps_global == 8.5 and vm.metricas.fps_por_camera[1] == 9.5)

# Contrato arquitetural estático: módulo de métricas não executa pipeline.
metric_src = (BASE/'metricas_runtime.py').read_text()
for name, token in [
    ('METRICAS_NAO_EXECUTAM_YOLO','ultralytics'),
    ('METRICAS_NAO_EXECUTAM_POSE','rastreamento_pessoas'),
    ('METRICAS_NAO_EXECUTAM_DEEPFACE','deepface'),
    ('METRICAS_NAO_EXECUTAM_TRACKING','GerenciadorRastreamentoPessoas'),
    ('METRICAS_NAO_DECIDEM_EPI','avaliacao_estado_epi'),
    ('METRICAS_NAO_CRIAM_INCIDENTE','GestorIncidentesEPI'),
    ('METRICAS_NAO_ENVIAM_NOTIFICACAO','GestorNotificacoesIncidentes'),
]:
    ok(name, token not in metric_src)

main_src = (BASE/'main.py').read_text()
ok('LATENCIA_PIPELINE_TERMINA_ANTES_RENDERIZACAO', main_src.index('gestor_metricas_runtime.registrar_latencia_pipeline') < main_src.index('renderizar_visao_gerente(', main_src.index('def main():')))
ok('G_NAO_ALTERA_FPS_PIPELINE', 'modo_visual_monitoramento = "GERENTE"' in main_src and 'registrar_ciclo_pipeline' in main_src)
ok('C_NAO_ALTERA_FPS_PIPELINE', 'modo_visual_monitoramento = "COLABORADOR"' in main_src and 'registrar_ciclo_pipeline' in main_src)
ok('CAMERA_AMPLIADA_NAO_ALTERA_MEDICAO_MULTICAMERA', 'camera_selecionada_id' not in metric_src)
ok('VER_TODAS_NAO_ALTERA_MEDICAO_MULTICAMERA', 'VER TODAS' not in metric_src)

# Multicâmera independente.
g4 = GestorMetricasRuntime(relogio=clock)
g4.sincronizar_ambiente('A', [1,2,3])
t0=clock(); g4.registrar_frame_real(1,CAMERA_ONLINE,t0); g4.registrar_frame_real(2,CAMERA_ONLINE,t0)
clock.advance(.1); g4.registrar_frame_real(1,CAMERA_ONLINE,clock())
clock.advance(.1); g4.registrar_frame_real(1,CAMERA_ONLINE,clock()); g4.registrar_frame_real(2,CAMERA_ONLINE,clock())
s=g4.snapshot({1:CAMERA_ONLINE,2:CAMERA_ONLINE,3:CAMERA_OFFLINE})
ok('DUAS_CAMERAS_FPS_INDEPENDENTE', s.fps_por_camera[1] != s.fps_por_camera[2])
ok('CAMERA_LENTA_NAO_SUBSTITUI_FPS_DA_OUTRA', s.fps_por_camera[1] is not None and s.fps_por_camera[2] is not None)
ok('CAMERA_OFFLINE_NAO_REMOVE_METRICA_DAS_ONLINE', s.fps_por_camera[3] is None and s.fps_por_camera[1] is not None)
g4.atualizar_status_camera(3,CAMERA_RECONECTANDO)
ok('CAMERA_RECONECTANDO_NAO_BLOQUEIA_METRICAS_GLOBAIS', g4.snapshot({1:CAMERA_ONLINE,2:CAMERA_ONLINE,3:CAMERA_RECONECTANDO}).fps_por_camera[1] is not None)

print('ALL_ETAPA14_TESTS=OK')
