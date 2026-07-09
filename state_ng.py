"""
state_ng.py - Estado do wizard na versao NiceGUI (equivalente ao st.session_state).

Cada aba do navegador tem seu proprio dict (app.storage.client), do mesmo jeito
que cada sessao Streamlit tem seu proprio session_state. Reusamos as MESMAS
chaves de telas.py para que a logica de dominio (prefill, resumo, sequencia)
seja identica nas duas versoes.
"""
from __future__ import annotations

from nicegui import app


def get() -> dict:
    """Dict de estado da aba atual (equivalente a st.session_state)."""
    return app.storage.client


def reset() -> None:
    get().clear()
