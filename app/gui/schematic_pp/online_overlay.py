"""
app.gui.schematic_pp.online_overlay — Single-line diagram
"online" mode (v1.1.0).

Filosofia
==========

PTW Power*Tools, ETAP e EasyPower oferecem um modo
**Online View** (PTW) / **Online Display Mode** (ETAP) /
**Live Display** (EasyPower) onde os resultados das análises
mais recentes (SC, PF, Coordenação) são **sobrepostos
diretamente sobre o esquemático ativo** — sem precisar abrir
relatórios separados ou navegar para a aba de resultados.

Em PTW, cada bus exibe ao lado do símbolo:

* **Ik''** (initial symmetrical SC current, kA)
* **kV nominal** + **V atual** se PF foi rodado
* **Cor**: verde (OK), amarelo (≥80% rating), vermelho
  (violation, ≥100% rating)

Cabos exibem **% loading** e **V-drop %**. Disjuntores
mostram **Iccs/Ik**. Motores exibem **kVA atual / kVA nominal**.

Implementação
=============

O modo Online é construído como uma **camada de anotações**
(``OnlineAnnotation``) que pode ser anexada a qualquer
``ComponentItem``. O ``ComponentItem.paint()`` foi modificado
em v1.1.0 para desenhar a annotation se ela estiver setada
(``self._online_annotation is not None``).

O ``OnlineOverlayManager`` orquestra: lê o ``StudyCache`` do
``MainWindow``, walks os componentes da cena, anexa
``OnlineAnnotation`` a cada um conforme apropriado.
``set_enabled(False)`` limpa todas as anotações.

Cobertura normativa
====================

* IEC 60909-0 — Short-circuit currents (Ik''/ip/Ib/Ik)
* IEEE 399 — Power Flow / Voltage profile
* NBR 5410 §6.2.7 — Voltage drop limits

Severidade dos badges (heurística PTW):

* ``"info"``  → cinza/azul: dado informativo
* ``"ok"``    → verde:      dentro de limites
* ``"warn"``  → amarelo:    margem reduzida (≥80% do rating)
* ``"violation"`` → vermelho: viola norma/rating
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from PySide6.QtGui import QColor


# ---------------------------------------------------------------------------
# Severity colors (paleta PTW corporativa)
# ---------------------------------------------------------------------------


SEVERITY_COLORS: dict[str, tuple[QColor, QColor]] = {
    # (text_color, background_fill)
    "info":      (QColor(20, 50, 80),    QColor(235, 245, 255)),  # azul claro
    "ok":        (QColor(46, 125, 50),   QColor(232, 245, 233)),  # verde claro
    "warn":      (QColor(180, 120, 0),   QColor(255, 248, 220)),  # amarelo claro
    "violation": (QColor(192, 57, 43),   QColor(253, 232, 230)),  # vermelho claro
}


def severity_colors(sev: str) -> tuple[QColor, QColor]:
    """Retorna (text, bg) para a severidade. Default 'info'."""
    return SEVERITY_COLORS.get(sev, SEVERITY_COLORS["info"])


# ---------------------------------------------------------------------------
# Annotation dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OnlineAnnotation:
    """
    Anotação Online a ser desenhada ao lado de um
    :class:`ComponentItem` quando o modo Online estiver ativo.

    Attributes
    ----------
    lines:
        Linhas de texto a desenhar (uma por linha do badge).
        Mantenha curto — cada linha será desenhada em ~9pt
        Bold. Tipicamente 1-3 linhas.
    severity:
        ``"info"``, ``"ok"``, ``"warn"``, ``"violation"`` —
        controla cor de texto e fundo.
    placement:
        ``"right"`` (default — ao lado direito do símbolo) ou
        ``"below"`` (abaixo do label do componente). PTW usa
        ``"right"`` em SLDs horizontais.
    """

    lines: tuple[str, ...]
    severity: str = "info"
    placement: str = "right"

    @property
    def text(self) -> str:
        """Concatena lines em um único string com newlines."""
        return "\n".join(self.lines)


# ---------------------------------------------------------------------------
# Annotation builders — mapeiam resultado de estudo → OnlineAnnotation
# ---------------------------------------------------------------------------


def annotation_from_sc(
    sc_result: Any,
    *,
    bus_rating_kA: Optional[float] = None,
) -> OnlineAnnotation:
    """
    Cria uma anotação a partir de um ``ShortCircuitResult``.

    Linhas geradas:

    * ``Ik" = X.XX kA``
    * ``ip  = X.XX kA``
    * (se ``bus_rating_kA`` fornecido) ``Util: XX% rating``

    Severidade:

    * Se ``Ik'' ≥ bus_rating_kA`` → ``violation`` (rating excedido).
    * Se ``Ik'' ≥ 0.80 × bus_rating_kA`` → ``warn``.
    * Caso contrário → ``ok``.
    * Sem rating → ``info``.
    """
    lines: list[str] = []
    try:
        ik = float(sc_result.Ik_pp_kA)
    except (AttributeError, TypeError, ValueError):
        return OnlineAnnotation(
            lines=("(SC inválido)",),
            severity="warn",
        )
    lines.append(f"Ik\" = {ik:.2f} kA")
    try:
        ip = float(sc_result.ip_kA)
        lines.append(f"ip  = {ip:.2f} kA")
    except (AttributeError, TypeError, ValueError):
        pass

    sev = "info"
    if bus_rating_kA is not None and bus_rating_kA > 0:
        ratio = ik / bus_rating_kA
        lines.append(f"Util: {ratio*100:.0f}% rating")
        if ratio >= 1.0:
            sev = "violation"
        elif ratio >= 0.80:
            sev = "warn"
        else:
            sev = "ok"

    return OnlineAnnotation(
        lines=tuple(lines),
        severity=sev,
    )


def annotation_from_pf(
    voltage_pu: float,
    *,
    voltage_kV_nominal: Optional[float] = None,
    nbr5410_limit_pu: float = 0.95,  # 5% drop = 0.95 pu
) -> OnlineAnnotation:
    """
    Cria anotação para resultado de Power Flow num bus.

    Severidade conforme NBR 5410 §6.2.7 (limite default 5%).
    Se ``voltage_pu < nbr5410_limit_pu``, marca ``violation``.
    """
    lines = [f"V = {voltage_pu:.3f} pu"]
    if voltage_kV_nominal is not None:
        v_kV = voltage_pu * voltage_kV_nominal
        lines.append(f"  ({v_kV:.2f} kV)")

    sev = "ok"
    if voltage_pu < nbr5410_limit_pu:
        sev = "violation"
    elif voltage_pu < nbr5410_limit_pu + 0.02:  # 2% margem do limite
        sev = "warn"
    elif voltage_pu > 1.05:  # sobretensão
        sev = "warn"
    return OnlineAnnotation(
        lines=tuple(lines),
        severity=sev,
    )


# ---------------------------------------------------------------------------
# Manager — conecta StudyCache → cena
# ---------------------------------------------------------------------------


class OnlineOverlayManager:
    """
    Gerencia anotações Online sobre um conjunto de
    :class:`ComponentItem` da cena de schematic_pp.

    Ciclo:

    1. ``set_enabled(True)`` — liga o modo Online.
    2. ``refresh(study_cache, project)`` — lê o cache de
       estudos e anexa anotações aos componentes corretos
       (BUS recebe SC, etc.).
    3. ``set_enabled(False)`` — limpa todas as anotações.

    Observação: o manager é stateless — ele lê o cache toda
    vez que ``refresh()`` é chamado. O caller (PpEditor /
    MainWindow) é responsável por chamar refresh sempre que
    o cache mudar (ex: ao final de cada análise).
    """

    def __init__(self) -> None:
        self._enabled: bool = False
        # Componentes anotados nesta sessão — usado para limpar
        # rapidamente em set_enabled(False).
        self._annotated_items: list = []

    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Liga/desliga o modo. Se desligar, limpa todas anotações."""
        self._enabled = bool(enabled)
        if not self._enabled:
            self._clear_all()

    def _clear_all(self) -> None:
        """Remove anotações de todos os items registrados."""
        for item in self._annotated_items:
            try:
                item.set_online_annotation(None)
            except Exception:
                # Item pode ter sido deletado da cena.
                pass
        self._annotated_items.clear()

    def refresh(self, scene, study_cache) -> int:
        """
        Lê o ``study_cache`` e anexa anotações aos
        ``ComponentItem`` da ``scene`` que tenham resultados
        no cache.

        Atualmente cobre:

        * **BUS** → resultado SC do cache (Ik'', ip)

        Se ``set_enabled(False)`` foi chamado antes, é no-op
        e retorna 0.

        Returns
        -------
        int
            Número de componentes anotados.
        """
        if not self._enabled:
            return 0
        # Limpa do refresh anterior antes de aplicar novo.
        self._clear_all()
        if scene is None or study_cache is None:
            return 0

        count = 0
        try:
            items = list(scene.items())
        except Exception:
            return 0

        for item in items:
            comp = getattr(item, "component", None)
            if comp is None:
                continue
            ctype = getattr(comp, "type", None)
            cname = getattr(comp, "name", None)
            if not cname or cname == "*":
                continue

            ann = self._annotation_for(ctype, cname, study_cache, comp)
            if ann is not None:
                try:
                    item.set_online_annotation(ann)
                    self._annotated_items.append(item)
                    count += 1
                except Exception:
                    pass
        return count

    def _annotation_for(
        self, ctype: str, cname: str, cache, component,
    ) -> Optional[OnlineAnnotation]:
        """
        Decide qual anotação se aplica para um componente.

        Cobertura v1.4.2:
        * **BUS**: SC (Ik''/ip) do cache + utilization vs rating
        * **RELAY**: settings ativos (51 LTPU, 50 INST, ANSI devices)
        * **XFMR3**: vector_group + impedance_pct + kVA_rated
        * **MOTOR**: rated power + voltage + efficiency
        * **CABLE**: section + material + I_load_pct (se PF cached)
        * **CT**: ratio + class + Vk
        """
        # BUS — comportamento original v1.1.0
        if ctype == "BUS":
            sc = cache.get_sc(cname)
            if sc is None:
                return None
            # Possível ler bus_rating_kA da própria propriedade do bus
            # (campo "isc_rating_kA" se existir no spec).
            bus_rating = self._bus_rating_kA(component)
            return annotation_from_sc(sc, bus_rating_kA=bus_rating)

        # v1.4.2: anotações estáticas para tipos novos —
        # mostram CONFIG do componente (não dependem de cache).
        # Útil para audit visual: o que está no esquemático
        # tem as configurações esperadas?
        if ctype == "RELAY":
            return self._relay_static_annotation(component)
        if ctype == "XFMR3":
            return self._xfmr3_static_annotation(component)
        if ctype == "MOTOR":
            return self._motor_static_annotation(component)
        if ctype == "CABLE":
            return self._cable_static_annotation(component)
        if ctype == "CT":
            return self._ct_static_annotation(component)

        return None

    # ---- v1.4.2: anotações estáticas por tipo --------------------

    @staticmethod
    def _get_prop_value(component, prop_name: str) -> str:
        """Helper: lê valor de uma property pelo nome (string)."""
        from app.preprocessor.spec import get_default_registry
        try:
            spec = get_default_registry().get(component.type)
        except Exception:
            return ""
        if spec is None:
            return ""
        for idx, prop_spec in enumerate(spec.properties):
            if prop_spec.name == prop_name:
                if idx < len(component.properties):
                    return str(component.properties[idx].value or "")
        return ""

    def _relay_static_annotation(self, component) -> Optional[OnlineAnnotation]:
        """RELAY: mostra ANSI devices + 51 LTPU + 50 INST."""
        ansi = self._get_prop_value(component, "ansi_devices") or "?"
        pickup_51 = self._get_prop_value(component, "pickup_51_A") or "?"
        tms_51 = self._get_prop_value(component, "tms_51") or "?"
        pickup_50 = self._get_prop_value(component, "pickup_50_A") or "?"
        return OnlineAnnotation(
            lines=(
                f"ANSI: {ansi}",
                f"51: {pickup_51}A TMS={tms_51}",
                f"50: {pickup_50}A",
            ),
            severity="info",
        )

    def _xfmr3_static_annotation(self, component) -> Optional[OnlineAnnotation]:
        """XFMR3: mostra vector_group + kVA + Z%."""
        vg = self._get_prop_value(component, "vector_group") or "?"
        kva = self._get_prop_value(component, "kVA_rated") or "?"
        z = self._get_prop_value(component, "impedance_pct") or "?"
        v_pri = self._get_prop_value(component, "V_pri_kV") or "?"
        v_sec = self._get_prop_value(component, "V_sec_kV") or "?"
        return OnlineAnnotation(
            lines=(
                f"{kva} kVA · {v_pri}/{v_sec} kV",
                f"{vg} · Z={z}%",
            ),
            severity="info",
        )

    def _motor_static_annotation(self, component) -> Optional[OnlineAnnotation]:
        """MOTOR: mostra power + voltage."""
        power = self._get_prop_value(component, "rated_power_kW") \
            or self._get_prop_value(component, "P_rated_kW") or "?"
        voltage = self._get_prop_value(component, "rated_voltage_V") \
            or self._get_prop_value(component, "V_rated_kV") or "?"
        return OnlineAnnotation(
            lines=(
                f"P = {power} kW",
                f"V = {voltage}",
            ),
            severity="info",
        )

    def _cable_static_annotation(self, component) -> Optional[OnlineAnnotation]:
        """CABLE: mostra section + material."""
        section = self._get_prop_value(component, "section_mm2") or "?"
        material = self._get_prop_value(component, "material") or "?"
        length = self._get_prop_value(component, "length_m") or ""
        lines = [f"S={section}mm² {material}"]
        if length and length != "?":
            lines.append(f"L={length}m")
        return OnlineAnnotation(
            lines=tuple(lines),
            severity="info",
        )

    def _ct_static_annotation(self, component) -> Optional[OnlineAnnotation]:
        """CT: mostra ratio + class."""
        ratio_pri = self._get_prop_value(component, "ratio_pri") or "?"
        ratio_sec = self._get_prop_value(component, "ratio_sec") or "?"
        classe = self._get_prop_value(component, "classe") or "?"
        return OnlineAnnotation(
            lines=(
                f"TC: {ratio_pri}/{ratio_sec}",
                f"Classe: {classe}",
            ),
            severity="info",
        )

    @staticmethod
    def _bus_rating_kA(component) -> Optional[float]:
        """
        Lê o rating de SC do bus se estiver na lista de
        propriedades. Procura por nomes ``isc_rating_kA``,
        ``isc_kA`` ou ``rated_isc_kA``.

        Retorna None se não encontrar.
        """
        spec = None
        try:
            from app.preprocessor.spec import get_default_registry
            spec = get_default_registry().get(component.type)
        except Exception:
            return None
        if spec is None:
            return None
        candidate_names = {
            "isc_rating_kA", "isc_kA", "rated_isc_kA", "isc_rating",
        }
        for idx, prop_spec in enumerate(spec.properties):
            if prop_spec.name in candidate_names:
                if idx < len(component.properties):
                    raw = component.properties[idx].value
                    try:
                        return float(str(raw))
                    except (TypeError, ValueError):
                        return None
        return None


