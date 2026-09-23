const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'
).replace(/\/$/, '');

let contexto = {
  perfil: 'GERENCIAL',
  matricula: null,
};

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

export function setApiContext({ perfil, matricula } = {}) {
  contexto = {
    perfil: String(perfil || 'GERENCIAL').trim().toUpperCase(),
    matricula: matricula ? String(matricula).trim() : null,
  };
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

async function apiRequest(path, options = {}) {
  const {
    method = 'GET',
    body,
    headers = {},
    signal,
  } = options;

  const requestHeaders = {
    'X-Perfil': contexto.perfil,
    ...headers,
  };

  if (contexto.matricula) {
    requestHeaders['X-Matricula'] = contexto.matricula;
  }

  let requestBody = body;

  if (
    body !== undefined &&
    body !== null &&
    !(body instanceof FormData)
  ) {
    requestHeaders['Content-Type'] =
      requestHeaders['Content-Type'] ||
      'application/json';

    if (
      requestHeaders['Content-Type'].includes(
        'application/json'
      )
    ) {
      requestBody = JSON.stringify(body);
    }
  }

  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}${path}`,
      {
        method,
        headers: requestHeaders,
        body: requestBody,
        signal,
      }
    );
  } catch (error) {
    throw new ApiError(
      'BACKEND_INDISPONIVEL',
      0,
      {
        sucesso: false,
        erro: 'BACKEND_INDISPONIVEL',
      }
    );
  }

  const contentType =
    response.headers.get('content-type') || '';

  let payload = null;

  if (
    contentType.includes(
      'application/json'
    )
  ) {
    payload = await response.json();
  } else {
    const text = await response.text();

    payload = text
      ? {
          sucesso: response.ok,
          conteudo: text,
        }
      : {};
  }

  if (
    !response.ok ||
    payload?.sucesso === false
  ) {
    const code =
      payload?.erro ||
      `HTTP_${response.status}`;

    throw new ApiError(
      code,
      response.status,
      payload
    );
  }

  return payload;
}

export const camerasApi = {
  listar: () =>
    apiRequest('/api/cameras'),

  statusGeral: () =>
    apiRequest('/api/cameras/status'),

  obter: (cameraUid) =>
    apiRequest(
      `/api/cameras/${encodeURIComponent(
        cameraUid
      )}`
    ),

  obterStatus: (cameraUid) =>
    apiRequest(
      `/api/cameras/${encodeURIComponent(
        cameraUid
      )}/status`
    ),

  obterVinculos: (cameraUid) =>
    apiRequest(
      `/api/cameras/${encodeURIComponent(
        cameraUid
      )}/vinculos`
    ),

  buscarRede: () =>
    apiRequest(
      '/api/cameras/rede/buscar',
      {
        method: 'POST',
        body: {},
      }
    ),

  testarRede: (payload) =>
    apiRequest(
      '/api/cameras/rede/testar',
      {
        method: 'POST',
        body: payload,
      }
    ),

  cadastrarRede: (payload) =>
    apiRequest(
      '/api/cameras/rede',
      {
        method: 'POST',
        body: payload,
      }
    ),

  buscarUsb: () =>
    apiRequest(
      '/api/cameras/usb/buscar',
      {
        method: 'POST',
        body: {},
      }
    ),

  testarUsb: (indice) =>
    apiRequest(
      '/api/cameras/usb/testar',
      {
        method: 'POST',
        body: {
          indice,
        },
      }
    ),

  cadastrarUsb: ({
    indice,
    nome,
  }) =>
    apiRequest(
      '/api/cameras/usb',
      {
        method: 'POST',
        body: {
          indice,
          nome,
        },
      }
    ),

  editar: (
    cameraUid,
    payload
  ) =>
    apiRequest(
      `/api/cameras/${encodeURIComponent(
        cameraUid
      )}`,
      {
        method: 'PUT',
        body: payload,
      }
    ),

  remover: (cameraUid) =>
    apiRequest(
      `/api/cameras/${encodeURIComponent(
        cameraUid
      )}`,
      {
        method: 'DELETE',
      }
    ),

  iniciarPreviewTemporario: (payload) =>
    apiRequest(
      '/api/cameras/preview-temporario',
      {
        method: 'POST',
        body: payload,
      }
    ),

  iniciarPreview: (
    cameraUid
  ) =>
    apiRequest(
      `/api/cameras/${encodeURIComponent(
        cameraUid
      )}/preview`,
      {
        method: 'POST',
        body: {},
      }
    ),

  obterFramePreview: (
    sessionId
  ) =>
    apiRequest(
      `/api/cameras/preview/${encodeURIComponent(
        sessionId
      )}/frame`
    ),

  reconectarPreview: (
    sessionId
  ) =>
    apiRequest(
      `/api/cameras/preview/${encodeURIComponent(
        sessionId
      )}/reconectar`,
      {
        method: 'POST',
        body: {},
      }
    ),

  pararPreview: (
    sessionId
  ) =>
    apiRequest(
      `/api/cameras/preview/${encodeURIComponent(
        sessionId
      )}`,
      {
        method: 'DELETE',
      }
    ),
};

function montarQuery(params = {}) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([chave, valor]) => {
    if (valor === undefined || valor === null || valor === '') return;
    query.set(chave, String(valor));
  });

  const texto = query.toString();
  return texto ? `?${texto}` : '';
}

export const ambientesApi = {
  listar: (filtros = {}) =>
    apiRequest(`/api/ambientes${montarQuery(filtros)}`),

  obter: (ambienteId) =>
    apiRequest(`/api/ambientes/${encodeURIComponent(ambienteId)}`),

  detalhes: (ambienteId) =>
    apiRequest(`/api/ambientes/${encodeURIComponent(ambienteId)}/detalhes`),

  statusGeral: () =>
    apiRequest('/api/ambientes/status'),

  status: (ambienteId) =>
    apiRequest(`/api/ambientes/${encodeURIComponent(ambienteId)}/status`),

  criar: (payload) =>
    apiRequest('/api/ambientes', {
      method: 'POST',
      body: payload,
    }),

  editar: (ambienteId, payload) =>
    apiRequest(`/api/ambientes/${encodeURIComponent(ambienteId)}`, {
      method: 'PUT',
      body: payload,
    }),

  remover: (ambienteId) =>
    apiRequest(`/api/ambientes/${encodeURIComponent(ambienteId)}`, {
      method: 'DELETE',
    }),

  finalizar: (ambienteId) =>
    apiRequest(`/api/ambientes/${encodeURIComponent(ambienteId)}/finalizar`, {
      method: 'POST',
      body: {},
    }),

  listarRois: (ambienteId) =>
    apiRequest(`/api/ambientes/${encodeURIComponent(ambienteId)}/rois`),

  obterRoi: (ambienteId, cameraUid) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/rois/${encodeURIComponent(cameraUid)}`
    ),

  definirRoi: (ambienteId, cameraUid, roi) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/rois/${encodeURIComponent(cameraUid)}`,
      {
        method: 'PUT',
        body: roi,
      }
    ),

  removerRoi: (ambienteId, cameraUid) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/rois/${encodeURIComponent(cameraUid)}`,
      {
        method: 'DELETE',
      }
    ),

  previsualizarArea: (payload) =>
    apiRequest('/api/ambientes/area-monitoramento/previsualizar', {
      method: 'POST',
      body: payload,
    }),

  previewRoiSalva: (ambienteId, cameraUid, payload) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/rois/${encodeURIComponent(cameraUid)}/preview`,
      {
        method: 'POST',
        body: payload,
      }
    ),

  analisarArea: (payload) =>
    apiRequest('/api/ambientes/area-monitoramento/analisar', {
      method: 'POST',
      body: payload,
    }),

  analisarRoiSalva: (ambienteId, cameraUid, payload) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/rois/${encodeURIComponent(cameraUid)}/analisar`,
      {
        method: 'POST',
        body: payload,
      }
    ),

  prepararMaquinario: (ambienteId, payload) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/maquinario/preparar`,
      {
        method: 'POST',
        body: payload,
      }
    ),

  salvarMaquinario: (ambienteId, payload) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/maquinario`,
      {
        method: 'PUT',
        body: payload,
      }
    ),

  listarObjetos: (ambienteId) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/objetos`
    ),

  listarMaquinarios: (ambienteId) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/maquinarios`
    ),

  descartarAnaliseMaquinario: (analiseId) =>
    apiRequest(
      `/api/ambientes/analises-maquinario/${encodeURIComponent(analiseId)}`,
      {
        method: 'DELETE',
      }
    ),

  listarEpisDisponiveis: () =>
    apiRequest('/api/ambientes/epis/disponiveis'),

  obterEpis: (ambienteId) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/epis`
    ),

  definirEpis: (ambienteId, episObrigatorios) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/epis`,
      {
        method: 'PUT',
        body: {
          epis_obrigatorios: episObrigatorios,
        },
      }
    ),

  listarColaboradoresDisponiveis: () =>
    apiRequest('/api/ambientes/colaboradores/disponiveis'),

  obterColaboradores: (ambienteId) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/colaboradores`
    ),

  definirColaboradores: (ambienteId, matriculas) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/colaboradores`,
      {
        method: 'PUT',
        body: {
          matriculas,
        },
      }
    ),

  vincularColaborador: (ambienteId, matricula) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/colaboradores/${encodeURIComponent(matricula)}`,
      {
        method: 'POST',
        body: {},
      }
    ),

  desvincularColaborador: (ambienteId, matricula) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/colaboradores/${encodeURIComponent(matricula)}`,
      {
        method: 'DELETE',
      }
    ),

  revisao: (ambienteId) =>
    apiRequest(
      `/api/ambientes/${encodeURIComponent(ambienteId)}/revisao`
    ),
};

