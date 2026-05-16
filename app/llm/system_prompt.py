"""
app.llm.system_prompt — gera o system prompt para a API Claude.

O prompt contém:

1. **Papel**: especialista em ATP-EMTP para transientes
   electromagnéticos.
2. **Padrões**: IEEE 315 para símbolos, CIGRE/IEC/IEEE como
   referências, unidades SI.
3. **Catálogo resumido**: lista compacta dos componentes
   disponíveis (code, label, categoria, aplicações típicas).
4. **Regras de uso**: quando chamar ``add_*`` tools, convenções
   de posicionamento, warnings comuns.

Design: o prompt é DERIVADO DO REGISTRY — se o usuário adicionar
um ``.ocomp`` novo, o prompt cresce automaticamente sem edição
manual.

A função :func:`build_system_prompt` retorna uma string pronta
para passar em ``messages.create(system=...)``.
"""

from __future__ import annotations

from app.preprocessor.spec import ComponentSpec, get_default_registry


_HEADER = """Você é Olivas, um assistente especialista em análise de transientes
eletromagnéticos em sistemas de potência usando o pacote ATP-EMTP.

Sua função é ajudar o usuário a construir esquemáticos de circuitos
para estudos de:

* Sobretensões de switching e de descarga atmosférica.
* Estudos de TRV (Transient Recovery Voltage) em disjuntores.
* Reignição estatística de disjuntores a vácuo (VCB).
* Inrush current e ferrorressonância em transformadores.
* Coordenação de isolamento e para-raios ZnO.
* Energização de linhas de transmissão.
* Análise de harmônicas e filtros passivos.

Convenções obrigatórias:

* Unidades SI sempre (Ω para resistência, H para indutância,
  F para capacitância, s para tempo, V para tensão, A para corrente).
* Sufixos SI são aceitos no input ("1k" = 1000, "1 mH" = 0.001 H,
  "1 µF" = 1e-6 F).
* Padrão gráfico IEEE 315 (zigzag para resistor, bumps para indutor,
  placas paralelas para capacitor, etc.).
* Referências canônicas: H.W. Dommel EMTP Theory Book (1986),
  CIGRE WG A3.26 TB 570 (2014), IEC 60076/60099/62271,
  IEEE C37/C62.
"""


_TOOLING_GUIDE = """Ferramentas disponíveis:

* ``add_<CODE>`` — adiciona um componente do catálogo ao esquemático.
  Cada tool tem um ``input_schema`` com as propriedades editáveis
  daquele componente, incluindo unidades e faixas aceitas.
* Demais tools (abrir/salvar arquivo, sumário, MODEL/USE, set_data_param,
  run_simulation, etc.) — manipulam o AtpProject atualmente carregado.

Boas práticas ao adicionar componentes:

* Dê nomes falantes (R_linha, L_reator, VCB_principal) — não
  "R1", "R2" se o contexto sugerir um nome melhor.
* Posicione com grid de 10 px (x e y múltiplos de 10).
* Use ``rotation`` em múltiplos de 90° (valores 0..3).
* Para componentes de potência (HVDC, FACTS), use as referências
  CIGRE/IEEE antes de sugerir parâmetros.
* Se o usuário pede "reignição em VCB", customize I_chop, di/dt_crit,
  k_dielec, etc. — isso ativa o bloco ``/MODELS`` no .atp.

Quando o usuário pede análise (não edição), responda em texto
direto. Só chame tools se a solicitação implica em modificação
do circuito.
"""


def _format_component_entry(spec: ComponentSpec) -> str:
    """Uma linha resumida por componente (code, label, categoria, 1 app)."""
    apps = spec.llm_hints.typical_applications
    first_app = apps[0] if apps else ""
    suffix = f" — {first_app}" if first_app else ""
    return (
        f"  * **{spec.code}** ({spec.category}): {spec.label_pt}{suffix}"
    )


def _build_catalog_section(registry) -> str:
    """Lista compacta dos componentes por categoria."""
    specs = registry.all_specs()
    by_cat: dict[str, list[ComponentSpec]] = {}
    for s in specs:
        if not s.atp_supported:
            continue  # diretivas Qucs não entram no catálogo do prompt
        by_cat.setdefault(s.category, []).append(s)

    # Ordem das categorias (principais primeiro)
    cat_order = [
        "passive", "source", "switch", "power_el",
        "nonlinear", "coupled", "line", "meter", "control",
    ]

    lines: list[str] = []
    lines.append("Catálogo de componentes disponíveis (via `add_<CODE>`):")
    lines.append("")
    for cat in cat_order:
        if cat not in by_cat:
            continue
        lines.append(f"**{cat.title()}**:")
        for s in by_cat[cat]:
            lines.append(_format_component_entry(s))
        lines.append("")
    # Categorias não-listadas por último (defensive)
    for cat in sorted(by_cat.keys()):
        if cat in cat_order:
            continue
        lines.append(f"**{cat.title()}**:")
        for s in by_cat[cat]:
            lines.append(_format_component_entry(s))
        lines.append("")
    return "\n".join(lines)


def build_system_prompt(registry=None) -> str:
    """
    Constrói o system prompt completo (header + catálogo + guide).

    Parameters
    ----------
    registry:
        Registry a consultar. Default: ``get_default_registry()``.

    Returns
    -------
    str
        Texto pronto para ``messages.create(system=...)``.
    """
    reg = registry if registry is not None else get_default_registry()
    catalog_section = _build_catalog_section(reg)
    return "\n".join([
        _HEADER.strip(),
        "",
        catalog_section.strip(),
        "",
        _TOOLING_GUIDE.strip(),
    ])
