import streamlit as st
import pandas as pd
import os
import locale
import unicodedata
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
    .kpi-main-card { background-color: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); display: flex; flex-direction: column; position: relative; overflow: hidden;}
    .kpi-main-title { color: #6B7280; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 0.5rem; }
    .kpi-main-value { color: #005F60; font-size: 3.5rem; font-weight: 800; line-height: 1; margin: 0; }
    
    .kpi-sub-card { background-color: white; padding: 1.2rem; border-radius: 6px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03); margin-bottom: 1rem; }
    .border-pj { border-left: 4px solid #005F60; }
    .border-sede { border-left: 4px solid #6B7280; }
    .border-pf { border-left: 4px solid #7DD3FC; }
    .border-ppd { border-left: 4px solid #8B4513; }
    .kpi-sub-title { color: #6B7280; font-size: 0.9rem; font-weight: 800; margin-bottom: 0.2rem; }
    .kpi-sub-value { color: #111827; font-size: 1.8rem; font-weight: 700; margin: 0; }
    
    .dept-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #E5E7EB; padding-bottom: 0.5rem; margin-bottom: 1rem; }
    .dept-title { font-weight: 700; color: #374151; font-size: 1rem; display: flex; align-items: center; gap: 0.5rem;}
    .dot-pj { height: 8px; width: 8px; background-color: #005F60; border-radius: 50%; display: inline-block; }
    .dot-sede { height: 8px; width: 8px; background-color: #6B7280; border-radius: 50%; display: inline-block; }
    .dot-pf { height: 8px; width: 8px; background-color: #7DD3FC; border-radius: 50%; display: inline-block; }
    .dept-total-badge { background-color: #F3F4F6; color: #374151; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;}
    .dept-item { background-color: white; border: 1px solid #F3F4F6; padding: 0.8rem; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; box-shadow: 0 1px 2px rgba(0,0,0,0.02);}
    .dept-name { font-size: 0.85rem; color: #4B5563; font-weight: 600; text-transform: uppercase;}
    .dept-num { font-size: 0.9rem; color: #005F60; font-weight: 700; }
    
    .section-title { font-size: 1.25rem; font-weight: 700; color: #111827; margin-top: 2rem; margin-bottom: 1rem; }
    .badge-status { padding: 4px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
    .bg-active { background-color: #D1FAE5; color: #065F46; }
    .bg-short { background-color: #DBEAFE; color: #1E40AF; }
    .bg-urgent { background-color: #FFEDD5; color: #9A3412; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)


# ==========================================
# ESTRUTURA ORGANIZACIONAL E PADRONIZAÇÃO
# ==========================================
DEFAULT_ALVOS = {
    "PJ": {"Cadastro Requisitórios": 5, "NIRA": 1, "Detran": 8, "Litispendência": 25, "Obrigação de Fazer": 28, "OPV": 28, "Trabalhista": 3, "TI": 6, "Nomeação Contador": 1, "Precatórios": 6, "Cálculos": 41, "Cartografia": 5, "NPM": 6, "NRST": 2},
    "SEDE": {"APJ": 43, "Saneamento": 1, "Transação": 3, "CGP": 1, "CSAC": 1, "DOF": 4, "Centro de Estudos": 2, "Consultoria": 1, "Subcontencioso": 1, "Cadastro": 45, "ATIC": 2, "PDA": 2, "Auxílio Saúde": 7},
    "PF": {"ITCMD": 4, "Cálculos": 10, "Multirão Garantia": 1, "Jurimetria": 1, "Cumprimento Geral": 3, "Gestão de Crédito": 6, "Arrematação": 2, "TI": 3, "Fazenda Autora": 8, "NASS": 6, "Falência": 4, "Pesquisa": 5, "Subsídios / Falência": 3, "Levantamento": 2, "TUSD": 3},
    "PPD": {"Equipe Geral": 4}
}

ESTRUTURA = {
    "PJ": list(DEFAULT_ALVOS["PJ"].keys()),
    "SEDE": list(DEFAULT_ALVOS["SEDE"].keys()),
    "PF": list(DEFAULT_ALVOS["PF"].keys()),
    "PPD": ["Equipe Geral"]
}

def remover_acentos_espacos(txt):
    if pd.isna(txt): return ""
    txt = str(txt).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

MAPA_SETORES_NORM = {remover_acentos_espacos(s): s for loc, setores in ESTRUTURA.items() for s in setores}

def padronizar_local(txt_local):
    norm = remover_acentos_espacos(txt_local)
    if 'pj' in norm or 'procuradoria judicial' in norm: return 'PJ'
    elif 'sede' in norm: return 'SEDE'
    elif 'pf' in norm or 'procuradoria fiscal' in norm: return 'PF'
    elif 'ppd' in norm: return 'PPD'
    return str(txt_local).strip().upper()

def padronizar_setor(txt_setor):
    norm = remover_acentos_espacos(txt_setor)
    return MAPA_SETORES_NORM.get(norm, str(txt_setor).strip().title() if str(txt_setor).strip() else "Não Informado")

def padronizar_genero(txt_genero):
    norm = remover_acentos_espacos(txt_genero)
    if norm in ['m', 'masc', 'masculino']: return 'Masculino'
    if norm in ['f', 'fem', 'feminino']: return 'Feminino'
    return 'Outro'

def aplicar_lgpd(df: pd.DataFrame, perfil_usuario: str) -> pd.DataFrame:
    if perfil_usuario == 'Admin' or df.empty: return df
    df_mascarado = df.copy()
    def mascarar_email(email):
        email = str(email)
        return f"{email[0]}***@{email.split('@')[-1]}" if '@' in email else ""
    if 'email' in df_mascarado.columns: 
        df_mascarado['email'] = df_mascarado['email'].apply(mascarar_email)
    return df_mascarado

def render_status_badge(status):
    status_up = str(status).upper()
    if "ATIVO" in status_up: return f'<span class="badge-status bg-active">{status}</span>'
    elif "PRÉVIA" in status_up or "SHORTLISTING" in status_up: return f'<span class="badge-status bg-short">{status}</span>'
    else: return f'<span class="badge-status bg-urgent">{status}</span>'


# ==========================================
# BANCO DE DADOS E AUDITORIA
# ==========================================
class DatabaseManager:
    def __init__(self):
        db_url = st.secrets["DATABASE_URL"] if "DATABASE_URL" in st.secrets else "sqlite:///gerenciamento_bk_v2.db"
        self.engine = create_engine(db_url)
        self._inicializar_tabelas()

    def _inicializar_tabelas(self):
        with self.engine.connect() as conn:
            conn.execute(text('''CREATE TABLE IF NOT EXISTS colab_v3 (id SERIAL PRIMARY KEY, nome VARCHAR(150) UNIQUE NOT NULL, email VARCHAR(100), raca VARCHAR(50), genero VARCHAR(50), local VARCHAR(50), setor VARCHAR(100), status VARCHAR(20) DEFAULT 'Ativo')'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS auditoria_logs (id SERIAL PRIMARY KEY, data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP, usuario VARCHAR(100), acao VARCHAR(255), detalhes TEXT)'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS users_v3 (id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, senha VARCHAR(100) NOT NULL, perfil VARCHAR(20) NOT NULL, nome VARCHAR(100) NOT NULL, primeiro_acesso BOOLEAN DEFAULT TRUE)'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS metas_vagas (id SERIAL PRIMARY KEY, local VARCHAR(50) NOT NULL, setor VARCHAR(100) NOT NULL, meta INTEGER DEFAULT 0, UNIQUE(local, setor))'''))
            if conn.execute(text("SELECT COUNT(*) FROM users_v3")).scalar() == 0:
                conn.execute(text("INSERT INTO users_v3 (username, senha, perfil, nome, primeiro_acesso) VALUES ('bruno.admin', '123', 'Admin', 'Bruno Silva', TRUE)"))
            if conn.execute(text("SELECT COUNT(*) FROM metas_vagas")).scalar() == 0:
                for loc, setores in DEFAULT_ALVOS.items():
                    for setr, meta in setores.items():
                        conn.execute(text("INSERT INTO metas_vagas (local, setor, meta) VALUES (:l, :s, :m)"), {"l": loc, "s": setr, "m": meta})
            conn.commit()

    def ler_metas(self) -> pd.DataFrame:
        return pd.read_sql("SELECT local, setor, meta FROM metas_vagas ORDER BY local, setor", self.engine)

    def atualizar_metas(self, df_metas, usuario):
        with self.engine.connect() as conn:
            for _, row in df_metas.iterrows():
                conn.execute(text("UPDATE metas_vagas SET meta = :m WHERE local = :l AND setor = :s"), {"m": row['meta'], "l": row['local'], "s": row['setor']})
            conn.commit()
        self.registrar_log(usuario, "Atualização de Metas", "Alterou parâmetros de vagas.")

    def autenticar_usuario(self, username, senha):
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT username, senha, perfil, nome, primeiro_acesso FROM users_v3 WHERE username = :usr AND senha = :pwd"), {"usr": username, "pwd": senha}).fetchone()
            if result: return {"username": result[0], "senha": result[1], "perfil": result[2], "nome": result[3], "primeiro_acesso": result[4]}
            return None

    def criar_usuario(self, username, senha, perfil, nome):
        with self.engine.connect() as conn:
            try:
                conn.execute(text("INSERT INTO users_v3 (username, senha, perfil, nome, primeiro_acesso) VALUES (:usr, :pwd, :prf, :nom, TRUE)"), {"usr": username, "pwd": senha, "prf": perfil, "nom": nome})
                conn.commit()
                return True
            except: return False 

    def atualizar_senha(self, username, nova_senha):
        with self.engine.connect() as conn:
            conn.execute(text("UPDATE users_v3 SET senha = :pwd, primeiro_acesso = FALSE WHERE username = :usr"), {"pwd": nova_senha, "usr": username})
            conn.commit()
            
    def resetar_senha(self, username):
        with self.engine.connect() as conn:
            conn.execute(text("UPDATE users_v3 SET senha = '123', primeiro_acesso = TRUE WHERE username = :usr"), {"usr": username})
            conn.commit()
            
    def atualizar_usuario_info(self, id_usr, nome, perfil):
        with self.engine.connect() as conn:
            conn.execute(text("UPDATE users_v3 SET nome = :n, perfil = :p WHERE id = :id"), {"n": nome, "p": perfil, "id": id_usr})
            conn.commit()

    def listar_usuarios(self) -> pd.DataFrame:
        return pd.read_sql("SELECT id, nome, username, perfil, primeiro_acesso FROM users_v3 ORDER BY id ASC", self.engine)

    def excluir_usuario(self, username):
        with self.engine.connect() as conn:
            try:
                conn.execute(text("DELETE FROM users_v3 WHERE username = :usr"), {"usr": username})
                conn.commit()
                return True
            except: return False

    def registrar_log(self, usuario, acao, detalhes=""):
        with self.engine.connect() as conn:
            conn.execute(text("INSERT INTO auditoria_logs (data_hora, usuario, acao, detalhes) VALUES (:dh, :usr, :acao, :det)"), {"dh": datetime.now(), "usr": usuario, "acao": acao, "det": detalhes})
            conn.commit()

    def ler_logs(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM auditoria_logs ORDER BY data_hora DESC LIMIT 100", self.engine)

    def ler_dados(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM colab_v3 ORDER BY id DESC", self.engine)

    def adicionar_colaborador(self, dados: dict, usuario: str):
        with self.engine.connect() as conn:
            try:
                conn.execute(text("INSERT INTO colab_v3 (nome, email, raca, genero, local, setor, status) VALUES (:nome, :email, :raca, :genero, :local, :setor, :status)"), dados)
                conn.commit()
                self.registrar_log(usuario, "Cadastro Colaborador", f"Adicionado: {dados['nome']}")
                return True
            except: return False
                
    def atualizar_colaborador(self, id_colab, nome, genero, local, setor, status, email, raca):
        with self.engine.connect() as conn:
            conn.execute(text("UPDATE colab_v3 SET nome=:n, genero=:g, local=:l, setor=:s, status=:st, email=:e, raca=:r WHERE id=:id"), {"n": nome, "g": genero, "l": local, "s": setor, "st": status, "e": email, "r": raca, "id": id_colab})
            conn.commit()

    def importar_massa(self, df_importacao: pd.DataFrame, usuario: str):
        registros_inseridos = 0
        with self.engine.connect() as conn:
            for _, row in df_importacao.iterrows():
                nome = str(row.get('nome', '')).strip()
                if nome and nome != 'nan':
                    try:
                        loc_tratado = padronizar_local(row.get('local', ''))
                        setor_tratado = padronizar_setor(row.get('setor', ''))
                        gen_tratado = padronizar_genero(row.get('genero', ''))
                        stts = str(row.get('status', 'Ativo')).strip()
                        if not stts or stts.lower() == 'nan': stts = 'Ativo'

                        conn.execute(text('''
                            INSERT INTO colab_v3 (nome, genero, local, setor, status, email, raca)
                            VALUES (:nome, :genero, :local, :setor, :status, '', 'Não Informado')
                            ON CONFLICT (nome) DO UPDATE SET 
                            genero = EXCLUDED.genero, local = EXCLUDED.local, 
                            setor = EXCLUDED.setor, status = EXCLUDED.status
                        '''), {
                            "nome": nome, "genero": gen_tratado, "local": loc_tratado, 
                            "setor": setor_tratado, "status": stts.title()
                        })
                        registros_inseridos += 1
                    except Exception as e: pass 
            conn.commit()
        if registros_inseridos > 0: self.registrar_log(usuario, "Importação em Massa", f"Processados {registros_inseridos} colaboradores.")
        return registros_inseridos

@st.cache_resource
def iniciar_conexao_banco(): return DatabaseManager()


# ==========================================
# SISTEMA DE LOGIN E SESSÃO
# ==========================================
db = iniciar_conexao_banco()

def tela_login():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.subheader("🔒 Acesso Seguro")
        usuario = st.text_input("Usuário (Minúsculo)").lower()
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar", type="primary", use_container_width=True):
            user_auth = db.autenticar_usuario(usuario, senha)
            if user_auth:
                st.session_state['logado'] = True
                st.session_state['usuario_atual'] = user_auth
                db.registrar_log(user_auth["nome"], "Login no Sistema")
                st.rerun()
            else: st.error("Credenciais inválidas.")
        st.markdown('</div>', unsafe_allow_html=True)

if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state.get('logado'):
    tela_login()
    st.stop()

if st.session_state.get('logado', False) and st.session_state.get('usuario_atual'):
    if st.session_state['usuario_atual'].get('primeiro_acesso', False):
        st.markdown("<br><br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.markdown('<div class="css-card" style="border-top: 5px solid #005F60;">', unsafe_allow_html=True)
            st.subheader("⚠️ Troca de Senha Obrigatória")
            st.write(f"Bem-vindo(a) **{st.session_state['usuario_atual']['nome']}**! Como este é o seu primeiro acesso (ou sua senha foi resetada), crie uma nova senha.")
            nova_senha = st.text_input("Nova Senha", type="password")
            confirma_senha = st.text_input("Confirme a Senha", type="password")
            if st.button("Salvar e Acessar o Sistema", type="primary", use_container_width=True):
                if len(nova_senha) < 4: st.error("A senha deve ter pelo menos 4 caracteres.")
                elif nova_senha != confirma_senha: st.error("As senhas não coincidem.")
                else:
                    db.atualizar_senha(st.session_state['usuario_atual']['username'], nova_senha)
                    st.session_state['usuario_atual']['primeiro_acesso'] = False
                    st.success("Senha atualizada com sucesso! Redirecionando...")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.stop()


# ==========================================
# APLICAÇÃO PRINCIPAL E CÁLCULOS DINÂMICOS
# ==========================================
usuario_logado = st.session_state['usuario_atual']
df_colab = db.ler_dados()

total_colaboradores = len(df_colab)
total_inativos = len(df_colab[df_colab['status'].str.lower() == 'inativo']) if not df_colab.empty else 0
total_homens = len(df_colab[df_colab['genero'].str.lower() == 'masculino']) if not df_colab.empty else 0
total_mulheres = len(df_colab[df_colab['genero'].str.lower() == 'feminino']) if not df_colab.empty else 0

pj_count = len(df_colab[df_colab['local'] == 'PJ']) if not df_colab.empty else 0
sede_count = len(df_colab[df_colab['local'] == 'SEDE']) if not df_colab.empty else 0
pf_count = len(df_colab[df_colab['local'] == 'PF']) if not df_colab.empty else 0
ppd_count = len(df_colab[df_colab['local'] == 'PPD']) if not df_colab.empty else 0

def count_setor_ativos(local, setor):
    if df_colab.empty: return 0
    return len(df_colab[(df_colab['local'] == local) & (df_colab['setor'].str.strip().str.lower() == str(setor).strip().lower()) & (df_colab['status'].str.lower() != 'inativo')])

def count_setor_todos(local, setor):
    if df_colab.empty: return 0
    return len(df_colab[(df_colab['local'] == local) & (df_colab['setor'].str.strip().str.lower() == str(setor).strip().lower())])

df_exibicao_segura = aplicar_lgpd(df_colab, usuario_logado['perfil'])


# --- SIDEBAR (Menu Lateral) ---
with st.sidebar:
    st.markdown("### 🏢 GERENCIAMENTO BK")
    st.markdown(f"👤 **{usuario_logado['nome']}**")
    st.caption(f"🛡️ Nível de Acesso: **{usuario_logado['perfil']}**")
    st.markdown("---")
    
    opcoes_menu = ["Home - Dashboard", "Gestão de Pessoas", "Integração de Dados (Planilhas)"]
    if usuario_logado['perfil'] == 'Admin':
        opcoes_menu.append("Configurações ⚙️")
        opcoes_menu.append("Auditoria e Logs 🔐")
        
    menu_selecionado = st.radio("Navegação", opcoes_menu)
    
    if usuario_logado['perfil'] == 'Admin':
        st.markdown("---")
        with st.expander("⚙️ Gestão de Usuários (Acessos)"):
            tab_add, tab_list = st.tabs(["➕ Criar", "📋 Editar/Excluir"])
            with tab_add:
                with st.form("form_novo_user"):
                    novo_nome = st.text_input("Nome Completo")
                    novo_usr = st.text_input("Login").lower()
                    nova_senha = st.text_input("Senha Provisória", type="password")
                    novo_perfil = st.selectbox("Perfil", ["Usuario", "Admin"])
                    if st.form_submit_button("Salvar Usuário", use_container_width=True):
                        if novo_nome and novo_usr and nova_senha:
                            if db.criar_usuario(novo_usr, nova_senha, novo_perfil, novo_nome):
                                db.registrar_log(usuario_logado['nome'], "Criação de Usuário", f"Criou o login '{novo_usr}'")
                                st.success("Usuário criado com sucesso!")
                            else: st.error("Erro: Login já existe.")
                        else: st.warning("Preencha todos os campos.")
            
            with tab_list:
                df_users = db.listar_usuarios()
                for _, u in df_users.iterrows():
                    with st.expander(f"{u['nome']} ({u['perfil']})"):
                        e_nome = st.text_input("Nome", value=u['nome'], key=f"e_n_{u['id']}")
                        e_perf = st.selectbox("Perfil", ["Usuario", "Admin"], index=0 if u['perfil']=='Usuario' else 1, key=f"e_p_{u['id']}")
                        colA, colB, colC = st.columns([1, 1, 1])
                        with colA:
                            if st.button("💾", key=f"sv_{u['id']}", help="Salvar nome/perfil"):
                                db.atualizar_usuario_info(u['id'], e_nome, e_perf)
                                st.success("OK")
                                st.rerun()
                        with colB:
                            if st.button("🔑", key=f"rs_{u['id']}", help="Reseta a senha para 123"):
                                db.resetar_senha(u['username'])
                                db.registrar_log(usuario_logado['nome'], "Reset de Senha", f"Senha de '{u['username']}' resetada.")
                                st.success("Reset OK!")
                        with colC:
                            if u['username'] != 'bruno.admin': 
                                if st.button("🗑️", key=f"del_{u['id']}", help="Excluir Usuário"):
                                    db.excluir_usuario(u['username'])
                                    db.registrar_log(usuario_logado['nome'], "Exclusão", f"Excluiu '{u['username']}'")
                                    st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 Sair", use_container_width=True):
        db.registrar_log(usuario_logado['nome'], "Logout do Sistema")
        st.session_state['logado'] = False
        st.rerun()

# --- HEADER SUPERIOR COM PESQUISA INTELIGENTE ---
col_titulo, col_busca, col_btn = st.columns([1.5, 2, 1])
with col_titulo: 
    st.title(menu_selecionado.split(" - ")[0])
with col_busca:
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    termo_busca = st.text_input("🔍 Pesquisa Inteligente", placeholder="Pesquisar talento, setor, departamento...", label_visibility="collapsed")
with col_btn:
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.rerun()


# ==========================================
# TELA 1: HOME (DASHBOARD)
# ==========================================
if menu_selecionado == "Home - Dashboard":
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f'<div class="kpi-main-card"><div class="kpi-main-title">TOTAL DE COLABORADORES</div><div class="kpi-main-value">{total_colaboradores}</div></div>', unsafe_allow_html=True)
    with k2: st.markdown(f'<div class="kpi-main-card" style="background-color: #F9FAFB;"><div class="kpi-main-title">INATIVOS</div><div class="kpi-main-value" style="color: #9CA3AF;">{total_inativos}</div></div>', unsafe_allow_html=True)
    with k3: st.markdown(f'<div class="kpi-main-card"><div class="kpi-main-title" style="color:#1976D2;">HOMENS</div><div class="kpi-main-value" style="color: #1976D2;">{total_homens}</div></div>', unsafe_allow_html=True)
    with k4: st.markdown(f'<div class="kpi-main-card"><div class="kpi-main-title" style="color:#C2185B;">MULHERES</div><div class="kpi-main-value" style="color: #C2185B;">{total_mulheres}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    h1, h2, h3, h4 = st.columns(4)
    with h1: st.markdown(f'<div class="kpi-sub-card border-pj"><div class="kpi-sub-title">PJ (Procuradoria Judicial)</div><div class="kpi-sub-value">{pj_count}</div></div>', unsafe_allow_html=True)
    with h2: st.markdown(f'<div class="kpi-sub-card border-sede"><div class="kpi-sub-title">SEDE</div><div class="kpi-sub-value">{sede_count}</div></div>', unsafe_allow_html=True)
    with h3: st.markdown(f'<div class="kpi-sub-card border-pf"><div class="kpi-sub-title">PF (Procuradoria Fiscal)</div><div class="kpi-sub-value">{pf_count}</div></div>', unsafe_allow_html=True)
    with h4: st.markdown(f'<div class="kpi-sub-card border-ppd"><div class="kpi-sub-title">PPD</div><div class="kpi-sub-value">{ppd_count}</div></div>', unsafe_allow_html=True)

    # --- EDIÇÃO DIRETA NAS LISTAS E EXPORTAÇÃO (Com Filtro de Busca Integrado) ---
    with st.expander("📊 Clique aqui para Listar/Editar/Exportar dados dos KPIs Acima"):
        filtro_relatorio = st.radio("Filtro Categoria:", ["Listar Ativos", "Listar Inativos", "Listar Afastados", "Listar PJ", "Listar SEDE", "Listar PF", "Listar Homens", "Listar Mulheres", "Listar Todos"], horizontal=True)
        
        df_view = df_exibicao_segura.copy()
        if filtro_relatorio == "Listar Ativos": df_view = df_view[df_view['status'].str.lower() == 'ativo']
        elif filtro_relatorio == "Listar Inativos": df_view = df_view[df_view['status'].str.lower() == 'inativo']
        elif filtro_relatorio == "Listar Afastados": df_view = df_view[df_view['status'].str.lower() == 'afastado']
        elif filtro_relatorio == "Listar PJ": df_view = df_view[df_view['local'] == 'PJ']
        elif filtro_relatorio == "Listar SEDE": df_view = df_view[df_view['local'] == 'SEDE']
        elif filtro_relatorio == "Listar PF": df_view = df_view[df_view['local'] == 'PF']
        elif filtro_relatorio == "Listar Homens": df_view = df_view[df_view['genero'].str.lower() == 'masculino']
        elif filtro_relatorio == "Listar Mulheres": df_view = df_view[df_view['genero'].str.lower() == 'feminino']
        
        # Aplica Pesquisa Inteligente
        if termo_busca and not df_view.empty:
            df_view = df_view[df_view.apply(lambda row: row.astype(str).str.contains(termo_busca, case=False, na=False).any(), axis=1)]
        
        if usuario_logado['perfil'] == 'Admin' and not df_view.empty:
            st.caption("Você é Admin. Dê um clique duplo na célula para corrigir dados. Depois clique em 'Salvar'.")
            edited_df = st.data_editor(df_view, use_container_width=True, hide_index=True, disabled=["id", "email"])
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("💾 Salvar Alterações", type="primary"):
                    try:
                        for _, row in edited_df.iterrows():
                            db.atualizar_colaborador(row['id'], row['nome'], row['genero'], row['local'], row['setor'], row['status'], row.get('email', ''), row.get('raca', ''))
                        st.success("Atualizado!")
                        st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
        else:
            st.dataframe(df_view, use_container_width=True, hide_index=True)
            if termo_busca and df_view.empty: st.warning(f"Nenhum colaborador encontrado para a pesquisa: '{termo_busca}'")
            
        if not df_view.empty:
            st.download_button(f"📥 Exportar Planilha", data=df_view.to_csv(index=False).encode('utf-8'), file_name=f'relatorio.csv', mime='text/csv')

    # --- DISTRIBUIÇÃO DEPARTAMENTAL ---
    st.markdown('<div class="section-title" style="display:flex; justify-content:space-between;"><span>Distribuição Departamental</span><span style="font-size:0.75rem; color:#9CA3AF; text-transform:uppercase; font-weight:600;">Mapeamento Organizacional</span></div>', unsafe_allow_html=True)
    col_pj, col_sede, col_pf = st.columns(3)
    
    with col_pj:
        st.markdown(f'<div class="dept-header"><span class="dept-title"><span class="dot-pj"></span>PJ (Procuradoria Judicial)</span><span class="dept-total-badge">{pj_count}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Cálculos</span><span class="dept-num">{count_setor_todos("PJ", "Cálculos")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Obrigação de Fazer</span><span class="dept-num">{count_setor_todos("PJ", "Obrigação de Fazer")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">OPV</span><span class="dept-num">{count_setor_todos("PJ", "OPV")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Litispendência</span><span class="dept-num">{count_setor_todos("PJ", "Litispendência")}</span></div>', unsafe_allow_html=True)
        with st.expander("VER MAIS DEPARTAMENTOS"):
            st.markdown(f'<div class="dept-item"><span class="dept-name">Detran</span><span class="dept-num">{count_setor_todos("PJ", "Detran")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Precatórios</span><span class="dept-num">{count_setor_todos("PJ", "Precatórios")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">TI</span><span class="dept-num">{count_setor_todos("PJ", "TI")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">NPM</span><span class="dept-num">{count_setor_todos("PJ", "NPM")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Cadastro Requisitórios</span><span class="dept-num">{count_setor_todos("PJ", "Cadastro Requisitórios")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Trabalhista</span><span class="dept-num">{count_setor_todos("PJ", "Trabalhista")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Cartografia</span><span class="dept-num">{count_setor_todos("PJ", "Cartografia")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">NRST</span><span class="dept-num">{count_setor_todos("PJ", "NRST")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Nomeação Contador</span><span class="dept-num">{count_setor_todos("PJ", "Nomeação Contador")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">NIRA</span><span class="dept-num">{count_setor_todos("PJ", "NIRA")}</span></div>', unsafe_allow_html=True)

    with col_sede:
        st.markdown(f'<div class="dept-header"><span class="dept-title"><span class="dot-sede"></span>SEDE</span><span class="dept-total-badge">{sede_count}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Cadastro</span><span class="dept-num">{count_setor_todos("SEDE", "Cadastro")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">APJ</span><span class="dept-num">{count_setor_todos("SEDE", "APJ")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Auxílio Saúde</span><span class="dept-num">{count_setor_todos("SEDE", "Auxílio Saúde")}</span></div>', unsafe_allow_html=True)
        with st.expander("VER MAIS DEPARTAMENTOS"):
            st.markdown(f'<div class="dept-item"><span class="dept-name">DOF</span><span class="dept-num">{count_setor_todos("SEDE", "DOF")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Transação</span><span class="dept-num">{count_setor_todos("SEDE", "Transação")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Centro de Estudos</span><span class="dept-num">{count_setor_todos("SEDE", "Centro de Estudos")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">ATIC</span><span class="dept-num">{count_setor_todos("SEDE", "ATIC")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">PDA</span><span class="dept-num">{count_setor_todos("SEDE", "PDA")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Saneamento</span><span class="dept-num">{count_setor_todos("SEDE", "Saneamento")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">CSAC</span><span class="dept-num">{count_setor_todos("SEDE", "CSAC")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Subcontencioso</span><span class="dept-num">{count_setor_todos("SEDE", "Subcontencioso")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">CGP</span><span class="dept-num">{count_setor_todos("SEDE", "CGP")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Consultoria</span><span class="dept-num">{count_setor_todos("SEDE", "Consultoria")}</span></div>', unsafe_allow_html=True)

    with col_pf:
        st.markdown(f'<div class="dept-header"><span class="dept-title"><span class="dot-pf"></span>PF (Procuradoria Fiscal)</span><div><span style="font-size:0.75rem; color:#7DD3FC; margin-right:5px;">{pf_count}</span><span class="dept-total-badge" style="background-color:#FFF7ED; color:#9A3412;">PPD: {ppd_count}</span></div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Cálculos</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Cálculos")}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dept-item"><span class="dept-name">Fazenda Autora</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Fazenda Autora")}</span></div>', unsafe_allow_html=True)
        with st.expander("VER MAIS DEPARTAMENTOS"):
            st.markdown(f'<div class="dept-item"><span class="dept-name">Gestão de Crédito</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Gestão de Crédito")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">NASS</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "NASS")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Pesquisa</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Pesquisa")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Falência</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Falência")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">ITCMD</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "ITCMD")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">TUSD</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "TUSD")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Cumprimento Geral</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Cumprimento Geral")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Subsídios / Falência</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Subsídios / Falência")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">TI</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "TI")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Arrematação</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Arrematação")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Levantamento</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Levantamento")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Multirão Garantia</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Multirão Garantia")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dept-item"><span class="dept-name">Jurimetria</span><span class="dept-num" style="color:#7DD3FC;">{count_setor_todos("PF", "Jurimetria")}</span></div>', unsafe_allow_html=True)

    # --- CÁLCULO DINÂMICO DE VAGAS ABERTAS ---
    st.markdown('<hr style="margin:2rem 0;">', unsafe_allow_html=True)
    v1, v2 = st.columns([1, 2])
    with v1: st.markdown('<div class="section-title" style="margin-top:0;">Vagas Abertas</div>', unsafe_allow_html=True)
    with v2: filtro_vaga = st.radio("Filtro Vagas", ["Tudo", "PJ", "SEDE", "PF", "PPD"], horizontal=True, label_visibility="collapsed")
    
    df_metas_banco = db.ler_metas()
    lista_vagas_abertas = []
    
    for _, row in df_metas_banco.iterrows():
        loc = row['local']
        setr = row['setor']
        alvo = row['meta']
        ativos_ocupando = count_setor_ativos(loc, setr)
        vagas_restantes = alvo - ativos_ocupando
        
        if vagas_restantes > 0:
            lista_vagas_abertas.append({
                "Departamento": f"{loc} ({setr})",
                "Título da Função": f"Vaga Alocada - {setr}",
                "Vagas": str(vagas_restantes),
                "Status": "RECRUTAMENTO ATIVO",
                "Filtro": loc
            })
                
    df_vagas_dinamico = pd.DataFrame(lista_vagas_abertas)
    
    st.markdown('<div class="kpi-main-card" style="padding: 0;">', unsafe_allow_html=True)
    colunas_header = st.columns([2, 3, 1, 2])
    for i, h in enumerate(["DEPARTAMENTO", "TÍTULO DA FUNÇÃO", "VAGAS ABERTAS", "STATUS"]):
        colunas_header[i].markdown(f"<span style='font-size:0.7rem; color:#9CA3AF; font-weight:700;'>{h}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
    
    df_vagas_filtrado = df_vagas_dinamico if (filtro_vaga == "Tudo" or df_vagas_dinamico.empty) else df_vagas_dinamico[df_vagas_dinamico['Filtro'] == filtro_vaga]
    
    # Aplica Pesquisa Inteligente nas Vagas
    if termo_busca and not df_vagas_filtrado.empty:
        df_vagas_filtrado = df_vagas_filtrado[df_vagas_filtrado.apply(lambda row: row.astype(str).str.contains(termo_busca, case=False, na=False).any(), axis=1)]
    
    if df_vagas_filtrado.empty:
        st.markdown("<p style='text-align:center; padding: 2rem; color: gray;'>Nenhuma vaga aberta encontrada para este filtro/pesquisa.</p>", unsafe_allow_html=True)
    else:
        for _, row in df_vagas_filtrado.iterrows():
            cols = st.columns([2, 3, 1, 2])
            cols[0].markdown(f"**{row['Departamento']}**", unsafe_allow_html=True)
            cols[1].markdown(f"{row['Título da Função']}", unsafe_allow_html=True)
            cols[2].markdown(f"<span style='font-weight:900; color:#005F60;'>{row['Vagas']}</span>", unsafe_allow_html=True)
            cols[3].markdown(render_status_badge(row['Status']), unsafe_allow_html=True)
            st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.5;'>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# TELA 2: CONFIGURAÇÕES DE VAGAS (Admin)
# ==========================================
elif menu_selecionado == "Configurações ⚙️":
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.subheader("⚙️ Configurações de Vagas por Departamento")
    st.write("Abaixo você pode definir a quantidade alvo (Meta de Vagas) para cada setor. O sistema usará este valor para calcular automaticamente quantas vagas estão abertas.")
    
    df_metas_atual = db.ler_metas()
    if termo_busca and not df_metas_atual.empty:
        df_metas_atual = df_metas_atual[df_metas_atual.apply(lambda row: row.astype(str).str.contains(termo_busca, case=False, na=False).any(), axis=1)]
        
    st.caption("Dê um duplo clique na coluna 'meta' para alterar o número de vagas. Os outros campos são bloqueados.")
    edited_metas = st.data_editor(df_metas_atual, use_container_width=True, hide_index=True, disabled=["local", "setor"])
    
    if st.button("💾 Salvar Novas Metas", type="primary"):
        try:
            db.atualizar_metas(edited_metas, usuario_logado['nome'])
            st.success("Metas atualizadas com sucesso!")
            st.rerun()
        except Exception as e: st.error(f"Erro ao salvar metas: {e}")
    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# TELA 3: GESTÃO DE PESSOAS
# ==========================================
elif menu_selecionado == "Gestão de Pessoas":
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.subheader("➕ Novo Cadastro")
    
    with st.form("form_novo_colab"):
        col1, col2, col3 = st.columns([2, 2, 1])
        nome = col1.text_input("Nome Completo*")
        email = col2.text_input("E-mail Corporativo")
        genero = col3.selectbox("Gênero", ["Não Informado", "Masculino", "Feminino", "Outro"])
        
        col4, col5, col6 = st.columns([1.5, 2, 1])
        local_selecionado = col4.selectbox("Local*", list(ESTRUTURA.keys()))
        setor_selecionado = col5.selectbox("Setor Alocado*", ESTRUTURA[local_selecionado])
        status = col6.selectbox("Status", ["Ativo", "Afastado", "Inativo"])
        
        if st.form_submit_button("Registrar Colaborador", type="primary"):
            if nome:
                dados_novos = {"nome": nome.strip(), "email": email, "raca": "Não Informado", "genero": genero, "local": local_selecionado, "setor": setor_selecionado, "status": status}
                if db.adicionar_colaborador(dados_novos, usuario_logado['nome']):
                    st.success(f"Cadastro de {nome} realizado com sucesso!")
                    st.rerun()
                else: st.error("Erro: Um colaborador com este nome exato já existe.")
            else: st.warning("O Nome é obrigatório.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if termo_busca:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.subheader("🔎 Resultado da Pesquisa")
        df_busca = df_exibicao_segura[df_exibicao_segura.apply(lambda row: row.astype(str).str.contains(termo_busca, case=False, na=False).any(), axis=1)]
        if df_busca.empty: st.warning("Nenhum registro encontrado.")
        else: st.dataframe(df_busca, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# TELA 4: IMPORTAÇÃO DE PLANILHAS
# ==========================================
elif menu_selecionado == "Integração de Dados (Planilhas)":
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.subheader("🔗 Importação em Massa")
    st.write("A planilha deve conter obrigatoriamente as colunas: **nome**, **genero**, **local**, **setor** e **status**.")
    
    arquivo = st.file_uploader("Selecione a planilha (Excel ou CSV)", type=['xlsx', 'csv'])
    if arquivo:
        try:
            if arquivo.name.endswith('.csv'): df_import = pd.read_csv(arquivo, delimiter=';', encoding='utf-8', on_bad_lines='skip')
            else: df_import = pd.read_excel(arquivo)
            df_import.columns = df_import.columns.str.lower().str.strip()
            df_import.columns = df_import.columns.str.replace(r'[^\w\s]', '', regex=True)
            
            st.success("Planilha lida com sucesso! Visualize a prévia:")
            st.dataframe(df_import.head())
            if st.button("Gravar Dados no Sistema", type="primary", use_container_width=True):
                qtd = db.importar_massa(df_import, usuario_logado['nome'])
                if qtd > 0: st.success(f"{qtd} registros processados/atualizados com sucesso!")
                else: st.warning("Nenhum dado importado. Verifique os nomes das colunas.")
        except Exception as e: st.error(f"Erro ao ler arquivo: {e}")
    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# TELA 5: AUDITORIA E LOGS (Somente Admin)
# ==========================================
elif menu_selecionado == "Auditoria e Logs 🔐":
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.subheader("Histórico de Acessos e Alterações")
    df_logs = db.ler_logs()
    
    if termo_busca:
        df_logs = df_logs[df_logs.apply(lambda row: row.astype(str).str.contains(termo_busca, case=False, na=False).any(), axis=1)]
        
    st.dataframe(df_logs, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
