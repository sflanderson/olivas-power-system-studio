"""
app.preprocessor.vcb_model_emitter — emissão do bloco /MODELS + USE
para o modelo estatístico de reignição do VCB/VCB3.

Arquitetura (v0.22.1):

* Template estático ``atp_templates/vcb_reignition.mod`` — implementa
  o algoritmo CIGRE WG A3.26 em ATP MODELS. Carregado uma vez em
  memória via :func:`load_reignition_template`.

* Funções de emissão:
  - :func:`vcb_needs_model` — decide se o componente precisa do MODEL
    (tem parâmetros de reignição configurados, não-default).
  - :func:`build_use_block` — constrói as linhas de ``USE ... ENDUSE``
    para UMA instância (uma fase ou o VCB monofásico).
  - :func:`build_models_section` — monta a seção ``/MODELS`` completa
    (``MODEL vcb_reignition`` + todos os ``USE`` necessários) para
    inserir em ``AtpProject.raw_lines``.

Limitação v0.22.1:
    O wiring TACS (MEASURING branch para obter ``i_branch``, SOURCE
    TACS para propagar ``switch_cmd`` ao TYPE-13) é manual. O MODEL
    é emitido com inputs/outputs DECLARADOS mas não conectados —
    o usuário precisa adicionar as linhas TACS no editor de texto.

    Automação completa: v0.22.2.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable

from app.preprocessor.models import PpComponent


# ---------------------------------------------------------------------------
# Template: carrega uma vez, cache em memória
# ---------------------------------------------------------------------------


_TEMPLATE_PATH: Path = (
    Path(__file__).resolve().parent / "atp_templates" / "vcb_reignition.mod"
)


@lru_cache(maxsize=1)
def load_reignition_template() -> str:
    """
    Retorna o texto completo do template ``vcb_reignition.mod``.

    Lazy-loaded + cacheado; threadsafe via functools.lru_cache. Pode
    ser invalidado com ``load_reignition_template.cache_clear()`` em
    testes que reescrevem o template.
    """
    if not _TEMPLATE_PATH.is_file():
        raise FileNotFoundError(
            f"Template VCB MODELS não encontrado: {_TEMPLATE_PATH}"
        )
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Constantes do layout de properties VCB/VCB3
# ---------------------------------------------------------------------------


# VCB 1φ: properties[0..9] → (T_open, T_close, I_chop, σ, di/dt, d(di/dt),
#                              k_dielec, U0, T_bounce, Seed)
# VCB 3φ: properties[0..5]  → T_open/T_close × 3 fases
#         properties[6..13] → 8 params de reignição (compartilhados)

VCB_REIGNITION_PROPS: tuple[tuple[str, int], ...] = (
    ("I_chop_mean",  2),
    ("I_chop_sigma", 3),
    ("didt_crit_0",  4),
    ("didt_sigma",   5),
    ("k_dielec",     6),
    ("U0_dielec",    7),
    ("T_bounce",     8),
    ("Seed",         9),
)
"""Mapping ``(nome_no_MODEL, índice_em_comp.properties)`` para VCB 1φ."""

VCB3_REIGNITION_PROPS: tuple[tuple[str, int], ...] = (
    ("I_chop_mean",  6),
    ("I_chop_sigma", 7),
    ("didt_crit_0",  8),
    ("didt_sigma",   9),
    ("k_dielec",     10),
    ("U0_dielec",    11),
    ("T_bounce",     12),
    ("Seed",         13),
)
"""Mapping ``(nome_no_MODEL, índice_em_comp.properties)`` para VCB 3φ."""


# Defaults de cada parâmetro de reignição (espelham CIGRE WG A3.26).
# Se o usuário deixa TODOS iguais a esses defaults, consideramos que
# ele NÃO pediu reignição — omite o MODEL (preserva compat com a
# emissão TYPE-13 simples).
VCB_REIGNITION_DEFAULTS: dict[str, str] = {
    "I_chop_mean":  "5.0",
    "I_chop_sigma": "1.0",
    "didt_crit_0":  "16.0",
    "didt_sigma":   "0.034",
    "k_dielec":     "17.0",
    "U0_dielec":    "690.0",
    "T_bounce":     "5e-4",
    "Seed":         "1",
}


def _get_prop_value(comp: PpComponent, index: int, default: str = "") -> str:
    """Lê a string bruta da property de índice ``index`` do componente."""
    raw = comp.get(index, default) or default
    return str(raw).strip()


def vcb_needs_model(comp: PpComponent) -> bool:
    """
    True se o componente VCB/VCB3 tem parâmetros de reignição que
    desviam dos defaults ou estão vazios.

    Racional: se o usuário deixou todos os defaults do schema, ele
    provavelmente quer apenas a chave simples TYPE-13 (comportamento
    legado v0.21.x). Se CUSTOMIZOU algum parâmetro (ex: I_chop = 8 A
    para simular câmara mais robusta), ele explicitamente ativou a
    reignição — emitimos o MODEL.
    """
    if comp.type == "VCB":
        props_layout = VCB_REIGNITION_PROPS
    elif comp.type == "VCB3":
        props_layout = VCB3_REIGNITION_PROPS
    else:
        return False

    for model_name, idx in props_layout:
        val = _get_prop_value(comp, idx)
        default = VCB_REIGNITION_DEFAULTS[model_name]
        if not val:
            # Vazio = não customizado. Continua checando os outros.
            continue
        try:
            # Compara numericamente para tolerar "5.0" vs "5".
            if abs(float(val) - float(default)) > 1e-9:
                return True
        except (TypeError, ValueError):
            # Valor não-numérico diferente do default: assumimos que é
            # customização intencional.
            if val != default:
                return True
    return False


# ---------------------------------------------------------------------------
# Emissão do bloco USE
# ---------------------------------------------------------------------------


def build_use_block(
    comp: PpComponent,
    instance_name: str,
    t_open_value: str,
    *,
    phase: str | None = None,
) -> list[str]:
    """
    Constrói o bloco ``USE vcb_reignition AS <instance> ... ENDUSE``
    para uma instância específica.

    Parameters
    ----------
    comp:
        O PpComponent VCB ou VCB3 de origem (para ler as properties).
    instance_name:
        Nome único do USE (ex: ``DJ1`` para VCB 1φ, ``DJ1_A`` para
        fase A de VCB3).
    t_open_value:
        Valor de T_open desta instância. Para VCB é props[0]; para
        VCB3 varia por fase (props[0]/[2]/[4]).
    phase:
        "A", "B" ou "C" para VCB3; None para VCB 1φ.

    Returns
    -------
    list[str]
        Linhas do bloco USE...ENDUSE, incluindo comentários.
    """
    if comp.type == "VCB":
        props_layout = VCB_REIGNITION_PROPS
        header_comment = "-- VCB 1φ: reignição estatística CIGRE WG A3.26"
    elif comp.type == "VCB3":
        props_layout = VCB3_REIGNITION_PROPS
        header_comment = (
            f"-- VCB 3φ fase {phase}: reignição compartilhada pelo pólo"
        )
    else:
        raise ValueError(
            f"build_use_block espera VCB ou VCB3, recebeu {comp.type!r}"
        )

    lines: list[str] = []
    lines.append(header_comment)
    lines.append(f"USE vcb_reignition AS {instance_name}")
    # INPUT: usa os MESMOS nomes que build_vcb_tacs_wiring
    # emite (v0.28.4-PRO followup blocker #2).
    i_name, v_name = measurement_node_names(instance_name)
    lines.append("INPUT")
    lines.append(f"  i_branch := {i_name}")
    lines.append(f"  v_branch := {v_name}")
    # DATA: parâmetros de reignição + T_open.
    lines.append("DATA")
    lines.append(f"  T_open := {t_open_value}")
    for model_name, idx in props_layout:
        val = _get_prop_value(comp, idx)
        if not val:
            val = VCB_REIGNITION_DEFAULTS[model_name]
        lines.append(f"  {model_name} := {val}")
    # OUTPUT: exposto para pós-processamento. Wiring real → v0.22.2.
    lines.append("OUTPUT")
    lines.append(f"  SWCMD_{instance_name} := switch_cmd")
    lines.append(f"  REIGN_{instance_name} := reign_count")
    lines.append("ENDUSE")
    return lines


# ---------------------------------------------------------------------------
# v0.28.4-PRO Onda 4.6: MEASURING + TACS SOURCE auto-wire
# ---------------------------------------------------------------------------


def build_vcb_tacs_wiring(
    comp: PpComponent,
    instance_name: str,
    branch_node1: str,
    branch_node2: str,
    *,
    phase: str | None = None,
) -> list[str]:
    """
    v0.28.4-PRO Onda 4.6: emite TACS MEASURING + SOURCE blocks
    necessários para conectar inputs/outputs do USE vcb_reignition.

    Antes (v0.22.1): MODEL emitido com inputs declarados mas
    NÃO conectados — usuário precisava editar .atp manualmente.

    Agora: emite os 2 cards TACS auxiliares:

    1. **TACS-90** (measuring branch current): mede ``i_branch``
       da chave VCB e expõe sob nome ``TACS_I_<instance_name>``
       que o MODEL consume como INPUT.

    2. **TACS-91** (measuring branch voltage): mede ``v_branch``
       e expõe sob ``TACS_V_<instance_name>``.

    Os outputs ``SWCMD_<instance>`` (switch command) e
    ``REIGN_<instance>`` (reign counter) ficam disponíveis para
    quem precisar (gating de outras chaves, contadores, etc.).

    Parameters
    ----------
    comp:
        Componente VCB/VCB3 original.
    instance_name:
        Nome único do USE (ex: "DJ1", "DJ1_A").
    branch_node1, branch_node2:
        Nós da chave (entrada e saída).
    phase:
        "A"/"B"/"C" para VCB3; None para VCB 1φ.

    Returns
    -------
    list[str]
        Linhas TACS para inserir antes do MODELS USE.

    Notes
    -----
    Implementa a estratégia comum em ATP-EMTP: dispositivos
    TACS de medição (90/91) com nós de saída nomeados, depois
    USE referencia esses nomes nos INPUTs do MODEL.
    """
    from app.preprocessor.atp_format import fmt_node, fmt_num
    label = f" fase {phase}" if phase else ""
    lines: list[str] = []
    lines.append(
        f"C v0.28.4-PRO: TACS wiring auto-emitted "
        f"para VCB {instance_name}{label}"
    )

    # v0.28.4-PRO followup (code-review blocker #2): nomes
    # de medição únicos por instância. Antes era ``[:6]`` cego,
    # gerando "TACS_I"/"TACS_V" idêntico para TODOS os VCBs
    # (colisão silenciosa em multi-VCB).
    # Estratégia: usa as últimas 4 chars do instance_name como
    # sufixo (mais distinto que prefixo para nomes "DJ1", "DJ2"...)
    # com prefixo curto "I" / "V".
    suffix = (instance_name or "X")[-4:].ljust(4, "_")
    name_i = ("I_" + suffix)[:6]
    name_v = ("V_" + suffix)[:6]

    # TACS-90: branch current measurement
    # Format: "90<NAME6><FROM6><TO6>" → 18 chars + comentário
    lines.append(
        f"90{fmt_node(name_i)}{fmt_node(branch_node1)}"
        f"{fmt_node(branch_node2)}"
        f"   ; medição i_branch para VCB MODEL ({instance_name})"
    )

    # TACS-91: branch voltage measurement (across switch)
    lines.append(
        f"91{fmt_node(name_v)}{fmt_node(branch_node1)}"
        f"{fmt_node(branch_node2)}"
        f"   ; medição v_branch para VCB MODEL ({instance_name})"
    )
    return lines


def measurement_node_names(instance_name: str) -> tuple[str, str]:
    """
    v0.28.4-PRO followup: helper para que ``build_use_block``
    e os clientes do MODEL referenciem os MESMOS nomes de
    medição que ``build_vcb_tacs_wiring`` emite.

    Retorna ``(i_node_name, v_node_name)`` (≤ 6 chars cada).
    """
    suffix = (instance_name or "X")[-4:].ljust(4, "_")
    return (
        ("I_" + suffix)[:6],
        ("V_" + suffix)[:6],
    )


# ---------------------------------------------------------------------------
# Emissão da seção /MODELS completa
# ---------------------------------------------------------------------------


def build_models_section(
    components: Iterable[PpComponent],
) -> list[str]:
    """
    Monta a seção ``/MODELS`` completa para inserir em
    ``AtpProject.raw_lines``.

    Se nenhum VCB/VCB3 precisa de reignição, retorna lista VAZIA
    (caller NÃO deve inserir a seção no output).

    Structure:
        /MODELS
        <MODEL vcb_reignition ... ENDMODEL>   -- uma única vez
        <USE DJ1 ... ENDUSE>                  -- uma por VCB 1φ
        <USE DJ2_A ... ENDUSE>                -- uma por fase de VCB3
        <USE DJ2_B ... ENDUSE>
        <USE DJ2_C ... ENDUSE>
        ...

    Parameters
    ----------
    components:
        Iterable de PpComponents. A função filtra só os VCB/VCB3 que
        satisfazem :func:`vcb_needs_model`.

    Returns
    -------
    list[str]
        Linhas prontas para inserir (sem BLANK no fim — o caller
        controla separadores). Se nenhuma instância, lista vazia.
    """
    relevant = [
        c for c in components
        if c.type in ("VCB", "VCB3") and vcb_needs_model(c)
    ]
    if not relevant:
        return []

    lines: list[str] = ["/MODELS"]

    # MODEL definition — uma única vez, mesmo com múltiplos USE.
    template = load_reignition_template()
    lines.extend(template.splitlines())
    lines.append("")  # linha em branco separadora

    # USE blocks — um por instância (fase, no caso de VCB3).
    for comp in relevant:
        name = (comp.name or comp.type).strip() or comp.type
        if comp.type == "VCB":
            t_open = _get_prop_value(comp, 0, "0")
            lines.extend(build_use_block(comp, name, t_open))
            lines.append("")
        elif comp.type == "VCB3":
            # VCB3: 3 USE blocks, um por fase, com T_open independente.
            for phase, idx in (("A", 0), ("B", 2), ("C", 4)):
                t_open = _get_prop_value(comp, idx, "0.05")
                instance_name = f"{name}_{phase}"
                lines.extend(
                    build_use_block(
                        comp, instance_name, t_open, phase=phase,
                    )
                )
                lines.append("")

    return lines
