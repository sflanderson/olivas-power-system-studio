"""
app.postprocessor.audit_trail — auditability primitives para
relatórios profissionais de estudos elétricos (v0.92.2).

Filosofia
==========

**Olivas Power System Studio** (alternativa nacional a SKM
PTW / ETAP / EasyPower) gera laudos técnicos sobre:

* Curto-circuito (IEC 60909-0:2016)
* Fluxo de potência (IEEE 399 Brown Book / Stevenson §9)
* Coordenação e seletividade (IEEE 242:2001 Buff Book §15)
* Energia incidente / arc-flash (NBR 17227:2025 / IEEE 1584-2018)
* Balanço de carga (IEEE 141:1993 Red Book)

Esses laudos são utilizados em:

* Auditorias NR-10 / NR-12
* Especificação de equipamentos (compra de switchgears)
* Defesa técnica em tribunais (acidentes, incidentes)
* ISO 9001 / ISO 50001 (gestão de qualidade)
* Aprovação de projeto em concessionárias

Para serem **defensáveis e auditáveis**, devem conter:

1. **Identidade do cálculo** (qual versão do software, hash dos
   inputs, timestamp imutável).
2. **Rastreabilidade norma** (qual seção/equação aplicada).
3. **Responsabilidade técnica** (engenheiro responsável, CREA,
   data, assinatura).
4. **Limitações declaradas** (heurísticas / simplificações
   aplicadas explicitamente).

Este módulo provê primitivas para os 4 pontos acima.

API
====

* :func:`compute_input_checksum(case_dict)` — SHA256 estável
  dos inputs do caso (rebuild possível).
* :func:`format_responsibility_block(...)` — bloco
  identificação engenheiro responsável.
* :func:`citation(standard, section, equation=None)` — string
  formatada para rodapé de cada cálculo.
* :func:`format_audit_header(report_kind, ...)` — header
  completo profissional (versão, timestamp, checksum,
  responsável, limitações).

Não é fonte canônica de cálculos — apenas formatação +
hashing. Não muta inputs.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.commercial.feature_gates import Feature, requires_feature


# ---------------------------------------------------------------------------
# Citation helpers
# ---------------------------------------------------------------------------


# Catálogo de normas referenciadas no app — fonte da verdade
# para títulos completos. Acessível por chave curta.
STANDARDS_CATALOG: dict[str, str] = {
    "IEC 60909-0": "IEC 60909-0:2016 — Short-circuit currents in three-phase a.c. systems",
    "IEC 60909-1": "IEC TR 60909-1:2002 — Factors for the calculation of short-circuit currents",
    "IEEE 141":   "IEEE Std 141-1993 (R2003) — IEEE Recommended Practice for Electric Power Distribution for Industrial Plants (Red Book)",
    "IEEE 242":   "IEEE Std 242-2001 — IEEE Recommended Practice for Protection and Coordination of Industrial and Commercial Power Systems (Buff Book)",
    "IEEE 399":   "IEEE Std 399-1997 — IEEE Recommended Practice for Industrial and Commercial Power Systems Analysis (Brown Book)",
    "IEEE 1584":  "IEEE Std 1584-2018 — IEEE Guide for Performing Arc-Flash Hazard Calculations",
    "IEC 60255":  "IEC 60255-151:2009 — Measuring relays and protection equipment — Functional requirements for over/under current relays",
    "NBR 17227":  "ABNT NBR 17227:2025 — Cálculo de energia incidente e definição de roupas de proteção (NBR 17227)",
    "NBR 5410":   "ABNT NBR 5410:2008+Em.1:2024 — Instalações elétricas de baixa tensão",
    "NBR 14039":  "ABNT NBR 14039:2021 — Instalações elétricas de média tensão",
    "NBR 5419":   "ABNT NBR 5419:2015 — Proteção contra descargas atmosféricas",
    "NFPA 70E":   "NFPA 70E:2024 — Standard for Electrical Safety in the Workplace",
    "NR-10":      "NR-10 (Min. Trabalho BR) — Segurança em Instalações e Serviços em Eletricidade",
}


def citation(
    standard: str,
    section: Optional[str] = None,
    equation: Optional[str] = None,
    extra: Optional[str] = None,
) -> str:
    """
    Formata uma citação normativa compacta para rodapé de
    cálculo / linha de relatório.

    Examples
    --------

    >>> citation("IEC 60909-0", "§4.3.1", "Eq.(31)")
    'IEC 60909-0:2016 §4.3.1 Eq.(31)'

    >>> citation("NBR 17227", "§5.2.6.2", "Eq.(3-6)", "VCB cabinet")
    'ABNT NBR 17227:2025 §5.2.6.2 Eq.(3-6) (VCB cabinet)'

    >>> citation("IEEE 1584")
    'IEEE Std 1584-2018'
    """
    title = STANDARDS_CATALOG.get(standard)
    if title is None:
        # Norma não catalogada — usa o nome direto.
        head = standard
    else:
        # Prefixo curto: ex "IEC 60909-0:2016" da string longa
        head = title.split(" — ")[0]
    parts = [head]
    if section:
        parts.append(section)
    if equation:
        parts.append(equation)
    line = " ".join(parts)
    if extra:
        line += f" ({extra})"
    return line


# ---------------------------------------------------------------------------
# Input checksum — SHA256 estável
# ---------------------------------------------------------------------------


def compute_input_checksum(payload: Any) -> str:
    """
    Calcula SHA256 estável de qualquer payload serializável
    para JSON. Usado em laudos para garantir que mudanças nos
    inputs gerariam outro relatório (rastreável).

    Algoritmo:
    1. Serializa via ``_to_jsonable()`` (dataclass → dict, etc).
    2. Dump JSON com ``sort_keys=True`` (ordem estável).
    3. SHA256.

    Returns
    -------
    str
        Hex digest 64 chars. Primeiros 16 são "fingerprint
        compacto" suficiente para identificar versão.

    Examples
    --------

    >>> compute_input_checksum({"a": 1, "b": 2}) == compute_input_checksum({"b": 2, "a": 1})
    True
    """
    jsonable = _to_jsonable(payload)
    text = json.dumps(jsonable, sort_keys=True, default=str)
    h = hashlib.sha256(text.encode("utf-8"))
    return h.hexdigest()


def _to_jsonable(obj: Any) -> Any:
    """
    Converte obj para algo JSON-serializável recursivamente.

    Suporte:
    * primitivos (passthrough)
    * dataclasses → dict via dataclasses.asdict
    * dict → recurse values
    * list/tuple → recurse items
    * outros → repr
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        try:
            return _to_jsonable(dataclasses.asdict(obj))
        except (TypeError, RecursionError):
            return repr(obj)
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted([_to_jsonable(x) for x in obj], key=str)
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    # Fallback genérico — use repr
    return repr(obj)


