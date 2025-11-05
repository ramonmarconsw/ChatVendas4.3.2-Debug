
import streamlit as st
from textwrap import dedent
from datetime import datetime
import pandas as pd
import re
from functools import lru_cache


from config import (
    DEFAULT_DATABASE,
    DEFAULT_TEMP,
    DEFAULT_TOP_P,
    DEFAULT_MAX_COMPLETION_TOKENS,
    HIDE_SQL_IN_UI,
    PERSIST_TURNS,
    DEFAULT_HISTORY_TOKEN_BUDGET,
    PII_COLUMN_HINTS,
    REGRAS_GERAIS,
    POS_FILE,
    NEG_FILE,
    AZURE_OAI_ENDPOINT,
    AZURE_OAI_DEPLOYMENT,
    AZURE_OAI_API_VERSION,
    AZURE_OAI_API_KEY
)

from db import (
    try_connect, 
    odbc_conn_str_windows, 
    #fetch_tables_and_columns_cached,
    #schema_to_text, 
    run_query, ensure_chat_table, insert_chat_turn
)
from llm import montar_prompt, call_azure_openai_completion, extract_sql, metric_hints_for_question, classify_intent, call_azure_openai_general, clear_intent_cache
from sql_utils import sql_sanity_rewrite, validate_sql, validate_known_tables, enforce_new_plants_sql, validate_blocked_tables
from feedback_utils import _append_feedback_txt
from ui_utils import narrate_result
from rules import SCHEMA_INFO, METRIC_RULES, EXEMPLOS_SQL

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("radar-ia")


