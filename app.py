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
    .stApp { background-color: #F8F9FA; }
    .css-card { background-color: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); margin-bottom: 1rem; }
    .css-card-dark { background-color: #005F60; color: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); margin-bottom: 1rem; }
    .css-card-alert { background-color: white; border-left: 5px solid #FFB890; padding: 1.5rem; border-radius: 5px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)


# ==========================================
# ESTRUTURA ORGANIZACIONAL
# ==========================================
ESTRUTURA = {
    "PJ": ["Cadastro Requisitórios", "NIRA", "Detran", "Litispendência", "Obrigação de Fazer", "OPV", "Trabalhista", "TI", "Nomeação Contador", "Precatórios", "Cálculos", "Cartografia", "NPM", "NRST"],
    "SEDE": ["APJ", "Saneamento", "Transação", "CGP", "CSAC", "DOF", "Centro de Estudos", "Consultoria", "Subcontencioso", "Cadastro", "ATIC", "PDA", "Auxílio Saúde"],
    "PF": ["ITCMD", "Cálculos", "Multirão Garantia", "Jurimetria", "Cumprimento Geral", "Gestão de Crédito", "Arrematação", "TI", "Fazenda Autora", "NASS", "Falência", "Pesquisa", "Subsídios / Falência", "Levantamento", "TUSD"],
    "PPD": ["Equipe Geral"]
}

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
            # Tabela de Colaboradores (Dados Sensíveis)
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
            
            # Tabela de Logs de Auditoria
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS auditoria_logs (
                    id SERIAL PRIMARY KEY,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario VARCHAR(100),
                    acao VARCHAR(255),
                    detalhes TEXT
                )
            '''))
            
            # Tabela de Usuários do Sistema (Login)
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    senha VARCHAR(100) NOT NULL,
                    perfil VARCHAR(20) NOT NULL,
                    nome VARCHAR(100) NOT NULL
                )
            '''))
            
            # Cria usuários padrão se a tabela estiver vazia
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
                return False # Falha se o username já existir

    # --- Funções de Logs ---
    def registrar_log(self, usuario, acao, detalhes=""):
        with self.engine.connect() as conn:
            conn.execute(text('''
                INSERT INTO auditoria_logs (data_hora, usuario, acao, detalhes)
                VALUES (:dh, :usr, :acao, :det)
            '''), {"dh": datetime.now(), "usr": usuario, "acao": acao, "det": detalhes})
            conn.commit()

    def ler_logs(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM auditoria_logs ORDER BY data_hora DESC LIMIT 100", self.engine)

    # --- Funções de Colaboradores ---
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

    if 'cpf' in df_mascarado.columns:
        df_mascarado['cpf'] = df_mascarado['cpf'].apply(mascarar_cpf)
    if 'rg' in df_mascarado.columns:
        df_mascarado['rg'] = "***.***.**"
    if 'email' in df_mascarado.columns:
        df_mascarado['email'] = df_mascarado['email'].apply(mascarar_email)
    
    return df_mascarado


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
            # Valida direto no banco de dados agora
            user_auth = banco_temp.autenticar_usuario(usuario, senha)
            
            if user_auth:
                st.session_state['logado'] = True
                st.session_state['usuario_atual'] = user_auth
                banco_temp.registrar_log(user_auth["nome"], "Login no Sistema")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
        st.markdown('</div>', unsafe_allow_html=True)

if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    tela_login()
    st.stop()


# ==========================================
# APLICAÇÃO PRINCIPAL (Após Login)
# ==========================================
db = iniciar_conexao_banco()
usuario_logado = st.session_state['usuario_atual']
df_colab = db.ler_dados()

df_exibicao_segura = aplicar_lgpd(df_colab, usuario_logado['perfil'])

df_ativos = df_colab[df_colab['status'] == 'Ativo']
df_inativos = df_colab[df_colab['status'] == 'Inativo']

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
    
    # --- ÁREA EXCLUSIVA DE ADMIN: CRIAR USUÁRIOS ---
    if usuario_logado['perfil'] == 'Admin':
        st.markdown("---")
        with st.expander("➕ Criar Novo Usuário"):
            with st.form("form_novo_user_lateral"):
                st.caption("Cadastrar acesso ao sistema:")
                novo_nome = st.text_input("Nome Completo")
                novo_usr = st.text_input("Login de Acesso")
                nova_senha = st.text_input("Senha Padrão", type="password")
                novo_perfil = st.selectbox("Perfil de Acesso", ["Usuario", "Admin"])
                
                if st.form_submit_button("Salvar Usuário", use_container_width=True):
                    if novo_nome and novo_usr and nova_senha:
                        sucesso = db.criar_usuario(novo_usr, nova_senha, novo_perfil, novo_nome)
                        if sucesso:
                            db.registrar_log(usuario_logado['nome'], "Criação de Usuário", f"Criou o login '{novo_usr}'")
                            st.success(f"Usuário {novo_usr} criado!")
                        else:
                            st.error("Erro: Este login já existe.")
                    else:
                        st.warning("Preencha todos os campos.")

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
    if st.download_button("📥 Exportar (Seguro)", data=csv, file_name='relatorio_rh.csv', mime='text/csv', use_container_width=True):
        db.registrar_log(usuario_logado['nome'], "Exportação de Dados", "Base de colaboradores baixada.")

st.markdown("---")

# ==========================================
# TELA 1: HOME (DASHBOARD)
# ==========================================
if menu_selecionado == "Home - Dashboard":
    kpi1, kpi2, kpi3 = st.columns(3)
    
    with kpi1:
        st.markdown(f"""
            <div class="css-card">
                <p style="color: gray; font-size: 14px; font-weight: bold;">TOTAL DE COLABORADORES</p>
                <h1 style="color: #005F60; margin: 0; font-size: 3rem;">{len(df_colab)}</h1>
            </div>
        """, unsafe_allow_html=True)
        
    with kpi2:
        st.markdown(f"""
            <div class="css-card">
                <p style="color: gray; font-size: 14px; font-weight: bold;">COLABORADORES ATIVOS</p>
                <h1 style="color: #28a745; margin: 0; font-size: 3rem;">{len(df_ativos)}</h1>
            </div>
        """, unsafe_allow_html=True)
        
    with kpi3:
        st.markdown(f"""
            <div class="css-card">
                <p style="color: gray; font-size: 14px; font-weight: bold;">COLABORADORES INATIVOS</p>
                <h1 style="color: #dc3545; margin: 0; font-size: 3rem;">{len(df_inativos)}</h1>
            </div>
        """, unsafe_allow_html=True)

    col_esq, col_dir = st.columns([1.5, 1])

    with col_esq:
        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.subheader("Distribuição por Local (Sedes)")
        if not df_ativos.empty:
            locais_count = df_ativos['local'].value_counts().reset_index()
            locais_count.columns = ['Local', 'Qtd']
            st.bar_chart(locais_count.set_index('Local'))
        else:
            st.info("Sem dados para exibir.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_dir:
        st.markdown("""
            <div class="css-card-alert">
                <h4 style="margin:0; color:#333;">🛡️ Status de Conformidade</h4>
                <p style="margin:0; color:gray; font-size: 14px;">Mascaramento LGPD Ativo. Acessos monitorados via log.</p>
            </div>
        """, unsafe_allow_html=True)


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
                if arq.name.endswith('.csv'):
                    lista_dfs.append(pd.read_csv(arq))
                else:
                    lista_dfs.append(pd.read_excel(arq))
            except Exception as e:
                st.error(f"Erro ao ler {arq.name}: {e}")
                
        st.success(f"{len(arquivos)} planilhas processadas na memória.")
        
        for idx in range(len(lista_dfs)):
            lista_dfs[idx].columns = lista_dfs[idx].columns.str.lower().str.strip()
            
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