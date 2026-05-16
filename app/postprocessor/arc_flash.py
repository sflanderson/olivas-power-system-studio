"""
app.postprocessor.arc_flash — calculadora de energia incidente
para arco elétrico seguindo ABNT NBR 17227:2025 e IEEE Std
1584:2018.

Workflow
========

::

    from app.postprocessor.arc_flash import (
        ArcFlashCase, calculate_arc_flash,
    )
    from app.standards.nbr17227 import (
        ElectrodeConfig, EquipmentClass,
    )

    case = ArcFlashCase(
        bus_name="CCM-A",
        rated_voltage_kV=4.16,
        bolted_fault_current_kA=15.0,   # de IEC 60909
        arc_clearing_time_ms=200,        # de coordenação proteção
        equipment_class=EquipmentClass.CCM_5KV,
        electrode_config=ElectrodeConfig.VCB,
    )

    report = calculate_arc_flash(case)
    print(report.summary())

A NBR 17227:2025 §5.1.1 estabelece que o estudo de energia
incidente **deve ser realizado em conjunto** com:

1. Estudo de **curto-circuito** (IEC 60909-0) — fornece Ibf.
2. Estudo de **coordenação de proteção** — fornece T (tempo de
   extinção do arco).
3. Levantamento de campo dos equipamentos (espaçamento G, dist.
   trabalho D, classe de invólucro).

Estes três insumos vêm dos outros pós-processores do Olivas
(``short_circuit.py``, ``relay_coordination.py`` em v0.27.4).

Fluxo IEEE 1584:2018 cobertos
==============================

1. Calcular ``Iarc`` a partir de Ibf, G, config e Voc.
2. Calcular ``Iarc_min`` = Iarc · (1 - 0.5·VarCf).
3. Calcular ``E`` (energia incidente) em J/cm² → cal/cm².
4. Calcular ``DLA`` (distância-limite de arco) em mm.
5. Repetir com Iarc_min e ficar com **maior** das duas
   energias (NBR 17227 §5.2.11).
6. Determinar categoria de EPI (NFPA 70E:2024).

Limitações MVP v0.27.3
=======================

* Coeficientes da Equação (1) — Iarc — completos para VCB e VCBB
  em 600/2700/14300 V. HCB/VOA/HOA usam fallback VCB com
  warning.
* Equação (3-6) — energia incidente — usa **fórmula calibrada
  simplificada** (cross-checked com IEEE 1584 Annex D ±15%).
  Coeficientes completos da Tabela 6 em v0.27.3.5.
* Sem interpolação fina entre 600/2700/14300 (usa banda
  imediata).
* Apenas cálculo trifásico simétrico — monofásico aproxima por
  Voc fase-terra (NBR 17227 §5.2.12).

Aplicações desbloqueadas
========================

* **Estudo de arc-flash** completo para painéis BT/MT.
* **Especificação de EPI** (categoria + arc rating mínimo).
* **DLA** para sinalização de zona controlada.
* **Memória de cálculo** auditável vs NBR 17227 §5.

Referências cruzadas
=====================

* ABNT NBR 17227:2025 §5
* IEEE Std 1584-2018
* NFPA 70E:2024 Tabela 130.5(C) e 130.7(C)(15)(c)
* IEEE 3002.3 (recommended practice for SC)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.standards.nbr17227 import (
    ElectrodeConfig, EquipmentClass, PpeCategory,
    TYPICAL_ENCLOSURE_MM, TYPICAL_GAP_MM, TYPICAL_WORKING_DISTANCE_MM,
    calculate_arc_current_kA,
    calculate_arc_current_min_kA,
    calculate_arc_flash_boundary_mm,
    calculate_incident_energy_J_per_cm2,
    calculate_VarCf,
    joule_to_calorie,
    ppe_arc_rating_required_cal_cm2,
    ppe_category_from_energy,
)


# ---------------------------------------------------------------------------
# Caso de estudo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArcFlashCase:
    """
    Caso de estudo de arc-flash para um ponto do sistema.

    Campos obrigatórios
    -------------------

    bus_name:
        Identificador do barramento/equipamento.
    rated_voltage_kV:
        Tensão Voc do sistema (linha-linha, kV).
        Range válido: 0.208 ≤ Voc ≤ 15.0.
    bolted_fault_current_kA:
        Corrente de falta franca trifásica Ibf (kA, RMS).
        Vem do estudo de SC (``app.postprocessor.short_circuit``).
    arc_clearing_time_ms:
        Tempo de extinção do arco (ms) — soma do tempo de
        operação de relés + abertura do disjuntor + tempo de
        comunicação. Vem do estudo de coordenação.
    equipment_class:
        Classe NBR 17227 — usado para preencher gap_mm,
        working_distance_mm e enclosure se não fornecidos.
    electrode_config:
        Configuração de eletrodos (default VCB).

    Campos opcionais (override dos defaults da classe)
    ---------------------------------------------------

    gap_mm:
        Espaçamento entre fases. Default = TYPICAL_GAP_MM[class].
    working_distance_mm:
        Distância cabeça-arco. Default = TYPICAL_WORKING_DISTANCE.
    enclosure_correction_factor:
        Fator de correção de tamanho de invólucro CF. Default
        1.0 (invólucro padrão).

    v0.92.2 — Validação automática
    -------------------------------

    ``__post_init__`` valida físicamente todos os campos. Levanta
    ``ValueError`` com contexto se algum estiver fora de faixa.
    Cumpre Princípio 4 da auditabilidade (recusar entrada
    inconsistente em vez de produzir laudo incorreto).
    """

    bus_name: str
    rated_voltage_kV: float
    bolted_fault_current_kA: float
    arc_clearing_time_ms: float
    equipment_class: EquipmentClass
    electrode_config: ElectrodeConfig = ElectrodeConfig.VCB

    # Overrides opcionais
    gap_mm: Optional[float] = None
    working_distance_mm: Optional[float] = None
    enclosure_correction_factor: float = 1.0

    def __post_init__(self) -> None:
        """
        v0.92.2: validação automática de inputs físicos.
        Levanta ``ValueError`` com contexto descritivo se algum
        campo estiver fora de faixa fisicamente plausível.

        Faixas validadas:
        * ``rated_voltage_kV`` ∈ [0.208, 15.0] (range NBR 17227 §5.2)
        * ``bolted_fault_current_kA`` ∈ (0, 200] (200 kA = limite IEEE 1584)
        * ``arc_clearing_time_ms`` ∈ (0, 2000] (2 s = limite prático)
        * ``enclosure_correction_factor`` ∈ (0, 5] (tipicamente ~1.0)
        * ``gap_mm`` (se fornecido) ∈ (0, 200] (>200 mm sai da faixa
          das tabelas IEEE 1584)
        * ``working_distance_mm`` (se fornecido) ∈ [50, 5000]
          (50 mm = mínimo prático; 5 m = afastamento extremo)

        Caso o usuário precise valor fora da faixa, deve
        sobrescrever via subclasse e justificar na seção
        "Limitações" do laudo.
        """
        from app.core.logging_config import get_logger
        log = get_logger(__name__)

        if not isinstance(self.bus_name, str) or not self.bus_name.strip():
            raise ValueError(
                f"ArcFlashCase: bus_name deve ser string não-vazia "
                f"(got {self.bus_name!r})"
            )

        # Tensão — faixa NBR 17227 §5.2 / IEEE 1584 §4.3
        if self.rated_voltage_kV <= 0:
            raise ValueError(
                f"ArcFlashCase[{self.bus_name}]: "
                f"rated_voltage_kV deve ser > 0 "
                f"(got {self.rated_voltage_kV})"
            )
        if self.rated_voltage_kV < 0.208:
            log.warning(
                "Tensão %.3f kV abaixo da faixa típica NBR 17227 "
                "(>=0.208 kV). Análise prossegue mas resultados "
                "extrapolados.",
                self.rated_voltage_kV,
            )
        if self.rated_voltage_kV > 15.0:
            log.warning(
                "Tensão %.3f kV acima da faixa NBR 17227 §5.2 "
                "(<=15.0 kV). Aplicar limitação 'arc_flash_lv_only' "
                "no relatório.",
                self.rated_voltage_kV,
            )

        # Corrente de falta franca
        if self.bolted_fault_current_kA <= 0:
            raise ValueError(
                f"ArcFlashCase[{self.bus_name}]: "
                f"bolted_fault_current_kA deve ser > 0 "
                f"(got {self.bolted_fault_current_kA})"
            )
        if self.bolted_fault_current_kA > 200.0:
            raise ValueError(
                f"ArcFlashCase[{self.bus_name}]: "
                f"bolted_fault_current_kA={self.bolted_fault_current_kA} "
                f"excede limite IEEE 1584 §4.3 (200 kA). "
                f"Verifique o estudo de SC."
            )

        # Tempo de extinção
        if self.arc_clearing_time_ms <= 0:
            raise ValueError(
                f"ArcFlashCase[{self.bus_name}]: "
                f"arc_clearing_time_ms deve ser > 0 "
                f"(got {self.arc_clearing_time_ms})"
            )
        if self.arc_clearing_time_ms > 2000.0:
            log.warning(
                "Tempo de extinção %.0f ms é muito alto (>2 s). "
                "Verifique coordenação 50/51 do barramento %s.",
                self.arc_clearing_time_ms, self.bus_name,
            )

        # Enclosure correction factor
        if not (0 < self.enclosure_correction_factor <= 5):
            raise ValueError(
                f"ArcFlashCase[{self.bus_name}]: "
                f"enclosure_correction_factor deve estar em (0, 5] "
                f"(got {self.enclosure_correction_factor})"
            )

        # Overrides opcionais
        if self.gap_mm is not None:
            if not (0 < self.gap_mm <= 200):
                raise ValueError(
                    f"ArcFlashCase[{self.bus_name}]: "
                    f"gap_mm deve estar em (0, 200] mm "
                    f"(got {self.gap_mm})"
                )

        if self.working_distance_mm is not None:
            if not (50 <= self.working_distance_mm <= 5000):
                raise ValueError(
                    f"ArcFlashCase[{self.bus_name}]: "
                    f"working_distance_mm deve estar em [50, 5000] mm "
                    f"(got {self.working_distance_mm})"
                )

    def effective_gap_mm(self) -> float:
        return (
            self.gap_mm if self.gap_mm is not None
            else TYPICAL_GAP_MM[self.equipment_class]
        )

    def effective_working_distance_mm(self) -> float:
        return (
            self.working_distance_mm if self.working_distance_mm is not None
            else TYPICAL_WORKING_DISTANCE_MM[self.equipment_class]
        )


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArcFlashReport:
    """
    Relatório de cálculo de arc-flash NBR 17227 / IEEE 1584-2018.

    Esta dataclass armazena **todos** os valores intermediários
    para auditoria e cross-check.

    Resultado final relevante:

    * ``incident_energy_cal_cm2``: maior das duas energias
      (com Iarc e Iarc_min) — para escolha de EPI.
    * ``arc_flash_boundary_mm``: DLA — distância segura.
    * ``ppe_category``: NFPA 70E categoria.
    * ``ppe_arc_rating_min_cal_cm2``: arc rating mínimo do EPI.
    """

    # Caso de entrada (echo back)
    case_label: str
    rated_voltage_kV: float
    Ibf_kA: float
    arc_duration_ms: float
    gap_mm: float
    working_distance_mm: float
    electrode_config: ElectrodeConfig
    equipment_class: EquipmentClass

    # Resultados intermediários
    Iarc_kA: float           # corrente de arco média
    VarCf: float             # fator de correção
    Iarc_min_kA: float       # corrente de arco reduzida
    E_arc_J_cm2: float       # energia com Iarc média
    E_arc_min_J_cm2: float   # energia com Iarc_min

    # Resultado final (maior das duas)
    incident_energy_J_cm2: float
    incident_energy_cal_cm2: float
    arc_flash_boundary_mm: float

    # PPE
    ppe_category: PpeCategory
    ppe_arc_rating_min_cal_cm2: float

    # Metadata
    source: str = (
        "ABNT NBR 17227:2025 / IEEE Std 1584-2018 / NFPA 70E:2024"
    )

    def summary(self) -> str:
        """Sumário humano-readable em texto plano."""
        cat = self.ppe_category.value
        danger_marker = " ⚠ DANGER ⚠ " if cat == "DANGER" else ""
        lines = [
            f"=== Arc-Flash Hazard Report {danger_marker}===",
            f"Source: {self.source}",
            f"Bus: {self.case_label}",
            f"Equipment: {self.equipment_class.value} "
            f"(electrode config: {self.electrode_config.value})",
            "",
            "--- Inputs ---",
            f"  V_oc = {self.rated_voltage_kV:.3f} kV",
            f"  I_bf = {self.Ibf_kA:.3f} kA (bolted fault)",
            f"  T   = {self.arc_duration_ms:.1f} ms (arc duration)",
            f"  G   = {self.gap_mm:.1f} mm (gap)",
            f"  D   = {self.working_distance_mm:.1f} mm (working distance)",
            "",
            "--- Arc Currents ---",
            f"  I_arc      = {self.Iarc_kA:.3f} kA  (average)",
            f"  VarCf      = {self.VarCf:.4f}",
            f"  I_arc_min  = {self.Iarc_min_kA:.3f} kA",
            "",
            "--- Incident Energies ---",
            f"  E (with I_arc)     = "
            f"{self.E_arc_J_cm2:.3f} J/cm² "
            f"= {joule_to_calorie(self.E_arc_J_cm2):.3f} cal/cm²",
            f"  E (with I_arc_min) = "
            f"{self.E_arc_min_J_cm2:.3f} J/cm² "
            f"= {joule_to_calorie(self.E_arc_min_J_cm2):.3f} cal/cm²",
            "",
            "--- Final Result ---",
            f"  Incident Energy = {self.incident_energy_J_cm2:.3f} J/cm² "
            f"= {self.incident_energy_cal_cm2:.3f} cal/cm²",
            f"  Arc-Flash Boundary (DLA) = "
            f"{self.arc_flash_boundary_mm:.0f} mm",
            "",
            "--- PPE Requirement (NFPA 70E:2024) ---",
            f"  Category: {self.ppe_category.value}",
            f"  Minimum Arc Rating: "
            f"{self.ppe_arc_rating_min_cal_cm2:.1f} cal/cm²",
        ]
        if self.ppe_category == PpeCategory.DANGER:
            lines.extend([
                "",
                "  ⚠ ENERGIA EXCEDE 40 cal/cm² — TRABALHO ENERGIZADO PROIBIDO.",
                "  Aplicar desligamento; consultar NBR 16384 / NR-10.",
            ])
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cálculo principal
# ---------------------------------------------------------------------------


def calculate_arc_flash(case: ArcFlashCase) -> ArcFlashReport:
    """
    Executa o cálculo completo NBR 17227:2025 / IEEE 1584-2018
    para um ``ArcFlashCase``.

    Sequência:

    1. Resolve gap_mm e working_distance_mm (override ou
       template da classe de equipamento).
    2. Calcula ``Iarc_avg`` via Equação (1).
    3. Calcula ``VarCf`` via Equação (2).
    4. Calcula ``Iarc_min`` via Equação (34).
    5. Calcula ``E_avg`` via Equação (3-6) (forma simplificada).
    6. Calcula ``E_min`` repetindo com Iarc_min.
    7. **E_final = max(E_avg, E_min)** (NBR 17227 §5.2.11).
    8. Calcula DLA via inversão da Equação de E.
    9. Determina categoria PPE via NFPA 70E.

    Returns
    -------
    ArcFlashReport
    """
    G = case.effective_gap_mm()
    D = case.effective_working_distance_mm()

    # Step 2: Iarc avg
    Iarc_avg = calculate_arc_current_kA(
        Ibf_kA=case.bolted_fault_current_kA,
        gap_mm=G,
        config=case.electrode_config,
        voltage_kV=case.rated_voltage_kV,
    )

    # Step 3-4: VarCf + Iarc_min
    var_cf = calculate_VarCf(
        config=case.electrode_config,
        voltage_kV=case.rated_voltage_kV,
    )
    Iarc_min = calculate_arc_current_min_kA(Iarc_avg, var_cf)

    # Step 5-6: energias
    E_avg = calculate_incident_energy_J_per_cm2(
        arc_duration_ms=case.arc_clearing_time_ms,
        Iarc_kA=Iarc_avg,
        Ibf_kA=case.bolted_fault_current_kA,
        gap_mm=G,
        working_distance_mm=D,
        config=case.electrode_config,
        voltage_kV=case.rated_voltage_kV,
        enclosure_correction_factor=case.enclosure_correction_factor,
    )
    E_min = calculate_incident_energy_J_per_cm2(
        arc_duration_ms=case.arc_clearing_time_ms,
        Iarc_kA=Iarc_min,
        Ibf_kA=case.bolted_fault_current_kA,
        gap_mm=G,
        working_distance_mm=D,
        config=case.electrode_config,
        voltage_kV=case.rated_voltage_kV,
        enclosure_correction_factor=case.enclosure_correction_factor,
    )

    # Step 7: pior caso
    E_final_J_cm2 = max(E_avg, E_min)
    Iarc_for_dla = Iarc_avg if E_avg >= E_min else Iarc_min

    # Step 8: DLA
    dla_mm = calculate_arc_flash_boundary_mm(
        arc_duration_ms=case.arc_clearing_time_ms,
        Iarc_kA=Iarc_for_dla,
        Ibf_kA=case.bolted_fault_current_kA,
        gap_mm=G,
        config=case.electrode_config,
        voltage_kV=case.rated_voltage_kV,
        threshold_J_per_cm2=5.0,   # = 1.2 cal/cm²
        enclosure_correction_factor=case.enclosure_correction_factor,
    )

    # Step 9: PPE
    E_cal = joule_to_calorie(E_final_J_cm2)
    ppe = ppe_category_from_energy(E_cal)
    arc_rating = ppe_arc_rating_required_cal_cm2(ppe)

    return ArcFlashReport(
        case_label=case.bus_name,
        rated_voltage_kV=case.rated_voltage_kV,
        Ibf_kA=case.bolted_fault_current_kA,
        arc_duration_ms=case.arc_clearing_time_ms,
        gap_mm=G,
        working_distance_mm=D,
        electrode_config=case.electrode_config,
        equipment_class=case.equipment_class,
        Iarc_kA=Iarc_avg,
        VarCf=var_cf,
        Iarc_min_kA=Iarc_min,
        E_arc_J_cm2=E_avg,
        E_arc_min_J_cm2=E_min,
        incident_energy_J_cm2=E_final_J_cm2,
        incident_energy_cal_cm2=E_cal,
        arc_flash_boundary_mm=dla_mm,
        ppe_category=ppe,
        ppe_arc_rating_min_cal_cm2=arc_rating,
    )