st.set_page_config(page_title="Radar IA", layout="centered")
st.markdown(
    """
    <style>
      /* Layout centralizado no estilo ChatGPT */
      .block-container { 
        padding-top: 1.25rem; 
        padding-bottom: 2rem;
        max-width: 860px;
        margin-left: auto;
        margin-right: auto;
      }
      /* Centraliza as mensagens do chat */
      .stChatMessage > div { 
        max-width: 820px; 
        margin-left: auto; 
        margin-right: auto; 
      }
      .stChatMessage { 
        border: none !important; 
        box-shadow: none !important; 
        padding: 0.25rem 0 !important;
      }
      /* Centraliza o input de chat */
      [data-testid="stChatInput"] > div { 
        max-width: 820px; 
        margin-left: auto; 
        margin-right: auto; 
      }
      /* Remove avatares/ícones (amarelo/laranja) das bolhas */
      .stChatMessage img,
      .stChatMessage svg,
      .stChatMessage [role="img"],
      .stChatMessage .stAvatar {
        display: none !important;
      }
      /* Título centralizado */
      .block-container h1 { text-align: center; }
      /* Contador de tokens discreto */
      .token-counter { 
        position: fixed; 
        bottom: 0.5rem; 
        right: 1rem; 
        font-size:0.85em; 
        color: gray;
      }
      .assistant-summary { 
        font-size:1.12rem; 
        line-height:1.35; 
        margin-top:0.6rem; 
        margin-bottom:0.6rem; 
        color:#111;
        text-align: left;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Radar IA")

# Estado inicial
if "conn_str" not in st.session_state: st.session_state.conn_str = None
if "connected" not in st.session_state: st.session_state.connected = False
#if "schema_text" not in st.session_state: st.session_state.schema_text = None
if "messages" not in st.session_state: st.session_state.messages = []
if "k_exemplos" not in st.session_state: st.session_state.k_exemplos = 12
if "pending_turn" not in st.session_state: st.session_state.pending_turn = None
if "turn_counter" not in st.session_state: st.session_state.turn_counter = 0
if "last_processed_turn_id" not in st.session_state: st.session_state.last_processed_turn_id = 0
if "last_question_sql" not in st.session_state: st.session_state.last_question_sql = None
if "last_usage" not in st.session_state: st.session_state.last_usage = None

# Autoconexão via Windows Auth
if not st.session_state.connected:
    try:
        from config import DEFAULT_SQL_SERVER, DEFAULT_DRIVER
        conn_str = odbc_conn_str_windows(DEFAULT_SQL_SERVER, DEFAULT_DATABASE, DEFAULT_DRIVER)
        st.session_state.conn_str = conn_str
        conn = try_connect(st.session_state.conn_str); conn.close()
        st.session_state.connected = True


    except Exception:
        st.session_state.connected = False



# Inicializações de sessão
st.session_state.setdefault('history_token_budget', DEFAULT_HISTORY_TOKEN_BUDGET)
# session_id único por sessão
if 'session_id' not in st.session_state:
    st.session_state.session_id = datetime.now().strftime('%Y%m%d%H%M%S')

# Render histórico (somente a verdade oficial da UI)
MAX_MSGS = 40
msgs = st.session_state.messages[-MAX_MSGS:]

# Computa o índice do último dataframe e depois renderiza tudo (código mais compacto)
last_df_idx = max((i for i, m in enumerate(msgs) if m.get("type") == "dataframe"), default=None)

for idx, m in enumerate(msgs):
    role = m.get("role", "assistant")
    display_role = "user" if role == "user" else "assistant"
    label = "Pergunta:" if role == "user" else "Resposta:"
    mtype = m.get("type")

    # Evita bolha vazia para SQL quando oculto
    if mtype == "sql" and HIDE_SQL_IN_UI:
        continue

    with st.chat_message(display_role, avatar=None):
        if mtype == "sql":
            # Só mostra SQL se não estiver oculto
            if not HIDE_SQL_IN_UI:
                st.markdown(f"**{label}**")
                st.code(m.get("content",""), language="sql")

        elif mtype == "dataframe":
            st.markdown(f"**{label}**")
            summary = m.get("summary")
            if summary:
                # usa classe já existente no seu CSS
                st.markdown(f"<div class='assistant-summary'>{summary}</div>", unsafe_allow_html=True)

            df = m.get("content")
            if df is not None:
                # Expande apenas o último dataframe por padrão
                st.expander("Ver tabela", expanded=(idx == last_df_idx)).dataframe(df, use_container_width=True)

        else:
            # Texto normal (pergunta do usuário ou resposta em markdown)
            st.markdown(m.get("content", ""))


# Entrada do usuário
user_q = st.chat_input("Pergunte algo (ex.: Volume total em 2025 na planta Pirapetinga)")
if user_q:
    st.session_state.turn_counter += 1
    st.session_state.pending_turn = {"id": st.session_state.turn_counter, "question": user_q}
    st.rerun()

# Helper resumo usuário
def make_user_friendly_summary(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "A consulta foi executada com sucesso, mas não retornou resultados."
    nrows, ncols = df.shape
    preferred = ["VALOR_TOTAL", "AREA_VENDIDA", "PESO_ENTREGUE", "NOME_CLI", "PRODUTO"]
    cols = list(df.columns)
    chosen = [p for p in preferred if p in cols]
    for c in cols:
        if c not in chosen:
            chosen.append(c)
        if len(chosen) >= 3: break
    first_row = df.iloc[0].to_dict()
    example_parts = [f"{c}: {first_row.get(c)}" for c in chosen[:3]]
    example = "; ".join(example_parts)
    return f"Foram retornadas {nrows:,} linha(s). Exemplo de registro — {example}."

# Constrói um contexto curto da conversa (últimos N turnos)

# --- Ferramentas customizadas (plugáveis) ------------------------------------
from typing import Dict, Any, Callable

ToolResult = Dict[str, Any]
TOOL_REGISTRY: Dict[str, Callable[[str, Dict[str, Any]], ToolResult]] = {}

def register_tool(name: str):
    def _wrap(fn):
        TOOL_REGISTRY[name] = fn
        return fn
    return _wrap

def run_tool(name: str, user_q: str, args: Dict[str, Any]) -> ToolResult:
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return {"type":"text", "text": f"Ferramenta '{name}' não encontrada."}
    try:
        return fn(user_q, args or {})
    except Exception as e:
        return {"type":"text", "text": f"Falha ao executar a ferramenta '{name}': {e}"}

@register_tool("carteira_mes")
def tool_carteira_mes(user_q: str, args: Dict[str, Any]) -> ToolResult:
    """
    Args:
      mes: 'YYYY-MM' (opcional). Default = mês atual do servidor.
    """
    today = datetime.now()
    mes = (args.get("mes") or f"{today.year:04d}-{today.month:02d}").strip()
    if not re.match(r"^\d{4}-\d{2}$", mes):
        return {"type":"text", "text":"Parâmetro 'mes' deve estar no formato YYYY-MM."}

    year, month = map(int, mes.split("-"))
    start = f"{year:04d}-{month:02d}-01 00:00:00"
    if month == 12:
        end = f"{year+1:04d}-01-01 00:00:00"
    else:
        end = f"{year:04d}-{month+1:02d}-01 00:00:00"

    sql = f"""
        SELECT
          COUNT(DISTINCT RecordID) AS QTD_REGISTROS,
          COALESCE(SUM(M2_Bruto),0) AS M2_BRUTO_CARTEIRA
        FROM dbo.DASH_ATUAL WITH (NOLOCK)
        WHERE TRY_CONVERT(datetime, Data_Entrega) >= '{start}'
          AND TRY_CONVERT(datetime, Data_Entrega) <  '{end}';
    """
    df = run_query(st.session_state.conn_str, sql)
    return {"type":"dataframe", "df": df, "summary": f"Carteira de {mes} (DASH_ATUAL)."}





# === Utilitários de contexto/máscara ===
def _approx_tokens(s: str) -> int:
    if not s:
        return 0
    # aproximação (~4 chars por token)
    return max(1, int(len(s) / 4))

def _mask_pii_column(colname: str) -> bool:
    name_up = (colname or "").upper()
    return any(h in name_up for h in PII_COLUMN_HINTS)

def _mask_cell(colname: str, val) -> str:
    s = "" if val is None else str(val)
    if _mask_pii_column(colname):
        # hash curta mantendo padrão estável para repetição
        import hashlib
        h = hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:6]
        return f"{colname}_***{h}"
    # truncagem leve por célula no contexto
    s = s.replace("\n", " ").strip()
    return (s[:24] + "…") if len(s) > 25 else s

# COLE em app.py (logo após o TOOL_REGISTRY e run_tool)

def handle_intent(q: str, intent: dict):
    route = (intent or {}).get("route", "sql")
    try:
        if route == "gpt":
            answer, usage = call_azure_openai_general(
                q, temperature=DEFAULT_TEMP, top_p=DEFAULT_TOP_P,
                max_completion_tokens=DEFAULT_MAX_COMPLETION_TOKENS
            )
            st.session_state.last_usage = usage
            st.session_state.messages.append({"role":"assistant","content":answer})
            return

        if route == "tool":
            tool_name = (intent or {}).get("tool")
            args = (intent or {}).get("args") or {}
            if not tool_name or tool_name not in TOOL_REGISTRY:
                st.session_state.messages.append({"role":"assistant","content":"Ferramenta não encontrada. Tente: carteira_mes."})
                return
            result = run_tool(tool_name, q, args)
            if result.get("type") == "dataframe":
                df = result.get("df")
                summary_text = result.get("summary") or make_user_friendly_summary(df)
                st.session_state.messages.append({"role":"assistant","type":"dataframe","content":df,"summary":summary_text})
            else:
                st.session_state.messages.append({"role":"assistant","content":result.get("text") or "Ok."})
            return

        # --- route == "sql" ---
        hist = build_chat_context(max_tokens=st.session_state.history_token_budget)
        safe_examples = EXEMPLOS_SQL

        prompt = montar_prompt(
            pergunta_usuario=q,
            schema_info=SCHEMA_INFO,
            regras_metricas=METRIC_RULES + "\n\n" + "\n".join(f"- {r}" for r in REGRAS_GERAIS),
            exemplos_pool=safe_examples,
            dbname=DEFAULT_DATABASE,
            k_exemplos=st.session_state.k_exemplos,
            historico_text=hist,
        )
        raw_text, usage = call_azure_openai_completion(
            prompt,
            temperature=DEFAULT_TEMP,
            top_p=DEFAULT_TOP_P,
            max_completion_tokens=DEFAULT_MAX_COMPLETION_TOKENS
        )
        st.session_state.last_usage = usage

        sql1 = extract_sql(raw_text)
        if not sql1:
            prompt2 = dedent(f"""Converta a pergunta a seguir em uma única consulta T-SQL válida.Database: {DEFAULT_DATABASE}Pergunta:{q}""")
            raw_text2, usage2 = call_azure_openai_completion(
                prompt2, temperature=0.05, top_p=0.95,
                max_completion_tokens=DEFAULT_MAX_COMPLETION_TOKENS
            )
            st.session_state.last_usage = usage2
            sql1 = extract_sql(raw_text2)
        if not sql1:
            st.error("Não consegui extrair SQL da resposta do modelo.")
            return

        sql1 = sql_sanity_rewrite(sql1)
        sql1 = enforce_new_plants_sql(sql1, q)
        st.session_state.messages.append({"role":"assistant","type":"sql","content":sql1})

        ok1, msg1 = validate_sql(sql1)
        ok2, msg2 = (True,"ok") if not SCHEMA_INFO else validate_known_tables(sql1, SCHEMA_INFO)
        ok3, msg3 = validate_blocked_tables(sql1)
        if not ok1:
            st.error(f"SQL inválido: {msg1}")
        if not ok2:
            st.warning(msg2)
        if not ok3:
            st.error(msg3)
            return

        df = run_query(st.session_state.conn_str, sql1)
        st.session_state.last_question_sql = {"q": q, "sql": sql1}
        try:
            summary_text = narrate_result(q, sql1, df)
        except Exception:
            summary_text = make_user_friendly_summary(df)

        st.session_state.messages.append({"role":"assistant","type":"dataframe","content":df,"summary":summary_text})

    except Exception as e:
        log.exception("Falha no handle_intent")
        st.error(f"Erro geral: {e}")
        st.session_state.messages.append({"role": "assistant", "content": "Opa, algo deu errado ao processar sua solicitação. Tente reformular ou informar o período/tabela desejada."})


def build_chat_context(max_tokens: int = None) -> str:
    """
    Constrói o contexto baseado em orçamento de tokens.
    Inclui: últimos 2 turnos (user/assistant), APENAS a última SQL válida,
    e mini-CSV mascarado (2 linhas x 5 colunas).
    """
    budget = max_tokens or DEFAULT_HISTORY_TOKEN_BUDGET
    used = 0
    blocks = []

    # 1) mensagens mais recentes
    messages = list(reversed(st.session_state.messages))

    # 2) última SQL
    last_sql = None
    for m in messages:
        if m.get("type") == "sql":
            content = (m.get("content") or "").strip()
            if content:
                last_sql = content
                break

    # 3) últimos 2 turnos (user/assistant)
    turns = []
    user_count = 0
    for m in messages:
        role = m.get("role")
        mtype = m.get("type")
        if role == "user":
            turns.append(("user", (m.get("content") or "").strip()))
            user_count += 1
            if user_count >= 2:
                break
        else:
            if mtype == "dataframe":
                df = m.get("content")
                summary = (m.get("summary") or "").strip()
                mini_csv = ""
                if df is not None:
                    try:
                        import pandas as pd
                        if isinstance(df, pd.DataFrame):
                            df2 = df.copy()
                            cols = list(df2.columns)[:5]
                            df2 = df2[cols].head(2)
                            for c in cols:
                                df2[c] = df2[c].map(lambda v: _mask_cell(c, v))
                            mini_csv = df2.to_csv(index=False)
                    except Exception:
                        mini_csv = ""
                bloco = "Assistente:"
                if summary:
                    bloco += f"\nresumo={summary}"
                if mini_csv:
                    bloco += f"\nAmostra CSV (até 2 linhas):\n{mini_csv}"
                turns.append(("assistant", bloco.strip()))
            elif mtype == "sql":
                # ignorar aqui; a última SQL entra uma única vez no final
                pass
            else:
                content = (m.get("content") or "").strip()
                if content:
                    turns.append(("assistant", content))

    def try_add(text: str) -> bool:
        nonlocal used, budget, blocks
        t = _approx_tokens(text)
        if used + t <= budget:
            blocks.append(text)
            used += t
            return True
        return False

    # adiciona turnos (do mais antigo ao mais recente)
    for who, text in reversed(turns[:4]):
        try_add(f"{'Usuário' if who=='user' else 'Assistente'}: {text}")

    # adiciona última SQL se couber
    if last_sql:
        try_add("Assistente (SQL anterior):\n```sql\n" + last_sql + "\n```")

    return "\n\n".join(blocks)

# Processamento do turno pendente
pending = st.session_state.pending_turn
if pending and pending["id"] > st.session_state.last_processed_turn_id:
    q = pending["question"]
    with st.chat_message("user", avatar=None): st.markdown(q)
    st.session_state.messages.append({"role": "user", "content": q})
    if PERSIST_TURNS and st.session_state.conn_str:
        try:
            ensure_chat_table(st.session_state.conn_str)
            insert_chat_turn(st.session_state.conn_str, st.session_state.session_id, "user", "text", q, None)
        except Exception:
            pass

    with st.chat_message("assistant", avatar=None):
        if not st.session_state.conn_str:
            st.warning("Sem conexão ativa com o banco de dados. Verifique sua conexão.")
        else:
            try:
                if not SCHEMA_INFO:
                    #print(" schema do banco................")
                   
                    """ NÃO USAR E VER
                    try:
                        cols = fetch_tables_and_columns_cached(st.session_state.conn_str)
                        st.session_state.schema_text = schema_to_text(cols)
                    except Exception:
                        st.session_state.schema_text = ""
                    """
                with st.spinner("Analisando dados..."):
                    # 1) Classificar intenção
                    
                    intent = classify_intent(q)  # {"route": "sql"|"gpt"|"tool", "tool":..., "args":...}
                    # 2) Roteamento LEAN
                  
                    handle_intent(q, intent)

            except Exception as e:
                st.error(f"Erro geral: {e}")
                st.session_state.messages.append({"role": "assistant", "content": f"Erro geral: {e}"})

    st.session_state.last_processed_turn_id = pending["id"]
    st.session_state.pending_turn = None
    st.rerun()

# Feedback global
payload = st.session_state.get("last_question_sql")
if payload and isinstance(payload, dict) and payload.get("q") and payload.get("sql"):
    current_hash = str(hash((payload["q"], payload["sql"])))
    if "last_feedback_hash" not in st.session_state: st.session_state.last_feedback_hash = None

    # Feedback na sidebar (estilo ChatGPT, não polui a timeline)
    with st.sidebar:
        st.markdown("### Feedback")
        st.caption("Avalie a última resposta")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍", key=f"fb_up_{current_hash}"):
                if st.session_state.last_feedback_hash != ("up", current_hash):
                    try:
                        _append_feedback_txt(POS_FILE, payload["q"], payload["sql"])
                        st.session_state.last_feedback_hash = ("up", current_hash)
                        st.success("Obrigado pelo feedback!")
                    except Exception as e: st.error(f"Falha ao salvar feedback: {e}")
        with col2:
            if st.button("👎", key=f"fb_down_{current_hash}"):
                if st.session_state.last_feedback_hash != ("down", current_hash):
                    try:
                        _append_feedback_txt(NEG_FILE, payload["q"], payload["sql"])
                        st.session_state.last_feedback_hash = ("down", current_hash)
                        st.warning("Obrigado pelo feedback!")
                    except Exception as e: st.error(f"Falha ao salvar feedback: {e}")

    # Contador de tokens

if "last_usage" in st.session_state and st.session_state.last_usage:
    u = st.session_state.last_usage
    total_tokens = u.get("total_tokens", 0)
    st.markdown(f"<div class='token-counter'>Tokens usados: {total_tokens}</div>", unsafe_allow_html=True)

