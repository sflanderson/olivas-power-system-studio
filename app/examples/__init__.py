"""
app.examples — exemplos executáveis dos estudos normativos
implementados no ATP Studio.

Cada exemplo:

* Reproduz um WORKED EXAMPLE da norma de referência.
* Imprime ambos: valores esperados (da norma) e calculados
  (pelo ATP Studio).
* Pode ser invocado pela GUI via menu "Exemplos" ou
  diretamente via ``python -m app.examples.<name>``.

Exemplos disponíveis (v0.33.0):

* ``stevenson_pf_3bus`` — Power flow 3-bus do livro
  Stevenson §9 Example 9.5.
* ``stevenson_sequential`` — Componentes simétricas
  §11 Example 11.4 (falta LG/LL).
* ``iec60909_annex_c`` — Sistema do Annex C da
  IEC 60909-0 (cálculo SC).
* ``ieee1584_ex_d2`` — Exemplo D.2 da IEEE 1584:2018
  (480V VCB).
* ``ieee399_motor_starting`` — Motor 1500 HP do Brown
  Book §10.
* ``nbr17227_example`` — Worked example da NBR 17227:2025.

API
====

Todos exemplos exportam ``run() -> ExampleResult`` que
retorna um relatório padronizado para a GUI consumir:

::

    @dataclass(frozen=True)
    class ExampleResult:
        title: str
        reference: str          # cite normativa
        expected: dict[str, float]
        computed: dict[str, float]
        tolerance_pct: float
        passed: bool
        narrative: str          # texto explicativo
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ExampleResult:
    """
    Resultado padronizado de um exemplo executável.

    Attributes
    ----------
    title:
        Título do exemplo (ex: "Stevenson §9 Ex 9.5 — PF 3-bus").
    reference:
        Citação normativa (livro/standard + capítulo).
    expected:
        Valores esperados (de norma/livro) — ``{nome: valor}``.
    computed:
        Valores calculados pelo ATP Studio.
    tolerance_pct:
        Tolerância para considerar um valor "OK" (default 5%).
    passed:
        True se TODOS os ``computed`` estão dentro da tolerância
        dos ``expected``.
    narrative:
        Texto explicativo do exemplo, fundamentação teórica,
        e comparação valores.
    extras:
        Bagagem extra (objetos do study, plots, etc).
    """
    title: str
    reference: str
    expected: dict
    computed: dict
    tolerance_pct: float
    passed: bool
    narrative: str
    extras: Optional[dict] = None

    def summary(self) -> str:
        status = "[PASS]" if self.passed else "[FAIL]"
        lines = [
            "=" * 70,
            f"  {self.title}  [{status}]",
            "=" * 70,
            f"Referência: {self.reference}",
            "",
            "Comparação esperado vs calculado:",
            f"  {'Quantidade':<30} {'Esperado':>14} {'Calculado':>14} {'Δ%':>8}",
            "  " + "-" * 66,
        ]
        for key in self.expected:
            exp = self.expected[key]
            comp = self.computed.get(key, float("nan"))
            try:
                err_pct = abs(comp - exp) / abs(exp) * 100.0 if exp != 0 else 0.0
            except (TypeError, ValueError):
                err_pct = float("nan")
            lines.append(
                f"  {key:<30} {exp:>14.4f} {comp:>14.4f} {err_pct:>7.2f}%"
            )
        lines.append("")
        lines.append(f"Tolerância: ±{self.tolerance_pct:.1f}%")
        lines.append("")
        lines.append(self.narrative)
        return "\n".join(lines)


def _check_tolerance(
    expected: dict, computed: dict, tolerance_pct: float,
) -> bool:
    """Helper: True se todos computed dentro da tolerância."""
    for key, exp in expected.items():
        comp = computed.get(key)
        if comp is None:
            return False
        if exp == 0:
            if abs(comp) > tolerance_pct / 100.0:
                return False
            continue
        err = abs(comp - exp) / abs(exp) * 100.0
        if err > tolerance_pct:
            return False
    return True