# ---------------------------------------------------------------------------
# v1.7.0 Sprint B — Live/Dead bus annotation builder
# ---------------------------------------------------------------------------


def annotation_from_energization(state) -> OnlineAnnotation:
    """
    Constrói :class:`OnlineAnnotation` a partir de
    :class:`BusState`.

    Mapeamento:
    * ``BusState.LIVE`` → severity ``"ok"``, label "● ENERGIZADO"
    * ``BusState.DEAD`` → severity ``"violation"``, label "✕ DESENERGIZADO"
    * ``BusState.UNKNOWN`` → severity ``"warn"``, label "? estado"

    A severidade ``violation`` faz o badge aparecer **vermelho**
    (paridade PTW "Out of Service" indication).

    Parameters
    ----------
    state:
        Valor de :class:`app.postprocessor.bus_energization.BusState`.

    Returns
    -------
    OnlineAnnotation
    """
    # Import local para evitar ciclo
    from app.postprocessor.bus_energization import BusState

    if state == BusState.LIVE:
        return OnlineAnnotation(
            lines=("● Energizado",),
            severity="ok",
        )
    if state == BusState.DEAD:
        return OnlineAnnotation(
            lines=("✕ Desenergizado",),
            severity="violation",   # vermelho
        )
    return OnlineAnnotation(
        lines=("? estado",),
        severity="warn",
    )
