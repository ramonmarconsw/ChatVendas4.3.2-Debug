# llm.py — inicialização lazy do cliente Azure
from __future__ import annotations
import time
import random
import unicodedata
from typing import Tuple, Optional, Dict, Sequence
from rules import PLANTAS as _PLANTAS_BASE 
from difflib import SequenceMatcher
from textwrap import dedent
from functools import lru_cache
import json, hashlib


from config import (
    DEFAULT_MAX_COMPLETION_TOKENS, DEFAULT_TEMP, DEFAULT_TOP_P,
    get_azure_oai_client, LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY,
    AZURE_OAI_API_KEY, AZURE_OAI_ENDPOINT, AZURE_OAI_DEPLOYMENT  # <- importante
)

_client = None  # NÃO chame get_azure_oai_client() aqui


def _normalize_text(text: str) -> str:
    """
    Remove acentos e baixa para minúsculas para comparações robustas.
    """
    if not text:
        return ""
    # NFKD decompõe acentos; descartamos marcas de combinação
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.lower()


def _get_client():
    """Cria o cliente sob demanda, só quando for realmente usar."""
    global _client
    if _client is None:
        _client = get_azure_oai_client()  # lança RuntimeError se não houver credenciais
    return _client

def _usage_from_resp(resp):
    u = getattr(resp, "usage", None)
    if not u: return None
    get = (lambda k: getattr(u, k, None) or (u.get(k) if isinstance(u, dict) else 0))
    return {"prompt_tokens": get("prompt_tokens"),
            "completion_tokens": get("completion_tokens"),
            "total_tokens": get("total_tokens")}

# --- NÃO USE 'prompt' dentro de _chat_complete; receba messages prontas ---
def _chat_complete(messages, *, temperature, top_p, max_completion_tokens):
    """
    Executa uma completion de chat com retry. 'messages' deve ser uma lista de dicts:
    [{"role":"system","content":"..."}, {"role":"user","content":"..."}]
    """
    last_err = None
    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            client = _get_client()
            # garante que 'messages' é lista (não tupla/gerador)
            msgs = list(messages) if isinstance(messages, (list, tuple)) else messages
            resp = client.chat.completions.create(
                model=AZURE_OAI_DEPLOYMENT,
                messages=msgs,
                temperature=temperature,
                top_p=top_p,
                max_completion_tokens=max_completion_tokens,
            )
            return resp
        except Exception as e:
            # erro de credencial: não adianta retry
            if isinstance(e, RuntimeError) and "AZURE_OAI_API_KEY" in str(e):
                raise
            last_err = e
            delay = LLM_RETRY_BASE_DELAY * (2 ** (attempt - 1))
            time.sleep(delay)
    raise last_err or RuntimeError("Falha na chamada ao modelo após retries.")