export const colaboradoresApi = {
  listar: (filtros = {}) =>
    apiRequest(
      `/api/colaboradores${montarQuery(filtros)}`
    ),

  obter: (matricula) =>
    apiRequest(
      `/api/colaboradores/${encodeURIComponent(
        matricula
      )}`
    ),

  imagem: (matricula) =>
    apiRequest(
      `/api/colaboradores/${encodeURIComponent(
        matricula
      )}/imagem`
    ),

  validarBiometria: (imagem) => {
    const form = new FormData();

    form.append(
      'imagem_biometrica',
      imagem,
      'captura_biometrica.jpg'
    );

    return apiRequest(
      '/api/colaboradores/biometria/validar',
      {
        method: 'POST',
        body: form,
      }
    );
  },

  cadastrar: ({
    matricula,
    nome,
    cargo,
    setor,
    frontal,
    esquerda,
    direita,
  }) => {
    const form = new FormData();

    form.append(
      'matricula',
      String(matricula || '').trim()
    );

    form.append(
      'nome',
      String(nome || '').trim()
    );

    form.append(
      'cargo',
      String(cargo || '').trim()
    );

    if (
      setor !== undefined &&
      setor !== null
    ) {
      form.append(
        'setor',
        String(setor).trim()
      );
    }

    if (frontal) {
      form.append(
        'imagem_frontal',
        frontal,
        'frontal.jpg'
      );
    }

    if (esquerda) {
      form.append(
        'imagem_esquerda',
        esquerda,
        'esquerda.jpg'
      );
    }

    if (direita) {
      form.append(
        'imagem_direita',
        direita,
        'direita.jpg'
      );
    }

    return apiRequest(
      '/api/colaboradores',
      {
        method: 'POST',
        body: form,
      }
    );
  },

  editar: (
    matricula,
    payload
  ) =>
    apiRequest(
      `/api/colaboradores/${encodeURIComponent(
        matricula
      )}`,
      {
        method: 'PUT',
        body: payload,
      }
    ),

  remover: (matricula) =>
    apiRequest(
      `/api/colaboradores/${encodeURIComponent(
        matricula
      )}`,
      {
        method: 'DELETE',
      }
    ),

  statusBiometria: (matricula) =>
    apiRequest(
      `/api/colaboradores/${encodeURIComponent(
        matricula
      )}/biometria/status`
    ),

  atualizarBiometria: (
    matricula,
    imagem
  ) => {
    const form = new FormData();

    form.append(
      'imagem_biometrica',
      imagem,
      'biometria.jpg'
    );

    return apiRequest(
      `/api/colaboradores/${encodeURIComponent(
        matricula
      )}/biometria`,
      {
        method: 'PUT',
        body: form,
      }
    );
  },
};

