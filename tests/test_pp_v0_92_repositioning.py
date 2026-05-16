"""
tests/test_pp_v0_92_repositioning.py — v0.92:

Auditoria do repositioning UX/UI: o Olivas é especialista
em **análise elétrica**, e a integração ATP é tooling
secundário.

Cobertura:

* Menu "Análise" existe e tem os 5 estudos especializados.
* Menu "Ferramentas" existe e contém o submenu "ATP/EMTP".
* Menu "Simulação" foi removido (era o antigo nome).
* Ordem dos menus: Arquivo → Editar → Análise → Validação →
  Ferramentas → … (Análise antes de Ferramentas).
* Welcome dialog tem 5 _AnalysisCard (informativos).
* Welcome dialog menciona audit trail / ISO 9001 / NR-10.
* Card "Abrir caso ATP" aparece como secundário/opcional.
"""

from __future__ import annotations

import os

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Menu reorganization
# ---------------------------------------------------------------------------


class TestMenuReorganization:

    def test_no_simulacao_menu(self, qapp):
        """v0.92: menu 'Simulação' foi renomeado para 'Ferramentas'."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        menus = [a.text() for a in mw.menuBar().actions()]
        assert "Simulação" not in menus, (
            f"Menu 'Simulação' ainda existe; deveria ser 'Ferramentas'. "
            f"Got: {menus}"
        )

    def test_ferramentas_menu_exists(self, qapp):
        """v0.92: novo menu 'Ferramentas' existe (substituiu Simulação)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        menus = [a.text() for a in mw.menuBar().actions()]
        assert "Ferramentas" in menus

    def test_analise_before_ferramentas(self, qapp):
        """v0.92: 'Análise' aparece ANTES de 'Ferramentas' no menu bar
        (foco do produto = análise; ATP é secundário)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        menus = [a.text() for a in mw.menuBar().actions()]
        idx_a = menus.index("Análise")
        idx_t = menus.index("Ferramentas")
        assert idx_a < idx_t, (
            f"Análise (idx {idx_a}) deve preceder Ferramentas "
            f"(idx {idx_t}). Got: {menus}"
        )

    def test_validacao_appears_near_analise(self, qapp):
        """v0.92: Validação fica logo após Análise (pré-laudo)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        menus = [a.text() for a in mw.menuBar().actions()]
        idx_a = menus.index("Análise")
        idx_v = menus.index("Validação")
        assert idx_v == idx_a + 1, (
            f"Validação deve ser o menu logo após Análise. "
            f"Got: {menus}"
        )

    def _find_menu(self, mw, name: str):
        """v0.92: helper — retorna QMenu by name, mantendo a action
        viva (sem segurar a action, PySide6 GC libera o menu)."""
        for a in mw.menuBar().actions():
            if a.text() == name:
                return a, a.menu()
        return None, None

    def test_analise_has_all_5_specialized_studies(self, qapp):
        """v0.92: o menu 'Análise' tem TODOS os 5 estudos
        especializados (SC, PF, Coord, Arc-flash, Balanço)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        _action, analise = self._find_menu(mw, "Análise")
        assert analise is not None
        items = [act.text() for act in analise.actions()]
        joined = " ".join(items)
        # Cada um dos 5 estudos
        assert "Curto-circuito" in joined, items
        assert "Fluxo de potência" in joined, items
        assert "Coordenação" in joined or "seletividade" in joined, items
        assert "Arc-flash" in joined or "Energia incidente" in joined, items
        assert "Balanço de carga" in joined or "partida" in joined.lower(), items
        # Plus the consolidated pipeline + report
        assert any("Estudo completo" in t for t in items)
        assert any("Relatório completo" in t for t in items)

    def test_analise_items_cite_norms(self, qapp):
        """v0.92: cada item do menu Análise referencia uma norma
        (IEC 60909, NBR 17227, IEEE 242, etc) para reforçar
        rastreabilidade."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        _action, analise = self._find_menu(mw, "Análise")
        assert analise is not None
        items = [act.text() for act in analise.actions() if act.text()]
        joined = " ".join(items)
        # Pelo menos 4 das normas principais aparecem nos rótulos
        norms_present = sum(
            1 for n in ["IEC 60909", "NBR 17227", "IEEE 1584",
                        "IEEE 242", "IEEE 399", "IEEE 141"]
            if n in joined
        )
        assert norms_present >= 4, (
            f"Esperava ≥4 normas referenciadas, achei {norms_present}: "
            f"{items}"
        )

    def test_ferramentas_does_not_have_atp_submenu(self, qapp):
        """v0.92.1: integração ATP foi DESVINCULADA — submenu
        'ATP / EMTP' NÃO deve existir mais em Ferramentas."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        _action, ferramentas = self._find_menu(mw, "Ferramentas")
        assert ferramentas is not None
        items = [act.text() for act in ferramentas.actions()]
        # Nenhum item deve mencionar ATP ou EMTP
        atp_items = [t for t in items if "ATP" in t or "EMTP" in t]
        assert not atp_items, (
            f"Ferramentas ainda tem itens ATP: {atp_items}. "
            f"Em v0.92.1 a integração foi removida."
        )

    def test_ferramentas_keeps_claude_api(self, qapp):
        """v0.92.1: Claude API permanece em Ferramentas (não é
        ATP-related, é integração de IA neutra)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        _action, ferramentas = self._find_menu(mw, "Ferramentas")
        assert ferramentas is not None
        items = [act.text() for act in ferramentas.actions()]
        joined = " ".join(items)
        assert (
            "Claude" in joined or "API" in joined
        ), f"Configurar API Key Claude ausente: {items}"

    def test_no_run_atp_in_toolbar(self, qapp):
        """v0.92.1: toolbar principal não tem mais 'Run ATP'."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        tb = mw._main_toolbar
        labels = [act.text() for act in tb.actions()]
        joined = " ".join(labels)
        assert "Run ATP" not in joined, (
            f"Toolbar ainda tem 'Run ATP': {labels}"
        )

    def test_no_atp_tabs_visible(self, qapp):
        """v0.92.1: tabs ATP (Texto bruto, Diferenças, Resultados,
        Formas de onda, Comparar, Esquemático legacy, Topologia)
        foram retirados da UI principal."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        tab_titles = [
            mw.tabs.tabText(i) for i in range(mw.tabs.count())
        ]
        forbidden = [
            "Texto bruto", "Diferenças", "Resultados",
            "Formas de onda", "Comparar", "Esquemático (legacy)",
            "Topologia",
        ]
        present = [t for t in forbidden if t in tab_titles]
        assert not present, (
            f"Tabs ATP-only ainda visíveis: {present}. "
            f"Tabs atuais: {tab_titles}"
        )

    def test_canvas_is_default_tab(self, qapp):
        """v0.92.1: 'Esquemático Visual' é a aba inicial — canvas
        é o foco do produto."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        idx = mw.tabs.currentIndex()
        title = mw.tabs.tabText(idx)
        assert "Esquemático" in title, (
            f"Tab default é {title!r}, esperava 'Esquemático Visual'"
        )


# ---------------------------------------------------------------------------
# Welcome dialog repositioning
# ---------------------------------------------------------------------------


class TestWelcomeDialogRepositioning:

    def test_welcome_has_analysis_cards(self, qapp):
        """v0.92: welcome dialog mostra _AnalysisCard
        (especialização clara do produto). v0.93.0:
        adicionado card 'Saturação de TC' (6 cards total)."""
        from app.gui.welcome_dialog import WelcomeDialog, _AnalysisCard
        dlg = WelcomeDialog()
        cards = dlg.findChildren(_AnalysisCard)
        # v0.93.0: 6 cards (5 originais + saturação de TC)
        assert len(cards) >= 5, (
            f"Esperava ≥5 análises destacadas; achei {len(cards)}"
        )

    def test_welcome_mentions_audit_trail(self, qapp):
        """v0.92: welcome menciona explicitamente audit trail /
        ISO 9001 / NR-10 (auditabilidade é o diferencial)."""
        from PySide6.QtWidgets import QLabel
        from app.gui.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog()
        all_text = " ".join(
            lbl.text() for lbl in dlg.findChildren(QLabel)
        )
        # Pelo menos um destes três deve estar
        keywords = ["audit", "ISO 9001", "NR-10", "auditá", "auditav"]
        present = [k for k in keywords if k.lower() in all_text.lower()]
        assert present, (
            f"Welcome não menciona auditabilidade. Keywords procuradas: "
            f"{keywords}. Texto: {all_text[:300]!r}"
        )

    def test_welcome_does_not_offer_atp_open(self, qapp):
        """v0.92.1: card 'Abrir caso ATP' foi REMOVIDO — não
        deve haver descrição mencionando 'caso ATP'."""
        from PySide6.QtWidgets import QLabel
        from app.gui.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog()
        all_text = " ".join(
            lbl.text() for lbl in dlg.findChildren(QLabel)
        )
        # ATP do branding "Olivas ATP Studio" pode estar, mas
        # não deve haver "Abrir caso ATP" / "Importar caso ATP".
        forbidden = [
            "Abrir caso ATP", "Importar caso ATP",
            "tooling secundário", "ATP/EMTP existente",
        ]
        present = [s for s in forbidden if s in all_text]
        assert not present, (
            f"Welcome ainda oferece ATP: {present}"
        )

    def test_welcome_lists_5_norms(self, qapp):
        """v0.92: welcome lista as 5 normas principais
        (IEC 60909, IEEE 399, IEEE 242, NBR 17227, IEEE 141)."""
        from PySide6.QtWidgets import QLabel
        from app.gui.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog()
        all_text = " ".join(
            lbl.text() for lbl in dlg.findChildren(QLabel)
        )
        norms = ["IEC 60909", "IEEE 399", "IEEE 242",
                 "NBR 17227", "IEEE 141"]
        missing = [n for n in norms if n not in all_text]
        assert not missing, (
            f"Welcome não lista todas as 5 normas. Faltam: {missing}"
        )
