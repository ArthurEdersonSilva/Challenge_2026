from __future__ import annotations

import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ok(name, cond):
    if not cond:
        raise AssertionError(name)
    print(f"{name}=OK")


def source(name):
    return (HERE / name).read_text(encoding="utf-8")


def imports_of(name):
    tree = ast.parse(source(name), filename=name)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


main = source("main.py")
notif_mgr = source("gestao_notificacoes_incidentes.py")
notif_driver = source("notificacoes.py")
metricas_runtime = source("metricas_runtime.py")
objetos_globais = source("objetos_globais.py")
cadastrar_usuario = source("cadastrar_usuario.py")
reconhecimento_facial = source("reconhecimento_facial.py")
metricas_det = source("metricas_deteccao.py")
avaliar_offline = source("avaliar_modelo_epi.py")
relatorio_offline = source("relatorio_avaliacao_epi.py")
test15 = source("test_etapa15.py")

# Arquitetura: incidentes apenas pela ETAPA 10.
ok("INCIDENTE_SOMENTE_ETAPA10", "GestorIncidentesEPI" in main and "decision_engine" not in imports_of("main.py") and "garantir_incidente_epi_atomico" not in main)

# Notificação: main orquestra somente o gestor da ETAPA 11 e não drivers diretamente.
ok("NOTIFICACAO_SOMENTE_ETAPA11", "GestorNotificacoesIncidentes" in main and "enviar_email_incidente" not in main and "reproduzir_audio" not in main)

# Biometria: caminho atual assíncrono; cadastro não é chamado pelo main.
ok("BIOMETRIA_SOMENTE_CAMINHO_ATUAL", "GerenciadorBiometriaAssincrona" in main and "cadastrar_usuario" not in main and "executar_cadastro" not in main)

# Avaliação EPI: único caminho semântico individual atual.
legacy_epi_terms = (
    "estado_temporal_epis",
    "presenca_global",
    "ausencia_explicita_global",
    "FRAMES_CONFIRMAR_EPI_PRESENTE",
    "FRAMES_CONFIRMAR_EPI_AUSENTE",
    "FRAMES_SEM_EVIDENCIA_PARA_AUSENCIA",
    "def calcular_severidade_epi",
    "def analisar_epis_frame",
)
ok("AVALIACAO_EPI_SOMENTE_CAMADAS_ATUAIS", "avaliar_estados_camera" in main and "estabilizar_estados_camera" in main and not any(t in main for t in legacy_epi_terms))
ok("STATUS_EPI_AGREGADO_LEGADO_REMOVIDO", not any(t in main for t in legacy_epi_terms))

# Uma única inferência best.pt no main: a função preservada analisar_epis_cameras.
ok("UMA_UNICA_INFERENCIA_BEST_PT", main.count("modelo.predict(") == 1)

# Não existe vínculo permanente funcionário -> EPI nos módulos de cadastro/biometria.
combined_identity = cadastrar_usuario + reconhecimento_facial
forbidden_identity_epi = ("EPIS_OBRIGATORIOS", "epis_obrigatorios", "epi_obrigatorio")
ok("SEM_VINCULO_PERSISTENTE_FUNCIONARIO_EPI", not any(t in combined_identity for t in forbidden_identity_epi))

# objetos_globais continua restrito a objetos/maquinários, sem identidade de pessoa.
forbidden_global_person = ("PessoaTrack", "track_instance_id", "matricula", "DeepFace", "ReconhecedorFacial")
ok("OBJETOS_GLOBAIS_NAO_IDENTIFICAM_PESSOAS", not any(t in objetos_globais for t in forbidden_global_person))

# APIs legadas de notificação realmente removidas.
legacy_notif = (
    "def atualizar_notificacoes",
    "def obter_alertas_ativos",
    "def obter_alerta_principal",
    "def limpar_notificacoes",
    "def encerrar_notificacoes",
    "def criar_chave_notificacao",
    "def mensagem_educativa",
)
ok("APIS_LEGADAS_NOTIFICACAO_REMOVIDAS", not any(t in notif_driver for t in legacy_notif))

# Drivers aprovados permanecem.
ok("DRIVERS_ETAPA11_PRESERVADOS", all(t in notif_driver for t in ("def mensagem_incidente", "def reproduzir_audio", "def enviar_email_incidente")))

# UI é apresentação: controladores/renderização aparecem depois do pipeline operacional.
pos_pipeline = main.index("processar_notificacoes_incidentes()", main.index("elif estado_sistema.fase_execucao == config.ESTADO_MONITORAMENTO"))
pos_snapshot = main.index("snapshot_interface", pos_pipeline)
ok("UI_NAO_CONTROLA_PIPELINE_CAMERAS", pos_snapshot > pos_pipeline and "renderizar_visao_gerente" in main[pos_snapshot:])

# Métricas de runtime e offline não se importam nem misturam conceitos.
offline_imports = imports_of("avaliar_modelo_epi.py") | imports_of("metricas_deteccao.py") | imports_of("relatorio_avaliacao_epi.py")
ok("METRICAS_RUNTIME_SEPARADAS_AVALIACAO_OFFLINE", "metricas_runtime" not in offline_imports and "estado_sistema" not in offline_imports and "mAP" not in metricas_runtime and "Precision" not in metricas_runtime and "Recall" not in metricas_runtime)

# Teste ETAPA15 não contém caminho absoluto do sandbox.
ok("TEST_ETAPA15_PORTATIL", "/mnt/data/etapa14_final" not in test15 and "ETAPA15_BASE_OPERACIONAL" in test15)

# Shutdown dinâmico dos workers.
from gestao_notificacoes_incidentes import GestorNotificacoesIncidentes


class EstadoFake:
    def __init__(self):
        self.consultas = 0

    def obter_incidentes_para_notificacao(self):
        self.consultas += 1
        return []


estado = EstadoFake()
gestor = GestorNotificacoesIncidentes(
    estado,
    ativar_visual=False,
    ativar_audio=False,
    ativar_email=False,
    iniciar_workers=True,
)
gestor.encerrar(timeout_segundos=0.6)
ok("WORKERS_NOTIFICACAO_ENCERRAM", all(not w.is_alive() for w in gestor._workers))
# Segunda chamada deve ser segura e não reativar nada.
gestor.encerrar(timeout_segundos=0.1)
ok("ENCERRAR_NOTIFICACOES_E_IDEMPOTENTE", gestor._parar.is_set() and all(not w.is_alive() for w in gestor._workers))
# Após encerramento processar retorna sem consultar/incorporar novos jobs.
antes = estado.consultas
ret = gestor.processar()
ok("NENHUM_JOB_NOVO_APOS_ENCERRAMENTO", ret is False and estado.consultas == antes and gestor.fila_audio.empty() and gestor.fila_email.empty())

# main encerra explicitamente notificações antes dos demais recursos.
finally_pos = main.index("finally:", main.rfind("while True"))
shutdown_tail = main[finally_pos:]
ok("MAIN_ENCERRA_GESTOR_NOTIFICACOES", "gestor_notificacoes_incidentes.encerrar()" in shutdown_tail)

print("ALL_ETAPA17_TESTS=OK")
