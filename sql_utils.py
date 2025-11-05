# sql_utils.py — saneamento e validação de SQL
# sql_utils.py — saneamento e validação de SQL (somente SELECT/CTE)

import re
import unicodedata
from config import DEFAULT_YEAR_IF_MISSING
from functools import lru_cache

_BLOCKED_TOKENS = [
    r"\bdrop\b", r"\balter\b", r"\btruncate\b", r"\bcreate\b", r"\bgrant\b", r"\brevoke\b",
    r"\bxp_", r"\bsp_", r"\bexec\b", r"\binsert\b", r"\bupdate\b", r"\bdelete\b", r"\bmerge\b"
]


def normalize_sql_token(s: str) -> str:
    if not s:
        return ""
    d = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in d if not unicodedata.combining(ch)).lower()
def _strip_inline_comments(sql: str) -> str:
    if not sql: return sql
    # remove -- comentários de linha (sem quebrar string literals)
    return re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)

def sql_sanity_rewrite(sql: str) -> str:
    if not sql:
        return sql
    s = _strip_inline_comments(sql).strip()

    # Corrige padrão YEAR(x)=MONTH(x)=m  ->  YEAR(x)=YYYY AND MONTH(x)=m
    pat = re.compile(r"YEAR\(\s*(?P<c>[^)]+?)\s*\)\s*=\s*MONTH\(\s*(?P=c)\s*\)\s*=\s*(?P<m>\d{1,2})", re.IGNORECASE)
    if pat.search(s):
        yyyy = DEFAULT_YEAR_IF_MISSING
        s = pat.sub(lambda m: f"YEAR({m.group('c')}) = {yyyy} AND MONTH({m.group('c')}) = {int(m.group('m'))}", s)

    # Injeta ano padrão quando só há mês em colunas frequentes
    for col in ["EMISSAO","DT_ENTREGA1","DT_ENTREGA","DATA","DATA_EMISSAO","Data_Entrega"]:
        if re.search(rf"YEAR\(\s*{col}\s*\)", s, flags=re.IGNORECASE):
            continue
        mm = re.search(rf"(MONTH\(\s*{col}\s*\)\s*=\s*(\d{{1,2}}))", s, flags=re.IGNORECASE)
        if mm:
            mnum = int(mm.group(2))
            if 1 <= mnum <= 12:
                yyyy = DEFAULT_YEAR_IF_MISSING
                s = s.replace(mm.group(1), f"{mm.group(1)} AND YEAR({col}) = {yyyy}")
    return s

def validate_sql(sql_text: str) -> (bool, str):
    if not sql_text:
        return False, "SQL vazio."
    lowered = f" {sql_text.lower()} "
    if not re.match(r"^\s*(select|with)\b", sql_text, flags=re.IGNORECASE):
        return False, "A consulta não parece um SELECT/CTE."
    if any(re.search(tok, lowered) for tok in _BLOCKED_TOKENS):
        return False, "Comando não permitido detectado (apenas SELECT/CTE são aceitos)."
    return True, "ok"

def validate_known_tables(sql_text: str, schema_info: dict) -> (bool, str):
    known_tables = set(schema_info.keys())
    mentioned = set()
    for t in known_tables:
        if re.search(rf"(?i)\b{re.escape(t)}\b", sql_text or ""):
            mentioned.add(t)
    if not mentioned:
        return False, "Nenhuma tabela conhecida do SCHEMA_INFO foi referenciada."
    return True, "ok"

# Mantemos apenas tabelas realmente proibidas (alinhado ao rules.py)
_BLOCKED_TABLES = []  # se quiser bloquear algo explicitamente, adicione aqui

def validate_blocked_tables(sql_text: str) -> (bool, str):
    s = (sql_text or "").upper()
    for t in _BLOCKED_TABLES:
        if f" {t.upper()} " in f" {s} ":
            return False, f"Tabela {t} está bloqueada."
    return True, "ok"

def enforce_new_plants_sql(sql_text: str, user_question: str) -> str:
    """Compat: fica aqui para futuras regras — retorna a SQL inalterada por enquanto."""
    return sql_text