export function mensagemApi(
  error
) {
  const codigo =
    error?.payload?.erro ||
    error?.message ||
    'ERRO_DESCONHECIDO';

  const mensagens = {
    BACKEND_INDISPONIVEL:
      'Backend não conectado em http://127.0.0.1:5000.',

    NAO_AUTENTICADO:
      'Contexto de acesso não autenticado.',

    ACESSO_NEGADO:
      'Este perfil não possui permissão para esta operação.',

    CAMERA_NAO_ENCONTRADA:
      'Câmera não encontrada.',

    CAMERA_POSSUI_VINCULOS:
      'A câmera está vinculada a um ou mais ambientes.',

    CAMERA_INDISPONIVEL:
      'A câmera está indisponível no momento.',

    CAMERA_USB_INDISPONIVEL:
      'A câmera USB está indisponível.',

    STREAM_INDISPONIVEL:
      'O stream informado não está disponível.',

    STREAM_NAO_DESCOBERTO:
      'Não foi possível descobrir um stream válido.',

    PREVIEW_NAO_ENCONTRADO:
      'A sessão de preview não existe mais.',

    FRAME_PREVIEW_NAO_RECEBIDO:
      'Não foi possível receber um frame da câmera.',

    FONTE_OU_CANDIDATO_OBRIGATORIO:
      'Informe uma URL ou selecione uma câmera descoberta.',

    URL_STREAM_OBRIGATORIA:
      'Informe a URL do stream.',

    NOME_OBRIGATORIO:
      'Informe o nome da câmera.',

    NOME_CAMERA_OBRIGATORIO:
      'Informe o nome da câmera.',

    NOME_AMBIENTE_OBRIGATORIO:
      'Informe o nome do ambiente.',

    NOME_AMBIENTE_JA_EXISTE:
      'Já existe um ambiente com esse nome.',

    AMBIENTE_NAO_ENCONTRADO:
      'Ambiente não encontrado.',

    DESCRICAO_AMBIENTE_MUITO_LONGA:
      'A descrição do ambiente deve possuir no máximo 500 caracteres.',

    CAMERA_NAO_VINCULADA_AO_AMBIENTE:
      'A câmera não está vinculada a este ambiente.',

    ROI_INVALIDA:
      'A área de monitoramento informada é inválida.',

    ROI_NAO_DEFINIDA:
      'A área de monitoramento ainda não foi definida.',

    EPI_NAO_DISPONIVEL:
      'Um ou mais EPIs selecionados não existem no catálogo do backend.',

    EPIS_OBRIGATORIOS_INVALIDOS:
      'A lista de EPIs obrigatórios é inválida.',

    AMBIENTE_COM_PENDENCIAS:
      'O ambiente ainda possui pendências para finalização.',

    MATRICULA_OBRIGATORIA:
      'Informe a matrícula do colaborador.',

    MATRICULA_INVALIDA:
      'A matrícula informada é inválida.',

    MATRICULA_JA_CADASTRADA:
      'Já existe um colaborador com essa matrícula.',

    CARGO_OBRIGATORIO:
      'Informe o cargo do colaborador.',

    IMAGEM_BIOMETRICA_OBRIGATORIA:
      'Capture a biometria facial antes de salvar.',

    CAPTURAS_BIOMETRICAS_INCOMPLETAS:
      'Capture as três referências: frente, esquerda e direita.',

    CAPTURA_BIOMETRICA_AUSENTE:
      'Uma das capturas biométricas está ausente.',

    BIOMETRIA_INVALIDA:
      'A captura facial não passou na validação biométrica.',

    ROSTO_NAO_DETECTADO:
      'Nenhum rosto utilizável foi detectado na captura.',

    ZERO_ROSTOS_UTILIZAVEIS:
      'Nenhum rosto utilizável foi detectado na captura.',

    MULTIPLOS_ROSTOS_UTILIZAVEIS:
      'Mantenha apenas um rosto visível durante a captura.',

    COLABORADOR_NAO_ENCONTRADO:
      'Colaborador não encontrado.',

    COLABORADOR_POSSUI_VINCULOS:
      'O colaborador está vinculado a um ou mais ambientes e não pode ser removido.',

    BIOMETRIA_JA_EXISTENTE:
      'Já existe biometria cadastrada para esta matrícula.',

    ANALISE_MAQUINARIO_NAO_ENCONTRADA:
      'A análise temporária de maquinário não foi encontrada.',
  };

  return (
    mensagens[codigo] ||
    codigo
  );
}