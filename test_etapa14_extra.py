from pathlib import Path
import hashlib

BASE=Path('/mnt/data/etapa14_final')
PREV=Path('/mnt/data/etapa13_final')

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ok(n,c=True):
    if not c: raise AssertionError(n)
    print(f'{n}=OK')

preservados = [
'config.py','visao_colaborador.py','rastreamento_pessoas.py','associacao_epi_pessoa.py',
'avaliacao_estado_epi.py','estabilizacao_temporal_epi.py','biometria_operador.py',
'reconhecimento_facial.py','cadastrar_usuario.py','gestao_incidentes_epi.py',
'gestao_notificacoes_incidentes.py','notificacoes.py','ambientes.py','camera_registry.py'
]
for nome in preservados:
    ok(f'BYTE_IDENTICAL_{nome.replace(".","_").upper()}', sha(BASE/nome)==sha(PREV/nome))

ok('VISAO_COLABORADOR_CONTINUA_FUNCIONAL', sha(BASE/'visao_colaborador.py')==sha(PREV/'visao_colaborador.py'))
ok('SEM_OTIMIZACAO_CONFIG', sha(BASE/'config.py')==sha(PREV/'config.py'))
ok('SEM_OTIMIZACAO_TRACKING', sha(BASE/'rastreamento_pessoas.py')==sha(PREV/'rastreamento_pessoas.py'))
ok('SEM_OTIMIZACAO_BIOMETRIA', sha(BASE/'biometria_operador.py')==sha(PREV/'biometria_operador.py'))
ok('SEM_OTIMIZACAO_ASSOCIACAO', sha(BASE/'associacao_epi_pessoa.py')==sha(PREV/'associacao_epi_pessoa.py'))
ok('SEM_OTIMIZACAO_AVALIACAO_EPI', sha(BASE/'avaliacao_estado_epi.py')==sha(PREV/'avaliacao_estado_epi.py'))
ok('SEM_OTIMIZACAO_ESTABILIZACAO', sha(BASE/'estabilizacao_temporal_epi.py')==sha(PREV/'estabilizacao_temporal_epi.py'))
ok('SEM_OTIMIZACAO_INCIDENTES', sha(BASE/'gestao_incidentes_epi.py')==sha(PREV/'gestao_incidentes_epi.py'))
ok('SEM_OTIMIZACAO_NOTIFICACOES', sha(BASE/'gestao_notificacoes_incidentes.py')==sha(PREV/'gestao_notificacoes_incidentes.py'))

metric_src=(BASE/'metricas_runtime.py').read_text()
ok('SEM_PERSISTENCIA_PERFORMANCE', all(t not in metric_src.lower() for t in ['csv','sqlite','pandas','open(','write(','gpu','cpu_percent','memory','vram','p95','p99']))
main=(BASE/'main.py').read_text()
# O bloco de renderização continua posterior à publicação das métricas.
pub=main.index('publicar_metricas_runtime(contexto_metricas)', main.index('def main():'))
render=main.index('renderizar_visao_gerente(', main.index('def main():'))
ok('PIPELINE_METRICA_ANTES_RENDERIZACAO', pub < render)
# G/C permanecem e não estão no agregador.
ok('TROCA_MODO_VISUAL_NAO_AFETA_PIPELINE', 'modo_visual_monitoramento = "GERENTE"' in main and 'modo_visual_monitoramento = "COLABORADOR"' in main and 'modo_visual_monitoramento' not in metric_src)
# UI gerente não importa gestor de métricas.
vg=(BASE/'visao_gerente.py').read_text()
ok('VISAO_GERENTE_NAO_CONSULTA_GESTOR_METRICAS', 'GestorMetricasRuntime' not in vg and 'metricas_runtime import' not in vg)
ok('VISAO_GERENTE_CONTINUA_FUNCIONAL', 'renderizar_visao_gerente' in vg and 'ControladorVisaoGerente' in vg)
print('ETAPA14_EXTRA_TESTS=OK')
