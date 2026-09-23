import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Video,
  Layers,
  FileCheck,
  PlusCircle,
  Settings,
  LogOut,
  Bell,
  Search,
  CheckCircle2,
  AlertTriangle,
  Play,
  Square,
  RefreshCw,
  Trash2,
  Edit,
  ExternalLink,
  Filter,
  Maximize2,
  Users,
  Eye,
  Camera,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  Cpu,
  Clock,
  ArrowRight,
  User,
  Lock,
  ArrowLeft,
  FolderOpen,
  UserPlus,
  Upload,
  X,
} from 'lucide-react';

import { ambientesApi, camerasApi, colaboradoresApi, mensagemApi, setApiContext } from './api.js';

// ==========================================
// 1. LOGO CODESPHERE (SVG Vetorial)
// ==========================================
const CodeSphereLogo = ({ size = 38, className = '' }) => (
  <div
    className={`relative flex items-center justify-center ${className}`}
    style={{ width: size, height: size }}
  >
    <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-md">
      <defs>
        <linearGradient id="orbitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FF7412" />
          <stop offset="100%" stopColor="#fb5b01" />
        </linearGradient>
      </defs>
      <circle
        cx="50"
        cy="50"
        r="38"
        fill="none"
        stroke="url(#orbitGrad)"
        strokeWidth="6"
        strokeDasharray="170 30"
        strokeLinecap="round"
        transform="rotate(-30 50 50)"
      />
      <circle cx="85" cy="40" r="6" fill="#FF7412" />
      <circle cx="15" cy="60" r="4.5" fill="#fb5b01" />
      <circle cx="50" cy="50" r="28" fill="#18181b" fillOpacity="0.8" />
      <path
        d="M42 38L32 50L42 62"
        fill="none"
        stroke="#FFFFFF"
        strokeWidth="4.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M58 38L68 50L58 62"
        fill="none"
        stroke="#FFFFFF"
        strokeWidth="4.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <line
        x1="53"
        y1="36"
        x2="47"
        y2="64"
        stroke="#FF7412"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  </div>
);

// ==========================================
// 2. COMPONENTE DE ESTADO VAZIO
// ==========================================
const EmptyState = ({
  icon: Icon = FolderOpen,
  title,
  description,
  actionText,
  onAction,
}) => (
  <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center flex flex-col items-center justify-center my-4 shadow-sm">
    <div className="w-16 h-16 rounded-full bg-orange-50 flex items-center justify-center text-[#FF7412] mb-4">
      <Icon className="w-8 h-8" />
    </div>
    <h3 className="text-base font-semibold text-slate-800 mb-1">{title}</h3>
    <p className="text-sm text-slate-500 max-w-sm mb-6">{description}</p>
    {actionText && onAction && (
      <button
        onClick={onAction}
        className="px-4 py-2 bg-[#FF7412] hover:bg-[#e0620a] text-white font-medium text-sm rounded-lg transition-colors inline-flex items-center gap-2 shadow-sm"
      >
        <PlusCircle className="w-4 h-4" />
        {actionText}
      </button>
    )}
  </div>
);

