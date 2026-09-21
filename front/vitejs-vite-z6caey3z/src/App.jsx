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
  const [ambientes, setAmbientes] = useState([]);
  const [colaboradores, setColaboradores] = useState([]);
  const [ocorrencias, setOcorrencias] = useState([]);

  // Estado para armazenar o ambiente sendo editado
  const [ambienteEmEdicao, setAmbienteEmEdicao] = useState(null);

  // Ações de Ambientes
  const handleSalvarAmbiente = (ambienteData) => {
    if (ambienteEmEdicao) {
      setAmbientes((prev) =>
        prev.map((a) =>
          a.id === ambienteEmEdicao.id
            ? { ...ambienteData, id: ambienteEmEdicao.id }
            : a
        )
      );
      setAmbienteEmEdicao(null);
      alert('Ambiente atualizado com sucesso!');
    } else {
      setAmbientes((prev) => [...prev, { ...ambienteData, id: Date.now() }]);
      alert('Ambiente cadastrado com sucesso!');
    }
    setActiveScreen('consulta-ambientes');
  };

  const handleIniciarEdicaoAmbiente = (ambiente) => {
    setAmbienteEmEdicao(ambiente);
    setActiveScreen('cadastro-ambiente');
  };

  const handleDeletarAmbiente = (id) => {
    setAmbientes((prev) => prev.filter((a) => a.id !== id));
    if (ambienteEmEdicao?.id === id) {
      setAmbienteEmEdicao(null);
    }
  };

  // Ações de Colaboradores
  const handleDeletarColaborador = (id) => {
    setColaboradores((prev) => prev.filter((c) => c.id !== id));
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
              onCadastrar={(novaCam) => {
                setCameras((prev) => [...prev, novaCam]);
                alert('Câmera registrada com sucesso!');
              }}
            />
          )}

          {activeScreen === 'consulta-cameras' && (
            <ConsultaCamerasView
              cameras={cameras}
              onNavigate={setActiveScreen}
            />
          )}

          {activeScreen === 'teste-cameras' && (
            <TesteCamerasView cameras={cameras} onNavigate={setActiveScreen} />
          )}

          {/* Cadastro e Edição de Ambientes */}
          {activeScreen === 'cadastro-ambiente' && (
            <CadastroAmbienteView
              ambienteEmEdicao={ambienteEmEdicao}
              camerasDisponiveis={cameras}
              onSalvarAmbiente={handleSalvarAmbiente}
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
              onEditarAmbiente={handleIniciarEdicaoAmbiente}
              onDeletarAmbiente={handleDeletarAmbiente}
              onNavigate={setActiveScreen}
            />
          )}

          {/* Colaboradores */}
          {activeScreen === 'consulta-colaboradores' && (
            <ConsultaColaboradoresView
              colaboradores={colaboradores}
              onDeletarColaborador={handleDeletarColaborador}
              onNavigate={setActiveScreen}
            />
          )}

          {activeScreen === 'cadastro-colaborador' && (
            <CadastroColaboradorView
              onCadastrarColaborador={(novoColab) => {
                setColaboradores((prev) => [...prev, novoColab]);
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
  const [ip, setIp] = useState('');
  const [protocolo, setProtocolo] = useState('RTSP');
  const [urlStream, setUrlStream] = useState('rtsp://192.168.0.4:8554/');
  const [usuario, setUsuario] = useState('admin');
  const [senha, setSenha] = useState('');
  const [testando, setTestando] = useState(false);
  const [statusConexao, setStatusConexao] = useState(null);

  const handleTestar = async () => {
    setTestando(true);
    setStatusConexao(null);

    try {
      const resposta = await fetch(
        'https://whole-olympic-amounts-scientists.trycloudflare.com/api/front/cameras/testar',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            fonte: urlStream,
            usuario,
            senha,
          }),
        }
      );

      const dados = await resposta.json();

      if (dados.sucesso) {
        setStatusConexao('sucesso');
      } else {
        setStatusConexao('erro');
        alert(`Erro: ${dados.erro}`);
      }
    } catch {
      setStatusConexao('erro');
      alert('Backend não conectado.');
    } finally {
      setTestando(false);
    }
  };

  const handleSalvar = (e) => {
    e.preventDefault();
    if (!nome) return;
    onCadastrar({
      id: Date.now(),
      nome,
      ip: ip || '192.168.0.20',
      protocolo,
      urlStream,
      status: 'Online',
    });
    setNome('');
    setIp('');
    setUrlStream('');
    setStatusConexao(null);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">
          Cadastro de Câmeras
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Localize dispositivos na rede industrial ou adicione manualmente
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-bold text-slate-800 mb-4 pb-2 border-b border-slate-100 flex items-center gap-2">
            <Settings className="w-4 h-4 text-[#FF7412]" />
            Dados de Comunicação do Dispositivo
          </h3>

          <form onSubmit={handleSalvar} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Nome da Câmera *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: CAM-01 - Linha de Montagem"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Endereço IP
                </label>
                <input
                  type="text"
                  placeholder="192.168.0.100"
                  value={ip}
                  onChange={(e) => setIp(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Protocolo
                </label>
                <select
                  value={protocolo}
                  onChange={(e) => setProtocolo(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
                >
                  <option value="RTSP">RTSP (Real Time Streaming)</option>
                  <option value="ONVIF">ONVIF Profile S</option>
                  <option value="HTTP">HTTP Snapshot</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  URL do Stream / Porta
                </label>
                <input
                  type="text"
                  placeholder="rtsp://192.168.0.4:8554/"
                  value={urlStream}
                  onChange={(e) => setUrlStream(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Usuário do Dispositivo
                </label>
                <input
                  type="text"
                  value={usuario}
                  onChange={(e) => setUsuario(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Senha de Acesso
                </label>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
                />
              </div>
            </div>

            {statusConexao === 'sucesso' && (
              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Fluxo de vídeo RTSP validado com sucesso!</span>
              </div>
            )}

            <div className="flex items-center gap-3 pt-3">
              <button
                type="button"
                onClick={handleTestar}
                disabled={testando}
                className="px-4 py-2 border border-slate-300 hover:bg-slate-100 rounded-lg text-xs font-semibold text-slate-700 flex items-center gap-2"
              >
                {testando ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5 text-[#FF7412]" />
                )}
                Testar Conexão
              </button>

              <button
                type="submit"
                className="px-5 py-2 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
              >
                Cadastrar Câmera
              </button>
            </div>
          </form>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[#FF7412]" />
              Varredura ONVIF na Rede
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              O módulo de descoberta busca câmeras ativas na sub-rede local
              industrial.
            </p>
            <div className="mt-4 p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1">
              <div>
                <strong>Sub-rede:</strong> 192.168.0.0/24
              </div>
              <div>
                <strong>Portas escaneadas:</strong> 554, 80, 8000
              </div>
            </div>
          </div>

          <button
            onClick={() => alert('Buscando dispositivos na rede local...')}
            className="w-full mt-6 py-2.5 border border-[#FF7412] text-[#FF7412] hover:bg-orange-50 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
          >
            <Search className="w-4 h-4" />
            Buscar Câmeras Conectadas
          </button>
        </div>
      </div>
    </div>
  );
}

// 3. CONSULTA DE CÂMERAS
function ConsultaCamerasView({ cameras, onNavigate }) {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Consulta de Câmeras
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Gerencie os fluxos de vídeo configurados no sistema
          </p>
        </div>
        <button
          onClick={() => onNavigate('cadastro-cameras')}
          className="px-4 py-2 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-xs font-semibold flex items-center gap-2 self-start"
        >
          <PlusCircle className="w-4 h-4" />
          Nova Câmera
        </button>
      </div>

      {cameras.length === 0 ? (
        <EmptyState
          icon={Video}
          title="Nenhuma câmera registrada no banco"
          description="Você ainda não possui câmeras salvas. Quando o backend retornar os dados ou você cadastrar uma nova, ela será listada nesta tabela."
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
                <th className="py-3 px-4">IP</th>
                <th className="py-3 px-4">Protocolo</th>
                <th className="py-3 px-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {cameras.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/80">
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                      {c.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-800">
                    {c.nome}
                  </td>
                  <td className="py-3 px-4">{c.ip}</td>
                  <td className="py-3 px-4">{c.protocolo}</td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <button className="text-slate-500 hover:text-slate-800 p-1">
                      <Edit className="w-3.5 h-3.5" />
                    </button>
                    <button className="text-red-500 hover:text-red-700 p-1">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// 4. TESTE DE CÂMERAS
function TesteCamerasView({ cameras, onNavigate }) {
  const [selectedCam, setSelectedCam] = useState(cameras[0]?.id || '');

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">
          Teste de Câmeras em Tempo Real
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Valide latência e estabilidade do stream de vídeo
        </p>
      </div>

      {cameras.length === 0 ? (
        <EmptyState
          icon={Camera}
          title="Sem câmeras para testar"
          description="Para rodar testes de streaming e validar FPS/latência, cadastre ao menos um dispositivo."
          actionText="Ir para Cadastro"
          onAction={() => onNavigate('cadastro-cameras')}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-black rounded-xl overflow-hidden aspect-video flex flex-col items-center justify-center text-white relative shadow-lg">
            <div className="text-center p-4">
              <Camera className="w-12 h-12 text-[#FF7412] mx-auto mb-2 opacity-80" />
              <p className="text-xs text-slate-400">Canal de Stream Pronto</p>
              <span className="text-[11px] text-slate-500 mt-1 block">
                Aguardando feed de vídeo do backend
              </span>
            </div>
            <div className="absolute top-3 left-3 bg-black/60 backdrop-blur px-2.5 py-1 rounded text-[10px] font-mono text-emerald-400 flex items-center gap-1.5 border border-white/10">
              <span className="w-2 h-2 rounded-full bg-emerald-500" /> RTSP
              READY
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Controle do Feed
            </h3>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Selecionar Câmera
              </label>
              <select
                value={selectedCam}
                onChange={(e) => setSelectedCam(e.target.value)}
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
              >
                {cameras.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nome}
                  </option>
                ))}
              </select>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg text-xs space-y-1.5 text-slate-600">
              <div className="flex justify-between">
                <span>Status:</span>{' '}
                <strong className="text-emerald-600">Conectado</strong>
              </div>
              <div className="flex justify-between">
                <span>Latência Média:</span> <strong>~45ms</strong>
              </div>
              <div className="flex justify-between">
                <span>Taxa de Quadros:</span> <strong>30 FPS</strong>
              </div>
            </div>

            <button className="w-full py-2 bg-[#FF7412] text-white rounded-lg text-xs font-semibold hover:bg-[#e0620a] transition-colors">
              Iniciar Captura de Teste
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// 5. CADASTRO / EDIÇÃO DE AMBIENTE (COM SUPORTE A EDIÇÃO COMPLETA)
function CadastroAmbienteView({
  ambienteEmEdicao,
  camerasDisponiveis,
  onSalvarAmbiente,
  onCancelarEdicao,
}) {
  const [nomeAmbiente, setNomeAmbiente] = useState('');
  const [cameraVinculada, setCameraVinculada] = useState('');
  const [descricao, setDescricao] = useState('');
  const [episObrigatorios, setEpisObrigatorios] = useState([
    'Capacete',
    'Óculos de proteção',
  ]);

  // Carrega os dados se estiver em modo de edição
  useEffect(() => {
    if (ambienteEmEdicao) {
      setNomeAmbiente(ambienteEmEdicao.nome || '');
      setCameraVinculada(ambienteEmEdicao.camera || '');
      setDescricao(ambienteEmEdicao.descricao || '');
      setEpisObrigatorios(ambienteEmEdicao.epis || []);
    } else {
      setNomeAmbiente('');
      setCameraVinculada('');
      setDescricao('');
      setEpisObrigatorios(['Capacete', 'Óculos de proteção']);
    }
  }, [ambienteEmEdicao]);

  const listaEpisDisponiveis = [
    'Capacete',
    'Óculos de proteção',
    'Protetor auricular',
    'Luvas térmicas / corte',
    'Colete reflexivo',
    'Máscara respiratória',
    'Botina com bico de aço',
  ];

  const handleToggleEpi = (epi) => {
    setEpisObrigatorios((prev) =>
      prev.includes(epi) ? prev.filter((item) => item !== epi) : [...prev, epi]
    );
  };

  const handleSalvar = (e) => {
    e.preventDefault();
    if (!nomeAmbiente) return;
    onSalvarAmbiente({
      nome: nomeAmbiente,
      camera: cameraVinculada || 'Sem câmera associada',
      descricao,
      epis: episObrigatorios,
    });
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            {ambienteEmEdicao
              ? 'Editar Informações do Ambiente'
              : 'Cadastro de Ambiente'}
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {ambienteEmEdicao
              ? `Modifique as configurações e regras de segurança para ${ambienteEmEdicao.nome}`
              : 'Defina as zonas fabris e configure as regras de EPIs obrigatórios exigidos no local'}
          </p>
        </div>

        {ambienteEmEdicao && (
          <button
            type="button"
            onClick={onCancelarEdicao}
            className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-slate-100 transition-colors flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Cancelar Edição
          </button>
        )}
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <form onSubmit={handleSalvar} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Nome do Setor / Ambiente *
              </label>
              <input
                type="text"
                required
                placeholder="Ex: Área de Soldagem e Usinagem"
                value={nomeAmbiente}
                onChange={(e) => setNomeAmbiente(e.target.value)}
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Câmera para Monitoramento
              </label>
              <select
                value={cameraVinculada}
                onChange={(e) => setCameraVinculada(e.target.value)}
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
              >
                <option value="">Selecione uma câmera cadastrada...</option>
                {camerasDisponiveis.map((c) => (
                  <option key={c.id} value={c.nome}>
                    {c.nome} ({c.ip})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Descrição do Ambiente e Riscos
            </label>
            <textarea
              rows="2"
              placeholder="Ex: Zona de faíscas e temperatura elevada. Monitoramento constante de proteção facial e ocular."
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
            />
          </div>

          <div className="pt-2 border-t border-slate-100">
            <div className="flex items-center gap-2 mb-1">
              <ShieldCheck className="w-4 h-4 text-[#FF7412]" />
              <label className="text-xs font-bold text-slate-800">
                EPIs de Uso Obrigatório Neste Setor
              </label>
            </div>
            <p className="text-[11px] text-slate-500 mb-3">
              Colaboradores identificados neste setor sem estes itens
              selecionados gerarão ocorrências automáticas.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              {listaEpisDisponiveis.map((epi) => {
                const selecionado = episObrigatorios.includes(epi);
                return (
                  <button
                    type="button"
                    key={epi}
                    onClick={() => handleToggleEpi(epi)}
                    className={`flex items-center gap-2.5 p-2.5 rounded-lg border text-xs text-left transition-all ${
                      selecionado
                        ? 'bg-orange-50 border-[#FF7412] text-slate-900 font-medium shadow-xs'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded flex items-center justify-center text-white text-[10px] ${
                        selecionado
                          ? 'bg-[#FF7412]'
                          : 'border border-slate-300 bg-white'
                      }`}
                    >
                      {selecionado && '✓'}
                    </div>
                    <span>{epi}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="pt-3 flex items-center gap-3">
            <button
              type="submit"
              className="px-6 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              {ambienteEmEdicao
                ? 'Atualizar Alterações'
                : 'Salvar Ambiente e Regras'}
            </button>

            {ambienteEmEdicao && (
              <button
                type="button"
                onClick={onCancelarEdicao}
                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
              >
                Cancelar
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

// 6. CONSULTA DE AMBIENTES (COM CLIQUES PARA EDITAR E APAGAR COM MODAL)
function ConsultaAmbientesView({
  ambientes,
  onEditarAmbiente,
  onDeletarAmbiente,
  onNavigate,
}) {
  const [ambienteParaRemover, setAmbienteParaRemover] = useState(null);

  const confirmarExclusao = () => {
    if (ambienteParaRemover) {
      onDeletarAmbiente(ambienteParaRemover.id);
      setAmbienteParaRemover(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Ambientes Cadastrados
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Clique em um ambiente para editar suas informações ou gerencie as
            regras
          </p>
        </div>
        <button
          onClick={() => onNavigate('cadastro-ambiente')}
          className="px-4 py-2 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm"
        >
          <PlusCircle className="w-4 h-4" />
          Novo Ambiente
        </button>
      </div>

      {ambientes.length === 0 ? (
        <EmptyState
          icon={Layers}
          title="Nenhum ambiente configurado"
          description="Cadastre os setores de operação para associar câmeras e definir as regras de EPIs obrigatórios."
          actionText="Cadastrar Primeiro Ambiente"
          onAction={() => onNavigate('cadastro-ambiente')}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {ambientes.map((a) => (
            <div
              key={a.id}
              className="group bg-white p-5 rounded-xl border border-slate-200 hover:border-[#FF7412]/60 hover:shadow-md transition-all flex flex-col justify-between relative cursor-pointer"
              onClick={() => onEditarAmbiente(a)}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <h4 className="font-bold text-slate-900 text-sm group-hover:text-[#FF7412] transition-colors">
                    {a.nome}
                  </h4>
                  <div
                    className="flex items-center gap-1 shrink-0"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      type="button"
                      onClick={() => onEditarAmbiente(a)}
                      className="p-1.5 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
                      title="Editar Ambiente"
                    >
                      <Edit className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setAmbienteParaRemover(a)}
                      className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                      title="Apagar Ambiente"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <span className="text-[11px] text-[#FF7412] font-semibold block mt-1 flex items-center gap-1">
                  <Camera className="w-3.5 h-3.5" />
                  {a.camera}
                </span>

                <p className="text-xs text-slate-500 mt-2 line-clamp-2">
                  {a.descricao || 'Sem observações adicionais.'}
                </p>
              </div>

              {/* EPIs Obrigatórios no card */}
              <div className="mt-4 pt-3 border-t border-slate-100">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold block">
                    EPIs Obrigatórios
                  </span>
                  <span className="text-[10px] text-slate-400 group-hover:text-[#FF7412] font-semibold flex items-center gap-0.5 transition-colors">
                    Editar <ChevronRight className="w-3 h-3" />
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {a.epis && a.epis.length > 0 ? (
                    a.epis.map((epi, idx) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.5 rounded bg-orange-50 text-[#FF7412] text-[10px] font-semibold border border-orange-200"
                      >
                        {epi}
                      </span>
                    ))
                  ) : (
                    <span className="text-[11px] text-slate-400 italic">
                      Nenhum EPI configurado
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* MODAL DE CONFIRMAÇÃO DE EXCLUSÃO DE AMBIENTE */}
      {ambienteParaRemover && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95 duration-150">
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
              <p className="text-[11px] text-red-500 mt-1">
                As regras de monitoramento de EPI deste setor deixarão de ser
                vigiadas pela IA.
              </p>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setAmbienteParaRemover(null)}
                className="flex-1 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={confirmarExclusao}
                className="flex-1 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-sm transition-colors"
              >
                Sim, Remover
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
  onDeletarColaborador,
  onNavigate,
}) {
  const [busca, setBusca] = useState('');
  const [colaboradorParaRemover, setColaboradorParaRemover] = useState(null);

  const filtrados = colaboradores.filter(
    (c) =>
      c.nome.toLowerCase().includes(busca.toLowerCase()) ||
      c.matricula.toLowerCase().includes(busca.toLowerCase())
  );

  const confirmarExclusao = () => {
    if (colaboradorParaRemover) {
      onDeletarColaborador(colaboradorParaRemover.id);
      setColaboradorParaRemover(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Quadro de Colaboradores
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Lista de funcionários cadastrados no banco de dados
          </p>
        </div>
        <button
          onClick={() => onNavigate('cadastro-colaborador')}
          className="px-4 py-2 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-xs font-semibold flex items-center gap-2 self-start shadow-sm"
        >
          <UserPlus className="w-4 h-4" />
          Cadastrar Colaborador
        </button>
      </div>

      {colaboradores.length === 0 ? (
        <EmptyState
          icon={Users}
          title="Nenhum colaborador registrado"
          description="Cadastre os funcionários com foto, nome e matrícula para alimentar os dados do sistema."
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
                placeholder="Buscar por nome ou matrícula..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                className="w-full text-xs pl-9 pr-4 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:border-[#FF7412]"
              />
            </div>
            <span className="text-xs text-slate-500 font-medium">
              {filtrados.length} colaborador(es)
            </span>
          </div>

          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Colaborador</th>
                <th className="py-3.5 px-4">Matrícula</th>
                <th className="py-3.5 px-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtrados.map((c) => (
                <tr
                  key={c.id}
                  className="hover:bg-slate-50/80 transition-colors"
                >
                  <td className="py-3 px-4 flex items-center gap-3">
                    {c.foto ? (
                      <img
                        src={c.foto}
                        alt={c.nome}
                        className="w-10 h-10 rounded-full object-cover border border-slate-300 shadow-xs shrink-0"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs shrink-0">
                        {c.nome.charAt(0)}
                      </div>
                    )}
                    <div>
                      <span className="font-semibold text-slate-900 block text-sm">
                        {c.nome}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        Ativo no sistema
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4 font-mono font-medium text-slate-700">
                    {c.matricula}
                  </td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <button
                      type="button"
                      onClick={() => alert(`Editar colaborador: ${c.nome}`)}
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
      )}

      {/* MODAL DE CONFIRMAÇÃO DE EXCLUSÃO DE COLABORADOR */}
      {colaboradorParaRemover && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
              <Trash2 className="w-6 h-6" />
            </div>

            <div className="text-center">
              <h3 className="text-base font-bold text-slate-900">
                Remover Colaborador?
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Tem certeza que deseja excluir{' '}
                <strong className="text-slate-800">
                  {colaboradorParaRemover.nome}
                </strong>{' '}
                (Matrícula: {colaboradorParaRemover.matricula}) do banco de
                dados?
              </p>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setColaboradorParaRemover(null)}
                className="flex-1 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={confirmarExclusao}
                className="flex-1 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-sm transition-colors"
              >
                Sim, Remover
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// 8. CADASTRO DE COLABORADOR
function CadastroColaboradorView({ onCadastrarColaborador }) {
  const [nome, setNome] = useState('');
  const [matricula, setMatricula] = useState('');
  const [fotoPreview, setFotoPreview] = useState(null);

  const handleFotoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setFotoPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemoverFoto = () => {
    setFotoPreview(null);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!nome || !matricula) return;

    onCadastrarColaborador({
      id: Date.now(),
      nome,
      matricula,
      foto: fotoPreview,
    });
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">
          Cadastro de Colaborador
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Preencha os dados do colaborador para registro no sistema
        </p>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Foto de Identificação
            </label>

            <div className="flex flex-col sm:flex-row items-center gap-5 p-4 rounded-xl bg-slate-50 border border-slate-200">
              {fotoPreview ? (
                <div className="relative">
                  <img
                    src={fotoPreview}
                    alt="Preview"
                    className="w-20 h-20 rounded-full object-cover border-2 border-[#FF7412] shadow-md"
                  />
                  <button
                    type="button"
                    onClick={handleRemoverFoto}
                    className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-1 hover:bg-red-600 transition-colors shadow-sm"
                    title="Remover foto"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <div className="w-20 h-20 rounded-full bg-slate-200 border-2 border-dashed border-slate-300 flex flex-col items-center justify-center text-slate-400">
                  <Camera className="w-6 h-6 mb-0.5" />
                  <span className="text-[9px] uppercase font-semibold">
                    Sem foto
                  </span>
                </div>
              )}

              <div className="flex-1 text-center sm:text-left">
                <label className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 hover:border-[#FF7412] text-slate-700 hover:text-[#FF7412] rounded-lg text-xs font-semibold cursor-pointer transition-colors shadow-xs">
                  <Upload className="w-4 h-4" />
                  <span>
                    {fotoPreview ? 'Trocar Foto' : 'Selecionar Imagem'}
                  </span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFotoUpload}
                    className="hidden"
                  />
                </label>
                <p className="text-[11px] text-slate-400 mt-2">
                  Formatos aceitos: JPG, PNG ou WEBP.
                </p>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Nome Completo *
            </label>
            <input
              type="text"
              required
              placeholder="Ex: Carlos Eduardo Lima"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Matrícula / ID *
            </label>
            <input
              type="text"
              required
              placeholder="Ex: COL-0042"
              value={matricula}
              onChange={(e) => setMatricula(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:border-[#FF7412] focus:outline-none font-mono"
            />
          </div>

          <div className="pt-2 flex items-center gap-3">
            <button
              type="submit"
              className="px-6 py-2.5 bg-[#FF7412] hover:bg-[#e0620a] text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              Salvar Cadastro
            </button>
          </div>
        </form>
      </div>
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
