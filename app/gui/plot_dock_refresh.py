"""
app.gui.plot_dock_refresh — Helper para refresh de plot docks
após estudos rodarem (v1.7.5).

Endereça issue do user gate v2.0.0/v2.0.2: "visualizar gráficos
ainda apresenta problemas de população de resultados".

v2.0.1 (Sprint C) já implementou `populate_from_cache()` em cada
dock + chamada em `_ensure_plot_dock`. Mas isso só popula **na
primeira abertura**. Se o dock já está aberto e o usuário roda
F5 (Power Flow), a dock NÃO é atualizada — fica com dados antigos.

v1.7.5 fecha o gap: após cada estudo (PF/SC/Coord/MC) rodar com
sucesso em `_dispatch_analysis`, chama `refresh_open_plot_docks()`
para repopular **todos os docks que estão abertos** (no-op para
docks fechados).

API
====

::

    from app.gui.plot_dock_refresh import refresh_open_plot_docks

    refresh_open_plot_docks(self)   # self = MainWindow instance

Anti-crash defensivo
=====================

* Cada dock acessado via getattr (None se atributo ausente)
* hasattr check antes de chamar populate_from_cache
* try/except envolve o populate (cache vazio → mantém empty state)
"""

from __future__ import annotations

from typing import Any


# Atributos de cache de docks no MainWindow (paridade
# `_ensure_plot_dock`)
_DOCK_ATTRS = (
    "_plot_dock_pf_voltage",
    "_plot_dock_sc_pie",
    "_plot_dock_tcc_overlay",
    "_plot_dock_mc_hist",
)


def refresh_open_plot_docks(main_window: Any) -> int:
    """
    Atualiza todos os plot docks abertos a partir do study cache.

    Parameters
    ----------
    main_window:
        Instância de :class:`MainWindow` (ou compatível) com
        atributos `_plot_dock_*` e método `_study_cache()`.

    Returns
    -------
    int
        Número de docks atualizados (0 se nenhum estava aberto).
    """
    # Obtém cache (pode falhar se MainWindow ainda inicializando)
    try:
        cache = main_window._study_cache()
    except Exception:
        return 0

    refreshed = 0
    for attr in _DOCK_ATTRS:
        dock = getattr(main_window, attr, None)
        if dock is None:
            continue
        if not hasattr(dock, "populate_from_cache"):
            continue
        try:
            dock.populate_from_cache(cache)
            refreshed += 1
        except Exception:
            # Anti-crash: cache vazio ou dock em estado ruim
            # → mantém estado atual (não derruba o pipeline)
            continue
    return refreshed