# ---------------------------------------------------------------------------
# Audit header (block to put at top of HTML/PDF reports)
# ---------------------------------------------------------------------------


@dataclass
class AuditHeader:
    """
    Bloco de identificação profissional para laudo técnico.

    Compatível com:
    * NBR ISO 9001 (rastreabilidade documentos)
    * NR-10 (responsabilidade técnica)
    * Tribunais (defesa de cálculo)
    """

    report_kind: str            # "Curto-circuito", "Arc-Flash", etc
    software_name: str          # "Olivas Power System Studio"
    software_version: str       # "0.92.2"
    timestamp_iso: str          # ISO 8601
    input_checksum: str         # SHA256
    standards_applied: list[str]   # ex ["IEC 60909-0", "NBR 17227"]
    responsible_engineer: str = ""    # opcional, preenchido por usuário
    crea_number: str = ""             # opcional
    art_number: str = ""              # opcional (Anotação de Responsabilidade Técnica)
    notes: str = ""                   # observações livres

    def to_text(self) -> str:
        """Bloco texto plano — usado em PDF cover ou HTML <pre>."""
        lines = [
            "═" * 72,
            f"  RELATÓRIO TÉCNICO — {self.report_kind}",
            "═" * 72,
            f"  Software:           {self.software_name} v{self.software_version}",
            f"  Gerado em:          {self.timestamp_iso}",
            f"  Checksum (inputs):  SHA256:{self.input_checksum[:16]}…",
            "  Normas aplicadas:",
        ]
        for std in self.standards_applied:
            full_title = STANDARDS_CATALOG.get(std, std)
            lines.append(f"    • {full_title}")
        lines.append("")
        lines.append(
            "  Responsável técnico: " +
            (self.responsible_engineer or "____________________________________"),
        )
        lines.append(
            "  CREA / Registro:     " +
            (self.crea_number or "____________________________________"),
        )
        lines.append(
            "  ART (opcional):      " +
            (self.art_number or "____________________________________"),
        )
        lines.append(
            "  Assinatura:          ____________________________________",
        )
        if self.notes:
            lines.append("")
            lines.append("  Observações:")
            for ln in self.notes.splitlines():
                lines.append(f"    {ln}")
        lines.append("═" * 72)
        return "\n".join(lines)

    def to_html(self) -> str:
        """Bloco HTML — para inclusão em report_html.py."""
        std_items = "".join(
            f"<li>{STANDARDS_CATALOG.get(s, s)}</li>"
            for s in self.standards_applied
        )
        return (
            "<div class='audit-header'>"
            f"<h2 class='audit-title'>RELATÓRIO TÉCNICO — {self.report_kind}</h2>"
            "<table class='audit-meta'>"
            f"<tr><th>Software</th>"
            f"<td>{self.software_name} v{self.software_version}</td></tr>"
            f"<tr><th>Gerado em</th><td>{self.timestamp_iso}</td></tr>"
            f"<tr><th>Checksum (inputs)</th>"
            f"<td><code>SHA256:{self.input_checksum[:16]}…</code></td></tr>"
            f"<tr><th>Normas aplicadas</th>"
            f"<td><ul>{std_items}</ul></td></tr>"
            f"<tr><th>Responsável técnico</th>"
            f"<td>{self.responsible_engineer or '<em>(a preencher)</em>'}</td></tr>"
            f"<tr><th>CREA / Registro</th>"
            f"<td>{self.crea_number or '<em>(a preencher)</em>'}</td></tr>"
            f"<tr><th>ART</th>"
            f"<td>{self.art_number or '<em>(a preencher)</em>'}</td></tr>"
            "<tr><th>Assinatura</th>"
            "<td><em>(a preencher manualmente após revisão)</em></td></tr>"
            "</table>"
            + (
                f"<div class='audit-notes'><strong>Observações:</strong>"
                f"<p>{self.notes}</p></div>"
                if self.notes else ""
            )
            + "</div>"
        )


