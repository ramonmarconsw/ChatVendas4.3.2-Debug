# ui_utils.py — Funções de interface e resumos textuais para o Radar IA
import pandas as pd
import unicodedata

def _fmt_num(x):
    try:
        if isinstance(x, (int, float)) and pd.notna(x):
            return f"{x:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except Exception:
        pass
    return str(x)

def narrate_result(question: str, sql: str, df: pd.DataFrame) -> str:
    """
    Gera um texto curto e amigável baseado no resultado da consulta.
    Foco no usuário final — sem detalhes de SQL.
    """
    q = (question or "").strip().rstrip("?").capitalize()
    if df is None or df.empty:
        return f"Não encontrei dados para **{q}** no período/tabelas consultados."

    linhas, colunas = df.shape
    cols = list(df.columns)

    # 1x1 agregado
    if linhas == 1 and len(cols) == 1:
        valor = _fmt_num(df.iloc[0, 0])
        colname = cols[0].replace("_"," ").capitalize()
        return f"Para **{q}**, o resultado é **{valor}** ({colname})."

    q_lower = q.lower()

    # Ranking/top
    if any(k in q_lower for k in ["cliente","top","ranking","maior","menor"]):
        top_rows = df.head(5)
        exemplos = ", ".join(_fmt_num(x) for x in top_rows.iloc[:, 0].tolist())
        return f"Principais resultados para **{q}**: {exemplos}."

    # Volume/valor/peso
    if any(k in q_lower for k in ["volume","valor","área","area","produc","faturamento","peso","kg","m²","m2"]):
        total = None
        for c in cols:
            if "total" in c.lower() or c.lower().startswith(("sum","area","valor","m2","m_2")):
                try:
                    total = float(df[c].sum())
                    break
                except Exception:
                    pass
        if total is not None:
            return f"O total calculado para **{q}** é **{_fmt_num(total)}**."
        return f"A consulta sobre **{q}** foi executada com sucesso."

    # Caso geral
    return f"Consulta concluída. Aqui estão os dados referentes a **{q}**."