// ==========================================
// 3. TELA DE LOGIN DO GESTOR
// ==========================================
const LoginScreen = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('gestor@codesphere.com.br');
  const [password, setPassword] = useState('admin123');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleLogin = (e) => {
    e.preventDefault();
    setErrorMsg('');
    setIsLoading(true);

    setTimeout(() => {
      if (email === 'gestor@codesphere.com.br' && password === 'admin123') {
        setIsLoading(false);
        onLoginSuccess({
          name: 'Arthur Gouvea',
          role: 'Gestor de Segurança & IA',
          department: 'Engenharia Operacional',
          email: 'gestor@codesphere.com.br',
        });
      } else {
        setIsLoading(false);
        setErrorMsg('Credenciais inválidas. Use o e-mail e senha sugeridos.');
      }
    }, 600);
  };

  return (
    <div className="min-h-screen w-full bg-[#0d0f12] flex items-center justify-center p-4 relative overflow-hidden font-sans">
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-[#FF7412]/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-[#fb5b01]/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-md w-full bg-[#181b20] border border-slate-800 rounded-2xl p-8 shadow-2xl relative z-10">
        <div className="flex flex-col items-center text-center mb-8">
          <CodeSphereLogo size={64} className="mb-3" />
          <div className="flex items-center gap-1.5 text-2xl font-bold tracking-wider text-white">
            <span>
              Code<span className="text-[#FF7412]">Sphere</span>
            </span>
          </div>
          <span className="text-xs uppercase tracking-widest text-slate-400 font-semibold mt-0.5">
            Metaindústria Vision AI
          </span>
          <p className="text-xs text-slate-400 mt-3 max-w-xs">
            Portal de Monitoramento e Prevenção Ativa de Acidentes Industriais
          </p>
        </div>

        {errorMsg && (
          <div className="mb-5 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              E-mail do Gestor
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nome@codesphere.com.br"
                className="w-full bg-[#121418] border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-[#FF7412] transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Senha de Acesso
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-[#121418] border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-[#FF7412] transition-colors"
              />
            </div>
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                defaultChecked
                className="rounded border-slate-700 text-[#FF7412] focus:ring-0 bg-slate-900"
              />
              <span>Lembrar credenciais</span>
            </label>
            <a
              href="#recuperar"
              onClick={(e) => e.preventDefault()}
              className="hover:text-[#FF7412] transition-colors"
            >
              Esqueceu a senha?
            </a>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-4 bg-gradient-to-r from-[#FF7412] to-[#fb5b01] hover:brightness-110 active:scale-[0.99] text-white font-semibold py-2.5 rounded-lg text-sm transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#FF7412]/20"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Autenticando...</span>
              </>
            ) : (
              <>
                <span>Acessar Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-slate-800 text-center">
          <p className="text-[11px] text-slate-500">
            Dica para teste:{' '}
            <span className="text-slate-300">gestor@codesphere.com.br</span> e
            senha <span className="text-slate-300">admin123</span>
          </p>
        </div>
      </div>
    </div>
  );
};

// ==========================================
// 4. APLICAÇÃO PRINCIPAL
// ==========================================
export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [activeScreen, setActiveScreen] = useState('dashboard');
  const [currentDateTime, setCurrentDateTime] = useState('');
  const [expandedMenus, setExpandedMenus] = useState({
    cameras: true,
    ambientes: true,
    colaboradores: true,
    ocorrencias: true,
  });

  // Estados dos dados
  const [cameras, setCameras] = useState([]);
  const [camerasLoading, setCamerasLoading] = useState(false);
  const [camerasErro, setCamerasErro] = useState(null);
  const [ambientes, setAmbientes] = useState([]);
  const [ambientesLoading, setAmbientesLoading] = useState(false);
  const [ambientesErro, setAmbientesErro] = useState(null);
  const [colaboradores, setColaboradores] = useState([]);
  const [colaboradoresLoading, setColaboradoresLoading] = useState(false);
  const [colaboradoresErro, setColaboradoresErro] = useState(null);
  const [ocorrencias, setOcorrencias] = useState([]);

  // Estado para armazenar o ambiente sendo editado
  const [ambienteEmEdicao, setAmbienteEmEdicao] = useState(null);

  // Integração real com a API de câmeras.
  const carregarCameras = async () => {
    setCamerasLoading(true);
    setCamerasErro(null);

    try {
      setApiContext({ perfil: 'GERENCIAL' });
      const dados = await camerasApi.listar();
      setCameras(Array.isArray(dados.cameras) ? dados.cameras : []);
    } catch (error) {
      setCameras([]);
      setCamerasErro(mensagemApi(error));
    } finally {
      setCamerasLoading(false);
    }
  };

  useEffect(() => {
    if (!currentUser) return;
    void carregarCameras();
  }, [currentUser]);

  // Integração real com a API de Ambientes.
  const carregarAmbientes = async () => {
    setAmbientesLoading(true);
    setAmbientesErro(null);

    try {
      setApiContext({ perfil: 'GERENCIAL' });
      const dados = await ambientesApi.listar({ pagina: 1, por_pagina: 200 });
      setAmbientes(Array.isArray(dados.ambientes) ? dados.ambientes : []);
    } catch (error) {
      setAmbientes([]);
      setAmbientesErro(mensagemApi(error));
    } finally {
      setAmbientesLoading(false);
    }
  };

  useEffect(() => {
    if (!currentUser) return;
    void carregarAmbientes();
  }, [currentUser]);

  // Ações de Ambientes — persistidas no backend real.
  const handleSalvarAmbiente = async (ambienteData) => {
    try {
      setApiContext({ perfil: 'GERENCIAL' });

      if (ambienteEmEdicao?.ambiente_id) {
        await ambientesApi.editar(ambienteEmEdicao.ambiente_id, ambienteData);
        alert('Ambiente atualizado com sucesso!');
      } else {
        await ambientesApi.criar(ambienteData);
        alert('Ambiente cadastrado com sucesso!');
      }

      setAmbienteEmEdicao(null);
      await carregarAmbientes();
      setActiveScreen('consulta-ambientes');
      return { sucesso: true, erro: null };
    } catch (error) {
      return { sucesso: false, erro: mensagemApi(error) };
    }
  };

  const handleConcluirFluxoAmbiente = async () => {
    setAmbienteEmEdicao(null);
    await carregarAmbientes();
    setActiveScreen('consulta-ambientes');
  };

  const handleIniciarEdicaoAmbiente = async (ambiente) => {
    const ambienteId = ambiente?.ambiente_id;
    if (!ambienteId) return;

    try {
      setApiContext({ perfil: 'GERENCIAL' });
      const detalhes = await ambientesApi.detalhes(ambienteId);
      setAmbienteEmEdicao(detalhes);
      setActiveScreen('cadastro-ambiente');
    } catch (error) {
      alert(mensagemApi(error));
    }
  };

  const handleDeletarAmbiente = async (ambienteId) => {
    try {
      setApiContext({ perfil: 'GERENCIAL' });
      await ambientesApi.remover(ambienteId);

      if (ambienteEmEdicao?.ambiente_id === ambienteId) {
        setAmbienteEmEdicao(null);
      }

      await carregarAmbientes();
      return { sucesso: true, erro: null };
    } catch (error) {
      return { sucesso: false, erro: mensagemApi(error) };
    }
  };

  // Integração real com a API de Colaboradores.
  const carregarColaboradores = async () => {
    setColaboradoresLoading(true);
    setColaboradoresErro(null);

    try {
      setApiContext({ perfil: 'GERENCIAL' });

      const dados = await colaboradoresApi.listar({
        pagina: 1,
        por_pagina: 200,
      });

      const base = Array.isArray(dados.colaboradores)
        ? dados.colaboradores
        : [];

      // A foto frontal é buscada apenas quando existe biometria.
      // Falha ao carregar uma miniatura não remove o colaborador da lista.
      const enriquecidos = await Promise.all(
        base.map(async (colaborador) => {
          let foto = null;

          if (colaborador?.biometria_cadastrada && colaborador?.matricula) {
            try {
              const imagem = await colaboradoresApi.imagem(colaborador.matricula);
              if (imagem?.imagem_base64) {
                foto = `data:${imagem.mime_type || 'image/jpeg'};base64,${imagem.imagem_base64}`;
              }
            } catch {
              foto = null;
            }
          }

          return {
            ...colaborador,
            id: colaborador.matricula,
            foto,
          };
        })
      );

      setColaboradores(enriquecidos);
    } catch (error) {
      setColaboradores([]);
      setColaboradoresErro(mensagemApi(error));
    } finally {
      setColaboradoresLoading(false);
    }
  };

  useEffect(() => {
    if (!currentUser) return;
    void carregarColaboradores();
  }, [currentUser]);

  const handleDeletarColaborador = async (matricula) => {
    try {
      setApiContext({ perfil: 'GERENCIAL' });
      await colaboradoresApi.remover(matricula);
      await carregarColaboradores();
      return { sucesso: true, erro: null };
    } catch (error) {
      return { sucesso: false, erro: mensagemApi(error) };
    }
  };

  // Relógio do Sistema
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const dateStr = now.toLocaleDateString('pt-BR', {
        weekday: 'long',
        day: '2-digit',
        month: 'long',
        year: 'numeric',
      });
      const timeStr = now.toLocaleTimeString('pt-BR', { hour12: false });
      setCurrentDateTime(`${dateStr} | ${timeStr}`);
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const toggleSubmenu = (key) => {
    setExpandedMenus((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (!currentUser) {
    return <LoginScreen onLoginSuccess={(user) => setCurrentUser(user)} />;
  }

  return (
    <div className="flex h-screen bg-[#f1f5f9] font-sans text-slate-800 overflow-hidden">
      {/* ---------------- BARRA LATERAL (SIDEBAR) ---------------- */}
      <aside className="w-64 bg-[#111419] flex flex-col justify-between shrink-0 select-none border-r border-slate-800 z-20">
        <div>
          {/* Logo CodeSphere */}
          <div className="p-4 border-b border-slate-800/80 flex items-center gap-3">
            <CodeSphereLogo size={36} />
            <div>
              <div className="text-lg font-bold text-white tracking-wider flex items-center leading-none">
                <span>
                  Code<span className="text-[#FF7412]">Sphere</span>
                </span>
              </div>
              <span className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold block mt-1">
                EPI Vision AI
              </span>
            </div>
          </div>

          {/* Menus de Navegação */}
          <nav className="p-3 space-y-1.5 overflow-y-auto max-h-[calc(100vh-210px)]">
            <button
              onClick={() => setActiveScreen('dashboard')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                activeScreen === 'dashboard'
                  ? 'bg-gradient-to-r from-[#FF7412] to-[#fb5b01] text-white shadow-md'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </button>

            {/* Câmeras */}
            <div>
              <button
                onClick={() => toggleSubmenu('cameras')}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800/60 transition-all"
              >
                <div className="flex items-center gap-3">
                  <Video className="w-4 h-4" />
                  <span>Câmeras</span>
                </div>
                {expandedMenus.cameras ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
              </button>
              {expandedMenus.cameras && (
                <div className="pl-6 pr-1 py-1 space-y-1">
                  <button
                    onClick={() => setActiveScreen('cadastro-cameras')}
                    className={`w-full text-left py-1.5 px-3 rounded text-[11px] font-medium transition-colors ${
                      activeScreen === 'cadastro-cameras'
                        ? 'text-[#FF7412] bg-slate-800/80 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    • Cadastro de Câmeras
                  </button>
                  <button
                    onClick={() => setActiveScreen('consulta-cameras')}
                    className={`w-full text-left py-1.5 px-3 rounded text-[11px] font-medium transition-colors ${
                      activeScreen === 'consulta-cameras'
                        ? 'text-[#FF7412] bg-slate-800/80 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    • Consulta de Câmeras
                  </button>
                  <button
                    onClick={() => setActiveScreen('teste-cameras')}
                    className={`w-full text-left py-1.5 px-3 rounded text-[11px] font-medium transition-colors ${
                      activeScreen === 'teste-cameras'
                        ? 'text-[#FF7412] bg-slate-800/80 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    • Teste de Câmeras
                  </button>
                </div>
              )}
            </div>

            {/* Ambientes */}
            <div>
              <button
                onClick={() => toggleSubmenu('ambientes')}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800/60 transition-all"
              >
                <div className="flex items-center gap-3">
                  <Layers className="w-4 h-4" />
                  <span>Ambientes</span>
                </div>
                {expandedMenus.ambientes ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
              </button>
              {expandedMenus.ambientes && (
                <div className="pl-6 pr-1 py-1 space-y-1">
                  <button
                    onClick={() => {
                      setAmbienteEmEdicao(null);
                      setActiveScreen('cadastro-ambiente');
                    }}
                    className={`w-full text-left py-1.5 px-3 rounded text-[11px] font-medium transition-colors ${
                      activeScreen === 'cadastro-ambiente'
                        ? 'text-[#FF7412] bg-slate-800/80 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    • Cadastro de Ambiente
                  </button>
                  <button
                    onClick={() => setActiveScreen('consulta-ambientes')}
                    className={`w-full text-left py-1.5 px-3 rounded text-[11px] font-medium transition-colors ${
                      activeScreen === 'consulta-ambientes'
                        ? 'text-[#FF7412] bg-slate-800/80 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    • Consulta de Ambientes
                  </button>
                </div>
              )}
            </div>

            {/* Colaboradores */}
            <div>
              <button
                onClick={() => toggleSubmenu('colaboradores')}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800/60 transition-all"
              >
                <div className="flex items-center gap-3">
                  <Users className="w-4 h-4" />
                  <span>Colaboradores</span>
                </div>
                {expandedMenus.colaboradores ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
              </button>
              {expandedMenus.colaboradores && (
                <div className="pl-6 pr-1 py-1 space-y-1">
                  <button
                    onClick={() => setActiveScreen('consulta-colaboradores')}
                    className={`w-full text-left py-1.5 px-3 rounded text-[11px] font-medium transition-colors ${
                      activeScreen === 'consulta-colaboradores'
                        ? 'text-[#FF7412] bg-slate-800/80 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    • Visão Geral
                  </button>
                  <button
                    onClick={() => setActiveScreen('cadastro-colaborador')}
                    className={`w-full text-left py-1.5 px-3 rounded text-[11px] font-medium transition-colors ${
                      activeScreen === 'cadastro-colaborador'
                        ? 'text-[#FF7412] bg-slate-800/80 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    • Cadastrar Colaborador
                  </button>
                </div>
              )}
            </div>

            {/* Ocorrências */}
            <div>
              <button
                onClick={() => toggleSubmenu('ocorrencias')}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800/60 transition-all"
              >
                <div className="flex items-center gap-3">
                  <FileCheck className="w-4 h-4" />
                  <span>Ocorrências</span>
                </div>
                {expandedMenus.ocorrencias ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
              </button>
              {expandedMenus.ocorrencias && (
                <div className="pl-6 pr-1 py-1 space-y-1">
                  <button
                    onClick={() => setActiveScreen('registro-ocorrencias')}
                    className={`w-full text-left py-1.5 px-3 rounded text-[11px] font-medium transition-colors ${
                      activeScreen === 'registro-ocorrencias'
                        ? 'text-[#FF7412] bg-slate-800/80 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    • Registro de Ocorrências
                  </button>
                  <button
                    onClick={() => setActiveScreen('relatorio-geral')}
                    className={`w-full text-left py-1.5 px-3 rounded text-[11px] font-medium transition-colors ${
                      activeScreen === 'relatorio-geral'
                        ? 'text-[#FF7412] bg-slate-800/80 font-bold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    • Relatório Geral
                  </button>
                </div>
              )}
            </div>
          </nav>
        </div>

        {/* Rodapé Lateral */}
        <div className="p-3 border-t border-slate-800/80 space-y-3">
          <div className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <span className="text-[11px] font-bold text-slate-200">
                Gateway CodeSphere
              </span>
            </div>
            <p className="text-[10px] text-slate-400">Serviços operacionais</p>
          </div>

          <button
            onClick={() => setCurrentUser(null)}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Encerrar Sessão</span>
          </button>
        </div>
      </aside>

      {/* ---------------- CONTEÚDO PRINCIPAL ---------------- */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Cabeçalho */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0 z-10">
          <div className="flex items-center gap-3">
            <h1 className="text-base font-bold text-slate-800 capitalize">
              {activeScreen.replace('-', ' ')}
            </h1>
            <span className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] bg-orange-100 text-[#FF7412] font-semibold border border-orange-200">
              Pronto para API
            </span>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-right hidden md:block">
              <span className="text-xs text-slate-600 font-medium block">
                {currentDateTime}
              </span>
            </div>

            <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
              <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-[#FF7412] to-[#fb5b01] text-white flex items-center justify-center font-bold text-sm shadow-sm">
                {currentUser.name.charAt(0)}
              </div>
              <div className="text-left hidden sm:block">
                <span className="text-xs font-bold text-slate-800 block leading-tight">
                  {currentUser.name}
                </span>
                <span className="text-[10px] text-slate-500 block leading-tight">
                  {currentUser.role}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Telas dinâmicas */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-50">
          {activeScreen === 'dashboard' && (
            <DashboardEmptyView
              camerasCount={cameras.length}
              ambientesCount={ambientes.length}
              colaboradoresCount={colaboradores.length}
              ocorrenciasCount={ocorrencias.length}
              onNavigate={setActiveScreen}
            />
          )}

          {activeScreen === 'cadastro-cameras' && (
            <CadastroCamerasView
              onCadastrar={async () => {
                await carregarCameras();
                alert('Câmera registrada com sucesso!');
              }}
            />
          )}

          {activeScreen === 'consulta-cameras' && (
            <ConsultaCamerasView
              cameras={cameras}
              loading={camerasLoading}
              erro={camerasErro}
              onRefresh={carregarCameras}
              onNavigate={setActiveScreen}
            />
          )}

          {activeScreen === 'teste-cameras' && (
            <TesteCamerasView
              cameras={cameras}
              loading={camerasLoading}
              erro={camerasErro}
              onRefresh={carregarCameras}
              onNavigate={setActiveScreen}
            />
          )}

          {/* Cadastro e Edição de Ambientes */}
          {activeScreen === 'cadastro-ambiente' && (
            <CadastroAmbienteView
              ambienteEmEdicao={ambienteEmEdicao}
              camerasDisponiveis={cameras}
              onSalvarAmbiente={handleSalvarAmbiente}
              onConcluirAmbiente={handleConcluirFluxoAmbiente}
              onCancelarEdicao={() => {
                setAmbienteEmEdicao(null);
                setActiveScreen('consulta-ambientes');
              }}
            />
          )}

          {/* Consulta de Ambientes com Editar e Apagar */}
          {activeScreen === 'consulta-ambientes' && (
            <ConsultaAmbientesView
              ambientes={ambientes}
              loading={ambientesLoading}
              erro={ambientesErro}
              onRefresh={carregarAmbientes}
              onEditarAmbiente={handleIniciarEdicaoAmbiente}
              onDeletarAmbiente={handleDeletarAmbiente}
              onNavigate={setActiveScreen}
            />
          )}

          {/* Colaboradores */}
          {activeScreen === 'consulta-colaboradores' && (
            <ConsultaColaboradoresView
              colaboradores={colaboradores}
              loading={colaboradoresLoading}
              erro={colaboradoresErro}
              onRefresh={carregarColaboradores}
              onDeletarColaborador={handleDeletarColaborador}
              onNavigate={setActiveScreen}
            />
          )}

          {activeScreen === 'cadastro-colaborador' && (
            <CadastroColaboradorView
              cameras={cameras}
              camerasLoading={camerasLoading}
              onCadastrarColaborador={async () => {
                await carregarColaboradores();
                alert('Colaborador cadastrado com sucesso!');
                setActiveScreen('consulta-colaboradores');
              }}
            />
          )}

          {/* Ocorrências */}
          {activeScreen === 'registro-ocorrencias' && (
            <RegistroOcorrenciasView ocorrencias={ocorrencias} />
          )}

          {activeScreen === 'relatorio-geral' && (
            <RelatorioGeralView ocorrenciasCount={ocorrencias.length} />
          )}
        </main>
      </div>
    </div>
  );
}

// =======================================================
// SUB-TELAS
// =======================================================

// 1. DASHBOARD
function DashboardEmptyView({
  camerasCount,
  ambientesCount,
  colaboradoresCount,
  ocorrenciasCount,
  onNavigate,
}) {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-slate-900">
          Dashboard de Monitoramento
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Visão geral do sistema de detecção e segurança de EPI
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500">
              Câmeras Conectadas
            </span>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {camerasCount}{' '}
              <span className="text-xs text-slate-400 font-normal">online</span>
            </div>
          </div>
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
            <Video className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500">
              Ambientes Mapeados
            </span>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {ambientesCount}{' '}
              <span className="text-xs text-slate-400 font-normal">zonas</span>
            </div>
          </div>
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500">
              Colaboradores
            </span>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {colaboradoresCount}{' '}
              <span className="text-xs text-slate-400 font-normal">
                cadastrados
              </span>
            </div>
          </div>
          <div className="p-3 bg-purple-50 text-purple-600 rounded-lg">
            <Users className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500">
              Ocorrências Hoje
            </span>
            <div className="text-2xl font-bold text-[#FF7412] mt-1">
              {ocorrenciasCount}
            </div>
          </div>
          <div className="p-3 bg-orange-50 text-[#FF7412] rounded-lg">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
      </div>

      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
            <Camera className="w-4 h-4 text-[#FF7412]" />
            Ambientes Monitorados ao Vivo
          </h3>
          <button
            onClick={() => onNavigate('cadastro-cameras')}
            className="text-xs text-[#FF7412] hover:underline font-medium"
          >
            + Adicionar Câmera
          </button>
        </div>

        {camerasCount === 0 ? (
          <EmptyState
            icon={Camera}
            title="Nenhum feed de câmera conectado"
            description="Conecte câmeras IP, RTSP ou ONVIF da fábrica para exibir os feeds de vídeo ao vivo."
            actionText="Localizar ou Cadastrar Câmera"
            onAction={() => onNavigate('cadastro-cameras')}
          />
        ) : null}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-[#FF7412]" />
            Últimas Ocorrências Registradas
          </h3>
          {ocorrenciasCount === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title="Nenhuma ocorrência registrada no momento"
              description="Quando o modelo de visão computacional registrar ausência de EPI nas zonas industriais, os registros surgirão aqui."
            />
          ) : null}
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
            <Bell className="w-4 h-4 text-[#FF7412]" />
            Alertas do Sistema
          </h3>
          <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <span className="text-xs font-semibold text-emerald-900 block">
                Todos os serviços operacionais
              </span>
              <span className="text-[11px] text-emerald-700">
                Aguardando dados da API backend
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// 2. CADASTRO DE CÂMERAS
function CadastroCamerasView({ onCadastrar }) {
  const [nome, setNome] = useState('');
  const [usuario, setUsuario] = useState('');
  const [senha, setSenha] = useState('');
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [testando, setTestando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [buscando, setBuscando] = useState(false);
  const [statusConexao, setStatusConexao] = useState(null);
  const [resultadoTeste, setResultadoTeste] = useState(null);
  const [candidatos, setCandidatos] = useState([]);
  const [candidatoSelecionado, setCandidatoSelecionado] = useState(null);
  const [redeDetectada, setRedeDetectada] = useState(null);

  const [previewSessionId, setPreviewSessionId] = useState(null);
  const [frameSrc, setFrameSrc] = useState(null);
  const [previewInfo, setPreviewInfo] = useState(null);
  const [previewErro, setPreviewErro] = useState(null);
  const previewSessionRef = React.useRef(null);
  const previewBoxRef = React.useRef(null);

  const [manualNome, setManualNome] = useState('');
  const [manualIp, setManualIp] = useState('');
  const [manualUrl, setManualUrl] = useState('');
  const [manualUsuario, setManualUsuario] = useState('');
  const [manualSenha, setManualSenha] = useState('');
  const [mostrarSenhaManual, setMostrarSenhaManual] = useState(false);
  const [manualTestando, setManualTestando] = useState(false);
  const [manualSalvando, setManualSalvando] = useState(false);
  const [manualStatus, setManualStatus] = useState(null);
  const [manualResultado, setManualResultado] = useState(null);
  const [previewContexto, setPreviewContexto] = useState(null);

  const pararPreviewTemporario = async () => {
    const sessionId = previewSessionRef.current;
    previewSessionRef.current = null;
    setPreviewSessionId(null);

    if (!sessionId) {
      setFrameSrc(null);
      setPreviewInfo(null);
      setPreviewErro(null);
      setPreviewContexto(null);
      return;
    }

    try {
      await camerasApi.pararPreview(sessionId);
    } catch (error) {
      if (error?.payload?.erro !== 'PREVIEW_NAO_ENCONTRADO') {
        setPreviewErro(mensagemApi(error));
      }
    } finally {
      setFrameSrc(null);
      setPreviewInfo(null);
      setPreviewContexto(null);
    }
  };

  useEffect(() => {
    return () => {
      const sessionId = previewSessionRef.current;
      if (sessionId) {
        void camerasApi.pararPreview(sessionId).catch(() => {});
      }
    };
  }, []);

  useEffect(() => {
    if (!previewSessionId) return undefined;

    let cancelado = false;
    let executando = false;

    const atualizarFrame = async () => {
      if (cancelado || executando) return;
      executando = true;

      try {
        const dados = await camerasApi.obterFramePreview(previewSessionId);

        if (!cancelado && dados?.frame_base64) {
          setFrameSrc(
            `data:${dados.mime_type || 'image/jpeg'};base64,${dados.frame_base64}`
          );
          setPreviewInfo((anterior) => ({ ...anterior, ...dados }));
          setPreviewErro(null);
        }
      } catch (error) {
        if (!cancelado) {
          setPreviewErro(mensagemApi(error));
        }
      } finally {
        executando = false;
      }
    };

    void atualizarFrame();
    const timer = window.setInterval(atualizarFrame, 300);

    return () => {
      cancelado = true;
      window.clearInterval(timer);
    };
  }, [previewSessionId]);

  const limparTesteSelecionada = () => {
    setStatusConexao(null);
    setResultadoTeste(null);
    setPreviewErro(null);
  };

  const limparTesteManual = () => {
    setManualStatus(null);
    setManualResultado(null);
    setPreviewErro(null);
  };

  const protocoloCandidato = (item) => {
    if (!item) return '-';
    if (item.origem === 'usb') return 'USB';

    const candidato = item.candidato || {};
    const protocolos = Array.isArray(candidato.protocolos)
      ? candidato.protocolos.filter(Boolean)
      : [];

    return (
      protocolos.join('/') ||
      candidato.protocolo ||
      candidato.tipo ||
      'REDE'
    );
  };

  const portasCandidato = (item) => {
    if (!item || item.origem === 'usb') return '-';
    const portas = item.candidato?.portas;
    return Array.isArray(portas) && portas.length ? portas.join(', ') : '-';
  };

  const nomeCandidato = (item, index = 0) => {
    if (!item) return 'Câmera';
    if (item.origem === 'usb') {
      return item.nome_dispositivo || `Câmera USB ${item.indice ?? index}`;
    }

    const candidato = item.candidato || {};
    return (
      candidato.nome_onvif ||
      candidato.nome ||
      candidato.ip ||
      `Câmera de rede ${index + 1}`
    );
  };

  const selecionarCandidato = async (item) => {
    await pararPreviewTemporario();
    setCandidatoSelecionado(item);
    limparTesteSelecionada();
    setManualStatus(null);

    if (item.origem === 'usb') {
      setNome(item.nome_dispositivo || 'Câmera USB');
      setUsuario('');
      setSenha('');
      return;
    }

    const candidato = item.candidato || {};
    setNome(candidato.nome_onvif || candidato.nome || '');
    setUsuario('');
    setSenha('');
  };

  const handleBuscar = async () => {
    setBuscando(true);
    setCandidatos([]);
    setCandidatoSelecionado(null);
    setRedeDetectada(null);
    limparTesteSelecionada();
    await pararPreviewTemporario();

    try {
      const [rede, usb] = await Promise.allSettled([
        camerasApi.buscarRede(),
        camerasApi.buscarUsb(),
      ]);

      const encontrados = [];

      if (rede.status === 'fulfilled') {
        setRedeDetectada(rede.value.rede || null);
        const itens = rede.value.candidatos || rede.value.cameras || [];

        itens.forEach((candidato) => {
          encontrados.push({ origem: 'rede', candidato });
        });
      }

      if (usb.status === 'fulfilled') {
        (usb.value.cameras || []).forEach((camera) => {
          encontrados.push({ origem: 'usb', ...camera });
        });
      }

      setCandidatos(encontrados);

      if (!encontrados.length) {
        alert('Nenhuma câmera foi encontrada. Você pode adicioná-la manualmente abaixo.');
      }
    } catch (error) {
      alert(mensagemApi(error));
    } finally {
      setBuscando(false);
    }
  };

  const iniciarPreviewComRetry = async (payload) => {
    try {
      return await camerasApi.iniciarPreviewTemporario(payload);
    } catch (error) {
      const codigo = error?.payload?.erro || error?.message;
      if (!['STREAM_INDISPONIVEL', 'CAMERA_INDISPONIVEL'].includes(codigo)) {
        throw error;
      }

      await new Promise((resolve) => window.setTimeout(resolve, 450));
      return camerasApi.iniciarPreviewTemporario(payload);
    }
  };

  const handleTestarSelecionada = async () => {
    if (!candidatoSelecionado) {
      alert('Selecione uma câmera encontrada primeiro.');
      return;
    }

    setTestando(true);
    limparTesteSelecionada();
    await pararPreviewTemporario();

    try {
      let teste;
      let payloadPreview;

      if (candidatoSelecionado.origem === 'usb') {
        teste = await camerasApi.testarUsb(candidatoSelecionado.indice);
        payloadPreview = {
          indice_usb: candidatoSelecionado.indice,
          nome: nome.trim() || candidatoSelecionado.nome_dispositivo || 'Câmera USB',
          qualidade_jpeg: 82,
        };
      } else {
        teste = await camerasApi.testarRede({
          candidato: candidatoSelecionado.candidato,
          usuario: usuario || null,
          senha: senha || null,
        });

        payloadPreview = {
          fonte: teste?.fonte || undefined,
          candidato: teste?.fonte ? undefined : candidatoSelecionado.candidato,
          usuario: usuario || null,
          senha: senha || null,
          nome: nome.trim() || nomeCandidato(candidatoSelecionado),
          qualidade_jpeg: 82,
        };
      }

      const preview = await iniciarPreviewComRetry(payloadPreview);

      previewSessionRef.current = preview.session_id;
      setPreviewSessionId(preview.session_id);
      setPreviewInfo({ ...teste, ...preview });
      setResultadoTeste({ ...teste, ...preview, fonte: teste?.fonte });
      setStatusConexao('sucesso');
      setPreviewContexto('selecionada');

      if (teste?.nome_dispositivo && !nome.trim()) {
        setNome(teste.nome_dispositivo);
      }
    } catch (error) {
      setStatusConexao('erro');
      setPreviewErro(mensagemApi(error));
    } finally {
      setTestando(false);
    }
  };

  const resetarSelecionada = async () => {
    await pararPreviewTemporario();
    setNome('');
    setUsuario('');
    setSenha('');
    setMostrarSenha(false);
    setCandidatoSelecionado(null);
    limparTesteSelecionada();
  };

  const handleSalvarSelecionada = async () => {
    if (!candidatoSelecionado) {
      alert('Selecione uma câmera encontrada.');
      return;
    }

    if (!nome.trim()) {
      alert('Informe o nome da câmera.');
      return;
    }

    if (statusConexao !== 'sucesso') {
      alert('Teste a conexão com sucesso antes de cadastrar.');
      return;
    }

    setSalvando(true);

    try {
      if (candidatoSelecionado.origem === 'usb') {
        await camerasApi.cadastrarUsb({
          indice: candidatoSelecionado.indice,
          nome: nome.trim(),
        });
      } else {
        const candidato = candidatoSelecionado.candidato || {};
        const fonteFinal = resultadoTeste?.fonte;

        if (!fonteFinal) {
          alert('O teste não retornou uma fonte válida para cadastro.');
          return;
        }

        await camerasApi.cadastrarRede({
          nome: nome.trim(),
          fonte: fonteFinal,
          onvif: Boolean(candidato.onvif),
          portas_detectadas: candidato.portas || [],
        });
      }

      await pararPreviewTemporario();
      await onCadastrar();
      await resetarSelecionada();
    } catch (error) {
      alert(mensagemApi(error));
    } finally {
      setSalvando(false);
    }
  };

  const handleTestarManual = async () => {
    if (!manualUrl.trim()) {
      alert('Informe a URL do stream.');
      return;
    }

    setManualTestando(true);
    limparTesteManual();
    await pararPreviewTemporario();

    try {
      const teste = await camerasApi.testarRede({
        fonte: manualUrl.trim(),
        usuario: manualUsuario || null,
        senha: manualSenha || null,
      });

      const preview = await iniciarPreviewComRetry({
        fonte: teste?.fonte || manualUrl.trim(),
        usuario: manualUsuario || null,
        senha: manualSenha || null,
        nome: manualNome.trim() || 'Câmera manual',
        qualidade_jpeg: 82,
      });

      previewSessionRef.current = preview.session_id;
      setPreviewSessionId(preview.session_id);
      setPreviewInfo({ ...teste, ...preview });
      setManualResultado({ ...teste, ...preview, fonte: teste?.fonte });
      setManualStatus('sucesso');
      setPreviewContexto('manual');

      if (teste?.ip && !manualIp.trim()) {
        setManualIp(teste.ip);
      }
    } catch (error) {
      setManualStatus('erro');
      setPreviewErro(mensagemApi(error));
    } finally {
      setManualTestando(false);
    }
  };

  const handleSalvarManual = async () => {
    if (!manualNome.trim()) {
      alert('Informe o nome da câmera.');
      return;
    }

    if (manualStatus !== 'sucesso') {
      alert('Teste a conexão com sucesso antes de cadastrar.');
      return;
    }

    const fonteFinal = manualResultado?.fonte || manualUrl.trim();
    if (!fonteFinal) {
      alert('Informe uma URL de stream válida.');
      return;
    }

    setManualSalvando(true);

    try {
      await camerasApi.cadastrarRede({
        nome: manualNome.trim(),
        fonte: fonteFinal,
        onvif: false,
        portas_detectadas: [],
      });

      await pararPreviewTemporario();
      await onCadastrar();

      setManualNome('');
      setManualIp('');
      setManualUrl('');
      setManualUsuario('');
      setManualSenha('');
      setMostrarSenhaManual(false);
      limparTesteManual();
    } catch (error) {
      alert(mensagemApi(error));
    } finally {
      setManualSalvando(false);
    }
  };

  const invalidarSelecionada = () => {
    limparTesteSelecionada();
    if (previewContexto === 'selecionada') {
      void pararPreviewTemporario();
    }
  };

  const invalidarManual = () => {
    limparTesteManual();
    if (previewContexto === 'manual') {
      void pararPreviewTemporario();
    }
  };

  const abrirFullscreen = async () => {
    if (!previewBoxRef.current) return;
    try {
      await previewBoxRef.current.requestFullscreen?.();
    } catch {
      // Fullscreen é apenas um recurso visual opcional.
    }
  };

  const candidato = candidatoSelecionado?.origem === 'rede'
    ? candidatoSelecionado.candidato || {}
    : {};

  const previewAtivoSelecionada = previewSessionId && previewContexto === 'selecionada';
  const previewAtivoManual = previewSessionId && previewContexto === 'manual';

  return (
    <div className="max-w-[1500px] mx-auto space-y-4">
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium mb-2">
            <span>Câmeras</span>
            <ChevronRight className="w-3 h-3" />
            <span className="text-slate-700 font-semibold">Cadastro de Câmeras</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-950">Cadastro de Câmeras</h2>
          <p className="text-sm text-slate-500 mt-1">
            Localize, teste e cadastre câmeras disponíveis na rede industrial.
          </p>
        </div>

        <div className="flex flex-wrap items-stretch gap-3">
          <div className="min-w-[175px] px-4 py-2.5 rounded-xl border border-emerald-200 bg-emerald-50 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center">
              <Video className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-emerald-700 block">Rede detectada</span>
              <span className="text-[10px] text-emerald-700/80 block mt-0.5">
                {redeDetectada || 'Aguardando busca'}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => void handleBuscar()}
            disabled={buscando}
            className="px-5 py-2.5 rounded-xl bg-[#FF7412] hover:bg-[#e0620a] text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-sm disabled:opacity-60"
          >
            {buscando ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            {buscando ? 'Buscando...' : 'Buscar Câmeras'}
          </button>
        </div>
      </div>

      {previewErro && (
        <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-red-700 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{previewErro}</span>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1.35fr_1fr] gap-4 items-stretch">
        <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-orange-50 text-[#FF7412] flex items-center justify-center">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Câmeras Encontradas</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Dispositivos localizados na rede e fontes USB disponíveis.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => void handleBuscar()}
              disabled={buscando}
              className="w-9 h-9 rounded-lg border border-slate-200 hover:bg-slate-50 text-[#FF7412] flex items-center justify-center disabled:opacity-50"
              title="Atualizar busca"
            >
              <RefreshCw className={`w-4 h-4 ${buscando ? 'animate-spin' : ''}`} />
            </button>
          </div>

          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-700 border-b border-slate-200">
                  <tr>
                    <th className="px-3 py-3 font-bold">Status</th>
                    <th className="px-3 py-3 font-bold">Dispositivo</th>
                    <th className="px-3 py-3 font-bold">IP / Fonte</th>
                    <th className="px-3 py-3 font-bold">Protocolo</th>
                    <th className="px-3 py-3 font-bold">Portas</th>
                    <th className="px-3 py-3 font-bold">ONVIF</th>
                    <th className="px-3 py-3 font-bold text-right">Ação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {candidatos.map((item, index) => {
                    const rede = item.origem === 'rede' ? item.candidato || {} : {};
                    const selecionado = candidatoSelecionado === item;

                    return (
                      <tr
                        key={`${item.origem}-${item.indice ?? rede.ip ?? index}`}
                        className={selecionado ? 'bg-orange-50/60' : 'hover:bg-slate-50/70'}
                      >
                        <td className="px-3 py-3">
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold text-emerald-700">
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                            Encontrada
                          </span>
                        </td>
                        <td className="px-3 py-3 font-semibold text-slate-800 whitespace-nowrap">
                          {nomeCandidato(item, index)}
                        </td>
                        <td className="px-3 py-3 text-slate-600 whitespace-nowrap">
                          {item.origem === 'usb' ? `USB ${item.indice ?? '-'}` : rede.ip || '-'}
                        </td>
                        <td className="px-3 py-3 text-slate-600 whitespace-nowrap uppercase">
                          {protocoloCandidato(item)}
                        </td>
                        <td className="px-3 py-3 text-slate-600 whitespace-nowrap">
                          {portasCandidato(item)}
                        </td>
                        <td className="px-3 py-3">
                          {item.origem === 'usb' ? (
                            <span className="text-slate-400">-</span>
                          ) : (
                            <span className={rede.onvif ? 'text-emerald-600 font-semibold' : 'text-slate-500'}>
                              {rede.onvif ? 'Sim' : 'Não'}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => void selecionarCandidato(item)}
                            className={`px-3 py-1.5 rounded-lg border text-[10px] font-semibold transition-colors ${
                              selecionado
                                ? 'border-[#FF7412] bg-[#FF7412] text-white'
                                : 'border-orange-200 text-[#FF7412] hover:bg-orange-50'
                            }`}
                          >
                            {selecionado ? 'Selecionada' : 'Selecionar'}
                          </button>
                        </td>
                      </tr>
                    );
                  })}

                  {!buscando && candidatos.length === 0 && (
                    <tr>
                      <td colSpan="7" className="px-4 py-12 text-center">
                        <Camera className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        <p className="text-xs font-semibold text-slate-600">Nenhuma busca realizada.</p>
                        <p className="text-[10px] text-slate-400 mt-1">
                          Clique em “Buscar Câmeras” para localizar dispositivos disponíveis.
                        </p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 flex items-center gap-3">
            <div className="w-6 h-6 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs font-bold shrink-0">i</div>
            <div>
              <span className="text-[11px] font-semibold text-blue-800">
                {candidatos.length} dispositivo(s) encontrado(s)
              </span>
              <p className="text-[10px] text-blue-700 mt-0.5">
                Selecione uma câmera, informe as credenciais quando necessário e teste a conexão.
              </p>
            </div>
          </div>
        </section>

        <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-orange-50 text-[#FF7412] flex items-center justify-center">
              <Settings className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Configurar Câmera</h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Teste a conexão e confira o vídeo antes de cadastrar.
              </p>
            </div>
          </div>

          {candidatoSelecionado ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-3">
                <div className="rounded-xl border border-orange-100 bg-orange-50/60 p-3.5">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-lg bg-white border border-orange-100 text-[#FF7412] flex items-center justify-center shrink-0">
                      <Video className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <span className="text-[10px] font-bold text-[#FF7412] block">Câmera Selecionada</span>
                      <strong className="text-xs text-slate-900 block truncate mt-0.5">
                        {nomeCandidato(candidatoSelecionado)}
                      </strong>
                      <div className="mt-2 space-y-1 text-[10px] text-slate-600">
                        <p>
                          Fonte: <strong>{candidatoSelecionado.origem === 'usb' ? `USB ${candidatoSelecionado.indice}` : candidato.ip || '-'}</strong>
                        </p>
                        <p>
                          Protocolo: <strong className="uppercase">{protocoloCandidato(candidatoSelecionado)}</strong>
                        </p>
                        <p className="flex items-center gap-1.5">
                          Status:
                          <span className={`w-2 h-2 rounded-full ${statusConexao === 'sucesso' ? 'bg-emerald-500' : statusConexao === 'erro' ? 'bg-red-500' : 'bg-slate-400'}`} />
                          <strong>
                            {statusConexao === 'sucesso'
                              ? 'Conexão validada'
                              : statusConexao === 'erro'
                                ? 'Falha no teste'
                                : 'Ainda não testada'}
                          </strong>
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <span className="text-[11px] font-bold text-slate-800 block mb-2">Preview da Câmera</span>
                  <div
                    ref={previewBoxRef}
                    className="relative aspect-video rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center"
                  >
                    {previewAtivoSelecionada && frameSrc ? (
                      <img
                        src={frameSrc}
                        alt="Preview da câmera selecionada"
                        className="absolute inset-0 w-full h-full object-contain bg-black"
                      />
                    ) : (
                      <div className="text-center px-4">
                        {testando ? (
                          <RefreshCw className="w-8 h-8 text-[#FF7412] animate-spin mx-auto mb-2" />
                        ) : (
                          <Camera className="w-9 h-9 text-slate-600 mx-auto mb-2" />
                        )}
                        <p className="text-[10px] text-slate-400">
                          {testando ? 'Abrindo transmissão...' : 'Clique em Testar Conexão para abrir a câmera.'}
                        </p>
                      </div>
                    )}

                    {previewAtivoSelecionada && (
                      <div className="absolute top-2 left-2 rounded bg-black/65 border border-white/10 px-2 py-1 text-[9px] text-white flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        AO VIVO
                      </div>
                    )}

                    {previewAtivoSelecionada && frameSrc && (
                      <button
                        type="button"
                        onClick={() => void abrirFullscreen()}
                        className="absolute right-2 bottom-2 w-8 h-8 rounded-lg bg-black/60 hover:bg-black/80 border border-white/10 text-white flex items-center justify-center"
                        title="Tela cheia"
                      >
                        <Maximize2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1.5">
                    Nome da câmera <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={nome}
                    onChange={(e) => setNome(e.target.value)}
                    placeholder="Ex: CAM-02 - Produção"
                    className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2.5 focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1.5">Usuário</label>
                  <input
                    type="text"
                    value={usuario}
                    onChange={(e) => {
                      setUsuario(e.target.value);
                      invalidarSelecionada();
                    }}
                    disabled={candidatoSelecionado.origem === 'usb'}
                    placeholder="Ex: admin"
                    className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2.5 focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none disabled:bg-slate-100"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1.5">Senha</label>
                  <div className="relative">
                    <input
                      type={mostrarSenha ? 'text' : 'password'}
                      value={senha}
                      onChange={(e) => {
                        setSenha(e.target.value);
                        invalidarSelecionada();
                      }}
                      disabled={candidatoSelecionado.origem === 'usb'}
                      placeholder="••••••••"
                      className="w-full text-xs bg-white border border-slate-300 rounded-lg pl-3 pr-10 py-2.5 focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none disabled:bg-slate-100"
                    />
                    <button
                      type="button"
                      onClick={() => setMostrarSenha((valor) => !valor)}
                      disabled={candidatoSelecionado.origem === 'usb'}
                      className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 disabled:opacity-40"
                      title="Mostrar ou ocultar senha"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 rounded-xl bg-slate-50 border border-slate-200 p-3 text-[10px]">
                <div>
                  <span className="text-slate-400 block">Status</span>
                  <strong className={statusConexao === 'sucesso' ? 'text-emerald-600' : 'text-slate-600'}>
                    {statusConexao === 'sucesso' ? 'ONLINE' : '-'}
                  </strong>
                </div>
                <div>
                  <span className="text-slate-400 block">Resolução</span>
                  <strong className="text-slate-700">
                    {previewInfo?.largura && previewInfo?.altura
                      ? `${previewInfo.largura} × ${previewInfo.altura}`
                      : '-'}
                  </strong>
                </div>
                <div>
                  <span className="text-slate-400 block">FPS</span>
                  <strong className="text-slate-700">{previewInfo?.fps ?? '-'}</strong>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => void handleTestarSelecionada()}
                  disabled={testando || salvando}
                  className="px-4 py-2.5 border border-orange-200 hover:bg-orange-50 rounded-lg text-[11px] font-semibold text-[#FF7412] flex items-center gap-2 disabled:opacity-50"
                >
                  {testando ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  {previewAtivoSelecionada ? 'Testar Novamente' : 'Testar Conexão'}
                </button>

                <button
                  type="button"
                  onClick={() => void handleSalvarSelecionada()}
                  disabled={salvando || statusConexao !== 'sucesso'}
                  className="px-4 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-[11px] font-semibold flex items-center gap-2 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {salvando ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  {salvando ? 'Cadastrando...' : 'Cadastrar Câmera'}
                </button>
              </div>
            </div>
          ) : (
            <div className="min-h-[430px] rounded-xl border border-dashed border-slate-300 bg-slate-50 flex items-center justify-center p-8 text-center">
              <div>
                <Camera className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <h4 className="text-sm font-bold text-slate-700">Nenhuma câmera selecionada</h4>
                <p className="text-[11px] text-slate-500 mt-1 max-w-sm">
                  Faça uma busca e selecione uma câmera na lista ao lado para configurar e visualizar o preview.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>

      <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-orange-50 text-[#FF7412] flex items-center justify-center shrink-0">
            <PlusCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">Adicionar Câmera Manualmente</h3>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Use esta opção quando a câmera não for encontrada automaticamente.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[1fr_1fr_1.25fr_0.8fr_0.8fr] gap-3">
          <div>
            <label className="block text-[10px] font-bold text-slate-700 mb-1.5">
              Nome da câmera <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={manualNome}
              onChange={(e) => setManualNome(e.target.value)}
              placeholder="Ex: CAM-03 - Entrada"
              className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2.5 focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-700 mb-1.5">IP ou endereço</label>
            <input
              type="text"
              value={manualIp}
              onChange={(e) => setManualIp(e.target.value)}
              placeholder="Ex: 192.168.0.100"
              className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2.5 focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-700 mb-1.5">
              URL do Stream <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={manualUrl}
              onChange={(e) => {
                setManualUrl(e.target.value);
                invalidarManual();
              }}
              placeholder="Ex: rtsp://192.168.0.100:554/stream"
              className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2.5 focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-700 mb-1.5">Usuário</label>
            <input
              type="text"
              value={manualUsuario}
              onChange={(e) => {
                setManualUsuario(e.target.value);
                invalidarManual();
              }}
              placeholder="Ex: admin"
              className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2.5 focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-700 mb-1.5">Senha</label>
            <div className="relative">
              <input
                type={mostrarSenhaManual ? 'text' : 'password'}
                value={manualSenha}
                onChange={(e) => {
                  setManualSenha(e.target.value);
                  invalidarManual();
                }}
                placeholder="••••••••"
                className="w-full text-xs bg-white border border-slate-300 rounded-lg pl-3 pr-10 py-2.5 focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setMostrarSenhaManual((valor) => !valor)}
                className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                title="Mostrar ou ocultar senha"
              >
                <Eye className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[auto_auto_1fr] gap-3 items-center mt-4">
          <button
            type="button"
            onClick={() => void handleTestarManual()}
            disabled={manualTestando || manualSalvando}
            className="px-4 py-2.5 border border-orange-200 hover:bg-orange-50 rounded-lg text-[11px] font-semibold text-[#FF7412] flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {manualTestando ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {previewAtivoManual ? 'Testar Novamente' : 'Testar Conexão'}
          </button>

          <button
            type="button"
            onClick={() => void handleSalvarManual()}
            disabled={manualSalvando || manualStatus !== 'sucesso'}
            className="px-4 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-[11px] font-semibold flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {manualSalvando ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            {manualSalvando ? 'Cadastrando...' : 'Cadastrar Câmera'}
          </button>

          <div className={`min-h-[42px] rounded-lg border px-3 py-2 flex items-center gap-3 ${
            manualStatus === 'sucesso'
              ? 'border-emerald-200 bg-emerald-50'
              : manualStatus === 'erro'
                ? 'border-red-200 bg-red-50'
                : 'border-slate-200 bg-slate-50'
          }`}>
            {previewAtivoManual && frameSrc ? (
              <img
                src={frameSrc}
                alt="Preview da câmera manual"
                className="w-14 h-9 rounded object-cover bg-black shrink-0"
              />
            ) : (
              <div className="w-14 h-9 rounded bg-slate-200 flex items-center justify-center shrink-0">
                <Camera className="w-4 h-4 text-slate-400" />
              </div>
            )}
            <div className="min-w-0">
              <span className={`text-[10px] font-bold block ${
                manualStatus === 'sucesso'
                  ? 'text-emerald-700'
                  : manualStatus === 'erro'
                    ? 'text-red-700'
                    : 'text-slate-500'
              }`}>
                {manualStatus === 'sucesso'
                  ? 'Conexão validada — preview ativo'
                  : manualStatus === 'erro'
                    ? 'Falha ao abrir a câmera'
                    : 'Aguardando teste da câmera manual'}
              </span>
              {manualStatus === 'sucesso' && (
                <span className="text-[9px] text-emerald-700/80 block truncate">
                  {previewInfo?.largura && previewInfo?.altura
                    ? `${previewInfo.largura} × ${previewInfo.altura}`
                    : 'Resolução não informada'}
                  {previewInfo?.fps ? ` • ${previewInfo.fps} FPS` : ''}
                </span>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}


// 3. CONSULTA DE CÂMERAS
function ConsultaCamerasView({ cameras, loading, erro, onRefresh, onNavigate }) {
  const [processandoUid, setProcessandoUid] = useState(null);

  const handleRemover = async (camera) => {
    const uid = camera.camera_uid;
    if (!uid) return;

    if (!window.confirm(`Remover a câmera "${camera.nome}"?`)) {
      return;
    }

    setProcessandoUid(uid);

    try {
      const vinculos = await camerasApi.obterVinculos(uid);
      const possui = Boolean(vinculos.possui_vinculos || vinculos.vinculada);
      const itens = vinculos.vinculos || vinculos.ambientes || [];

      if (possui) {
        const nomes = itens
          .map((item) => item.nome || item.ambiente_nome || item.ambiente_id)
          .filter(Boolean)
          .join(', ');

        alert(`A câmera possui vínculo com ambiente${itens.length === 1 ? '' : 's'}${nomes ? `: ${nomes}` : '.'}`);
        return;
      }

      await camerasApi.remover(uid);
      await onRefresh();
    } catch (error) {
      alert(mensagemApi(error));
    } finally {
      setProcessandoUid(null);
    }
  };

  const handleEditar = async (cameraResumo) => {
    const uid = cameraResumo.camera_uid;
    if (!uid) return;

    setProcessandoUid(uid);

    try {
      const detalhe = await camerasApi.obter(uid);
      const camera = detalhe.camera || {};
      const novoNome = window.prompt('Nome da câmera:', camera.nome || cameraResumo.nome || '');

      if (novoNome === null) return;

      const payload = { nome: novoNome.trim() };

      if (String(camera.tipo || '').toLowerCase() !== 'usb') {
        const fonteAtual = camera.conexao?.fonte || '';
        const novaFonte = window.prompt('URL do stream:', fonteAtual);
        if (novaFonte === null) return;
        payload.fonte = novaFonte.trim();
        payload.onvif = camera.conexao?.onvif;
      }

      await camerasApi.editar(uid, payload);
      await onRefresh();
    } catch (error) {
      alert(mensagemApi(error));
    } finally {
      setProcessandoUid(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Consulta de Câmeras</h2>
          <p className="text-xs text-slate-500 mt-0.5">Gerencie os fluxos de vídeo configurados no sistema</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => void onRefresh()}
            disabled={loading}
            className="px-4 py-2 border border-slate-300 hover:bg-slate-100 rounded-lg text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar Status
          </button>
          <button
            onClick={() => onNavigate('cadastro-cameras')}
            className="px-4 py-2 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-xs font-semibold flex items-center gap-2 self-start"
          >
            <PlusCircle className="w-4 h-4" />
            Nova Câmera
          </button>
        </div>
      </div>

      {erro && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {erro}
        </div>
      )}

      {loading && cameras.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-sm text-slate-500">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-3 text-[#FF7412]" />
          Consultando câmeras no backend...
        </div>
      ) : cameras.length === 0 ? (
        <EmptyState
          icon={Video}
          title="Nenhuma câmera registrada no banco"
          description="O backend não retornou câmeras cadastradas. Cadastre uma câmera para começar."
          actionText="Adicionar Primeira Câmera"
          onAction={() => onNavigate('cadastro-cameras')}
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Nome</th>
                <th className="py-3 px-4">Tipo</th>
                <th className="py-3 px-4">Resolução</th>
                <th className="py-3 px-4">FPS</th>
                <th className="py-3 px-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {cameras.map((camera) => {
                const online = Boolean(camera.online) || String(camera.status).toUpperCase() === 'ONLINE';
                const processando = processandoUid === camera.camera_uid;

                return (
                  <tr key={camera.camera_uid} className="hover:bg-slate-50/80">
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        online ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-700'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${online ? 'bg-emerald-600' : 'bg-red-600'}`} />
                        {camera.status || (online ? 'ONLINE' : 'OFFLINE')}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-800">{camera.nome}</td>
                    <td className="py-3 px-4 uppercase">{camera.tipo || '-'}</td>
                    <td className="py-3 px-4">{camera.largura && camera.altura ? `${camera.largura} × ${camera.altura}` : '-'}</td>
                    <td className="py-3 px-4">{camera.fps ?? '-'}</td>
                    <td className="py-3 px-4 text-right space-x-2">
                      <button
                        onClick={() => void handleEditar(camera)}
                        disabled={processando}
                        className="text-slate-500 hover:text-slate-800 p-1 disabled:opacity-40"
                        title="Editar câmera"
                      >
                        <Edit className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => void handleRemover(camera)}
                        disabled={processando}
                        className="text-red-500 hover:text-red-700 p-1 disabled:opacity-40"
                        title="Remover câmera"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// 4. TESTE DE CÂMERAS
function TesteCamerasView({ cameras, loading, erro, onRefresh, onNavigate }) {
  const [selectedCam, setSelectedCam] = useState(cameras[0]?.camera_uid || '');
  const [sessionId, setSessionId] = useState(null);
  const [frameSrc, setFrameSrc] = useState(null);
  const [previewInfo, setPreviewInfo] = useState(null);
  const [previewErro, setPreviewErro] = useState(null);
  const [iniciando, setIniciando] = useState(false);
  const [reconectando, setReconectando] = useState(false);
  const previewRef = React.useRef(null);

  const cameraSelecionada = cameras.find((camera) => camera.camera_uid === selectedCam) || null;

  useEffect(() => {
    if (!selectedCam && cameras[0]?.camera_uid) {
      setSelectedCam(cameras[0].camera_uid);
    }
  }, [cameras, selectedCam]);

  const pararPreview = async (session = sessionId) => {
    if (!session) return;

    try {
      await camerasApi.pararPreview(session);
    } catch (error) {
      if (error?.payload?.erro !== 'PREVIEW_NAO_ENCONTRADO') {
        setPreviewErro(mensagemApi(error));
      }
    } finally {
      setSessionId(null);
      setFrameSrc(null);
      setPreviewInfo(null);
    }
  };

  const iniciarPreview = async () => {
    if (!selectedCam) return;

    if (sessionId) {
      await pararPreview(sessionId);
    }

    setIniciando(true);
    setPreviewErro(null);

    try {
      const dados = await camerasApi.iniciarPreview(selectedCam);
      setSessionId(dados.session_id);
      setPreviewInfo(dados);
    } catch (error) {
      setPreviewErro(mensagemApi(error));
    } finally {
      setIniciando(false);
    }
  };

  const reconectar = async () => {
    if (!sessionId) return;

    setReconectando(true);
    setPreviewErro(null);

    try {
      const dados = await camerasApi.reconectarPreview(sessionId);
      setPreviewInfo((prev) => ({ ...prev, ...dados }));
    } catch (error) {
      setPreviewErro(mensagemApi(error));
    } finally {
      setReconectando(false);
    }
  };

  useEffect(() => {
    if (!sessionId) return undefined;

    let cancelado = false;
    let executando = false;

    const atualizarFrame = async () => {
      if (cancelado || executando) return;
      executando = true;

      try {
        const dados = await camerasApi.obterFramePreview(sessionId);
        if (!cancelado && dados.frame_base64) {
          setFrameSrc(`data:${dados.mime_type || 'image/jpeg'};base64,${dados.frame_base64}`);
          setPreviewInfo((prev) => ({ ...prev, ...dados }));
          setPreviewErro(null);
        }
      } catch (error) {
        if (!cancelado) {
          setPreviewErro(mensagemApi(error));
        }
      } finally {
        executando = false;
      }
    };

    void atualizarFrame();
    const timer = window.setInterval(atualizarFrame, 300);

    return () => {
      cancelado = true;
      window.clearInterval(timer);
    };
  }, [sessionId]);

  useEffect(() => {
    return () => {
      if (sessionId) {
        void camerasApi.pararPreview(sessionId).catch(() => {});
      }
    };
  }, [sessionId]);

  const trocarCamera = async (novoUid) => {
    if (sessionId) {
      await pararPreview(sessionId);
    }
    setSelectedCam(novoUid);
    setPreviewErro(null);
  };

  const abrirFullscreen = async () => {
    if (!previewRef.current) return;
    try {
      await previewRef.current.requestFullscreen?.();
    } catch {
      // Fullscreen é opcional e visual.
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Teste de Câmeras em Tempo Real</h2>
          <p className="text-xs text-slate-500 mt-0.5">Visualize e valide a transmissão das câmeras cadastradas no backend</p>
        </div>
        <button
          onClick={() => void onRefresh()}
          disabled={loading}
          className="px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      {(erro || previewErro) && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {previewErro || erro}
        </div>
      )}

      {cameras.length === 0 ? (
        <EmptyState
          icon={Camera}
          title="Sem câmeras para testar"
          description="Cadastre ao menos uma câmera no backend para iniciar o preview."
          actionText="Ir para Cadastro"
          onAction={() => onNavigate('cadastro-cameras')}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-3">
            <div
              ref={previewRef}
              className="bg-black rounded-xl overflow-hidden aspect-video flex flex-col items-center justify-center text-white relative shadow-lg"
            >
              {frameSrc ? (
                <img src={frameSrc} alt="Preview da câmera" className="w-full h-full object-contain bg-black" />
              ) : (
                <div className="text-center p-4">
                  <Camera className="w-12 h-12 text-[#FF7412] mx-auto mb-2 opacity-80" />
                  <p className="text-xs text-slate-300">
                    {sessionId ? 'Aguardando frame da câmera...' : 'Transmissão parada'}
                  </p>
                </div>
              )}

              <div className="absolute top-3 left-3 bg-black/60 backdrop-blur px-2.5 py-1 rounded text-[10px] font-mono text-white flex items-center gap-1.5 border border-white/10">
                <span className={`w-2 h-2 rounded-full ${sessionId ? 'bg-emerald-500' : 'bg-slate-500'}`} />
                {cameraSelecionada?.nome || 'Câmera'}
              </div>

              <button
                type="button"
                onClick={abrirFullscreen}
                className="absolute right-3 bottom-3 p-2 rounded bg-black/60 border border-white/10 hover:bg-black/80"
                title="Tela cheia"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              {!sessionId ? (
                <button
                  type="button"
                  onClick={() => void iniciarPreview()}
                  disabled={iniciando || !selectedCam}
                  className="px-4 py-2 bg-[#FF7412] text-white rounded-lg text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
                >
                  {iniciando ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  Iniciar Transmissão
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => void pararPreview()}
                  className="px-4 py-2 border border-red-300 text-red-600 rounded-lg text-xs font-semibold flex items-center gap-2"
                >
                  <Square className="w-4 h-4" />
                  Parar Transmissão
                </button>
              )}

              <button
                type="button"
                onClick={() => void reconectar()}
                disabled={!sessionId || reconectando}
                className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold flex items-center gap-2 disabled:opacity-40"
              >
                <RefreshCw className={`w-4 h-4 ${reconectando ? 'animate-spin' : ''}`} />
                Reconectar
              </button>
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Controle do Feed</h3>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Selecionar Câmera</label>
              <select
                value={selectedCam}
                onChange={(e) => void trocarCamera(e.target.value)}
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
              >
                {cameras.map((camera) => (
                  <option key={camera.camera_uid} value={camera.camera_uid}>
                    {camera.nome}
                  </option>
                ))}
              </select>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg text-xs space-y-1.5 text-slate-600">
              <div className="flex justify-between">
                <span>Status:</span>
                <strong className={String(cameraSelecionada?.status).toUpperCase() === 'ONLINE' ? 'text-emerald-600' : 'text-red-600'}>
                  {cameraSelecionada?.status || '-'}
                </strong>
              </div>
              <div className="flex justify-between">
                <span>Tipo:</span>
                <strong className="uppercase">{cameraSelecionada?.tipo || '-'}</strong>
              </div>
              <div className="flex justify-between">
                <span>Resolução:</span>
                <strong>
                  {previewInfo?.largura && previewInfo?.altura
                    ? `${previewInfo.largura} × ${previewInfo.altura}`
                    : cameraSelecionada?.largura && cameraSelecionada?.altura
                      ? `${cameraSelecionada.largura} × ${cameraSelecionada.altura}`
                      : '-'}
                </strong>
              </div>
              <div className="flex justify-between">
                <span>FPS:</span>
                <strong>{previewInfo?.fps ?? cameraSelecionada?.fps ?? '-'}</strong>
              </div>
            </div>

            <p className="text-[10px] text-slate-400 leading-relaxed">
              Codec e latência não são exibidos porque o backend atual não fornece esses dados.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// 5. CADASTRO / EDIÇÃO DE AMBIENTE — ETAPA 1 VISUAL
function CadastroAmbienteView({
  ambienteEmEdicao,
  camerasDisponiveis,
  onSalvarAmbiente,
  onConcluirAmbiente,
  onCancelarEdicao,
}) {
  const [nomeAmbiente, setNomeAmbiente] = useState('');
  const [descricao, setDescricao] = useState('');
  const [cameraSelecionadaUid, setCameraSelecionadaUid] = useState('');
  const [erro, setErro] = useState(null);
  const [etapaAtual, setEtapaAtual] = useState(1);

  // Etapa 2 — preview e ROI.
  const [previewSessionId, setPreviewSessionId] = useState(null);
  const [frameSrc, setFrameSrc] = useState(null);
  const [previewInfo, setPreviewInfo] = useState(null);
  const [previewErro, setPreviewErro] = useState(null);
  const [iniciandoPreview, setIniciandoPreview] = useState(false);
  const [modoSelecao, setModoSelecao] = useState(false);
  const [arrastandoRoi, setArrastandoRoi] = useState(false);
  const [inicioRoi, setInicioRoi] = useState(null);
  const [roi, setRoi] = useState(null);
  const [roiConfirmada, setRoiConfirmada] = useState(false);
  const [frameSize, setFrameSize] = useState({ width: 0, height: 0 });
  const [previewBox, setPreviewBox] = useState({ width: 0, height: 0 });

  // Etapa 3 — persistência mínima do ambiente + seleção manual de maquinário.
  const [ambienteIdFluxo, setAmbienteIdFluxo] = useState(null);
  const [preparandoMaquinario, setPreparandoMaquinario] = useState(false);
  const [analiseMaquinarioId, setAnaliseMaquinarioId] = useState(null);
  const [objetosDetectados, setObjetosDetectados] = useState([]);
  const [idsMaquinario, setIdsMaquinario] = useState([]);
  const [imagemMaquinarioSrc, setImagemMaquinarioSrc] = useState(null);
  const [salvandoMaquinario, setSalvandoMaquinario] = useState(false);
  const [maquinarioConfirmado, setMaquinarioConfirmado] = useState(false);

  // Etapa 4 — EPIs obrigatórios.
  const [episDisponiveis, setEpisDisponiveis] = useState([]);
  const [episObrigatorios, setEpisObrigatorios] = useState([]);
  const [episLoading, setEpisLoading] = useState(false);
  const [salvandoEpis, setSalvandoEpis] = useState(false);
  const [episConfirmados, setEpisConfirmados] = useState(false);

  // Etapa 5 — colaboradores vinculados.
  const [colaboradoresDisponiveis, setColaboradoresDisponiveis] = useState([]);
  const [matriculasSelecionadas, setMatriculasSelecionadas] = useState([]);
  const [colaboradoresLoading, setColaboradoresLoading] = useState(false);
  const [salvandoColaboradores, setSalvandoColaboradores] = useState(false);
  const [colaboradoresConfirmados, setColaboradoresConfirmados] = useState(false);
  const [buscaColaboradorAmbiente, setBuscaColaboradorAmbiente] = useState('');

  // Etapa 6 — revisão e finalização.
  const [revisaoDados, setRevisaoDados] = useState(null);
  const [revisaoLoading, setRevisaoLoading] = useState(false);
  const [finalizandoAmbiente, setFinalizandoAmbiente] = useState(false);

  const previewStageRef = React.useRef(null);
  const previewSessionRef = React.useRef(null);
  const zoomCanvasRef = React.useRef(null);

  const etapas = [
    { numero: 1, titulo: 'Dados do Ambiente', resumo: 'Nome, descrição e câmera' },
    { numero: 2, titulo: 'Área de Monitoramento', resumo: 'Defina a região na imagem' },
    { numero: 3, titulo: 'Maquinário', resumo: 'Detecte e confirme os equipamentos' },
    { numero: 4, titulo: 'EPIs', resumo: 'Selecione os EPIs obrigatórios' },
    { numero: 5, titulo: 'Colaboradores', resumo: 'Vincule os colaboradores' },
    { numero: 6, titulo: 'Revisão', resumo: 'Confira e salve o ambiente' },
  ];

  useEffect(() => {
    if (ambienteEmEdicao) {
      setNomeAmbiente(ambienteEmEdicao.nome || '');
      setDescricao(ambienteEmEdicao.descricao || '');
      setCameraSelecionadaUid(
        Array.isArray(ambienteEmEdicao.cameras)
          ? ambienteEmEdicao.cameras[0]?.camera_uid || ''
          : ''
      );
    } else {
      setNomeAmbiente('');
      setDescricao('');
      setCameraSelecionadaUid('');
    }

    setEtapaAtual(1);
    setErro(null);
    setPreviewErro(null);
    setFrameSrc(null);
    setPreviewInfo(null);
    setRoi(null);
    setRoiConfirmada(false);
    setModoSelecao(false);
    setAmbienteIdFluxo(ambienteEmEdicao?.ambiente_id || null);
    setPreparandoMaquinario(false);
    setAnaliseMaquinarioId(null);
    setObjetosDetectados([]);
    setIdsMaquinario([]);
    setImagemMaquinarioSrc(null);
    setSalvandoMaquinario(false);
    setMaquinarioConfirmado(false);
    setEpisDisponiveis([]);
    setEpisObrigatorios([]);
    setEpisLoading(false);
    setSalvandoEpis(false);
    setEpisConfirmados(false);
    setColaboradoresDisponiveis([]);
    setMatriculasSelecionadas([]);
    setColaboradoresLoading(false);
    setSalvandoColaboradores(false);
    setColaboradoresConfirmados(false);
    setBuscaColaboradorAmbiente('');
    setRevisaoDados(null);
    setRevisaoLoading(false);
    setFinalizandoAmbiente(false);
  }, [ambienteEmEdicao]);

  useEffect(() => {
    if (!cameraSelecionadaUid && camerasDisponiveis.length === 1) {
      setCameraSelecionadaUid(camerasDisponiveis[0].camera_uid || '');
    }
  }, [camerasDisponiveis, cameraSelecionadaUid]);

  useEffect(() => {
    const elemento = previewStageRef.current;
    if (!elemento || typeof ResizeObserver === 'undefined') return undefined;

    const observer = new ResizeObserver(([entry]) => {
      const rect = entry.contentRect;
      setPreviewBox({ width: rect.width, height: rect.height });
    });

    observer.observe(elemento);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    return () => {
      const sessionId = previewSessionRef.current;
      if (sessionId) {
        void camerasApi.pararPreview(sessionId).catch(() => {});
      }
    };
  }, []);

  useEffect(() => {
    if (!previewSessionId) return undefined;

    let cancelado = false;
    let executando = false;

    const atualizarFrame = async () => {
      if (cancelado || executando) return;
      executando = true;

      try {
        const dados = await camerasApi.obterFramePreview(previewSessionId);
        if (!cancelado && dados.frame_base64) {
          setFrameSrc(`data:${dados.mime_type || 'image/jpeg'};base64,${dados.frame_base64}`);
          setPreviewInfo((prev) => ({ ...prev, ...dados }));
          setPreviewErro(null);
        }
      } catch (error) {
        if (!cancelado) {
          setPreviewErro(mensagemApi(error));
        }
      } finally {
        executando = false;
      }
    };

    void atualizarFrame();
    const timer = window.setInterval(atualizarFrame, 300);

    return () => {
      cancelado = true;
      window.clearInterval(timer);
    };
  }, [previewSessionId]);

  useEffect(() => {
    const canvas = zoomCanvasRef.current;
    if (!canvas || !frameSrc || !roi?.largura || !roi?.altura) return;

    const imagem = new Image();
    imagem.onload = () => {
      const larguraSaida = Math.min(720, Math.max(1, Math.round(roi.largura)));
      const alturaSaida = Math.max(
        1,
        Math.round(larguraSaida * (roi.altura / roi.largura))
      );

      canvas.width = larguraSaida;
      canvas.height = alturaSaida;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(
        imagem,
        roi.x,
        roi.y,
        roi.largura,
        roi.altura,
        0,
        0,
        canvas.width,
        canvas.height
      );
    };
    imagem.src = frameSrc;
  }, [frameSrc, roi]);

  const cameraSelecionada =
    camerasDisponiveis.find((camera) => camera.camera_uid === cameraSelecionadaUid) || null;

  const cameraOnline = cameraSelecionada
    ? Boolean(cameraSelecionada.online) || String(cameraSelecionada.status).toUpperCase() === 'ONLINE'
    : false;

  const larguraFonte =
    frameSize.width || previewInfo?.largura || cameraSelecionada?.largura || 0;
  const alturaFonte =
    frameSize.height || previewInfo?.altura || cameraSelecionada?.altura || 0;

  const calcularGeometriaImagem = () => {
    if (!larguraFonte || !alturaFonte || !previewBox.width || !previewBox.height) {
      return null;
    }

    const escala = Math.min(
      previewBox.width / larguraFonte,
      previewBox.height / alturaFonte
    );
    const larguraExibida = larguraFonte * escala;
    const alturaExibida = alturaFonte * escala;

    return {
      escala,
      offsetX: (previewBox.width - larguraExibida) / 2,
      offsetY: (previewBox.height - alturaExibida) / 2,
      larguraExibida,
      alturaExibida,
    };
  };

  const pontoDoEvento = (event) => {
    const elemento = previewStageRef.current;
    const geometria = calcularGeometriaImagem();
    if (!elemento || !geometria || !larguraFonte || !alturaFonte) return null;

    const rect = elemento.getBoundingClientRect();
    const localX = event.clientX - rect.left - geometria.offsetX;
    const localY = event.clientY - rect.top - geometria.offsetY;

    const x = Math.max(
      0,
      Math.min(larguraFonte, localX / geometria.escala)
    );
    const y = Math.max(
      0,
      Math.min(alturaFonte, localY / geometria.escala)
    );

    return { x, y };
  };

  const pararPreviewAtual = async () => {
    const sessionId = previewSessionRef.current;
    previewSessionRef.current = null;
    setPreviewSessionId(null);

    if (sessionId) {
      try {
        await camerasApi.pararPreview(sessionId);
      } catch (error) {
        if (error?.payload?.erro !== 'PREVIEW_NAO_ENCONTRADO') {
          setPreviewErro(mensagemApi(error));
        }
      }
    }
  };

  const iniciarPreviewCamera = async (cameraUid = cameraSelecionadaUid) => {
    if (!cameraUid) return;

    setIniciandoPreview(true);
    setPreviewErro(null);

    try {
      await pararPreviewAtual();
      const dados = await camerasApi.iniciarPreview(cameraUid);
      previewSessionRef.current = dados.session_id;
      setPreviewSessionId(dados.session_id);
      setPreviewInfo(dados);
    } catch (error) {
      setPreviewErro(mensagemApi(error));
    } finally {
      setIniciandoPreview(false);
    }
  };

  const handleTrocarCamera = async (novoUid) => {
    if (novoUid === cameraSelecionadaUid) return;

    await pararPreviewAtual();
    setCameraSelecionadaUid(novoUid);
    setFrameSrc(null);
    setPreviewInfo(null);
    setFrameSize({ width: 0, height: 0 });
    setRoi(null);
    setRoiConfirmada(false);
    setModoSelecao(false);
    setPreviewErro(null);
    setAnaliseMaquinarioId(null);
    setObjetosDetectados([]);
    setIdsMaquinario([]);
    setImagemMaquinarioSrc(null);
    setMaquinarioConfirmado(false);
    setEpisObrigatorios([]);
    setEpisConfirmados(false);
    setMatriculasSelecionadas([]);
    setColaboradoresConfirmados(false);
    setRevisaoDados(null);

    if (etapaAtual >= 3) {
      setEtapaAtual(2);
    }

    if (etapaAtual >= 2 && novoUid) {
      await iniciarPreviewCamera(novoUid);
    }
  };

  const handleContinuar = async () => {
    setErro(null);

    if (!nomeAmbiente.trim()) {
      setErro('Informe o nome do ambiente.');
      return;
    }

    if (descricao.trim().length > 500) {
      setErro('A descrição deve possuir no máximo 500 caracteres.');
      return;
    }

    if (!cameraSelecionadaUid) {
      setErro('Selecione a câmera que será utilizada no monitoramento.');
      return;
    }

    setEtapaAtual(2);
    await iniciarPreviewCamera(cameraSelecionadaUid);
  };

  const handlePointerDown = (event) => {
    if (!modoSelecao || !frameSrc) return;

    const ponto = pontoDoEvento(event);
    if (!ponto) return;

    event.preventDefault();
    previewStageRef.current?.setPointerCapture?.(event.pointerId);
    setArrastandoRoi(true);
    setInicioRoi(ponto);
    setRoi({
      x: Math.round(ponto.x),
      y: Math.round(ponto.y),
      largura: 1,
      altura: 1,
    });
    setRoiConfirmada(false);
  };

  const handlePointerMove = (event) => {
    if (!arrastandoRoi || !inicioRoi) return;

    const ponto = pontoDoEvento(event);
    if (!ponto) return;

    const x = Math.min(inicioRoi.x, ponto.x);
    const y = Math.min(inicioRoi.y, ponto.y);
    const largura = Math.abs(ponto.x - inicioRoi.x);
    const altura = Math.abs(ponto.y - inicioRoi.y);

    setRoi({
      x: Math.round(x),
      y: Math.round(y),
      largura: Math.max(1, Math.round(largura)),
      altura: Math.max(1, Math.round(altura)),
    });
  };

  const handlePointerUp = (event) => {
    if (!arrastandoRoi) return;

    previewStageRef.current?.releasePointerCapture?.(event.pointerId);
    setArrastandoRoi(false);
    setInicioRoi(null);
    setModoSelecao(false);

    if (!roi || roi.largura < 8 || roi.altura < 8) {
      setRoi(null);
      setErro('Selecione uma área maior na imagem.');
    }
  };

  const handleAcaoPrincipalRoi = () => {
    setErro(null);

    if (!frameSrc) {
      setErro('Aguarde a imagem da câmera antes de selecionar a área.');
      return;
    }

    if (!roi) {
      setModoSelecao(true);
      setRoiConfirmada(false);
      return;
    }

    if (!roiConfirmada) {
      setRoiConfirmada(true);
      setModoSelecao(false);
      return;
    }

    setRoi(null);
    setRoiConfirmada(false);
    setModoSelecao(true);
  };

  const handleLimparRoi = () => {
    setRoi(null);
    setRoiConfirmada(false);
    setModoSelecao(false);
    setErro(null);
  };

  const handleRestaurarRoi = () => {
    if (!larguraFonte || !alturaFonte) return;

    setRoi({
      x: 0,
      y: 0,
      largura: Math.round(larguraFonte),
      altura: Math.round(alturaFonte),
    });
    setRoiConfirmada(false);
    setModoSelecao(false);
    setErro(null);
  };

  const normalizarRoiParaBackend = () => {
    if (!roi || !larguraFonte || !alturaFonte) return null;

    const limitar = (valor) => Math.max(0, Math.min(1, valor));

    return {
      x1: limitar(roi.x / larguraFonte),
      y1: limitar(roi.y / alturaFonte),
      x2: limitar((roi.x + roi.largura) / larguraFonte),
      y2: limitar((roi.y + roi.altura) / alturaFonte),
    };
  };

  const garantirAmbientePersistido = async () => {
    const nome = nomeAmbiente.trim();
    const descricaoNormalizada = descricao.trim();

    if (!nome) {
      throw new Error('NOME_AMBIENTE_OBRIGATORIO');
    }

    const camerasOriginais = Array.isArray(ambienteEmEdicao?.cameras)
      ? ambienteEmEdicao.cameras
          .map((camera) => camera?.camera_uid)
          .filter(Boolean)
      : [];

    const cameraUids = Array.from(
      new Set([...camerasOriginais, cameraSelecionadaUid].filter(Boolean))
    );

    const idAtual = ambienteIdFluxo || ambienteEmEdicao?.ambiente_id || null;

    if (idAtual) {
      await ambientesApi.editar(idAtual, {
        nome,
        descricao: descricaoNormalizada,
        camera_uids: cameraUids,
      });
      setAmbienteIdFluxo(idAtual);
      return idAtual;
    }

    const dados = await ambientesApi.criar({
      nome,
      descricao: descricaoNormalizada,
      camera_uids: cameraUids,
      epis_obrigatorios: [],
    });

    const novoId = dados?.ambiente?.ambiente_id || dados?.ambiente_id || null;

    if (!novoId) {
      throw new Error('AMBIENTE_ID_NAO_RETORNADO');
    }

    setAmbienteIdFluxo(novoId);
    return novoId;
  };

  const handleAvancarMaquinario = async () => {
    setErro(null);
    setPreviewErro(null);

    if (!roiConfirmada || !roi) {
      setErro('Confirme a área de monitoramento antes de avançar.');
      return;
    }

    if (!cameraSelecionadaUid || !previewSessionId) {
      setErro('A câmera precisa estar com a transmissão ativa para analisar o maquinário.');
      return;
    }

    const roiNormalizada = normalizarRoiParaBackend();
    if (!roiNormalizada) {
      setErro('Não foi possível normalizar a área selecionada.');
      return;
    }

    setPreparandoMaquinario(true);
    setMaquinarioConfirmado(false);

    try {
      setApiContext({ perfil: 'GERENCIAL' });

      if (analiseMaquinarioId) {
        try {
          await ambientesApi.descartarAnaliseMaquinario(analiseMaquinarioId);
        } catch {
          // A análise temporária pode já ter expirado; uma nova será criada abaixo.
        }
      }

      const ambienteId = await garantirAmbientePersistido();

      await ambientesApi.definirRoi(
        ambienteId,
        cameraSelecionadaUid,
        roiNormalizada
      );

      const analise = await ambientesApi.prepararMaquinario(ambienteId, {
        sessoes_por_camera: {
          [cameraSelecionadaUid]: previewSessionId,
        },
        qualidade_jpeg: 90,
      });

      const objetos = Array.isArray(analise?.objetos) ? analise.objetos : [];
      const analiseCamera =
        analise?.analises_cameras?.[cameraSelecionadaUid] ||
        Object.values(analise?.analises_cameras || {})[0] ||
        null;
      const imagem = analiseCamera?.imagem_analisada || null;

      setAnaliseMaquinarioId(analise?.analise_id || null);
      setObjetosDetectados(objetos);
      setIdsMaquinario([]);
      setImagemMaquinarioSrc(
        imagem?.frame_base64
          ? `data:${imagem.mime_type || 'image/jpeg'};base64,${imagem.frame_base64}`
          : frameSrc
      );
      setEtapaAtual(3);
    } catch (error) {
      setErro(mensagemApi(error));
    } finally {
      setPreparandoMaquinario(false);
    }
  };

  const idDoObjeto = (objeto) =>
    String(objeto?.id || objeto?.id_global || '').trim();

  const handleToggleMaquinario = (objeto) => {
    const id = idDoObjeto(objeto);
    if (!id || maquinarioConfirmado) return;

    setIdsMaquinario((prev) =>
      prev.includes(id)
        ? prev.filter((item) => item !== id)
        : [...prev, id]
    );
  };

  const handleConfirmarMaquinario = async () => {
    setErro(null);

    if (!ambienteIdFluxo || !analiseMaquinarioId) {
      setErro('A análise de maquinário não está disponível. Execute a análise novamente.');
      return;
    }

    setSalvandoMaquinario(true);

    try {
      setApiContext({ perfil: 'GERENCIAL' });
      const resultado = await ambientesApi.salvarMaquinario(ambienteIdFluxo, {
        analise_id: analiseMaquinarioId,
        ids_maquinario: idsMaquinario,
      });

      setObjetosDetectados(
        Array.isArray(resultado?.objetos) ? resultado.objetos : objetosDetectados
      );
      setAnaliseMaquinarioId(null);
      setMaquinarioConfirmado(true);
    } catch (error) {
      setErro(mensagemApi(error));
    } finally {
      setSalvandoMaquinario(false);
    }
  };

  const handleRefazerAnaliseMaquinario = async () => {
    setIdsMaquinario([]);
    setMaquinarioConfirmado(false);
    setEpisConfirmados(false);
    setColaboradoresConfirmados(false);
    setRevisaoDados(null);
    await handleAvancarMaquinario();
  };

  const valorEpi = (epi) =>
    String(
      typeof epi === 'string'
        ? epi
        : epi?.codigo || epi?.id || epi?.nome || epi?.label || ''
    ).trim();

  const rotuloEpi = (epi) =>
    String(
      typeof epi === 'string'
        ? epi
        : epi?.nome || epi?.label || epi?.codigo || epi?.id || ''
    ).trim();

  const carregarEtapaEpis = async () => {
    if (!ambienteIdFluxo) {
      setErro('O ambiente ainda não foi persistido.');
      return false;
    }

    setEpisLoading(true);
    setErro(null);

    try {
      setApiContext({ perfil: 'GERENCIAL' });
      const [catalogo, atuais] = await Promise.all([
        ambientesApi.listarEpisDisponiveis(),
        ambientesApi.obterEpis(ambienteIdFluxo).catch(() => null),
      ]);

      const listaCatalogo = Array.isArray(catalogo?.epis)
        ? catalogo.epis
        : Array.isArray(catalogo?.epis_disponiveis)
          ? catalogo.epis_disponiveis
          : [];

      const listaAtuais = Array.isArray(atuais?.epis_obrigatorios)
        ? atuais.epis_obrigatorios
        : Array.isArray(atuais?.epis)
          ? atuais.epis
          : Array.isArray(ambienteEmEdicao?.epis_obrigatorios)
            ? ambienteEmEdicao.epis_obrigatorios
            : [];

      setEpisDisponiveis(listaCatalogo);
      setEpisObrigatorios(listaAtuais.map(valorEpi).filter(Boolean));
      return true;
    } catch (error) {
      setErro(mensagemApi(error));
      return false;
    } finally {
      setEpisLoading(false);
    }
  };

  const handleContinuarParaEpis = async () => {
    if (!maquinarioConfirmado) {
      setErro('Confirme o maquinário antes de avançar.');
      return;
    }

    const carregou = await carregarEtapaEpis();
    if (carregou) setEtapaAtual(4);
  };

  const handleToggleEpiFluxo = (epi) => {
    const valor = valorEpi(epi);
    if (!valor) return;

    setEpisObrigatorios((prev) =>
      prev.includes(valor)
        ? prev.filter((item) => item !== valor)
        : [...prev, valor]
    );
    setEpisConfirmados(false);
    setColaboradoresConfirmados(false);
    setRevisaoDados(null);
  };

  const carregarEtapaColaboradores = async () => {
    if (!ambienteIdFluxo) {
      setErro('O ambiente ainda não foi persistido.');
      return false;
    }

    setColaboradoresLoading(true);
    setErro(null);

    try {
      setApiContext({ perfil: 'GERENCIAL' });
      const [disponiveis, atuais] = await Promise.all([
        ambientesApi.listarColaboradoresDisponiveis(),
        ambientesApi.obterColaboradores(ambienteIdFluxo).catch(() => null),
      ]);

      const listaDisponiveis = Array.isArray(disponiveis?.colaboradores)
        ? disponiveis.colaboradores
        : Array.isArray(disponiveis?.itens)
          ? disponiveis.itens
          : [];

      const listaAtuais = Array.isArray(atuais?.matriculas)
        ? atuais.matriculas
        : Array.isArray(atuais?.colaboradores)
          ? atuais.colaboradores.map((item) => item?.matricula || item).filter(Boolean)
          : [];

      setColaboradoresDisponiveis(listaDisponiveis);
      setMatriculasSelecionadas(listaAtuais.map((item) => String(item).trim()).filter(Boolean));
      return true;
    } catch (error) {
      setErro(mensagemApi(error));
      return false;
    } finally {
      setColaboradoresLoading(false);
    }
  };

  const handleSalvarEpisEAvancar = async () => {
    if (!ambienteIdFluxo) return;

    setSalvandoEpis(true);
    setErro(null);

    try {
      setApiContext({ perfil: 'GERENCIAL' });
      await ambientesApi.definirEpis(ambienteIdFluxo, episObrigatorios);
      setEpisConfirmados(true);

      const carregou = await carregarEtapaColaboradores();
      if (carregou) setEtapaAtual(5);
    } catch (error) {
      setErro(mensagemApi(error));
    } finally {
      setSalvandoEpis(false);
    }
  };

  const matriculaColaborador = (colaborador) =>
    String(colaborador?.matricula || colaborador?.id || '').trim();

  const nomeColaborador = (colaborador) =>
    String(colaborador?.nome || colaborador?.nome_completo || matriculaColaborador(colaborador) || 'Colaborador');

  const handleToggleColaborador = (colaborador) => {
    const matricula = matriculaColaborador(colaborador);
    if (!matricula) return;

    setMatriculasSelecionadas((prev) =>
      prev.includes(matricula)
        ? prev.filter((item) => item !== matricula)
        : [...prev, matricula]
    );
    setColaboradoresConfirmados(false);
    setRevisaoDados(null);
  };

  const carregarRevisao = async () => {
    if (!ambienteIdFluxo) return false;

    setRevisaoLoading(true);
    setErro(null);

    try {
      setApiContext({ perfil: 'GERENCIAL' });
      const dados = await ambientesApi.revisao(ambienteIdFluxo);
      setRevisaoDados(dados || {});
      return true;
    } catch (error) {
      setErro(mensagemApi(error));
      return false;
    } finally {
      setRevisaoLoading(false);
    }
  };

  const handleSalvarColaboradoresEAvancar = async () => {
    if (!ambienteIdFluxo) return;

    setSalvandoColaboradores(true);
    setErro(null);

    try {
      setApiContext({ perfil: 'GERENCIAL' });
      await ambientesApi.definirColaboradores(ambienteIdFluxo, matriculasSelecionadas);
      setColaboradoresConfirmados(true);

      const carregou = await carregarRevisao();
      if (carregou) setEtapaAtual(6);
    } catch (error) {
      setErro(mensagemApi(error));
    } finally {
      setSalvandoColaboradores(false);
    }
  };

  const handleFinalizarAmbiente = async () => {
    if (!ambienteIdFluxo) return;

    setFinalizandoAmbiente(true);
    setErro(null);

    try {
      setApiContext({ perfil: 'GERENCIAL' });

      // Atualiza a revisão imediatamente antes da finalização para não usar dados antigos.
      const revisaoAtual = await ambientesApi.revisao(ambienteIdFluxo);
      setRevisaoDados(revisaoAtual || {});

      await ambientesApi.finalizar(ambienteIdFluxo);
      await pararPreviewAtual();
      alert(ambienteEmEdicao ? 'Ambiente atualizado e finalizado com sucesso!' : 'Ambiente cadastrado e finalizado com sucesso!');
      await onConcluirAmbiente?.();
    } catch (error) {
      setErro(mensagemApi(error));
    } finally {
      setFinalizandoAmbiente(false);
    }
  };

  const colaboradoresFiltrados = colaboradoresDisponiveis.filter((colaborador) => {
    const termo = buscaColaboradorAmbiente.trim().toLowerCase();
    if (!termo) return true;
    return (
      nomeColaborador(colaborador).toLowerCase().includes(termo) ||
      matriculaColaborador(colaborador).toLowerCase().includes(termo)
    );
  });

  const pendenciasRevisao = Array.isArray(revisaoDados?.pendencias)
    ? revisaoDados.pendencias
    : Array.isArray(revisaoDados?.revisao?.pendencias)
      ? revisaoDados.revisao.pendencias
      : [];

  const geometriaImagem = calcularGeometriaImagem();
  const estiloRoi =
    roi && geometriaImagem
      ? {
          left: `${geometriaImagem.offsetX + roi.x * geometriaImagem.escala}px`,
          top: `${geometriaImagem.offsetY + roi.y * geometriaImagem.escala}px`,
          width: `${roi.largura * geometriaImagem.escala}px`,
          height: `${roi.altura * geometriaImagem.escala}px`,
        }
      : null;

  const calcularProporcao = () => {
    if (!roi?.largura || !roi?.altura) return '—';

    const mdc = (a, b) => {
      let x = Math.max(1, Math.round(a));
      let y = Math.max(1, Math.round(b));
      while (y) {
        const resto = x % y;
        x = y;
        y = resto;
      }
      return x;
    };

    const divisor = mdc(roi.largura, roi.altura);
    const w = Math.round(roi.largura / divisor);
    const h = Math.round(roi.altura / divisor);

    if (w > 50 || h > 50) {
      return `${(roi.largura / roi.altura).toFixed(2)}:1`;
    }

    return `${w}:${h}`;
  };

  const textoBotaoRoi = !roi
    ? modoSelecao
      ? 'Arraste na Imagem'
      : 'Selecionar Área'
    : roiConfirmada
      ? 'Selecionar Novamente'
      : 'Confirmar Área';

  return (
    <div className="max-w-[1500px] mx-auto space-y-4">
      {/* Cabeçalho da tela */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium mb-2">
            <span>Ambientes</span>
            <ChevronRight className="w-3 h-3" />
            <span className="text-slate-700 font-semibold">
              {ambienteEmEdicao ? 'Editar Ambiente' : 'Cadastro de Ambiente'}
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-950">
            {ambienteEmEdicao ? 'Editar Ambiente' : 'Cadastro de Ambiente'}
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Configure uma área para monitoramento e detecção de EPI.
          </p>
        </div>

        {ambienteEmEdicao && (
          <button
            type="button"
            onClick={onCancelarEdicao}
            className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-white transition-colors flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Cancelar Edição
          </button>
        )}
      </div>

      {/* Etapas superiores */}
      <div className="bg-white border border-slate-200 rounded-xl px-5 py-4 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3 md:gap-0">
          {etapas.map((etapa, index) => {
            const concluida =
              etapa.numero < etapaAtual ||
              (etapa.numero === 2 && roiConfirmada && etapaAtual === 2) ||
              (etapa.numero === 3 && maquinarioConfirmado);
            const ativa = etapa.numero === etapaAtual && !concluida;

            return (
              <div key={etapa.numero} className="relative flex items-center md:pr-4">
                <div
                  className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center text-xs font-bold border-2 z-10 ${
                    concluida
                      ? 'bg-emerald-500 border-emerald-500 text-white'
                      : ativa
                        ? 'bg-[#FF7412] border-[#FF7412] text-white shadow-sm'
                        : 'bg-slate-100 border-slate-200 text-slate-500'
                  }`}
                >
                  {concluida ? <CheckCircle2 className="w-4 h-4" /> : etapa.numero}
                </div>
                <div className="ml-2 min-w-0">
                  <span
                    className={`block text-[11px] font-semibold truncate ${
                      ativa || concluida ? 'text-slate-900' : 'text-slate-500'
                    }`}
                  >
                    {etapa.titulo}
                  </span>
                </div>
                {index < etapas.length - 1 && (
                  <div className="hidden md:block absolute left-[calc(100%-18px)] right-0 top-4 h-px bg-slate-200" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {(erro || previewErro) && (
        <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-red-700 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{erro || previewErro}</span>
        </div>
      )}

      {/* Conteúdo principal em três colunas */}
      <div className="grid grid-cols-1 xl:grid-cols-[1.05fr_1.35fr_0.72fr] gap-4 items-stretch">
        {/* Coluna 1 — Dados do Ambiente */}
        <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 flex flex-col">
          <div className="flex items-start gap-3 mb-5">
            <div
              className={`w-9 h-9 rounded-full text-white flex items-center justify-center text-sm font-bold shrink-0 ${
                etapaAtual > 1 ? 'bg-emerald-500' : 'bg-[#FF7412]'
              }`}
            >
              {etapaAtual > 1 ? <CheckCircle2 className="w-5 h-5" /> : 1}
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Dados do Ambiente</h3>
              <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">
                Informe as informações básicas e selecione a câmera que será utilizada.
              </p>
            </div>
          </div>

          <div className="space-y-4 flex-1">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Nome do ambiente <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={nomeAmbiente}
                onChange={(e) => setNomeAmbiente(e.target.value)}
                placeholder="Ex: Área de Soldagem 01"
                className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2.5 focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-700">Descrição</label>
                <span className="text-[10px] text-slate-400">{descricao.length}/500</span>
              </div>
              <textarea
                rows="4"
                maxLength={500}
                value={descricao}
                onChange={(e) => setDescricao(e.target.value)}
                placeholder="Descreva o ambiente, atividade realizada e riscos principais."
                className="w-full text-xs bg-white border border-slate-300 rounded-lg px-3 py-2.5 resize-none focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Câmera para monitoramento <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <select
                  value={cameraSelecionadaUid}
                  onChange={(e) => void handleTrocarCamera(e.target.value)}
                  className="w-full appearance-none text-xs bg-white border border-slate-300 rounded-lg pl-9 pr-9 py-2.5 focus:border-[#FF7412] focus:ring-2 focus:ring-orange-100 focus:outline-none"
                >
                  <option value="">Selecione uma câmera</option>
                  {camerasDisponiveis.map((camera) => (
                    <option key={camera.camera_uid} value={camera.camera_uid}>
                      {camera.nome || camera.camera_uid}
                    </option>
                  ))}
                </select>
                <Camera className="w-4 h-4 text-[#FF7412] absolute left-3 top-2.5" />
                <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-2.5 pointer-events-none" />
              </div>
            </div>

            {cameraSelecionada ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
                <div className="flex gap-3">
                  <div className="w-24 h-16 rounded-lg bg-slate-900 flex items-center justify-center shrink-0 overflow-hidden">
                    {frameSrc ? (
                      <img src={frameSrc} alt="Miniatura da câmera" className="w-full h-full object-cover" />
                    ) : (
                      <Camera className="w-7 h-7 text-slate-500" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <span className="text-xs font-bold text-slate-900 block truncate">
                          {cameraSelecionada.nome || 'Câmera selecionada'}
                        </span>
                        <span className="text-[10px] text-slate-500 uppercase block mt-0.5">
                          {cameraSelecionada.tipo || 'Tipo não informado'}
                        </span>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold shrink-0 ${
                          previewSessionId || cameraOnline
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-slate-200 text-slate-600'
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            previewSessionId || cameraOnline ? 'bg-emerald-500' : 'bg-slate-400'
                          }`}
                        />
                        {previewSessionId ? 'Online' : cameraSelecionada.status || (cameraOnline ? 'Online' : 'Offline')}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-2 text-[10px] text-slate-500">
                      <span>
                        Resolução:{' '}
                        <strong className="text-slate-700 font-semibold">
                          {larguraFonte && alturaFonte
                            ? `${larguraFonte} × ${alturaFonte}`
                            : '-'}
                        </strong>
                      </span>
                      <span>
                        FPS:{' '}
                        <strong className="text-slate-700 font-semibold">
                          {previewInfo?.fps ?? cameraSelecionada.fps ?? '-'}
                        </strong>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-center">
                <Camera className="w-5 h-5 text-slate-400 mx-auto mb-1.5" />
                <p className="text-[11px] text-slate-500">
                  Selecione uma câmera cadastrada para preparar a área de monitoramento.
                </p>
              </div>
            )}

            <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 flex gap-2.5">
              <div className="w-5 h-5 rounded-full bg-blue-500 text-white text-[11px] font-bold flex items-center justify-center shrink-0">
                i
              </div>
              <p className="text-[10px] text-blue-700 leading-relaxed">
                A imagem da câmera será utilizada para definir a área de monitoramento nas próximas etapas.
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between gap-3 mt-5 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onCancelarEdicao}
              className="px-5 py-2.5 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={() => void handleContinuar()}
              disabled={iniciandoPreview}
              className="px-5 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] disabled:opacity-60 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center gap-2"
            >
              {iniciandoPreview ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : etapaAtual > 1 ? (
                <RefreshCw className="w-4 h-4" />
              ) : null}
              {iniciandoPreview ? 'Abrindo câmera...' : etapaAtual > 1 ? 'Atualizar Câmera' : 'Continuar'}
              {!iniciandoPreview && etapaAtual === 1 && <ArrowRight className="w-4 h-4" />}
            </button>
          </div>
        </section>

        {etapaAtual === 3 ? (
          <>
            {/* Coluna 2 — Maquinário */}
            <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 flex flex-col">
              <div className="flex items-start justify-between gap-3 mb-4">
                <div className="flex items-start gap-3">
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${
                      maquinarioConfirmado
                        ? 'bg-emerald-500 text-white'
                        : 'bg-[#FF7412] text-white'
                    }`}
                  >
                    {maquinarioConfirmado ? <CheckCircle2 className="w-5 h-5" /> : 3}
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Maquinário</h3>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      A IA detecta os objetos; você confirma manualmente quais são maquinários.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => void handleRefazerAnaliseMaquinario()}
                  disabled={preparandoMaquinario || salvandoMaquinario}
                  className="px-3 py-2 border border-slate-300 hover:bg-slate-50 rounded-lg text-[10px] font-semibold text-slate-600 flex items-center gap-1.5 disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${preparandoMaquinario ? 'animate-spin' : ''}`} />
                  Refazer análise
                </button>
              </div>

              <div className="relative flex-1 min-h-[430px] rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center">
                {imagemMaquinarioSrc ? (
                  <img
                    src={imagemMaquinarioSrc}
                    alt="Análise de objetos para seleção de maquinário"
                    className="absolute inset-0 w-full h-full object-contain"
                  />
                ) : (
                  <div className="text-center px-8">
                    <Cpu className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                    <p className="text-xs font-semibold text-slate-300">
                      Nenhuma imagem de análise disponível
                    </p>
                  </div>
                )}

                <div className="absolute top-3 left-3 rounded-lg bg-black/65 border border-white/10 px-3 py-1.5 text-[10px] text-white flex items-center gap-2">
                  <Cpu className="w-3.5 h-3.5 text-[#FF7412]" />
                  {objetosDetectados.length} objeto(s) detectado(s)
                </div>

                <div className="absolute top-3 right-3 rounded-lg bg-black/65 border border-white/10 px-3 py-1.5 text-[10px] text-white">
                  {cameraSelecionada?.nome || 'Câmera'}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 mt-3">
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                  <span className="block text-[9px] uppercase font-bold text-slate-400">Detectados</span>
                  <strong className="text-lg text-slate-900">{objetosDetectados.length}</strong>
                </div>
                <div className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2.5">
                  <span className="block text-[9px] uppercase font-bold text-orange-500">Selecionados</span>
                  <strong className="text-lg text-orange-700">{idsMaquinario.length}</strong>
                </div>
                <div className={`rounded-lg border px-3 py-2.5 ${maquinarioConfirmado ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-slate-50'}`}>
                  <span className={`block text-[9px] uppercase font-bold ${maquinarioConfirmado ? 'text-emerald-500' : 'text-slate-400'}`}>Status</span>
                  <strong className={`text-xs ${maquinarioConfirmado ? 'text-emerald-700' : 'text-slate-700'}`}>
                    {maquinarioConfirmado ? 'Confirmado' : 'Aguardando confirmação'}
                  </strong>
                </div>
              </div>
            </section>

            {/* Coluna 3 — Seleção de maquinário */}
            <aside className="space-y-4">
              <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
                <div className="flex items-center justify-between gap-2 mb-3">
                  <h3 className="text-xs font-bold text-slate-900">Objetos Detectados</h3>
                  <span className="text-[9px] text-slate-400">Seleção manual</span>
                </div>

                {objetosDetectados.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-center">
                    <Cpu className="w-5 h-5 text-slate-400 mx-auto mb-1.5" />
                    <p className="text-[10px] text-slate-500 leading-relaxed">
                      Nenhum objeto foi detectado. Você pode confirmar a etapa sem selecionar maquinário.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[390px] overflow-y-auto pr-1">
                    {objetosDetectados.map((objeto, index) => {
                      const id = idDoObjeto(objeto);
                      const selecionado = idsMaquinario.includes(id);
                      const camerasObjeto = Array.isArray(objeto?.cameras) ? objeto.cameras : [];

                      return (
                        <button
                          type="button"
                          key={id || `objeto-${index}`}
                          onClick={() => handleToggleMaquinario(objeto)}
                          disabled={!id || maquinarioConfirmado}
                          className={`w-full p-3 rounded-lg border text-left transition-all disabled:cursor-default ${
                            selecionado
                              ? 'border-[#FF7412] bg-orange-50'
                              : 'border-slate-200 bg-white hover:border-slate-300'
                          }`}
                        >
                          <div className="flex items-start gap-2.5">
                            <div
                              className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 mt-0.5 ${
                                selecionado
                                  ? 'bg-[#FF7412] border-[#FF7412] text-white'
                                  : 'border-slate-300 bg-white'
                              }`}
                            >
                              {selecionado && <CheckCircle2 className="w-3 h-3" />}
                            </div>
                            <div className="min-w-0 flex-1">
                              <span className="text-[11px] font-bold text-slate-900 block truncate">
                                {objeto?.nome || `Objeto ${objeto?.numero ?? index + 1}`}
                              </span>
                              <span className="text-[9px] text-slate-400 block mt-0.5 truncate">
                                ID: {id || 'não informado'}
                              </span>
                              {camerasObjeto.length > 0 && (
                                <span className="text-[9px] text-slate-500 block mt-1">
                                  {camerasObjeto.length} câmera(s)
                                </span>
                              )}
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}

                <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 flex gap-2.5 mt-4">
                  <div className="w-5 h-5 rounded-full bg-blue-500 text-white text-[11px] font-bold flex items-center justify-center shrink-0">i</div>
                  <p className="text-[10px] text-blue-700 leading-relaxed">
                    O backend detecta objetos, mas não decide quais são máquinas. Essa classificação depende da sua seleção.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => void handleConfirmarMaquinario()}
                  disabled={salvandoMaquinario || maquinarioConfirmado || !ambienteIdFluxo}
                  className={`w-full mt-4 py-2.5 rounded-lg text-[11px] font-semibold text-white flex items-center justify-center gap-2 transition-colors disabled:opacity-55 disabled:cursor-not-allowed ${
                    maquinarioConfirmado
                      ? 'bg-emerald-600'
                      : 'bg-[#FF7412] hover:bg-[#e0620a]'
                  }`}
                >
                  {salvandoMaquinario ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : maquinarioConfirmado ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : (
                    <Cpu className="w-4 h-4" />
                  )}
                  {salvandoMaquinario
                    ? 'Salvando seleção...'
                    : maquinarioConfirmado
                      ? 'Maquinário Confirmado'
                      : idsMaquinario.length > 0
                        ? `Confirmar ${idsMaquinario.length} Maquinário(s)`
                        : 'Confirmar sem Maquinário'}
                </button>
              </div>

              <div className={`border rounded-xl shadow-sm p-4 ${maquinarioConfirmado ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'}`}>
                <div className={`flex items-center gap-2 ${maquinarioConfirmado ? 'text-emerald-700' : 'text-slate-600'}`}>
                  {maquinarioConfirmado ? (
                    <CheckCircle2 className="w-5 h-5 shrink-0" />
                  ) : (
                    <Clock className="w-5 h-5 shrink-0" />
                  )}
                  <span className="text-xs font-bold">
                    {maquinarioConfirmado ? 'Etapa 3 concluída' : 'Etapa 3 em andamento'}
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 leading-relaxed mt-2">
                  {maquinarioConfirmado
                    ? 'A seleção foi persistida no ambiente. O próximo passo será definir os EPIs obrigatórios.'
                    : 'Selecione os objetos que representam maquinários e confirme a decisão.'}
                </p>
                {maquinarioConfirmado && (
                  <button
                    type="button"
                    onClick={() => void handleContinuarParaEpis()}
                    disabled={episLoading}
                    className="w-full mt-3 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] disabled:opacity-55 text-white rounded-lg text-[11px] font-semibold flex items-center justify-center gap-2"
                  >
                    {episLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                    {episLoading ? 'Carregando EPIs...' : 'Continuar para EPIs'}
                    {!episLoading && <ArrowRight className="w-4 h-4" />}
                  </button>
                )}
              </div>
            </aside>
          </>
        ) : etapaAtual === 4 ? (
          <>
            <section className="xl:col-span-2 bg-white border border-slate-200 rounded-xl shadow-sm p-5 flex flex-col">
              <div className="flex items-start justify-between gap-3 mb-5">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-full bg-[#FF7412] text-white flex items-center justify-center text-sm font-bold shrink-0">4</div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">EPIs Obrigatórios</h3>
                    <p className="text-[11px] text-slate-500 mt-0.5">Selecione os EPIs exigidos para este ambiente.</p>
                  </div>
                </div>
                <span className="text-[10px] font-semibold text-slate-500">{episObrigatorios.length} selecionado(s)</span>
              </div>

              {episLoading ? (
                <div className="flex-1 min-h-[380px] flex items-center justify-center text-slate-500 text-xs">
                  <RefreshCw className="w-5 h-5 animate-spin mr-2 text-[#FF7412]" /> Carregando catálogo de EPIs...
                </div>
              ) : episDisponiveis.length === 0 ? (
                <div className="flex-1 min-h-[380px] rounded-xl border border-dashed border-slate-300 bg-slate-50 flex items-center justify-center text-center p-8">
                  <div>
                    <ShieldCheck className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                    <p className="text-xs font-semibold text-slate-700">Nenhum EPI disponível no catálogo</p>
                    <p className="text-[10px] text-slate-500 mt-1">Você ainda pode salvar esta etapa sem EPIs.</p>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 content-start">
                  {episDisponiveis.map((epi, index) => {
                    const valor = valorEpi(epi);
                    const selecionado = episObrigatorios.includes(valor);
                    return (
                      <button
                        type="button"
                        key={valor || `epi-${index}`}
                        onClick={() => handleToggleEpiFluxo(epi)}
                        className={`p-4 rounded-xl border text-left transition-all ${
                          selecionado
                            ? 'border-[#FF7412] bg-orange-50 shadow-sm'
                            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-5 h-5 rounded border flex items-center justify-center shrink-0 ${
                            selecionado ? 'bg-[#FF7412] border-[#FF7412] text-white' : 'border-slate-300 bg-white'
                          }`}>
                            {selecionado && <CheckCircle2 className="w-3.5 h-3.5" />}
                          </div>
                          <div className="min-w-0">
                            <span className="block text-xs font-bold text-slate-900">{rotuloEpi(epi) || valor}</span>
                            {typeof epi !== 'string' && epi?.descricao && (
                              <span className="block text-[10px] text-slate-500 mt-1 line-clamp-2">{epi.descricao}</span>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              <div className="mt-auto pt-5 flex justify-between gap-3">
                <button type="button" onClick={() => setEtapaAtual(3)} className="px-4 py-2.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50">Voltar</button>
                <button
                  type="button"
                  onClick={() => void handleSalvarEpisEAvancar()}
                  disabled={salvandoEpis || episLoading}
                  className="px-5 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] disabled:opacity-55 text-white rounded-lg text-xs font-semibold flex items-center gap-2"
                >
                  {salvandoEpis && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {salvandoEpis ? 'Salvando EPIs...' : 'Salvar e continuar'}
                  {!salvandoEpis && <ArrowRight className="w-4 h-4" />}
                </button>
              </div>
            </section>
          </>
        ) : etapaAtual === 5 ? (
          <>
            <section className="xl:col-span-2 bg-white border border-slate-200 rounded-xl shadow-sm p-5 flex flex-col">
              <div className="flex items-start justify-between gap-3 mb-4">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-full bg-[#FF7412] text-white flex items-center justify-center text-sm font-bold shrink-0">5</div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Colaboradores</h3>
                    <p className="text-[11px] text-slate-500 mt-0.5">Vincule os colaboradores que atuam neste ambiente.</p>
                  </div>
                </div>
                <span className="text-[10px] font-semibold text-slate-500">{matriculasSelecionadas.length} selecionado(s)</span>
              </div>

              <div className="relative mb-4">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={buscaColaboradorAmbiente}
                  onChange={(e) => setBuscaColaboradorAmbiente(e.target.value)}
                  placeholder="Buscar por nome ou matrícula..."
                  className="w-full text-xs pl-9 pr-4 py-2.5 bg-white border border-slate-300 rounded-lg focus:outline-none focus:border-[#FF7412]"
                />
              </div>

              {colaboradoresLoading ? (
                <div className="flex-1 min-h-[360px] flex items-center justify-center text-xs text-slate-500">
                  <RefreshCw className="w-5 h-5 animate-spin mr-2 text-[#FF7412]" /> Carregando colaboradores...
                </div>
              ) : colaboradoresFiltrados.length === 0 ? (
                <div className="flex-1 min-h-[360px] rounded-xl border border-dashed border-slate-300 bg-slate-50 flex items-center justify-center text-center p-8">
                  <div>
                    <Users className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                    <p className="text-xs font-semibold text-slate-700">Nenhum colaborador encontrado</p>
                    <p className="text-[10px] text-slate-500 mt-1">Você pode continuar sem vincular colaboradores.</p>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[430px] overflow-y-auto pr-1">
                  {colaboradoresFiltrados.map((colaborador, index) => {
                    const matricula = matriculaColaborador(colaborador);
                    const selecionado = matriculasSelecionadas.includes(matricula);
                    return (
                      <button
                        type="button"
                        key={matricula || `colaborador-${index}`}
                        onClick={() => handleToggleColaborador(colaborador)}
                        className={`p-3.5 rounded-xl border text-left transition-all ${
                          selecionado ? 'border-[#FF7412] bg-orange-50' : 'border-slate-200 bg-white hover:border-slate-300'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
                            selecionado ? 'bg-[#FF7412] text-white' : 'bg-slate-100 text-slate-600'
                          }`}>
                            {nomeColaborador(colaborador).charAt(0).toUpperCase()}
                          </div>
                          <div className="min-w-0 flex-1">
                            <span className="block text-xs font-bold text-slate-900 truncate">{nomeColaborador(colaborador)}</span>
                            <span className="block text-[10px] text-slate-500 font-mono mt-0.5">{matricula || 'Sem matrícula'}</span>
                          </div>
                          <div className={`w-5 h-5 rounded border flex items-center justify-center shrink-0 ${
                            selecionado ? 'bg-[#FF7412] border-[#FF7412] text-white' : 'border-slate-300 bg-white'
                          }`}>
                            {selecionado && <CheckCircle2 className="w-3.5 h-3.5" />}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              <div className="mt-auto pt-5 flex justify-between gap-3">
                <button type="button" onClick={() => setEtapaAtual(4)} className="px-4 py-2.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50">Voltar</button>
                <button
                  type="button"
                  onClick={() => void handleSalvarColaboradoresEAvancar()}
                  disabled={salvandoColaboradores || colaboradoresLoading}
                  className="px-5 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] disabled:opacity-55 text-white rounded-lg text-xs font-semibold flex items-center gap-2"
                >
                  {salvandoColaboradores && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {salvandoColaboradores ? 'Salvando vínculos...' : 'Salvar e revisar'}
                  {!salvandoColaboradores && <ArrowRight className="w-4 h-4" />}
                </button>
              </div>
            </section>
          </>
        ) : etapaAtual === 6 ? (
          <>
            <section className="xl:col-span-2 bg-white border border-slate-200 rounded-xl shadow-sm p-5">
              <div className="flex items-start justify-between gap-3 mb-5">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-full bg-[#FF7412] text-white flex items-center justify-center text-sm font-bold shrink-0">6</div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Revisão</h3>
                    <p className="text-[11px] text-slate-500 mt-0.5">Confira a configuração completa antes de finalizar.</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => void carregarRevisao()}
                  disabled={revisaoLoading}
                  className="px-3 py-2 border border-slate-300 rounded-lg text-[10px] font-semibold text-slate-600 hover:bg-slate-50 flex items-center gap-1.5 disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${revisaoLoading ? 'animate-spin' : ''}`} /> Atualizar revisão
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-xl border border-slate-200 p-4">
                  <h4 className="text-xs font-bold text-slate-900 mb-3 flex items-center gap-2"><Layers className="w-4 h-4 text-[#FF7412]" /> Ambiente</h4>
                  <div className="space-y-2 text-[11px]">
                    <div className="flex justify-between gap-3"><span className="text-slate-500">Nome</span><strong className="text-slate-800 text-right">{nomeAmbiente}</strong></div>
                    <div className="flex justify-between gap-3"><span className="text-slate-500">Câmera</span><strong className="text-slate-800 text-right">{cameraSelecionada?.nome || cameraSelecionadaUid}</strong></div>
                    <div className="flex justify-between gap-3"><span className="text-slate-500">Área</span><strong className="text-emerald-700">Confirmada</strong></div>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 p-4">
                  <h4 className="text-xs font-bold text-slate-900 mb-3 flex items-center gap-2"><Cpu className="w-4 h-4 text-[#FF7412]" /> Maquinário</h4>
                  <div className="space-y-2 text-[11px]">
                    <div className="flex justify-between gap-3"><span className="text-slate-500">Selecionados</span><strong className="text-slate-800">{idsMaquinario.length}</strong></div>
                    <div className="flex justify-between gap-3"><span className="text-slate-500">Status</span><strong className="text-emerald-700">Confirmado</strong></div>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 p-4">
                  <h4 className="text-xs font-bold text-slate-900 mb-3 flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-[#FF7412]" /> EPIs</h4>
                  {episObrigatorios.length === 0 ? (
                    <p className="text-[10px] text-slate-500">Nenhum EPI obrigatório selecionado.</p>
                  ) : (
                    <div className="flex flex-wrap gap-1.5">
                      {episObrigatorios.map((epi) => <span key={epi} className="px-2 py-1 rounded-full bg-orange-50 border border-orange-200 text-[9px] font-semibold text-orange-700">{epi}</span>)}
                    </div>
                  )}
                </div>

                <div className="rounded-xl border border-slate-200 p-4">
                  <h4 className="text-xs font-bold text-slate-900 mb-3 flex items-center gap-2"><Users className="w-4 h-4 text-[#FF7412]" /> Colaboradores</h4>
                  <div className="text-2xl font-bold text-slate-900">{matriculasSelecionadas.length}</div>
                  <p className="text-[10px] text-slate-500 mt-1">colaborador(es) vinculado(s)</p>
                </div>
              </div>

              <div className={`mt-4 rounded-xl border p-4 ${pendenciasRevisao.length ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'}`}>
                <div className="flex items-start gap-3">
                  {revisaoLoading ? (
                    <RefreshCw className="w-5 h-5 animate-spin text-[#FF7412] shrink-0" />
                  ) : pendenciasRevisao.length ? (
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  )}
                  <div>
                    <span className={`text-xs font-bold ${pendenciasRevisao.length ? 'text-amber-900' : 'text-emerald-900'}`}>
                      {revisaoLoading ? 'Atualizando revisão...' : pendenciasRevisao.length ? 'Pendências encontradas pelo backend' : 'Revisão pronta para finalização'}
                    </span>
                    {pendenciasRevisao.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {pendenciasRevisao.map((item, index) => (
                          <div key={`${String(item)}-${index}`} className="text-[10px] text-amber-800">• {typeof item === 'string' ? item : item?.mensagem || item?.erro || JSON.stringify(item)}</div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-5 flex justify-between gap-3">
                <button type="button" onClick={() => setEtapaAtual(5)} className="px-4 py-2.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50">Voltar</button>
                <button
                  type="button"
                  onClick={() => void handleFinalizarAmbiente()}
                  disabled={finalizandoAmbiente || revisaoLoading}
                  className="px-6 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] disabled:opacity-55 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm"
                >
                  {finalizandoAmbiente ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  {finalizandoAmbiente ? 'Finalizando...' : 'Finalizar Ambiente'}
                </button>
              </div>
            </section>
          </>
        ) : (
          <>
            {/* Coluna 2 — Área de Monitoramento */}
            <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 flex flex-col">
              <div className="flex items-start gap-3 mb-4">
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${
                    etapaAtual === 2
                      ? 'bg-[#FF7412] text-white'
                      : 'bg-slate-100 border border-slate-200 text-slate-500'
                  }`}
                >
                  2
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Área de Monitoramento</h3>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Selecione e ajuste a área da imagem que será monitorada.
                  </p>
                </div>
              </div>

              <div
                ref={previewStageRef}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                className={`relative flex-1 min-h-[370px] rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center select-none ${
                  modoSelecao ? 'cursor-crosshair' : 'cursor-default'
                }`}
              >
                {frameSrc ? (
                  <img
                    src={frameSrc}
                    alt="Área de monitoramento da câmera"
                    draggable={false}
                    onLoad={(event) => {
                      setFrameSize({
                        width: event.currentTarget.naturalWidth,
                        height: event.currentTarget.naturalHeight,
                      });
                    }}
                    className="absolute inset-0 w-full h-full object-contain pointer-events-none"
                  />
                ) : (
                  <div className="text-center px-8">
                    {iniciandoPreview ? (
                      <RefreshCw className="w-12 h-12 text-[#FF7412] mx-auto mb-3 animate-spin" />
                    ) : (
                      <Camera className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                    )}
                    <p className="text-xs font-semibold text-slate-300">
                      {etapaAtual < 2
                        ? 'Clique em Continuar para abrir a câmera'
                        : iniciandoPreview
                          ? 'Abrindo transmissão da câmera...'
                          : 'Aguardando imagem da câmera...'}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-1">
                      Depois, clique em Selecionar Área e arraste sobre a imagem.
                    </p>
                  </div>
                )}

                {estiloRoi && (
                  <div
                    className={`absolute border-2 ${
                      roiConfirmada
                        ? 'border-emerald-400 bg-emerald-400/15'
                        : 'border-[#FF7412] bg-[#FF7412]/15'
                    } pointer-events-none`}
                    style={estiloRoi}
                  >
                    <div
                      className={`absolute -top-7 left-0 px-2 py-1 rounded text-[9px] font-bold text-white whitespace-nowrap ${
                        roiConfirmada ? 'bg-emerald-600' : 'bg-[#FF7412]'
                      }`}
                    >
                      {roiConfirmada ? 'Área Confirmada' : 'Área de Monitoramento'}
                    </div>
                  </div>
                )}

                <div className="absolute top-3 left-3 inline-flex items-center gap-2 rounded-lg bg-black/60 border border-white/10 px-3 py-1.5 text-[10px] text-white pointer-events-none">
                  <span className={`w-2 h-2 rounded-full ${previewSessionId ? 'bg-emerald-500' : 'bg-slate-500'}`} />
                  {cameraSelecionada?.nome || 'Nenhuma câmera selecionada'}
                </div>

                <div className="absolute top-3 right-3 inline-flex items-center gap-1.5 rounded-lg bg-black/60 border border-white/10 px-3 py-1.5 text-[10px] font-bold text-white pointer-events-none">
                  <span className={`w-2 h-2 rounded-full ${previewSessionId ? 'bg-red-500' : 'bg-slate-500'}`} />
                  {previewSessionId ? 'AO VIVO' : 'PARADO'}
                </div>

                {modoSelecao && frameSrc && (
                  <div className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-lg bg-black/70 border border-white/10 px-3 py-1.5 text-[10px] font-semibold text-white pointer-events-none">
                    Clique e arraste para marcar a área
                  </div>
                )}
              </div>

              <div className="grid grid-cols-3 gap-2.5 mt-3">
                <button
                  type="button"
                  onClick={handleAcaoPrincipalRoi}
                  disabled={etapaAtual < 2 || !frameSrc || iniciandoPreview}
                  className={`py-2.5 rounded-lg text-[11px] font-semibold transition-colors disabled:opacity-45 disabled:cursor-not-allowed ${
                    roiConfirmada
                      ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                      : 'bg-[#FF7412] hover:bg-[#e0620a] text-white'
                  }`}
                >
                  {textoBotaoRoi}
                </button>
                <button
                  type="button"
                  onClick={handleLimparRoi}
                  disabled={!roi}
                  className="py-2.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50 text-[11px] font-semibold disabled:opacity-45 disabled:cursor-not-allowed"
                >
                  Limpar Seleção
                </button>
                <button
                  type="button"
                  onClick={handleRestaurarRoi}
                  disabled={!frameSrc || !larguraFonte || !alturaFonte}
                  className="py-2.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50 text-[11px] font-semibold disabled:opacity-45 disabled:cursor-not-allowed"
                >
                  Restaurar
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3 mt-3">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-2.5">
                  <span className="block text-[10px] font-bold text-slate-700 mb-2">Imagem Original</span>
                  <div className="aspect-video rounded-lg bg-slate-950 border border-slate-200 overflow-hidden flex items-center justify-center">
                    {frameSrc ? (
                      <img src={frameSrc} alt="Imagem original" className="w-full h-full object-contain" />
                    ) : (
                      <Camera className="w-6 h-6 text-slate-500" />
                    )}
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-2.5">
                  <span className="block text-[10px] font-bold text-slate-700 mb-2">Área Selecionada (Zoom)</span>
                  <div className="aspect-video rounded-lg bg-slate-950 border border-slate-200 overflow-hidden flex items-center justify-center">
                    {frameSrc && roi ? (
                      <canvas
                        ref={zoomCanvasRef}
                        className="w-full h-full object-contain bg-black"
                      />
                    ) : (
                      <Maximize2 className="w-6 h-6 text-slate-500" />
                    )}
                  </div>
                </div>
              </div>

              {roiConfirmada && (
                <button
                  type="button"
                  onClick={() => void handleAvancarMaquinario()}
                  disabled={preparandoMaquinario || !previewSessionId}
                  className="w-full mt-3 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] disabled:opacity-55 text-white rounded-lg text-[11px] font-semibold flex items-center justify-center gap-2"
                >
                  {preparandoMaquinario ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Cpu className="w-4 h-4" />
                  )}
                  {preparandoMaquinario ? 'Analisando área...' : 'Continuar para Maquinário'}
                  {!preparandoMaquinario && <ArrowRight className="w-4 h-4" />}
                </button>
              )}
            </section>

            {/* Coluna 3 — Informações da seleção */}
            <aside className="space-y-4">
              <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
                <h3 className="text-xs font-bold text-slate-900 mb-4">Informações da Seleção</h3>
                <div className="space-y-2 text-[10px] text-slate-500">
                  <div className="flex justify-between gap-3"><span>X:</span><strong className="text-slate-700">{roi ? roi.x : '—'}</strong></div>
                  <div className="flex justify-between gap-3"><span>Y:</span><strong className="text-slate-700">{roi ? roi.y : '—'}</strong></div>
                  <div className="flex justify-between gap-3"><span>Largura:</span><strong className="text-slate-700">{roi ? roi.largura : '—'}</strong></div>
                  <div className="flex justify-between gap-3"><span>Altura:</span><strong className="text-slate-700">{roi ? roi.altura : '—'}</strong></div>
                  <div className="flex justify-between gap-3"><span>Proporção:</span><strong className="text-slate-700">{calcularProporcao()}</strong></div>
                </div>

                <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 flex gap-2.5 mt-4">
                  <div className="w-5 h-5 rounded-full bg-blue-500 text-white text-[11px] font-bold flex items-center justify-center shrink-0">i</div>
                  <p className="text-[10px] text-blue-700 leading-relaxed">
                    A área selecionada será utilizada para detecção de maquinário, EPIs e colaboradores.
                  </p>
                </div>
              </div>

              <div
                className={`border rounded-xl shadow-sm p-4 ${
                  roiConfirmada
                    ? 'bg-emerald-50 border-emerald-200'
                    : roi
                      ? 'bg-amber-50 border-amber-200'
                      : 'bg-slate-50 border-slate-200'
                }`}
              >
                <h3
                  className={`text-xs font-bold mb-3 ${
                    roiConfirmada
                      ? 'text-emerald-900'
                      : roi
                        ? 'text-amber-900'
                        : 'text-slate-700'
                  }`}
                >
                  Pré-visualização da área
                </h3>
                <div
                  className={`space-y-2 text-[10px] ${
                    roiConfirmada
                      ? 'text-emerald-700'
                      : roi
                        ? 'text-amber-700'
                        : 'text-slate-500'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span>
                      {roiConfirmada
                        ? 'Área válida e confirmada para monitoramento'
                        : roi
                          ? 'Área selecionada — confirme para continuar'
                          : 'Aguardando definição da área'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span>
                      {frameSrc
                        ? 'Imagem da câmera disponível para seleção'
                        : 'Aguardando imagem da câmera'}
                    </span>
                  </div>
                </div>
              </div>

              {roiConfirmada && (
                <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
                  <div className="flex items-center gap-2 text-emerald-700 mb-2">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="text-xs font-bold">Etapa 2 concluída</span>
                  </div>
                  <p className="text-[10px] text-slate-500 leading-relaxed">
                    Ao avançar, o ambiente e a ROI serão persistidos para permitir a análise de maquinário no backend.
                  </p>
                </div>
              )}
            </aside>
          </>
        )}
      </div>

      {/* Barra inferior das etapas */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="grid grid-cols-1 md:grid-cols-6 divide-y md:divide-y-0 md:divide-x divide-slate-200">
          {etapas.map((etapa) => {
            const concluida =
              etapa.numero < etapaAtual ||
              (etapa.numero === 2 && roiConfirmada) ||
              (etapa.numero === 3 && maquinarioConfirmado);
            const ativa = etapa.numero === etapaAtual && !concluida;

            return (
              <div key={etapa.numero} className="p-3.5 flex items-start gap-2.5 min-h-[78px]">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 ${
                    concluida
                      ? 'bg-emerald-500 text-white'
                      : ativa
                        ? 'bg-[#FF7412] text-white'
                        : 'bg-slate-100 border border-slate-200 text-slate-500'
                  }`}
                >
                  {concluida ? <CheckCircle2 className="w-4 h-4" /> : etapa.numero}
                </div>
                <div className="min-w-0">
                  <span
                    className={`block text-[10px] font-bold ${
                      concluida || ativa ? 'text-slate-900' : 'text-slate-700'
                    }`}
                  >
                    {etapa.titulo}
                  </span>
                  <span className="block text-[9px] leading-relaxed text-slate-400 mt-1">
                    {etapa.numero === 2 && roiConfirmada
                      ? 'Área confirmada'
                      : etapa.numero === 3 && maquinarioConfirmado
                        ? 'Seleção confirmada'
                        : etapa.resumo}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// 6. CONSULTA DE AMBIENTES — dados reais do backend
function ConsultaAmbientesView({
  ambientes,
  loading,
  erro,
  onRefresh,
  onEditarAmbiente,
  onDeletarAmbiente,
  onNavigate,
}) {
  const [ambienteParaRemover, setAmbienteParaRemover] = useState(null);
  const [removendo, setRemovendo] = useState(false);
  const [erroRemocao, setErroRemocao] = useState(null);

  const confirmarExclusao = async () => {
    if (!ambienteParaRemover?.ambiente_id) return;

    setRemovendo(true);
    setErroRemocao(null);
    const resultado = await onDeletarAmbiente(ambienteParaRemover.ambiente_id);
    setRemovendo(false);

    if (resultado?.sucesso) {
      setAmbienteParaRemover(null);
    } else {
      setErroRemocao(resultado?.erro || 'Não foi possível remover o ambiente.');
    }
  };

  const statusClass = (status) => {
    const valor = String(status || '').toUpperCase();
    if (valor === 'ATIVO') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (valor === 'COM_PROBLEMA') return 'bg-amber-50 text-amber-700 border-amber-200';
    return 'bg-slate-100 text-slate-600 border-slate-200';
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Ambientes Cadastrados
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Dados carregados diretamente da API de Ambientes
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => void onRefresh()}
            disabled={loading}
            className="px-3 py-2 bg-white hover:bg-slate-50 text-slate-600 border border-slate-300 rounded-lg text-xs font-semibold flex items-center gap-2 disabled:opacity-60"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
          <button
            onClick={() => onNavigate('cadastro-ambiente')}
            className="px-4 py-2 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            Novo Ambiente
          </button>
        </div>
      </div>

      {erro && (
        <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-red-700 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{erro}</span>
        </div>
      )}

      {loading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-10 flex items-center justify-center gap-2 text-sm text-slate-500">
          <RefreshCw className="w-5 h-5 animate-spin" />
          Carregando ambientes...
        </div>
      ) : ambientes.length === 0 ? (
        <EmptyState
          icon={Layers}
          title="Nenhum ambiente configurado"
          description="Cadastre os setores de operação e defina as regras de monitoramento."
          actionText="Cadastrar Primeiro Ambiente"
          onAction={() => onNavigate('cadastro-ambiente')}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {ambientes.map((a) => {
            const cameraNome =
              a.camera_principal?.nome ||
              (a.quantidade_cameras > 0
                ? `${a.quantidade_cameras} câmera(s) vinculada(s)`
                : 'Sem câmera associada');

            return (
              <div
                key={a.ambiente_id}
                className="group bg-white p-5 rounded-xl border border-slate-200 hover:border-[#FF7412]/60 hover:shadow-md transition-all flex flex-col justify-between relative cursor-pointer"
                onClick={() => void onEditarAmbiente(a)}
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h4 className="font-bold text-slate-900 text-sm group-hover:text-[#FF7412] transition-colors truncate">
                        {a.nome}
                      </h4>
                      <span
                        className={`inline-flex mt-1 px-2 py-0.5 rounded-full border text-[9px] font-bold ${statusClass(a.status)}`}
                      >
                        {a.status || 'INATIVO'}
                      </span>
                    </div>
                    <div
                      className="flex items-center gap-1 shrink-0"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        type="button"
                        onClick={() => void onEditarAmbiente(a)}
                        className="p-1.5 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
                        title="Editar Ambiente"
                      >
                        <Edit className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setErroRemocao(null);
                          setAmbienteParaRemover(a);
                        }}
                        className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                        title="Apagar Ambiente"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <span className="text-[11px] text-[#FF7412] font-semibold mt-2 flex items-center gap-1">
                    <Camera className="w-3.5 h-3.5" />
                    {cameraNome}
                  </span>

                  <p className="text-xs text-slate-500 mt-2 line-clamp-2">
                    {a.descricao || 'Sem observações adicionais.'}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center">
                  <div>
                    <span className="block text-sm font-bold text-slate-800">
                      {a.quantidade_epis ?? 0}
                    </span>
                    <span className="text-[9px] uppercase text-slate-400 font-semibold">
                      EPIs
                    </span>
                  </div>
                  <div>
                    <span className="block text-sm font-bold text-slate-800">
                      {a.quantidade_colaboradores ?? 0}
                    </span>
                    <span className="text-[9px] uppercase text-slate-400 font-semibold">
                      Pessoas
                    </span>
                  </div>
                  <div>
                    <span className="block text-sm font-bold text-slate-800">
                      {a.infracoes_hoje ?? 0}
                    </span>
                    <span className="text-[9px] uppercase text-slate-400 font-semibold">
                      Infrações
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {ambienteParaRemover && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
              <Trash2 className="w-6 h-6" />
            </div>

            <div className="text-center">
              <h3 className="text-base font-bold text-slate-900">
                Remover Ambiente?
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Tem certeza que deseja excluir o ambiente{' '}
                <strong className="text-slate-800">
                  {ambienteParaRemover.nome}
                </strong>
                ?
              </p>
            </div>

            {erroRemocao && (
              <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
                {erroRemocao}
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                disabled={removendo}
                onClick={() => setAmbienteParaRemover(null)}
                className="flex-1 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-60"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={removendo}
                onClick={() => void confirmarExclusao()}
                className="flex-1 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-sm transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {removendo && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                {removendo ? 'Removendo...' : 'Sim, Remover'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// 7. VISÃO GERAL DE COLABORADORES
function ConsultaColaboradoresView({
  colaboradores,
  loading,
  erro,
  onRefresh,
  onDeletarColaborador,
  onNavigate,
}) {
  const [busca, setBusca] = useState('');
  const [colaboradorParaRemover, setColaboradorParaRemover] = useState(null);
  const [removendo, setRemovendo] = useState(false);

  const termo = busca.trim().toLowerCase();
  const filtrados = colaboradores.filter((c) => {
    if (!termo) return true;
    return (
      String(c?.nome || '').toLowerCase().includes(termo) ||
      String(c?.matricula || '').toLowerCase().includes(termo) ||
      String(c?.cargo || '').toLowerCase().includes(termo) ||
      String(c?.setor || '').toLowerCase().includes(termo)
    );
  });

  const confirmarExclusao = async () => {
    if (!colaboradorParaRemover?.matricula) return;

    setRemovendo(true);
    try {
      const resultado = await onDeletarColaborador(colaboradorParaRemover.matricula);
      if (!resultado?.sucesso) {
        alert(resultado?.erro || 'Não foi possível remover o colaborador.');
        return;
      }
      setColaboradorParaRemover(null);
    } finally {
      setRemovendo(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Quadro de Colaboradores</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Colaboradores persistidos no backend e disponíveis para biometria.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void onRefresh()}
            disabled={loading}
            className="px-4 py-2 border border-slate-300 hover:bg-slate-100 rounded-lg text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
          <button
            onClick={() => onNavigate('cadastro-colaborador')}
            className="px-4 py-2 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm"
          >
            <UserPlus className="w-4 h-4" />
            Cadastrar Colaborador
          </button>
        </div>
      </div>

      {erro && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {erro}
        </div>
      )}

      {loading && colaboradores.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-sm text-slate-500">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-3 text-[#FF7412]" />
          Carregando colaboradores do backend...
        </div>
      ) : colaboradores.length === 0 ? (
        <EmptyState
          icon={Users}
          title="Nenhum colaborador registrado"
          description="Cadastre o primeiro colaborador e suas referências biométricas."
          actionText="Cadastrar Primeiro Colaborador"
          onAction={() => onNavigate('cadastro-colaborador')}
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 flex items-center justify-between gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Buscar por nome, matrícula, cargo ou setor..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                className="w-full text-xs pl-9 pr-4 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:border-[#FF7412]"
              />
            </div>
            <span className="text-xs text-slate-500 font-medium">
              {filtrados.length} colaborador(es)
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">Colaborador</th>
                  <th className="py-3.5 px-4">Matrícula</th>
                  <th className="py-3.5 px-4">Cargo / Setor</th>
                  <th className="py-3.5 px-4">Biometria</th>
                  <th className="py-3.5 px-4 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtrados.map((c) => (
                  <tr key={c.matricula} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        {c.foto ? (
                          <img
                            src={c.foto}
                            alt={c.nome}
                            className="w-10 h-10 rounded-full object-cover border border-slate-300 shadow-xs shrink-0"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs shrink-0">
                            {String(c.nome || '?').charAt(0).toUpperCase()}
                          </div>
                        )}
                        <div>
                          <span className="font-semibold text-slate-900 block text-sm">{c.nome}</span>
                          <span className="text-[11px] text-slate-400">Ativo no sistema</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono font-medium text-slate-700">{c.matricula}</td>
                    <td className="py-3 px-4">
                      <span className="font-semibold text-slate-700 block">{c.cargo || '-'}</span>
                      <span className="text-[10px] text-slate-400">{c.setor || 'Setor não informado'}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-semibold ${
                        c.biometria_cadastrada
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-amber-100 text-amber-700'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${c.biometria_cadastrada ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                        {c.biometria_cadastrada
                          ? `${c.quantidade_biometrias || 1} referência(s)`
                          : 'Sem biometria'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      <button
                        type="button"
                        onClick={() => alert(`Edição de ${c.nome} será tratada na próxima etapa.`)}
                        className="text-slate-400 hover:text-slate-800 p-1.5 rounded hover:bg-slate-100 transition-colors"
                        title="Editar Colaborador"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setColaboradorParaRemover(c)}
                        className="text-red-400 hover:text-red-600 p-1.5 rounded hover:bg-red-50 transition-colors"
                        title="Remover Colaborador"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {colaboradorParaRemover && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
              <Trash2 className="w-6 h-6" />
            </div>
            <div className="text-center">
              <h3 className="text-base font-bold text-slate-900">Remover Colaborador?</h3>
              <p className="text-xs text-slate-500 mt-1">
                Remover <strong className="text-slate-800">{colaboradorParaRemover.nome}</strong>{' '}
                (Matrícula: {colaboradorParaRemover.matricula})?
              </p>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                disabled={removendo}
                onClick={() => setColaboradorParaRemover(null)}
                className="flex-1 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={removendo}
                onClick={() => void confirmarExclusao()}
                className="flex-1 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-sm disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {removendo && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                {removendo ? 'Removendo...' : 'Sim, Remover'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// 8. CADASTRO DE COLABORADOR — 3 REFERÊNCIAS BIOMÉTRICAS
function CadastroColaboradorView({
  cameras,
  camerasLoading,
  onCadastrarColaborador,
}) {
  const [nome, setNome] = useState('');
  const [matricula, setMatricula] = useState('');
  const [cargo, setCargo] = useState('');
  const [setor, setSetor] = useState('');
  const [cameraUid, setCameraUid] = useState('');

  const [sessionId, setSessionId] = useState(null);
  const [frameSrc, setFrameSrc] = useState(null);
  const [previewInfo, setPreviewInfo] = useState(null);
  const [previewErro, setPreviewErro] = useState(null);
  const [iniciandoPreview, setIniciandoPreview] = useState(false);

  const [capturas, setCapturas] = useState({
    frontal: null,
    esquerda: null,
    direita: null,
  });
  const [capturando, setCapturando] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);

  const previewSessionRef = React.useRef(null);

  const referencias = [
    {
      id: 'frontal',
      titulo: 'Frente',
      instrucao: 'Olhe diretamente para a câmera, com o rosto centralizado.',
    },
    {
      id: 'esquerda',
      titulo: 'Esquerda',
      instrucao: 'Vire levemente o rosto para a esquerda, mantendo os olhos visíveis.',
    },
    {
      id: 'direita',
      titulo: 'Direita',
      instrucao: 'Vire levemente o rosto para a direita, mantendo os olhos visíveis.',
    },
  ];

  useEffect(() => {
    if (!cameraUid && cameras?.[0]?.camera_uid) {
      setCameraUid(cameras[0].camera_uid);
    }
  }, [cameras, cameraUid]);

  const pararPreview = async () => {
    const atual = previewSessionRef.current;
    previewSessionRef.current = null;
    setSessionId(null);
    setFrameSrc(null);
    setPreviewInfo(null);

    if (!atual) return;

    try {
      await camerasApi.pararPreview(atual);
    } catch (error) {
      if (error?.payload?.erro !== 'PREVIEW_NAO_ENCONTRADO') {
        setPreviewErro(mensagemApi(error));
      }
    }
  };

  useEffect(() => {
    return () => {
      const atual = previewSessionRef.current;
      if (atual) {
        void camerasApi.pararPreview(atual).catch(() => {});
      }
    };
  }, []);

  useEffect(() => {
    if (!sessionId) return undefined;

    let cancelado = false;
    let executando = false;

    const atualizarFrame = async () => {
      if (cancelado || executando) return;
      executando = true;

      try {
        const dados = await camerasApi.obterFramePreview(sessionId);
        if (!cancelado && dados?.frame_base64) {
          setFrameSrc(`data:${dados.mime_type || 'image/jpeg'};base64,${dados.frame_base64}`);
          setPreviewInfo((anterior) => ({ ...anterior, ...dados }));
          setPreviewErro(null);
        }
      } catch (error) {
        if (!cancelado) setPreviewErro(mensagemApi(error));
      } finally {
        executando = false;
      }
    };

    void atualizarFrame();
    const timer = window.setInterval(atualizarFrame, 300);

    return () => {
      cancelado = true;
      window.clearInterval(timer);
    };
  }, [sessionId]);

  const iniciarPreview = async () => {
    if (!cameraUid) {
      setErro('Selecione uma câmera cadastrada.');
      return;
    }

    setIniciandoPreview(true);
    setErro(null);
    setPreviewErro(null);

    try {
      await pararPreview();
      const dados = await camerasApi.iniciarPreview(cameraUid);
      previewSessionRef.current = dados.session_id;
      setSessionId(dados.session_id);
      setPreviewInfo(dados);
    } catch (error) {
      setPreviewErro(mensagemApi(error));
    } finally {
      setIniciandoPreview(false);
    }
  };

  const trocarCamera = async (novoUid) => {
    if (novoUid === cameraUid) return;
    await pararPreview();
    setCameraUid(novoUid);
    setPreviewErro(null);
    setCapturas({ frontal: null, esquerda: null, direita: null });
  };

  const dataUrlParaBlob = async (dataUrl) => {
    const resposta = await fetch(dataUrl);
    return resposta.blob();
  };

  const capturarReferencia = (referencia) => {
    if (!frameSrc) {
      setErro('Inicie a câmera e aguarde a imagem antes de capturar.');
      return;
    }

    const snapshot = frameSrc;
    const frameSeq = previewInfo?.frame_seq ?? null;

    const frameJaUsado = Object.entries(capturas).some(
      ([chave, captura]) =>
        chave !== referencia &&
        captura?.frameSeq !== null &&
        frameSeq !== null &&
        captura?.frameSeq === frameSeq
    );

    if (frameJaUsado) {
      setErro('Aguarde a câmera atualizar a imagem antes de fazer a próxima captura.');
      return;
    }

    setErro(null);
    setCapturando(referencia);

    setCapturas((anteriores) => ({
      ...anteriores,
      [referencia]: {
        src: snapshot,
        frameSeq,
      },
    }));

    window.setTimeout(() => {
      setCapturando(null);
    }, 120);
  };

  const removerCaptura = (referencia) => {
    setCapturas((anteriores) => ({
      ...anteriores,
      [referencia]: null,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErro(null);

    if (!nome.trim()) {
      setErro('Informe o nome completo.');
      return;
    }
    if (!matricula.trim()) {
      setErro('Informe a matrícula.');
      return;
    }
    if (!cargo.trim()) {
      setErro('Informe o cargo ou função.');
      return;
    }

    const faltantes = referencias
      .filter((item) => !capturas[item.id])
      .map((item) => item.titulo);

    if (faltantes.length) {
      setErro(`Capture as três referências biométricas. Faltando: ${faltantes.join(', ')}.`);
      return;
    }

    setSalvando(true);

    try {
      setApiContext({ perfil: 'GERENCIAL' });

      // Libera a câmera antes da validação biométrica pesada no backend.
      // As três fotos já estão preservadas em `capturas`.
      await pararPreview();

      const [frontal, esquerda, direita] = await Promise.all([
        dataUrlParaBlob(capturas.frontal.src),
        dataUrlParaBlob(capturas.esquerda.src),
        dataUrlParaBlob(capturas.direita.src),
      ]);

      await colaboradoresApi.cadastrar({
        matricula: matricula.trim(),
        nome: nome.trim(),
        cargo: cargo.trim(),
        setor: setor.trim(),
        frontal,
        esquerda,
        direita,
      });

      await pararPreview();
      await onCadastrarColaborador?.();
    } catch (error) {
      setErro(mensagemApi(error));
    } finally {
      setSalvando(false);
    }
  };

  const cameraSelecionada = cameras.find((camera) => camera.camera_uid === cameraUid) || null;
  const quantidadeCapturas = referencias.filter((item) => capturas[item.id]).length;
  const proxima = referencias.find((item) => !capturas[item.id]) || null;

  return (
    <div className="max-w-[1350px] mx-auto space-y-5">
      <div>
        <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium mb-2">
          <span>Colaboradores</span>
          <ChevronRight className="w-3 h-3" />
          <span className="text-slate-700 font-semibold">Cadastrar Colaborador</span>
        </div>
        <h2 className="text-2xl font-bold text-slate-950">Cadastro de Colaborador</h2>
        <p className="text-sm text-slate-500 mt-1">
          Cadastre os dados e três referências faciais para reconhecimento biométrico.
        </p>
      </div>

      {(erro || previewErro) && (
        <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-red-700 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{erro || previewErro}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 xl:grid-cols-[0.85fr_1.15fr] gap-4">
          <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
            <div className="flex items-start gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-orange-50 text-[#FF7412] flex items-center justify-center">
                <UserPlus className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Dados do Colaborador</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Informações utilizadas no cadastro e no monitoramento.</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Nome completo *</label>
                <input
                  type="text"
                  required
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  placeholder="Ex: Carlos Eduardo Lima"
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">Matrícula / ID *</label>
                  <input
                    type="text"
                    required
                    value={matricula}
                    onChange={(e) => setMatricula(e.target.value)}
                    placeholder="Ex: 557079"
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">Setor</label>
                  <input
                    type="text"
                    value={setor}
                    onChange={(e) => setSetor(e.target.value)}
                    placeholder="Ex: Produção"
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Cargo / Função *</label>
                <input
                  type="text"
                  required
                  value={cargo}
                  onChange={(e) => setCargo(e.target.value)}
                  placeholder="Ex: Operador"
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Câmera para captura *</label>
                <div className="relative">
                  <select
                    value={cameraUid}
                    onChange={(e) => void trocarCamera(e.target.value)}
                    disabled={camerasLoading || sessionId}
                    className="w-full appearance-none text-xs bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-9 py-2.5 focus:border-[#FF7412] focus:outline-none disabled:bg-slate-100"
                  >
                    <option value="">Selecione uma câmera</option>
                    {cameras.map((camera) => (
                      <option key={camera.camera_uid} value={camera.camera_uid}>
                        {camera.nome || camera.camera_uid}
                      </option>
                    ))}
                  </select>
                  <Camera className="w-4 h-4 text-[#FF7412] absolute left-3 top-2.5" />
                  <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-2.5 pointer-events-none" />
                </div>
                {cameraSelecionada && (
                  <p className="text-[10px] text-slate-400 mt-1.5">
                    {cameraSelecionada.nome} • {String(cameraSelecionada.tipo || '-').toUpperCase()}
                  </p>
                )}
              </div>

              <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 text-[10px] text-blue-700 leading-relaxed">
                A foto frontal continua sendo a referência principal do cadastro. As capturas esquerda e direita aumentam a variedade biométrica sem quebrar cadastros antigos.
              </div>
            </div>
          </section>

          <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
            <div className="flex items-start justify-between gap-3 mb-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-orange-50 text-[#FF7412] flex items-center justify-center">
                  <Camera className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Captura Biométrica</h3>
                  <p className="text-[11px] text-slate-500 mt-0.5">Capture frente, esquerda e direita usando a câmera cadastrada.</p>
                </div>
              </div>
              <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
                {quantidadeCapturas}/3 capturas
              </span>
            </div>

            <div className="relative aspect-video rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center">
              {frameSrc ? (
                <img src={frameSrc} alt="Preview biométrico" className="absolute inset-0 w-full h-full object-contain bg-black" />
              ) : (
                <div className="text-center px-4">
                  {iniciandoPreview ? (
                    <RefreshCw className="w-10 h-10 text-[#FF7412] animate-spin mx-auto mb-3" />
                  ) : (
                    <Camera className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                  )}
                  <p className="text-xs text-slate-400">
                    {iniciandoPreview ? 'Abrindo câmera...' : 'Inicie a transmissão para começar a captura.'}
                  </p>
                </div>
              )}

              {sessionId && (
                <div className="absolute top-3 left-3 rounded bg-black/65 border border-white/10 px-2 py-1 text-[9px] text-white flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  AO VIVO
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2 mt-3">
              {!sessionId ? (
                <button
                  type="button"
                  onClick={() => void iniciarPreview()}
                  disabled={iniciandoPreview || !cameraUid}
                  className="px-4 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-[11px] font-semibold flex items-center gap-2 disabled:opacity-50"
                >
                  {iniciandoPreview ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  Iniciar Câmera
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => void pararPreview()}
                  className="px-4 py-2.5 border border-red-200 text-red-600 hover:bg-red-50 rounded-lg text-[11px] font-semibold flex items-center gap-2"
                >
                  <Square className="w-4 h-4" />
                  Parar Câmera
                </button>
              )}

              <div className="text-[10px] text-slate-500">
                {proxima ? (
                  <><strong>Próxima:</strong> {proxima.titulo} — {proxima.instrucao}</>
                ) : (
                  <span className="text-emerald-600 font-semibold">As três capturas foram realizadas.</span>
                )}
              </div>
            </div>

            {previewInfo?.largura && previewInfo?.altura && (
              <div className="mt-3 text-[10px] text-slate-400">
                Resolução: {previewInfo.largura} × {previewInfo.altura}
                {previewInfo?.fps ? ` • ${previewInfo.fps} FPS` : ''}
              </div>
            )}
          </section>
        </div>

        <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Referências Faciais</h3>
              <p className="text-[11px] text-slate-500 mt-0.5">As capturas são instantâneas. A validação biométrica ocorre ao salvar o colaborador.</p>
            </div>
            <span className={`text-[10px] font-semibold ${quantidadeCapturas === 3 ? 'text-emerald-600' : 'text-slate-500'}`}>
              {quantidadeCapturas === 3 ? 'Capturas prontas para validação' : 'Complete as três posições'}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {referencias.map((referencia) => {
              const captura = capturas[referencia.id];
              const emCaptura = capturando === referencia.id;

              return (
                <div key={referencia.id} className={`rounded-xl border p-3 ${captura ? 'border-emerald-200 bg-emerald-50/40' : 'border-slate-200 bg-slate-50'}`}>
                  <div className="aspect-[4/3] rounded-lg overflow-hidden bg-slate-900 flex items-center justify-center relative">
                    {captura ? (
                      <img src={captura.src} alt={`Captura ${referencia.titulo}`} className="w-full h-full object-cover" />
                    ) : (
                      <User className="w-10 h-10 text-slate-600" />
                    )}
                    {captura && (
                      <div className="absolute top-2 right-2 w-7 h-7 rounded-full bg-emerald-500 text-white flex items-center justify-center shadow">
                        <CheckCircle2 className="w-4 h-4" />
                      </div>
                    )}
                  </div>

                  <div className="mt-3">
                    <div className="flex items-center justify-between gap-2">
                      <strong className="text-xs text-slate-900">{referencia.titulo}</strong>
                      <span className={`text-[9px] font-bold ${captura ? 'text-emerald-600' : 'text-slate-400'}`}>
                        {captura ? 'CAPTURADA' : 'PENDENTE'}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1 min-h-[30px]">{referencia.instrucao}</p>
                  </div>

                  <div className="flex gap-2 mt-3">
                    <button
                      type="button"
                      onClick={() => void capturarReferencia(referencia.id)}
                      disabled={!frameSrc}
                      className="flex-1 px-3 py-2 rounded-lg bg-[#FF7412] hover:bg-[#e0620a] text-white text-[10px] font-semibold flex items-center justify-center gap-1.5 disabled:opacity-40"
                    >
                      {emCaptura ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Camera className="w-3.5 h-3.5" />}
                      {emCaptura ? 'Capturado' : captura ? 'Refazer' : 'Capturar'}
                    </button>
                    {captura && (
                      <button
                        type="button"
                        onClick={() => removerCaptura(referencia.id)}
                        className="px-3 py-2 rounded-lg border border-slate-300 text-slate-500 hover:text-red-600 hover:border-red-200 text-[10px] font-semibold"
                      >
                        Limpar
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <div className="flex items-center justify-end gap-3">
          <button
            type="submit"
            disabled={salvando || quantidadeCapturas !== 3}
            className="px-6 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {salvando ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            {salvando ? 'Salvando cadastro...' : 'Salvar Colaborador'}
          </button>
        </div>
      </form>
    </div>
  );
}

// 9. REGISTRO DE OCORRÊNCIAS
function RegistroOcorrenciasView({ ocorrencias }) {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">
          Registro de Ocorrências
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Histórico de não conformidades identificadas pelo sistema de visão
        </p>
      </div>

      {ocorrencias.length === 0 ? (
        <EmptyState
          icon={FileCheck}
          title="Nenhuma ocorrência registrada"
          description="O repositório de ocorrências está em conformidade. Assim que uma não conformidade de EPI for identificada pelo modelo, os snapshots e dados aparecerão aqui."
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          {/* Tabela de ocorrências */}
        </div>
      )}
    </div>
  );
}

// 10. RELATÓRIO GERAL
function RelatorioGeralView({ ocorrenciasCount }) {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">
          Relatório Geral Consolidado
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Indicadores de conformidade industrial e segurança de trabalho
        </p>
      </div>

      {ocorrenciasCount === 0 ? (
        <EmptyState
          icon={Clock}
          title="Sem dados para gerar o relatório analítico"
          description="Os gráficos de tendência temporal e indicadores por tipo de EPI serão calculados com base nas ocorrências enviadas pelo backend."
        />
      ) : null}
    </div>
  );
}