@requires_feature(Feature.AUDIT_TRAIL_SHA256)
def make_audit_header(
    report_kind: str,
    inputs: Any,
    standards_applied: list[str],
    *,
    responsible_engineer: str = "",
    crea_number: str = "",
    art_number: str = "",
    notes: str = "",
    software_name: str = "Olivas Power System Studio",
) -> AuditHeader:
    """
    Conveniência: cria :class:`AuditHeader` calculando timestamp
    + checksum dos inputs + lendo VERSION do app.
    """
    try:
        from app.core.version import VERSION
        version = VERSION
    except ImportError:
        version = "?"

    return AuditHeader(
        report_kind=report_kind,
        software_name=software_name,
        software_version=version,
        timestamp_iso=datetime.now().isoformat(timespec="seconds"),
        input_checksum=compute_input_checksum(inputs),
        standards_applied=list(standards_applied),
        responsible_engineer=responsible_engineer,
        crea_number=crea_number,
        art_number=art_number,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Limitations / disclaimers helper
# ---------------------------------------------------------------------------


# Limitações conhecidas no MVP — devem aparecer EXPLICITAMENTE
# no relatório quando a análise as toca. Catálogo vem da
# auditoria normativa (v0.92).
KNOWN_LIMITATIONS: dict[str, str] = {
    "sc_ib_far_only": (
        "Corrente de breaking Ib calculada como Ik'' "
        "(far-from-generator). Próximo a geradores síncronos "
        "Ib pode estar SUPERESTIMADO em até 30% (factor μ·q "
        "da IEC 60909 §4.6 não aplicado nesta versão)."
    ),
    "sc_method_b_kappa": (
        "Factor κ calculado por Method B (single equivalent "
        "R/X) per IEC 60909 §4.3.1.2. Para sistemas com "
        "múltiplas malhas R/X distintas, Method C "
        "(frequency-equivalent) seria mais preciso."
    ),
    "arc_flash_lv_only": (
        "Energia incidente calculada para sistemas até 15 kV "
        "(NBR 17227 §5.2). Sistemas >15 kV requerem métodos "
        "alternativos (EPRI 2011, Terzija-Konglin) não "
        "implementados nesta versão."
    ),
    "arc_flash_3p_only": (
        "Cálculo assume falta TRIFÁSICA simétrica (NBR 17227 "
        "§5.1.4). Faltas fase-terra com baixa impedância "
        "podem gerar energia equivalente; aproximação "
        "conservadora aceita pela NBR."
    ),
    "pf_positive_seq_only": (
        "Fluxo de potência positive-sequence apenas (3φ "
        "balanceado). Desbalanços e sequência 0/2 não "
        "considerados (IEEE 399 §6 menciona, não exigido "
        "para load flow primário)."
    ),
    "pf_no_q_limits": (
        "Limites de Q (capability curve) em barras PV não "
        "aplicados — solução pode indicar Q irreal. "
        "Verificar manualmente capability dos geradores "
        "(IEEE 399 §6.3)."
    ),
    "coord_no_auto_dt_min": (
        "Validação automática de margem de tempo Δt entre "
        "relés a montante/jusante NÃO implementada. "
        "Verificar manualmente que Δt ≥ valores típicos: "
        "0.3-0.4s eletromecânico, 0.2-0.3s estático, "
        "0.15-0.25s digital (IEEE 242 §15.10.1)."
    ),
}


def format_limitations_block(applied_keys: list[str]) -> str:
    """
    Formata lista de limitações aplicadas em texto plano para
    incluir no relatório. Apenas as keys passadas — outras
    limitações não relevantes ficam fora.

    Examples
    --------

    >>> txt = format_limitations_block(["sc_ib_far_only"])
    >>> "factor μ·q" in txt
    True
    """
    if not applied_keys:
        return ""
    lines = ["LIMITAÇÕES TÉCNICAS APLICADAS:", ""]
    for key in applied_keys:
        text = KNOWN_LIMITATIONS.get(key)
        if text:
            lines.append(f"  • {text}")
    return "\n".join(lines)


def format_limitations_html(applied_keys: list[str]) -> str:
    """v0.92: formata limitações como bloco HTML destacado."""
    if not applied_keys:
        return ""
    items = "".join(
        f"<li>{KNOWN_LIMITATIONS[k]}</li>"
        for k in applied_keys
        if k in KNOWN_LIMITATIONS
    )
    if not items:
        return ""
    return (
        "<div class='audit-limitations'>"
        "<h3>⚠ Limitações técnicas aplicadas</h3>"
        f"<ul>{items}</ul>"
        "</div>"
    )
