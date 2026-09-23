"""Entrypoint Gradio perfil demo-cpu (FakeChatModel, sem Llama)."""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault('PERFIL_EXECUCAO', 'demo-cpu')

from lib.agent import build_agent
from lib.db import connect, init_schema
from lib.llm_fake import FakeChatModel
from lib.mock_data import populate
from lib.tools import build_langchain_tools
from lib.ui import build_ui
from lib.workflows.obstetrico import build_obstetrico_workflow
from lib.workflows.prevencao import build_prevencao_workflow
from lib.workflows.risco_ml import build_risco_ml_workflow
from lib.workflows.triagem import build_triagem_workflow
from lib.workflows.violencia import build_violencia_workflow


class _Doc:
    def __init__(self, text, meta):
        self.page_content = text
        self.metadata = meta


class _Retriever:
    def invoke(self, query: str):
        return [
            _Doc(
                'Protocolo MS de pré-natal.',
                {'doc_id': 'ms_prenatal', 'category': 'ginecologia_obstetricia', 'chunk_id': '1'},
            )
        ]


def main():
    db = Path(os.environ.get('HOSPITAL_DB_PATH', ROOT / 'artifacts' / 'demo' / 'hospital_ui.db'))
    conn = connect(db)
    init_schema(conn)
    n = conn.execute('SELECT COUNT(*) AS c FROM pacientes').fetchone()['c']
    if n == 0:
        populate(conn, seed=42, verbose=False)
    chat = FakeChatModel()
    retr = _Retriever()
    tools = build_langchain_tools(conn, retr)
    try:
        agent = build_agent(chat, tools)
    except Exception:
        agent = None
    wfs = {
        'triagem': build_triagem_workflow(chat, conn, retr),
        'violencia': build_violencia_workflow(chat, conn, retr),
        'obstetrico': build_obstetrico_workflow(chat, conn, retr),
        'prevencao': build_prevencao_workflow(chat, conn, retr),
        'risco_ml': build_risco_ml_workflow(chat, conn, retr),
    }
    app = build_ui(agent, conn, workflows=wfs)
    app.launch(server_name='0.0.0.0', server_port=int(os.environ.get('PORT', '7860')))


if __name__ == '__main__':
    main()
