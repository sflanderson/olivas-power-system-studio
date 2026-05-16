"""
app.preprocessor.catalog — catálogo de tipos de componente Qucs.

Esta versão (sprint v0.21.0) é um *stub* mínimo. Apenas mapeia
códigos de tipo Qucs (``"R"``, ``"L"``, ``"Vdc"``, ...) para uma
descrição humana e um indicador de "tem equivalente ATP?".

A versão completa, com schema de propriedades por tipo, vem na
sprint v0.21.1 (`bridge_to_atp.py` precisa do schema para extrair
R/L/C corretamente). A v0.21.2 adiciona dados de renderização.

A partir de **v0.21.8.b**, os getters ``get()``, ``all_entries()``,
``by_category()`` e ``is_atp_supported()`` consultam o
:func:`app.preprocessor.spec.get_default_registry` primeiro. Códigos
sem ``.ocomp`` correspondente caem no fallback ``_ENTRIES`` legado.
Isso permite migração incremental — cada ``.ocomp`` novo que vira
fonte única de verdade para seu código.

Foco
----
Componentes de **potência** e **eletrônica de potência** (não
microeletrônica RF/HF). Componentes Qucs só-RF (microstrip,
S-parameters, etc.) ficam marcados como `atp_supported=False`.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.preprocessor.spec import ComponentSpec, get_default_registry


@dataclass(frozen=True)
class CatalogEntry:
    """
    Metadata mínima para um tipo de componente.

    Attributes
    ----------
    code:
        Código curto Qucs (ex: ``"R"``).
    label_pt:
        Nome humano em português.
    category:
        Categoria para agrupamento na paleta visual futura.
    atp_supported:
        Se True, há (ou haverá) tradução para um elemento ATP
        nativo. False = componente puramente Qucs/RF/HF que será
        rejeitado na bridge `to_atp` da v0.21.1.
    """

    code: str
    label_pt: str
    category: str
    atp_supported: bool


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------
# A ordem aqui é a ordem em que os componentes aparecerão na
# paleta da v0.21.3 (passivos primeiro, fontes depois, etc.).
# ---------------------------------------------------------------------------


_ENTRIES: tuple[CatalogEntry, ...] = (
    # Passivos lineares
    CatalogEntry("R",       "Resistor",                  "passive",   True),
    CatalogEntry("L",       "Indutor",                   "passive",   True),
    CatalogEntry("C",       "Capacitor",                 "passive",   True),
    CatalogEntry("GND",     "Terra",                     "passive",   True),
    # Acoplados
    CatalogEntry("Tr",      "Transformador 2-enrol.",    "coupled",   True),
    CatalogEntry("sTr",     "Transformador simples",     "coupled",   True),
    CatalogEntry("Tr3",     "Transformador 3-enrol.",    "coupled",   True),
    CatalogEntry("MUT",     "Indutores acoplados (M)",   "coupled",   True),
    # Linhas
    CatalogEntry("TLIN",    "Linha PI nominal",          "line",      True),
    CatalogEntry("BERG",    "Linha Bergeron (distrib.)", "line",      True),
    CatalogEntry("JMARTI",  "Linha J. Marti Z(omega)",   "line",      True),
    # Fontes
    CatalogEntry("Vdc",     "Fonte de tensão DC",        "source",    True),
    CatalogEntry("Vac",     "Fonte de tensão AC",        "source",    True),
    CatalogEntry("Idc",     "Fonte de corrente DC",      "source",    True),
    CatalogEntry("Iac",     "Fonte de corrente AC",      "source",    True),
    CatalogEntry("Vrect",   "Fonte de tensão rampa",     "source",    True),
    CatalogEntry("Vsurge",  "Surge 1.2/50, 8/20",        "source",    True),
    # Chaves
    CatalogEntry("SwIdeal", "Chave ideal (Topen/Tclose)", "switch",   True),
    CatalogEntry("Relais",  "Chave controlada",          "switch",    True),
    CatalogEntry("SwTACS",  "Chave controlada por TACS", "switch",    True),
    CatalogEntry("VCB",     "Disjuntor a vácuo (VCB) 1φ","switch",    True),
    CatalogEntry("VCB3",    "Disjuntor a vácuo (VCB) 3φ","switch",    True),
    # Eletrônica de potência
    CatalogEntry("Diode",   "Diodo de potência",         "power_el",  True),
    CatalogEntry("Thyr",    "Tiristor",                  "power_el",  True),
    CatalogEntry("GTO",     "GTO",                       "power_el",  True),
    CatalogEntry("IGBT",    "IGBT",                      "power_el",  True),
    CatalogEntry("MOSFET",  "MOSFET de potência",        "power_el",  True),
    # Não-lineares
    CatalogEntry("ZnO",     "Para-raios ZnO",            "nonlinear", True),
    CatalogEntry("RNL",     "Resistor não-linear R(I)",  "nonlinear", True),
    CatalogEntry("LNL",     "Indutor saturável L(i)",    "nonlinear", True),
    # Medição
    CatalogEntry("VProbe",  "Voltímetro (probe)",        "meter",     True),
    CatalogEntry("IProbe",  "Amperímetro (probe)",       "meter",     True),
    # Controle / TACS / MODELS
    CatalogEntry("TACS",    "Fonte TACS",                "control",   True),
    CatalogEntry("MODEL",   "Bloco MODEL (USE)",         "control",   True),
    CatalogEntry("Eqn",     "Bloco de equações",         "control",   False),
    # TACS prebuilt blocks (v0.26.5)
    CatalogEntry("PID",        "Controlador PID",        "control",   True),
    CatalogEntry("Integrator", "Integrador (K/s)",       "control",   True),
    CatalogEntry("LowPass",    "Passa-baixa 1ª ordem",   "control",   True),
    CatalogEntry("Limiter",    "Limitador hard",         "control",   True),
    CatalogEntry("TSum",       "Somador ponderado",      "control",   True),
    # Máquinas elétricas (v0.27.0)
    CatalogEntry("SM",         "Máquina síncrona SM59/58", "machine", True),
    # Hybrid Transformer XFMR (v0.27.5) — Mork model
    CatalogEntry("XFMR",       "Transformador Hybrid (XFMR)", "coupled", True),
    # Barramentos / Painéis (v0.27.7) — estilo SKM PTW
    CatalogEntry("BUS",        "Barramento / Painel",         "passive", True),
    # Motores (v0.27.7.9) — IM/MS para SC contribution
    CatalogEntry("MOTOR",      "Motor (IM/MS)",               "machine", True),
    # Diretivas de simulação Qucs (não vão para ATP, são metadata)
    CatalogEntry(".TR",     "Análise transitória",       "sim",       False),
    CatalogEntry(".DC",     "Análise DC",                "sim",       False),
    CatalogEntry(".AC",     "Análise AC",                "sim",       False),
    CatalogEntry(".SW",     "Sweep paramétrico",         "sim",       False),
    CatalogEntry(".SP",     "S-parameters",              "sim",       False),
)


_BY_CODE: dict[str, CatalogEntry] = {e.code: e for e in _ENTRIES}


# ---------------------------------------------------------------------------
# Ponte registry ↔ CatalogEntry
# ---------------------------------------------------------------------------
# A partir de v0.21.8.b, o registry de ``.ocomp`` é a fonte preferida.
# Esta helper converte um ``ComponentSpec`` para ``CatalogEntry`` (shape
# legado) preservando compat bit-a-bit com o código legado.
# ---------------------------------------------------------------------------


def _entry_from_spec(spec: ComponentSpec) -> CatalogEntry:
    """Converte um ``ComponentSpec`` para ``CatalogEntry``."""
    return CatalogEntry(
        code=spec.code,
        label_pt=spec.label_pt,
        category=spec.category,
        atp_supported=spec.atp_supported,
    )


def get(code: str) -> CatalogEntry | None:
    """
    Retorna a entrada do catálogo, ou None se desconhecida.

    Registry-first (v0.21.8.b): se existe um ``.ocomp`` com este ``code``,
    deriva o CatalogEntry do spec. Caso contrário, usa o dict legado
    ``_BY_CODE``.
    """
    spec = get_default_registry().get(code)
    if spec is not None:
        return _entry_from_spec(spec)
    return _BY_CODE.get(code)


def all_entries() -> tuple[CatalogEntry, ...]:
    """
    Tupla imutável com todas as entradas, na ordem da paleta.

    Registry-first (v0.21.8.b): entradas com ``.ocomp`` são derivadas do
    spec (garantindo label/category sempre sincronizados com o arquivo
    canônico); demais entradas vêm do ``_ENTRIES`` legado.

    v1.0.1: também inclui specs do registry que NÃO estão em
    ``_ENTRIES`` (ex: CABLE, CT adicionados em v1.0.1) — assim
    novos componentes ficam visíveis na paleta sem precisar
    editar o tuple ``_ENTRIES``.
    """
    registry = get_default_registry()
    result: list[CatalogEntry] = []
    legacy_codes: set[str] = set()
    for legacy in _ENTRIES:
        legacy_codes.add(legacy.code)
        spec = registry.get(legacy.code)
        if spec is not None:
            result.append(_entry_from_spec(spec))
        else:
            result.append(legacy)
    # v1.0.1: codes do registry que não estão no legacy
    for code in registry.all_codes():
        if code not in legacy_codes:
            spec = registry.get(code)
            if spec is not None:
                result.append(_entry_from_spec(spec))
    return tuple(result)


def by_category(category: str) -> list[CatalogEntry]:
    """Filtra entradas por categoria (passive/source/switch/...)."""
    return [e for e in all_entries() if e.category == category]


def is_atp_supported(code: str) -> bool:
    """
    Conveniência para a bridge: True se o código tem tradução ATP
    prevista (ou seja, NÃO devemos rejeitar na bridge_to_atp).

    Códigos desconhecidos retornam False (conservador).

    Registry-first (v0.21.8.b): consulta ``.ocomp`` antes do legacy.
    """
    entry = get(code)
    return entry is not None and entry.atp_supported


CATEGORIES: tuple[str, ...] = (
    "passive",
    "coupled",
    "line",
    "source",
    "switch",
    "power_el",
    "nonlinear",
    "meter",
    "control",
    "sim",
    # v0.27.0 — máquinas elétricas
    "machine",
)


# ---------------------------------------------------------------------------
# Labels humanos para cada propriedade (por código de componente)
# ---------------------------------------------------------------------------
# Usado pelo `PpPropertiesPanel` para mostrar "Topen" em vez de "#1:".
# Componentes não listados aqui caem no fallback `"#{n}:"`.
#
# Ordem: o mesmo índice da lista de `PpProperty` em `PpComponent.properties`
# (e o mesmo índice do `_DEFAULT_PROPS` em `editor.py`).
# ---------------------------------------------------------------------------


_PROPERTY_LABELS: dict[str, tuple[str, ...]] = {
    # Passivos
    "R":       ("R",          "T_amb [°C]", "Modelo"),
    "L":       ("L",          "I_0",        "T_amb [°C]"),
    "C":       ("C",          "V_0",        "Polaridade"),
    # Fontes
    "Vdc":     ("Amplitude",),
    "Vac":     ("Amplitude",  "Frequência",  "Fase [°]", "Delay [s]"),
    "Idc":     ("Amplitude",),
    "Iac":     ("Amplitude",  "Frequência",  "Fase [°]", "Delay [s]"),
    "Vrect":   ("Amplitude",  "T_rampa"),
    "Vsurge":  ("Amplitude",),
    # Chaves
    "SwIdeal": ("T_close [s]", "T_open [s]"),
    "Relais":  ("T_close [s]", "T_open [s]"),
    "SwTACS":  ("Sinal TACS",),
    # VCB 1φ — chave a vácuo com modelo estatístico de reignição
    "VCB": (
        "T_open [s]",
        "T_close [s]",
        "I_chop [A]",
        "σ(I_chop) [A]",
        "di/dt_crit [A/µs]",
        "d(di/dt) [A/µs²]",
        "k_dielec [V/µs]",
        "U0_dielec [V]",
        "T_bounce [s]",
        "Seed",
    ),
    # VCB 3φ — 3 chaves com T_open/T_close independentes por fase
    # + parâmetros de reignição compartilhados
    "VCB3": (
        "T_open_A [s]",
        "T_close_A [s]",
        "T_open_B [s]",
        "T_close_B [s]",
        "T_open_C [s]",
        "T_close_C [s]",
        "I_chop [A]",
        "σ(I_chop) [A]",
        "di/dt_crit [A/µs]",
        "d(di/dt) [A/µs²]",
        "k_dielec [V/µs]",
        "U0_dielec [V]",
        "T_bounce [s]",
        "Seed",
    ),
    # Eletrônica de potência
    "Diode":   ("V_forward",  "R_on"),
    "Thyr":    ("V_forward",  "R_on"),
    "GTO":     ("V_forward",  "R_on"),
    "IGBT":    ("V_gate_on",  "R_on"),
    "MOSFET":  ("R_DSon",     "R_on"),
    # Acoplados
    "Tr":      ("Razão",      "L_mag"),
    "sTr":     ("Razão",      "L_mag"),
    "Tr3":     ("Razão",      "L_mag"),
    "MUT":     ("L1",         "L2",         "k"),
    # Linhas
    "TLIN":    ("Comprimento", "R/km"),
    "BERG":    ("Comprimento", "Z_char"),
    "JMARTI":  ("Arquivo .pch",),
    # Não-lineares
    "ZnO":     ("V_ref",),
    "RNL":     ("Tabela R(I)",),
    "LNL":     ("Tabela L(i)",),
    # Controle
    "TACS":    ("Expressão",),
    "MODEL":   ("Arquivo .mod",),
}


def property_labels(code: str) -> tuple[str, ...]:
    """
    Retorna a tupla de labels humanos para cada propriedade do
    componente ``code``.

    Se o código não tem labels definidos, retorna tupla vazia — o
    caller deve cair no fallback genérico ``f"#{idx + 1}:"``.
    """
    return _PROPERTY_LABELS.get(code, ())
