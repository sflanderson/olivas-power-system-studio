"""
app.standards — codificação de normas técnicas como dados Python
imutáveis usados pelos pós-processores do Olivas ATP Studio.

Filosofia
=========

Cada norma vira um módulo com:

* **Tabelas** (frozen dataclasses) reproduzindo valores
  numéricos da norma (gaps típicos, voltage factors, c-factors,
  envelopes de TRT, coeficientes IEEE 1584 etc.).
* **Funções de cálculo** que aplicam as fórmulas da norma sem
  ambiguidade.
* **Validadores** que checam se um caso de estudo está dentro
  do escopo da norma.
* **Referência cruzada** explícita à seção/equação/tabela da
  norma (campo ``source``) para auditoria.

Estrutura de subpacotes (v0.27.x)
==================================

* ``iec62271`` — IEC 62271-100/200/203 (alta-tensão switchgear,
  TRT envelopes T10/T30/T60/T100, kpp factors).
* ``iec60909`` — IEC 60909-0/1/2/3/4 (cálculo de correntes de
  curto-circuito em sistemas trifásicos AC).
* ``nbr17227`` — ABNT NBR 17227:2025 (gerenciamento de risco
  de energia incidente — IEEE 1584:2018 Brazilian adoption).
* ``ansi_devices`` — ANSI/IEEE C37.2 device numbers (50/51/87
  etc.) para coordenação de proteção.
* ``ieee242`` — IEEE Std 242-2001 (Buff Book — protection and
  coordination of industrial and commercial power systems).

Uso
===

::

    from app.standards.iec62271 import (
        first_pole_factor_kpp, trt_envelope_4param,
        TestDuty,
    )
    env = trt_envelope_4param(
        rated_voltage_kV=145, kpp=1.3, duty=TestDuty.T100s,
    )

Cada módulo é puramente computacional — não depende de PySide6,
matplotlib, numpy (exceto onde explícito). Pode ser importado
em qualquer contexto (lib, CLI, GUI, notebook).

Referências bibliográficas
==========================

Library local (D:\\…\\MVP\\LIBRARY\\):

* IEC 60909-0:2016 — Short-circuit currents in three-phase a.c.
  systems — Part 0: Calculation of currents.
* IEC 60909-1, -2, -3, -4 (parts on factors, examples, faults
  to ground, examples for high-voltage).
* IEC 62271-200 — A.C. metal-enclosed switchgear and controlgear
  for rated voltages above 1 kV and up to 52 kV.
* IEC 62271-203 — Gas-insulated metal-enclosed switchgear for
  rated voltages above 52 kV.
* IEC 61482-2 — Live working — protective clothing against arc
  thermal hazards.
* ABNT NBR 17227:2025 — Arco elétrico — gerenciamento de risco
  de energia incidente, precauções e métodos de cálculo.
* IEEE Std 242-2001 — Buff Book.
* IEEE Std 141-1993 — Red Book.
* IEEE Std C37.91/96/97/101/108/109/113 — protection of
  generators, transformers, motors, buses, lines.
* ANSI/IEEE Device Numbers (C37.2).
* NFPA 70E:2024 — Electrical Safety in the Workplace.
* ASTM F1506-22 — Standard performance specification for
  flame resistant and electric arc rated apparel.
"""

from __future__ import annotations

# Versão do package standards (independente do Olivas main).
STANDARDS_VERSION = "1.0.0"

# Lista de normas codificadas (atualizar quando módulo novo entrar).
SUPPORTED_STANDARDS = (
    "IEC 60909-0:2016",
    "IEC 62271-100",
    "IEC 62271-200",
    "ABNT NBR 17227:2025",
    "IEEE Std 1584-2018",
    "IEEE Std 242-2001",
    "ANSI/IEEE C37.2",
)


__all__ = [
    "STANDARDS_VERSION",
    "SUPPORTED_STANDARDS",
]
