# config.py — constantes e variáveis de ambiente

import os
from datetime import datetime
from openai import AzureOpenAI
from pathlib import Path

try:
    from dotenv import load_dotenv  # pip install python-dotenv
    # 1) tenta .env ao lado do config.py
    _here = Path(__file__).resolve().parent
    load_dotenv(dotenv_path=_here / ".env", override=False)
    # 2) tenta também um .env na raiz do projeto (suba 1 nível se seu app roda de uma pasta "Debug")
    load_dotenv(dotenv_path=_here.parent / ".env", override=False)
    # 3) fallback: .env do CWD (quando rodar via streamlit run, por ex.)
    load_dotenv(override=False)
except Exception:
    pass

DEFAULT_SQL_SERVER = os.getenv("SQL_SERVER", "BR-SPA1-M006")
DEFAULT_DATABASE   = os.getenv("SQL_DATABASE", "BI")
DEFAULT_DRIVER     = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")

# Limites e geração
DEFAULT_MAX_COMPLETION_TOKENS = int(os.getenv("DEFAULT_MAX_COMPLETION_TOKENS", "1200"))
DEFAULT_TEMP = float(os.getenv("DEFAULT_TEMP", "0.15"))
DEFAULT_TOP_P = float(os.getenv("DEFAULT_TOP_P", "0.9"))

# Azure OpenAI (NUNCA deixe chave hardcoded no código)
AZURE_OAI_ENDPOINT = os.getenv("AZURE_OAI_ENDPOINT")
AZURE_OAI_DEPLOYMENT = os.getenv("AZURE_OAI_DEPLOYMENT")
AZURE_OAI_API_VERSION = os.getenv("AZURE_OAI_API_VERSION")
AZURE_OAI_API_KEY = os.getenv("AZURE_OAI_API_KEY")  # sem fallback

# Persistência/Histórico
PERSIST_TURNS = os.getenv("PERSIST_TURNS", "false").lower() in ("1","true","yes","on")
DEFAULT_HISTORY_TOKEN_BUDGET = int(os.getenv("HISTORY_TOKEN_BUDGET", "3000"))

# Colunas PII para mascaramento no mini-CSV do prompt
PII_COLUMN_HINTS = [
    "NOME", "NOME_CLI", "CLIENTE", "CPF", "CNPJ", "EMAIL", "E_MAIL", "TELEFONE", "CELULAR", "ENDERECO",
]

# Timeouts e retries (ajustáveis por env)
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_RETRY_BASE_DELAY = float(os.getenv("LLM_RETRY_BASE_DELAY", "0.7"))

# Query guard (server-side)
SQL_COMMAND_TIMEOUT_SECONDS = int(os.getenv("SQL_COMMAND_TIMEOUT_SECONDS", "60"))

DEFAULT_YEAR_IF_MISSING = int(os.getenv("DEFAULT_YEAR_IF_MISSING", "2025"))

HIDE_SQL_IN_UI = os.getenv("HIDE_SQL_IN_UI", "true").lower() in ("1","true","yes","on")
DEBUG_SHOW_MODEL_RAW = os.getenv("DEBUG_SHOW_MODEL_RAW", "false").lower() in ("1","true","yes","on")

# Diretório e arquivos de feedback
FEEDBACK_DIR = os.path.join(os.getcwd(), "feedback")
POS_FILE = os.path.join(FEEDBACK_DIR, "positives.txt")
NEG_FILE = os.path.join(FEEDBACK_DIR, "negatives.txt")
os.makedirs(FEEDBACK_DIR, exist_ok=True)
for _path in (POS_FILE, NEG_FILE):
    if not os.path.exists(_path):
        with open(_path, "w", encoding="utf-8") as f:
            f.write(f"# Radar IA feedback log — criado em {datetime.now():%Y-%m-%d %H:%M:%S}\n")
    try:
        os.utime(_path, None)
    except Exception:
        pass

# Regras gerais (linhas específicas ficam em rules.py)
REGRAS_GERAIS = [
    "Prefira SQL ANSI, SELECT/FROM/WHERE/GROUP BY/ORDER BY.",
    "Agregações com SUM, AVG, COUNT(*) devem ter alias claros.",
    "Datas no SQL Server: use GETDATE() quando fizer sentido.",
    "Nunca crie tabelas temporárias. Apenas SELECT/CTE.",
    "Se a pergunta mencionar 'maiores', interprete como ORDER BY DESC.",
    "Quando a pergunta envolver clientes, use a coluna NOME_CLI.",
    "Quando houver 'excluir/sem/excepto', filtre com NOME_CLI NOT LIKE '%<nome>%' (collate CI_AI).",
]

# ===========================
# Azure OpenAI - Cliente
# ===========================
# cache do cliente para não recriar a cada chamada
try:
    import streamlit as st

    @st.cache_resource(show_spinner=False)
    def get_azure_oai_client() -> AzureOpenAI:
        if not AZURE_OAI_API_KEY:
            raise RuntimeError("AZURE_OAI_API_KEY não definido. Configure a variável de ambiente.")
        return AzureOpenAI(
            api_version=AZURE_OAI_API_VERSION,
            azure_endpoint=AZURE_OAI_ENDPOINT,
            api_key=AZURE_OAI_API_KEY,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
except Exception:
    _azure_client_singleton = None
    def get_azure_oai_client() -> AzureOpenAI:
        global _azure_client_singleton
        if not AZURE_OAI_API_KEY:
            raise RuntimeError("AZURE_OAI_API_KEY não definido. Configure a variável de ambiente.")
        if _azure_client_singleton is None:
            _azure_client_singleton = AzureOpenAI(
                api_version=AZURE_OAI_API_VERSION,
                azure_endpoint=AZURE_OAI_ENDPOINT,
                api_key=AZURE_OAI_API_KEY,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        return _azure_client_singleton