def call_azure_openai_completion(
    prompt: str,
    *,
    temperature: float = DEFAULT_TEMP,
    top_p: float = DEFAULT_TOP_P,
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
):
    resp = _chat_complete(
        [
            {"role": "system", "content": "Você é um conversor de linguagem natural para SQL Server (T-SQL)."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature, top_p=top_p, max_completion_tokens=max_completion_tokens,
    )
    text = resp.choices[0].message.content if resp.choices else ""
    return text, _usage_from_resp(resp)


SYSTEM_MSG_HYBRID = (
    "Você é um assistente que responde em português com explicação curta e, quando fizer sentido, "
    "inclui UM único bloco SQL entre ```sql ... ``` terminando com '; --END'. "
    "Formato recomendado:\n"
    "1) Resumo curto (até 3 linhas)\n"
    "2) Bloco SQL único (opcional)."
)


def call_azure_openai_hybrid(
    prompt: str,
    *,
    temperature: float = DEFAULT_TEMP,
    top_p: float = DEFAULT_TOP_P,
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
):
    resp = _chat_complete(
        [
            {"role": "system", "content": SYSTEM_MSG_HYBRID},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature, top_p=top_p, max_completion_tokens=max_completion_tokens,
    )
    text = resp.choices[0].message.content if resp.choices else ""
    answer_md, sql = extract_answer_and_sql(text)  # mantém sua lógica atual
    return answer_md, sql, _usage_from_resp(resp)



# ===========================
# Utilidades de normalização / matching
# ===========================
def _norm_txt(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower()

def _contains_any(haystack: str, needles: Sequence[str]) -> bool:
    return any(n in haystack for n in needles)

def _sim(a: str, b: str) -> float:
    """Similaridade simples e robusta para selecionar exemplos."""
    aa = _normalize_text(a or "")
    bb = _normalize_text(b or "")
    if not aa or not bb:
        return 0.0
    return SequenceMatcher(None, aa, bb).ratio()


def _digest_examples(exemplos_pool: list[dict]) -> str:
    """
    Gera um hash estável do pool de exemplos (independente da ordem de chaves).
    Assim podemos usar cache com argumentos hashable.
    """
    # json.dumps com sort_keys garante consistência; ensure_ascii=False preserva PT-BR
    payload = json.dumps(exemplos_pool or [], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()
@lru_cache(maxsize=256)
def _selecionar_exemplos_cached(pergunta: str, exemplos_digest: str, k_exemplos: int) -> tuple[dict, ...]:
    """
    Versão cacheada que recebe somente tipos hashable.
    O conteúdo real dos exemplos é recuperado externamente via um registry simples.
    """
    # Recupera o pool real pelo digest (armazenado globalmente pela wrapper)
    pool = _EXEMPLOS_REGISTRY.get(exemplos_digest, [])
    pnorm = _normalize_text(pergunta or "")
    scored = []
    for ex in pool:
        s = max(_sim(pnorm, ex.get("pergunta", "")), _sim(pnorm, ex.get("sql", "")))
        scored.append((s, ex))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [ex for _, ex in scored[:max(1, int(k_exemplos or 3))]]
    # Retorna tupla (hashable) para o cache
    return tuple(top)

# Registry simples em memória para mapear digest -> lista original
_EXEMPLOS_REGISTRY: dict[str, list[dict]] = {}



def selecionar_exemplos(pergunta: str, exemplos_pool: list[dict], k_exemplos: int = 3) -> list[dict]:
    """
    Wrapper não-cacheado: registra o pool, computa digest e delega para a versão cacheada.
    Evita 'TypeError: unhashable type: list' no lru_cache.
    """
    digest = _digest_examples(exemplos_pool or [])
    # registra uma cópia leve (evita mutações externas afetarem o cache)
    _EXEMPLOS_REGISTRY[digest] = list(exemplos_pool or [])
    result = _selecionar_exemplos_cached(pergunta or "", digest, int(k_exemplos or 3))
    return list(result)

# ===========================
# Hints dinâmicos por pergunta
# ===========================
def metric_hints_for_question(pergunta_usuario: str) -> dict:
    """
    Gera dicas de métricas/plantas com base no texto da pergunta.
    Use SEMPRE o parâmetro 'pergunta_usuario' para evitar NameError.
    """
    # texto bruto e normalizado
    q_raw = (pergunta_usuario or "").strip()
    qn = _normalize_text(q_raw)  # requer o helper _normalize_text já importado
    uses_area    = _contains_any(qn, [" volume", "volume ", "vol ", "m2", "área", "area"])
    uses_peso    = _contains_any(qn, [" kg", "kg ", "peso", "ton", "tonelada"])
    uses_valor   = _contains_any(qn, ["dinheiro", "valor", "faturamento", "receita", " r$", "r$"])
    uses_cart    = _contains_any(qn, ["carteira", "entrega", "data_entrega"])
    uses_cliente = _contains_any(qn, ["cliente", "clientes"])
    uses_exclui  = _contains_any(qn, ["exclu", "sem ", "exceto", "excepto"])
    plants = _PLANTAS_BASE
    plants_hit = [p for p in plants if _normalize_text(p) in qn]

    lines = []
    if uses_area:
        lines.append("- Volume/área: usar **VW_DEVOLUCAO_LAB** com **SUM(AREA)**; filtros obrigatórios: GRUPO_PRODUTO NOT IN ('PAPEL','BOBINA') e TIPO IN ('VENDA','DEVOLUCAO'); data: **DATA_EMISSAO**; para cidade/planta, **GROUP BY CIDADE**.")
    if uses_cart or uses_valor or uses_peso:
        lines.append("- Carteira/entregas: usar **DASH_ATUAL** (mês corrente) ou **DASH_HISTORICO** (períodos passados). Medida padrão de carteira: **SUM(M2_Bruto)** filtrando **TRY_CONVERT(date, Data_Entrega)** no intervalo do mês (semi-aberto).")
    if uses_cliente:
        lines.append("- Clientes: usar **NOME_CLI** para agrupar/filtrar (evite CLIENTE/NOME_CLIENTE).")
    if uses_exclui:
        lines.append("- Exclusões: aplicar **NOME_CLI NOT LIKE '%<nome>%'** (collate CI_AI).")
    if plants_hit:
        ph = ", ".join(sorted(set(plants_hit)))
        lines.append(f"- Plantas citadas: {ph}. Usar igualdade CI_AI na comparação de strings.")

    return "\n".join(lines)


# ===========================
# Montagem do prompt principal (SQL-only)
# ===========================
# llm.py
def montar_prompt(
    pergunta_usuario: str,
    schema_info: Dict,
    regras_metricas: str,
    exemplos_pool: List[Dict],
    dbname: str,
    k_exemplos: int = 12,
    schema_text_db: str = "",
    historico_text: str = "",          # <--- NOVO
) -> str:
    partes = [
        "Você é um conversor de Linguagem Natural para SQL Server (T-SQL).",
        "Responda APENAS com um bloco markdown contendo somente a query SQL:",
        "```sql",
        "<SUA_QUERY_AQUI>",
        "```",
        "",
        "EXIGIDO: finalize a query com '; --END' na linha final.",
        "Proibido DDL/DCL/EXEC — apenas SELECT/CTE.",
        "Prefira CTEs quando precisar de etapas.",
        "Datas: use GETDATE() quando fizer sentido.",
        f"Database: {dbname}",
        "",
        "=== MAPEAMENTO DE MÉTRICAS E ORIGEM (ver SCHEMA_INFO e regras) ===",
        regras_metricas,
    ]

    spec = metric_hints_for_question(pergunta_usuario)
    if spec:
        partes.append("\n=== AJUSTES PARA ESTA PERGUNTA ===")
        partes.append(spec)

    # <<< NOVO: entra ANTES da pergunta corrente >>>
    if historico_text and historico_text.strip():
        partes.append("\n=== CONTEXTO DA CONVERSA (use se necessário) ===")
        # O histórico já vem resumido (resumos/mini CSV/SQL anteriores)
        partes.append(historico_text)

    partes.append("\n=== ESQUEMA (SCHEMA_INFO) ===")
    for tabela, dados in schema_info.items():
        partes.append(f"- {tabela}: {dados.get('descricao','')}")
        for col, desc in dados.get("colunas", {}).items():
            partes.append(f"  • {col}: {desc}")

    if schema_text_db:
        partes.append("\n=== ESQUEMA (INFORMATION_SCHEMA — resumo) ===")
        partes.append(schema_text_db)

    exs = selecionar_exemplos(pergunta_usuario, exemplos_pool, k_exemplos)
    if exs:
        partes.append("\n=== EXEMPLOS DE FORMATO (similaridade) ===")
        for ex in exs:
            sql_ex = (ex["sql"] or "").rstrip().rstrip(";") + "; --END"
            partes.append(f"Pergunta: {ex['pergunta']}\n```sql\n{sql_ex}\n```")

    partes.append(f"\nPergunta do usuário: {pergunta_usuario}")
    partes.append("Responda apenas com o bloco ```sql ... ``` finalizando com '; --END'.")
    return "\n".join(partes)

# ===========================
# Extração do SQL da resposta do modelo
# ===========================
def extract_sql(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"```sql\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return _cleanup_sql(m.group(1))
    m = re.search(r"```\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return _cleanup_sql(m.group(1))
    m = re.search(r"\b(SELECT|WITH)\b.*", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return _cleanup_sql(text[m.start():])
    return ""

def _cleanup_sql(s: str) -> str:
    s = re.sub(r"^\s*sql\s*\n", "", s, flags=re.IGNORECASE)
    s = s.strip().strip("`").strip()
    if "--END" in s:
        s = s.split("--END")[0]
    s = s.rstrip().rstrip(";").strip()
    return s



def extract_answer_and_sql(text: str) -> Tuple[str, str]:
    """
    Retorna (resposta_texto, sql_limpo).
    Se houver bloco ```sql ...```, separa o texto antes e o SQL limpo.
    """
    if not text:
        return "", ""
    m = re.search(r"```sql\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return text.strip(), ""
    sql_block = m.group(1).strip()
    sql_clean = _cleanup_sql(sql_block)
    answer_md = text[:m.start()].strip()
    return answer_md, sql_clean


# === INTENT ROUTER / GENERAL CHAT ============================================
import json, re
from typing import Any, Dict

_SQL_HEUR = [
    "volume", "área", "m²", "carteira", "otif", "sum(", "avg(", "count(", "group by",
    "top", "ranking", "por unidade", "por planta", "por cidade", "dashboard",
]
_TOOL_HEUR = [
    "relatório", "exportar", "gerar pdf", "csv", "enviar", "gráfico", "dashboard pronto",
]
_GPT_HEUR = [
    "explique", "como faço", "o que é", "por que", "resuma", "exemplos", "ideias",
]

def _rule_based_guess(q: str) -> str:
    qn = _norm_txt(q)
    if re.search(r"\b(select|with|from|where|join)\b", qn):
        return "sql"
    if any(k in qn for k in _SQL_HEUR):
        return "sql"
    if any(k in qn for k in _TOOL_HEUR):
        return "tool"
    if any(k in qn for k in _GPT_HEUR):
        return "gpt"
    return ""


def _safe_load_json_line(s: str) -> dict:
    import json, re
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m: 
        return {}
    try:
        obj = json.loads(m.group(0))
        if not isinstance(obj, dict): 
            return {}
        # Normaliza chaves essenciais
        return {
            "route": obj.get("route") in ("sql","gpt","tool") and obj.get("route") or "gpt",
            "tool": (obj.get("tool") or None),
            "args": obj.get("args") if isinstance(obj.get("args"), dict) else {},
        }
    except Exception:
        return {}

def _classify_via_llm(q: str) -> Dict[str, Any]:
    """
    Usa o LLM para classificar a pergunta quando as heurísticas não forem conclusivas.
    Retorna dict no formato: {"route": "sql"|"gpt"|"tool", "tool": str|None, "args": dict}
    """
    prompt = dedent(f"""
    Você é um classificador. Escolha a rota:
    - "sql": pede dados/contagens/agrupamentos vindos do banco (VW_DEVOLUCAO_LAB, DASH_ATUAL, DASH_HISTORICO, BI_OTIF).
    - "gpt": explicação, conceitos, brainstorm, resumo.
    - "tool": quando o usuário quer AÇÃO (ex.: exportar, pdf, csv, gráfico). Nomeie a ferramenta em snake_case.

    Responda STRICT JSON em uma única linha:
    {{"route":"sql"|"gpt"|"tool","tool":null|string,"args":{{}}}}

    Pergunta:
    {q}
    """)

    resp = _client.chat.completions.create(
        model=AZURE_OAI_DEPLOYMENT,
        messages=[
            {"role":"system","content":"Classifique e retorne APENAS JSON válido em UMA linha."},
            {"role":"user","content":prompt},
        ],
        temperature=0.1, top_p=0.9, max_completion_tokens=120,
    )

    parsed = _safe_load_json_line(resp.choices[0].message.content if resp.choices else "")
    if not parsed:
        return {"route":"gpt","tool":None,"args":{}}
    return parsed 

@lru_cache(maxsize=512)
def _classify_cached(q_norm: str) -> Dict[str, Any]:
    """
    Cacheia a classificação por chave normalizada (lowercase/sem acento).
    Primeiro tenta as heurísticas (zero custo). Se não decidir, chama o LLM.
    """
    # Heurística rule-based (usa q_norm; a função por dentro normaliza de novo, sem problemas)
    route = _rule_based_guess(q_norm)
    if route:
        return {"route": route, "tool": None, "args": {}}

    # Fallback: LLM (pode usar a string normalizada; para esse tipo de classe, é suficiente)
    return _classify_via_llm(q_norm)


def classify_intent(q: str) -> Dict[str, Any]:
    """
    Classifica a pergunta do usuário em 'sql' | 'gpt' | 'tool' (com cache LRU por texto normalizado).
    """
    qn = _norm_txt(q or "")
    return _classify_cached(qn)



def call_azure_openai_general(
    prompt: str,
    *,
    temperature: float = DEFAULT_TEMP,
    top_p: float = DEFAULT_TOP_P,
    max_completion_tokens: int = 900,
):
    """
    Resposta 'texto livre' em PT-BR, objetiva.
    """
    resp = _client.chat.completions.create(
        model=AZURE_OAI_DEPLOYMENT,
        messages=[
            {"role":"system","content":"Responda em português, de forma objetiva e clara."},
            {"role":"user","content":prompt},
        ],
        temperature=temperature, top_p=top_p, max_completion_tokens=max_completion_tokens,
    )
    text = resp.choices[0].message.content if resp.choices else ""

    usage = _usage_from_resp(resp)
    #u = getattr(resp, "usage", None)
    #usage = None
    #if u:
    #    usage = {
    #        "prompt_tokens": getattr(u, "prompt_tokens", None) or (u.get("prompt_tokens") if isinstance(u, dict) else 0),
    #        "completion_tokens": getattr(u, "completion_tokens", None) or (u.get("completion_tokens") if isinstance(u, dict) else 0),
    #        "total_tokens": getattr(u, "total_tokens", None) or (u.get("total_tokens") if isinstance(u, dict) else 0),
    #    }
    return text.strip(), usage

def clear_intent_cache():
    _classify_cached.cache_clear()


