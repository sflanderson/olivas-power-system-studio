"""
app.equipment — biblioteca de equipamentos elétricos com
data sheets de fabricantes (v0.98.0).

Filosofia
==========

PTW Power*Tools / ETAP / EasyPower têm bibliotecas com
1000+ modelos curados de fabricantes (SEL, ABB, Siemens,
GE, Eaton, WEG). Olivas v0.97 só tinha catálogo genérico
de 49 componentes elétricos.

Esta sprint adiciona uma **biblioteca curada de dados**
de equipamentos reais com:

* **Relés de proteção** (50+) — SEL-751/487/411, ABB
  REF615/620/630, Siemens 7SJ80/82/85, GE Multilin
  489/750/845
* **Motores elétricos** (30+) — WEG W22/W50/W60, Siemens
  1LE/1MB, ABB M3BP/M2BAX
* **Transformadores** (20+) — Siemens GEAFOL, ABB Resibloc,
  WEG Distribution (5–50 MVA)
* **Disjuntores** (30+) — ABB HD4/HV4, Siemens 8DJH/8DA,
  ortyr 3WL (LV)
* **Unidades de disparo LSIG** — ABB Ekip, Schneider Micrologic,
  WEG ABW-OCR, Eaton PXR/Digitrip, Siemens ETU (faixas de
  Ir/tr/Isd/tsd/Ii/Ig/tg de datasheets oficiais)
* **Fusíveis** — Bussmann NH gG/aM e 12 kV, SIBA HHM, ABB CEF/CMF,
  WEG aR (I²t de pré-arco/total por corrente nominal)

Cada entry em YAML estruturado com:

* Modelo + fabricante + classe ANSI (relés)
* Faixas operacionais (corrente, voltagem, frequência)
* Curvas suportadas (relés)
* Características nominais (kW, V, fp para motores)
* Data sheet URL + PDF reference

API
====

::

    from app.equipment import library

    # Lista todos os relés feeder
    relays = library.list_relays(application="feeder")

    # Busca por modelo
    sel_751 = library.get_relay("SEL-751")

    # Filtros combinados
    abb_mv = library.list_relays(vendor="ABB", voltage_class="MV")

    # Auto-binding ao bus
    bus.suggested_relay_id = "SEL-751"
    relay = library.get_relay(bus.suggested_relay_id)
    bus.apply_relay_defaults(relay)
"""

from __future__ import annotations

from app.equipment import library

__all__ = ["library"]
