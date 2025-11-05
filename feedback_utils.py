# feedback_utils.py — escrita em arquivos de feedback (não alterar contrato)
from datetime import datetime
import os

def _append_feedback_txt(path: str, question_or_sql: str, answer_sql: str | None = None):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}]\n")
            if answer_sql is None:
                f.write(question_or_sql + "\n")
            else:
                f.write("PERGUNTA:\n" + question_or_sql + "\n\n")
                f.write("SQL:\n" + answer_sql + "\n")
            f.write("-" * 80 + "\n")
    except Exception:
        # Evita quebrar a UI se disco estiver somente leitura
        pass