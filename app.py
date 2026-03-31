import streamlit as st
import pandas as pd
import os
import locale
from datetime import datetime
from sqlalchemy import create_engine, text

# Tenta configurar a data para português
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
except:
    pass

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E CSS CUSTOMIZADO
# ==========================================
st.set_page_config(page_title="Gerenciamento BK", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #F4F7F6; }
    
    /* Estilos dos Cartões Principais (Top KPIs) */
    .kpi-main-card { background-color: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); display: flex; flex-direction: column; position: relative; overflow: hidden;}
    .kpi-main-title { color: #6B7280; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 0.5rem; }
    .kpi-main-value { color: #005F60; font-size: 3.5rem; font-weight: 800; line-height: 1; margin: 0; }
    
    /* Estilos dos Cartões Secundários (Headcounts) */
    .kpi-sub-card { background-color: white; padding: 1.2rem; border-radius: 6px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03); margin-bottom: 1rem; }
    .border-pj { border-left: 4px solid #005F60; }
    .border-sede { border-left: 4px solid #6B7280; }
    .border-pf { border-left: 4px solid #7DD3FC; }
    .border-ppd { border-left: 4px solid #8B4513; }
    .kpi-sub-title { color: #6B7280; font-size: 0.75rem; font-weight: 700; margin-bottom: 0.2rem; }
    .kpi-sub-value { color: #111827; font-size: 1.8rem; font-weight: 700; margin: 0; }
    .kpi-sub-label { color: #9CA3AF; font-size: 0.8rem; font-weight: normal; }

    /* Estilos para a Distribuição Departamental */
    .dept-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #E5E7EB; padding-bottom: 0.5rem; margin-bottom: 1rem; }
    .dept-title { font-weight: 700; color: #374151; font-size: 1rem; display: flex; align-items: center; gap: 0.5rem;}
    .dot-pj { height: 8px; width: 8px; background-color: #005F60; border-radius: 50%; display: inline-block; }
    .dot-sede { height: 8px; width: 8px; background-color: #6B7280; border-radius: 50%; display: inline-block; }
    .dot-pf { height: 8px; width: 8px; background-color: #7DD3FC; border-radius: 50%; display: inline-block; }
    .dept-total-badge { background-color: #F3F4F6; color: #374151; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;}
    .dept-item { background-color: white; border: 1px solid #F3F4F6; padding: 0.8rem; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; box-shadow: 0 1px 2px rgba(0,0,0,0.02);}
    .dept-name { font-size: 0.85rem; color: #4B5563; font-weight: 600; text-transform: uppercase;}
    .dept-num { font-size: 0.9rem; color: #005F60; font-weight: 700; }
    
    /* Utils */
    .section-title { font-size: 1.25rem; font-weight: 700; color: #111827; margin-top: 2rem; margin-bottom: 1rem; }
    .badge-status { padding: 4px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
    .bg-active { background-color: #D1FAE5; color: #065F46; }
    .bg-short { background-color: #DBEAFE; color: #1E40AF; }
    .bg-urgent { background-color: #FFEDD5; color: #9A3412; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)


# ==========================================
# ESTRUTURA ORGANIZACIONAL & VAGAS (VAZIO)
# ==========================================
ESTRUTURA = {
    "PJ": ["Cadastro Requisitórios", "NIRA", "Detran", "Litispendência", "Obrigação de Fazer", "OPV", "Trabalhista", "TI", "Nomeação Contador", "Precatórios", "Cálculos", "Cartografia", "NPM", "NRST"],
    "SEDE": ["APJ", "Saneamento", "Transação", "CGP", "CSAC", "DOF", "Centro de Estudos", "Consultoria", "Subcontencioso", "Cadastro", "ATIC", "PDA", "Auxílio Saúde"],
    "PF": ["ITCMD", "Cálculos", "Multirão Garantia", "Jurimetria", "Cumprimento Geral", "Gestão de Crédito", "Arrematação", "TI", "Fazenda Autora", "NASS", "Falência", "Pesquisa", "Subsídios / Falência", "Levantamento", "TUSD"],
    "PPD": ["Equipe Geral"]
}

# Base de vagas inicia vazia para não mostrar dados fictícios
DADOS_VAGAS = pd.DataFrame(columns=["Departamento", "Título da Função", "Vagas", "Status", "Filtro"])

# ==========================================
# BANCO DE DADOS E AUDITORIA
# ==========================================
class DatabaseManager:
    def __init__(self):
        db_url = st.secrets["DATABASE_URL"] if "DATABASE_URL" in st.secrets else "sqlite:///colaboradores_v2.db"
        self.engine = create_engine(db_url)
        self._inicializar_tabelas()

    def _inicializar_tabelas(self):
        with self.engine.connect() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS colaboradores (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(150) NOT NULL,
                    cpf VARCHAR(20) UNIQUE,
                    rg VARCHAR(20),
                    email VARCHAR(100),
                    raca VARCHAR(50),
                    genero VARCHAR(50),
                    local VARCHAR(50),
                    setor VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'Ativo'
                )
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS auditoria_logs (
                    id SERIAL PRIMARY KEY,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario VARCHAR(100),
                    acao VARCHAR(255),
                    detalhes TEXT
                )
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    senha VARCHAR(100) NOT NULL,
                    perfil VARCHAR(20) NOT NULL,
                    nome VARCHAR(100) NOT NULL
                )
            '''))
            result_users = conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar()
            if result_users == 0:
                conn.execute(text('''
                    INSERT INTO usuarios (username, senha, perfil, nome) VALUES 
                    ('bruno.admin', '123', 'Admin', 'Bruno Silva'),
                    ('rh.user', '123', 'Usuario', 'Analista Base')
                '''))
            conn.commit()

    # --- Funções de Usuários (Login) ---
    def autenticar_usuario(self, username, senha):
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT username, senha, perfil, nome FROM usuarios WHERE username = :usr AND senha = :pwd"), 
                                  {"usr": username, "pwd": senha}).fetchone()
            if result:
                return {"username": result[0], "senha": result[1], "perfil": result[2], "nome": result[3]}
            return None

    def criar_usuario(self, username, senha, perfil, nome):
        with self.engine.connect() as conn:
            try:
                conn.execute(text("INSERT INTO usuarios (username, senha, perfil, nome) VALUES (:usr, :pwd, :prf, :nom)"),
                             {"usr": username, "pwd": senha, "prf": perfil, "nom": nome})
                conn.commit()
                return True
            except:
                return False 

    def listar_usuarios(self) -> pd.DataFrame:
        return pd.read_sql("SELECT id, nome, username, perfil FROM usuarios ORDER BY id ASC", self.engine)

    def excluir_usuario(self, username):
        with self.engine.connect() as conn:
            try:
                conn.execute(text("DELETE FROM usuarios WHERE username = :usr"), {"usr": username})
                conn.commit()
                return True
            except:
                return False

    # --- Funções de Logs e Colaboradores ---
    def registrar_log(self, usuario, acao, detalhes=""):
        with self.engine.connect() as conn:
            conn.execute(text('''
                INSERT INTO auditoria_logs (data_hora, usuario, acao, detalhes)
                VALUES (:dh, :usr, :acao, :det)
            '''), {"dh": datetime.now(), "usr": usuario, "acao": acao, "det": detalhes})
            conn.commit()

    def ler_logs(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM auditoria_logs ORDER BY data_hora DESC LIMIT 100", self.engine)

    def ler_dados(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM colaboradores ORDER BY id DESC", self.engine)

    def adicionar_colaborador(self, dados: dict, usuario: str):
        with self.engine.connect() as conn:
            conn.execute(text('''
                INSERT INTO colaboradores (nome, cpf, rg, email, raca, genero, local, setor, status)
                VALUES (:nome, :cpf, :rg, :email, :raca, :genero, :local, :setor, 'Ativo')
            '''), dados)
            conn.commit()
        self.registrar_log(usuario, "Cadastro de Colaborador", f"Adicionado: {dados['nome']}")

    def importar_massa(self, df_importacao: pd.DataFrame, usuario: str):
        registros_inseridos = 0
        with self.engine.connect() as conn:
            for _, row in df_importacao.iterrows():
                nome = str(row.get('nome', ''))
                cpf = str(row.get('cpf', ''))
                if nome and cpf and nome != 'nan' and cpf != 'nan':
                    try:
                        conn.execute(text('''
                            INSERT INTO colaboradores (nome, cpf, rg, email, raca, genero, local, setor, status)
                            VALUES (:nome, :cpf, :rg, :email, :raca, :genero, :local, :setor, 'Ativo')
                            ON CONFLICT (cpf) DO NOTHING
                        '''), {
                            "nome": nome, "cpf": cpf, "rg": str(row.get('rg', '')),
                            "email": str(row.get('email', '')), "raca": str(row.get('raca', 'Não Informado')),
                            "genero": str(row.get('genero', 'Não Informado')), "local": str(row.get('local', 'Não Informado')),
                            "setor": str(row.get('setor', 'Não Informado'))
                        })
                        registros_inseridos += 1
                    except:
                        pass 
            conn.commit()
        if registros_inseridos > 0:
            self.registrar_log(usuario, "Importação em Massa", f"Foram inseridos {registros_inseridos} novos colaboradores.")
        return registros_inseridos

@st.cache_resource
def iniciar_conexao_banco():
    return DatabaseManager()

# ==========================================
# MÓDULO LGPD (Mascaramento de Dados)
# ==========================================
def aplicar_lgpd(df: pd.DataFrame, perfil_usuario: str) -> pd.DataFrame:
    if perfil_usuario == 'Admin' or df.empty:
        return df
    df_mascarado = df.copy()
    def mascarar_cpf(cpf):
        cpf = str(cpf)
        return f"***.{cpf[4:7]}.{cpf[8:11]}-**" if len(cpf) > 10 else "***.***.***-**"
    def mascarar_email(email):
        email = str(email)
        return f"{email[0]}***@{email.split('@')[-1]}" if '@' in email else "***@***.com"

    if 'cpf' in df_mascarado.columns: df_mascarado['cpf'] = df_mascarado['cpf'].apply(mascarar_cpf)
    if 'rg' in df_mascarado.columns: df_mascarado['rg'] = "***.***.**"
    if 'email' in df_mascarado.columns: df_mascarado['email'] = df_mascarado['email'].apply(mascarar_email)
    return df_mascarado

def render_status_badge(status):
    if "ATIVO" in status: return f'<span class="badge-status bg-active">{status}</span>'
    elif "PRÉVIA" in status or "SHORTLISTING" in status: return f'<span class="badge-status bg-short">{status}</span>'
    else: return f'<span class="badge-status bg-urgent">{status}</span>'


# ==========================================
# SISTEMA DE LOGIN (Sessão)
# ==========================================
def tela_login():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.subheader("🔒 Acesso Seguro")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar", type="primary", use_container_width=True):
            banco_temp = iniciar_conexao_banco()
            user_auth = banco_temp.autenticar_usuario(usuario, senha)
            
            if user_auth:
                st.session_state['logado'] = True
                st.session_state['usuario_atual'] = user_auth
                banco_temp.registrar_log(user_auth["nome"], "Login no Sistema")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
        st.markdown('</div>', unsafe_allow_html=True)

if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']:
    tela_login()
    st.stop()


# ==========================================
# APLICAÇÃO PRINCIPAL E CÁLCULOS DINÂMICOS
# ==========================================
db = iniciar_conexao_banco()
usuario_logado = st.session_state['usuario_atual']

# Lendo os dados reais do banco
df_colab = db.ler_dados()

# Calculando todos os KPIs e Departamentos de forma DINÂMICA
total_colaboradores = len(df_colab)
total_inativos = len(df_colab[df_colab['status'] == 'Inativo']) if not df_colab.empty else 0

pj_count = len(df_colab[df_colab['local'] == 'PJ']) if not df_colab.empty else 0
sede_count = len(df_colab[df_colab['local'] == 'SEDE']) if not df_colab.empty else 0
pf_count = len(df_colab[df_colab['local'] == 'PF']) if not df_colab.empty else 0
ppd_count = len(df_colab[df_colab['local'] == 'PPD']) if not df_colab.empty else 0

def count_setor(local, setor):
    if df_colab.empty: return 0
    return len(df_colab[(df_colab['local'] == local) & (df_colab['setor'] == setor)])

df_exibicao_segura = aplicar_lgpd(df_colab, usuario_logado['perfil'])

# --- SIDEBAR (Menu Lateral) ---
with st.sidebar:
    st.markdown("### 🏢 GERENCIAMENTO BK")
    st.markdown(f"👤 **{usuario_logado['nome']}**")
    st.caption(f"🛡️ Nível de Acesso: **{usuario_logado['perfil']}**")
    st.markdown("---")
    
    opcoes_menu = ["Home - Dashboard", "Gestão de Pessoas", "Integração de Dados (Planilhas)"]
    if usuario_logado['perfil'] == 'Admin':
        opcoes_menu.append("Auditoria e Logs 🔐")
        
    menu_selecionado = st.radio("Navegação", opcoes_menu)
    
    # --- ÁREA EXCLUSIVA DE ADMIN: GESTÃO DE USUÁRIOS ---
    if usuario_logado['perfil'] == 'Admin':
        st.markdown("---")
        with st.expander("⚙️ Gestão de Usuários (Acessos)"):
            tab_add, tab_list = st.tabs(["➕ Criar", "📋 Listar / Excluir"])
            
            with tab_add:
                with st.form("form_novo_user"):
                    novo_nome = st.text_input("Nome Completo")
                    novo_usr = st.text_input("Login")
                    nova_senha = st.text_input("Senha", type="password")
                    novo_perfil = st.selectbox("Perfil", ["Usuario", "Admin"])
                    if st.form_submit_button("Salvar Usuário", use_container_width=True):
                        if novo_nome and novo_usr and nova_senha:
                            if db.criar_usuario(novo_usr, nova_senha, novo_perfil, novo_nome):
                                db.registrar_log(usuario_logado['nome'], "Criação de Usuário", f"Criou o login '{novo_usr}'")
                                st.success(f"Usuário criado!")
                            else:
                                st.error("Erro: Login já existe.")
                        else:
                            st.warning("Preencha tudo.")
            
            with tab_list:
                df_users = db.listar_usuarios()
                for _, u in df_users.iterrows():
                    colA, colB = st.columns([3, 1])
                    with colA:
                        st.markdown(f"**{u['nome']}**<br><small>{u['username']} ({u['perfil']})</small>", unsafe_allow_html=True)
                    with colB:
                        if u['username'] != 'bruno.admin': # Proteção para não excluir o root
                            if st.button("🗑️", key=f"del_{u['username']}", help="Excluir"):
                                db.excluir_usuario(u['username'])
                                db.registrar_log(usuario_logado['nome'], "Exclusão de Usuário", f"Excluiu o login '{u['username']}'")
                                st.rerun()
                    st.divider()

    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 Sair", use_container_width=True):
        db.registrar_log(usuario_logado['nome'], "Logout do Sistema")
        st.session_state['logado'] = False
        st.rerun()

# --- HEADER SUPERIOR ---
col_titulo, col_vazia, col_export = st.columns([3, 1, 1])
with col_titulo:
    st.title(menu_selecionado.split(" - ")[0])
with col_export:
    st.markdown("<br>", unsafe_allow_html=True)
    csv = df_exibicao_segura.to_csv(index=False).encode('utf-8')
    if st.download_button("📥 Exportar Relatórios", data=csv, file_name='relatorio_rh.csv', mime='text/csv', use_container_width=True):
        db.registrar_log(usuario_logado['nome'], "Exportação de Dados", "Base de dados baixada.")


# ==========================================
# TELA 1: HOME (DASHBOARD) - RECRIAÇÃO FIEL DINÂMICA
# ==========================================
if menu_selecionado == "Home - Dashboard":
    # 1. KPIs Principais (Destaque Topo)
    k1, k2 = st.columns(2)
    with k1:
        st.markdown(f"""
            <div class="kpi-main-card">
                <div class="kpi-main-title">TOTAL DE COLABORADORES</div>
                <div class="kpi-main-value">{total_colaboradores}</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="kpi-main-card" style="background-color: #F9FAFB;">
                <div class="kpi-main-title">INATIVOS</div>
                <div class="kpi-main-value" style="color: #9CA3AF;">{total_inativos}</div>
            </div>
        """, unsafe_allow_html=True)

    # 2. KPIs Secundários (Headcounts por Local)
    st.markdown("<br>", unsafe_allow_html=True)
    h1, h2, h3, h4 = st.columns(4)
    with h1:
        st.markdown(f'<div class="kpi-sub-card border-pj"><div class="kpi-sub-title">PJ HEADCOUNT</div><div class="kpi-sub-value">{pj_count} <span class="kpi-sub-label">Total</span></div></div>', unsafe_allow_html=True)
    with h2:
        st.markdown(f'<div class="kpi-sub-card border-sede"><div class="kpi-sub-title">SEDE HEADCOUNT</div><div class="kpi-sub-value">{sede_count} <span class="kpi-sub-label">Total</span></div></div>', unsafe_allow_html=True)
    with h3:
        st.markdown(f'<div class="kpi-sub-card border-pf"><div class="kpi-sub-title">PF HEADCOUNT</div><div class="kpi-sub-value">{pf_count} <span class="kpi-sub-label">Total</span></div></div>', unsafe_allow_html=True)
    with h4:
        st.markdown(f'<div class="kpi-sub-card border-ppd"><div class="kpi-sub-title">PPD HEADCOUNT</div><div class="kpi-sub-value">{ppd_count} <span class="kpi-sub-label">Total</span></div></div>', unsafe_allow_html=True)

    # 3. Distribuição Departamental (Dinâmica baseada no BD)
    st.markdown('<div class="section-title" style="display:flex; justify-content:space-between;"><span>Distribuição Departamental</span><span style="font-size:0.75rem; color:#9CA3AF; text-transform:uppercase; font-weight:600;">Mapeamento Organizacional</span></div>', unsafe_allow_html=True)
    
    col_pj, col_sede, col_pf = st.columns(3)
    
    with col_pj:
        st.markdown(f'<div class="dept-header"><span class="dept-title"><span class="dot-pj"></span>PJ (Jurídico)</span><span class="dept-total-badge">{pj_count}</span></div>', unsafe_allow_html=True)
        # Itens Largura Total
        st.markdown(f'<div class="dept-item"><span class="dept-name">Cálculos</span><span class="dept-num">{count_setor("PJ", "Cálculos")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Obrigação de Fazer</span><span class="dept-num">{count_setor("PJ", "Obrigação de Fazer")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">OPV</span><span class="dept-num">{count_setor("PJ", "OPV")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Litispendência</span><span class="dept-num">{count_setor("PJ", "Litispendência")}</span></div>', unsafe_allow_html=True)
        # Grid 2x2
        g1, g2 = st.columns(2)
        with g1:
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">Detran</span><span class="dept-num">{count_setor("PJ", "Detran")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">Precatórios</span><span class="dept-num">{count_setor("PJ", "Precatórios")}</span></div>', unsafe_allow_html=True)
        with g2:
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">TI</span><span class="dept-num">{count_setor("PJ", "TI")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">NPM</span><span class="dept-num">{count_setor("PJ", "NPM")}</span></div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; font-size:0.75rem; color:#005F60; font-weight:700; cursor:pointer;">VER MAIS 6 DEPARTAMENTOS</p>', unsafe_allow_html=True)

    with col_sede:
        st.markdown(f'<div class="dept-header"><span class="dept-title"><span class="dot-sede"></span>SEDE (Admin)</span><span class="dept-total-badge">{sede_count}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Cadastro</span><span class="dept-num">{count_setor("SEDE", "Cadastro")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">APJ</span><span class="dept-num">{count_setor("SEDE", "APJ")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Auxílio Saúde</span><span class="dept-num">{count_setor("SEDE", "Auxílio Saúde")}</span></div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">DOF</span><span class="dept-num">{count_setor("SEDE", "DOF")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">C. Estudos</span><span class="dept-num">{count_setor("SEDE", "Centro de Estudos")}</span></div>', unsafe_allow_html=True)
        with g2:
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">Transação</span><span class="dept-num">{count_setor("SEDE", "Transação")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">ATIC</span><span class="dept-num">{count_setor("SEDE", "ATIC")}</span></div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; font-size:0.75rem; color:#6B7280; font-weight:700; cursor:pointer;">VER MAIS 6 DEPARTAMENTOS</p>', unsafe_allow_html=True)

    with col_pf:
        st.markdown(f'<div class="dept-header"><span class="dept-title"><span class="dot-pf"></span>PF (Pessoa Física)</span><div><span style="font-size:0.75rem; color:#7DD3FC; margin-right:5px;">{pf_count}</span><span class="dept-total-badge" style="background-color:#FFF7ED; color:#9A3412;">PPD: {ppd_count}</span></div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Cálculos</span><span class="dept-num" style="color:#7DD3FC;">{count_setor("PF", "Cálculos")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Fazenda Autora</span><span class="dept-num" style="color:#7DD3FC;">{count_setor("PF", "Fazenda Autora")}</span></div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">G. Crédito</span><span class="dept-num" style="color:#7DD3FC;">{count_setor("PF", "Gestão de Crédito")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">Pesquisa</span><span class="dept-num" style="color:#7DD3FC;">{count_setor("PF", "Pesquisa")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">Falência</span><span class="dept-num" style="color:#7DD3FC;">{count_setor("PF", "Falência")}</span></div>', unsafe_allow_html=True)
        with g2:
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">NASS</span><span class="dept-num" style="color:#7DD3FC;">{count_setor("PF", "NASS")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">ITCMD</span><span class="dept-num" style="color:#7DD3FC;">{count_setor("PF", "ITCMD")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item" style="flex-direction:column; padding:0.5rem;"><span class="dept-name" style="font-size:0.7rem;">TUSD</span><span class="dept-num" style="color:#7DD3FC;">{count_setor("PF", "TUSD")}</span></div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; font-size:0.75rem; color:#7DD3FC; font-weight:700; cursor:pointer;">VER MAIS 7 DEPARTAMENTOS</p>', unsafe_allow_html=True)

    # 4. Vagas Abertas (Tabela com Filtros)
    st.markdown('<hr style="margin:2rem 0;">', unsafe_allow_html=True)
    v1, v2 = st.columns([1, 2])
    with v1:
        st.markdown('<div class="section-title" style="margin-top:0;">Vagas Abertas</div>', unsafe_allow_html=True)
    with v2:
        filtro_vaga = st.radio("Filtro", ["Tudo", "PJ", "SEDE", "PF", "PPD", "DETRAN"], horizontal=True, label_visibility="collapsed")
    
    st.markdown('<div class="kpi-main-card" style="padding: 0;">', unsafe_allow_html=True)
    
    colunas_header = st.columns([2, 3, 1, 2, 1])
    headers = ["DEPARTAMENTO", "TÍTULO DA FUNÇÃO", "VAGAS", "STATUS", "AÇÃO"]
    for i, h in enumerate(headers):
        colunas_header[i].markdown(f"<span style='font-size:0.7rem; color:#9CA3AF; font-weight:700;'>{h}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
    
    df_vagas_filtrado = DADOS_VAGAS if filtro_vaga == "Tudo" else DADOS_VAGAS[DADOS_VAGAS['Filtro'] == filtro_vaga]
    
    if df_vagas_filtrado.empty:
        st.markdown("<p style='text-align:center; padding: 2rem; color: gray;'>Nenhuma vaga cadastrada para exibir no momento.</p>", unsafe_allow_html=True)
    else:
        for _, row in df_vagas_filtrado.iterrows():
            cols = st.columns([2, 3, 1, 2, 1])
            cols[0].markdown(f"**{row['Departamento']}**", unsafe_allow_html=True)
            cols[1].markdown(f"{row['Título da Função']}", unsafe_allow_html=True)
            cols[2].markdown(f"**{row['Vagas']}**", unsafe_allow_html=True)
            cols[3].markdown(render_status_badge(row['Status']), unsafe_allow_html=True)
            cols[4].markdown("•••", unsafe_allow_html=True)
            st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.5;'>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# TELA 2: GESTÃO DE PESSOAS
# ==========================================
elif menu_selecionado == "Gestão de Pessoas":
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.subheader("➕ Novo Cadastro (Requerido LGPD)")
    
    with st.form("form_novo_colab"):
        st.write("Dados Pessoais (Protegidos)")
        col1, col2, col3 = st.columns(3)
        nome = col1.text_input("Nome Completo*")
        cpf = col2.text_input("CPF* (Apenas números)")
        rg = col3.text_input("RG")
        
        col4, col5, col6 = st.columns(3)
        email = col4.text_input("E-mail Corporativo")
        raca = col5.selectbox("Raça/Cor", ["Não Informado", "Branca", "Preta", "Parda", "Amarela", "Indígena"])
        genero = col6.selectbox("Gênero", ["Não Informado", "Masculino", "Feminino", "Outro"])
        
        st.markdown("---")
        st.write("Alocação Organizacional")
        col7, col8 = st.columns(2)
        local_selecionado = col7.selectbox("Local (Matriz/Filial)*", list(ESTRUTURA.keys()))
        setor_selecionado = col8.selectbox("Setor Alocado*", ESTRUTURA[local_selecionado])
        
        if st.form_submit_button("Registrar Colaborador", type="primary"):
            if nome and cpf:
                dados_novos = {
                    "nome": nome, "cpf": cpf, "rg": rg, "email": email, 
                    "raca": raca, "genero": genero, "local": local_selecionado, "setor": setor_selecionado
                }
                db.adicionar_colaborador(dados_novos, usuario_logado['nome'])
                st.success(f"Cadastro de {nome} realizado com sucesso!")
                st.rerun()
            else:
                st.warning("Nome e CPF são campos obrigatórios.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.subheader("📋 Base de Dados (Visão Restrita)")
    if usuario_logado['perfil'] != 'Admin':
        st.warning("⚠️ Você está visualizando dados anonimizados conforme diretrizes da LGPD.")
    st.dataframe(df_exibicao_segura, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# TELA 3: IMPORTAÇÃO E MERGE DE PLANILHAS
# ==========================================
elif menu_selecionado == "Integração de Dados (Planilhas)":
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.subheader("🔗 Importar e Consolidar Bases Externas")
    st.write("Faça o upload de planilhas. O sistema irá cruzá-las usando uma chave (ex: cpf) e permitirá a inserção em massa no banco de dados.")
    
    arquivos = st.file_uploader("Selecione os arquivos (Excel ou CSV)", accept_multiple_files=True, type=['xlsx', 'csv'])
    
    if arquivos and len(arquivos) >= 2:
        lista_dfs = []
        for arq in arquivos:
            try:
                if arq.name.endswith('.csv'): lista_dfs.append(pd.read_csv(arq))
                else: lista_dfs.append(pd.read_excel(arq))
            except Exception as e: st.error(f"Erro ao ler {arq.name}: {e}")
                
        st.success(f"{len(arquivos)} planilhas processadas na memória.")
        for idx in range(len(lista_dfs)): lista_dfs[idx].columns = lista_dfs[idx].columns.str.lower().str.strip()
            
        colunas_disponiveis = lista_dfs[0].columns.tolist()
        chave_cruzamento = st.selectbox("Selecione a Coluna Chave para fundir os dados (ex: cpf, id):", colunas_disponiveis)
        
        if st.button("Comparar e Cruzar Dados", type="primary"):
            try:
                df_final = lista_dfs[0]
                for i in range(1, len(lista_dfs)):
                    df_final = pd.merge(df_final, lista_dfs[i], on=chave_cruzamento, how='outer', suffixes=('', f'_arq{i}'))
                st.session_state['df_cruzado'] = df_final
                st.success("Cruzamento realizado! Visualize abaixo:")
            except Exception as e:
                st.error(f"A coluna '{chave_cruzamento}' não foi encontrada em todas as planilhas.")
                
        if 'df_cruzado' in st.session_state:
            df_final_viz = st.session_state['df_cruzado']
            st.dataframe(aplicar_lgpd(df_final_viz, usuario_logado['perfil']), use_container_width=True)
            st.markdown("---")
            st.write("### 📤 Salvar no Banco de Dados Central")
            st.info("Atenção: A planilha final precisa ter obrigatoriamente as colunas **nome** e **cpf** para a inserção funcionar. Registros com CPFs já existentes no banco serão ignorados.")
            if st.button("Gravar Registros em Massa no Banco", type="primary", use_container_width=True):
                qtd_inseridos = db.importar_massa(df_final_viz, usuario_logado['nome'])
                if qtd_inseridos > 0:
                    st.success(f"Sucesso! {qtd_inseridos} novos colaboradores foram inseridos na base.")
                    del st.session_state['df_cruzado']
                else:
                    st.warning("Nenhum registro novo foi inserido. Verifique as colunas 'nome' e 'cpf'.")
                    
    elif arquivos:
        st.warning("Por favor, suba pelo menos 2 arquivos para fazer o cruzamento.")
    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# TELA 4: AUDITORIA E LOGS (Somente Admin)
# ==========================================
elif menu_selecionado == "Auditoria e Logs 🔐":
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.subheader("Histórico de Acessos e Alterações")
    st.write("Abaixo está o registro imutável de todas as ações realizadas na plataforma.")
    
    df_logs = db.ler_logs()
    
    busca = st.text_input("🔍 Buscar no log (por Usuário ou Ação):")
    if busca:
        df_logs = df_logs[df_logs['usuario'].str.contains(busca, case=False, na=False) | df_logs['acao'].str.contains(busca, case=False, na=False)]
        
    st.dataframe(df_logs, use_container_width=True, hide_index=True)
    st.caption("Os logs de sistema não podem ser apagados ou editados manualmente, garantindo a conformidade com a LGPD.")
    st.markdown('</div>', unsafe_allow_html=True)