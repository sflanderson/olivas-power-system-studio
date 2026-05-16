"""
app.preprocessor.bctran — rotina BCTRAN para cálculo de parâmetros
de transformador a partir de dados de teste padrão.

Referências
-----------
* H. W. Dommel, EMTP Theory Book, BPA, 1986, Ch. 6 (esp. §6.3.3-4).
* ATP Rule Book Vol 2, §5.3 (``BCTRAN`` em AUX).
* V. Brandwajn, H. W. Dommel, I. I. Dommel, "Matrix representation
  of three-phase n-winding transformers for steady-state and
  transient studies", IEEE Trans. PAS-101, 1982.

Escopo (v0.24.0 — MVP)
----------------------

* **Transformador monofásico 2-enrolamento** — é a base do BCTRAN.
  O algoritmo para 3-fase multi-enrolamento é extensão direta
  (prevista v0.24.2).
* **Linear (sem saturação)** — a magnetização é representada por
  impedância shunt fixa. Saturação via Type-98 entra em v0.24.2.

Dado que o usuário forneça:

* Tensões base de cada enrolamento (``V_H``, ``V_L``), potência
  nominal (``S_nom``), frequência (``f``);
* Teste de curto-circuito (SC): ``V_sc_pct`` (impedância percentual,
  normalmente 5-15%), ``P_sc_kW`` (perdas em cobre);
* Teste de circuito aberto (OC): ``I_0_pct`` (corrente de excitação
  percentual), ``P_0_kW`` (perdas a vazio / núcleo).

O BCTRAN retorna:

* Matrizes 2×2 ``[R]``, ``[L]`` (em ohms, henries respectivamente)
  refletidas ao lado primário.

Esses dados geram um único ramo ATP tipo 51 (mutually coupled R-L)
com 4 pinos (H1-H2 + L1-L2).

Algoritmo (linear, 2-winding)
-----------------------------

1. Impedâncias base por enrolamento: ``Z_H = V_H² / S_nom``,
   ``Z_L = V_L² / S_nom``.
2. Impedância de curto-circuito referida ao primário:
   ``Z_sc = (V_sc_pct/100) * Z_H``.
3. Resistência de curto-circuito:
   ``R_sc = (P_sc_kW*1000) / (S_nom/V_H)²`` (perdas em cobre).
4. Reatância de CC: ``X_sc = sqrt(Z_sc² - R_sc²)``.
5. Magnetização: ``Y_m = I_0_pct * S_nom / V_H² / 100``;
   ``G_m = P_0_kW*1000 / V_H²`` (condutância — perdas no ferro);
   ``B_m = sqrt(Y_m² - G_m²)``.
6. Matriz [R]: diagonal com ``R_1 = R_2 = R_sc/2`` (simplificação
   padrão — assume distribuição simétrica das perdas em cobre
   entre enrolamentos, exato só para trafos ideais; ajuste fino
   requer ensaio específico).
7. Matriz [L]: calculada a partir de ``[L] = [X] / (2πf)``
   onde:
   * ``X[0,0] = X_sc/2 + X_m`` (reatância de dispersão primária +
     magnetizante),
   * ``X[1,1] = X_sc/2 + X_m`` (análogo secundário),
   * ``X[0,1] = X[1,0] = X_m`` (mútua).

Essa é a redução de Dommel (Theory Book §6.3.3): o modelo [R],[L]
equivalente ao T-equivalente de Steinmetz.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence


# ---------------------------------------------------------------------------
# Conexões trifásicas e clock groups (v0.24.4)
# ---------------------------------------------------------------------------


class TransformerConnection(str, Enum):
    """
    Tipo de conexão trifásica do enrolamento.

    * **Y** (wye, estrela): ponto comum ao neutro. Tensão fase-
      neutro = V_linha / √3.
    * **D** (delta, triângulo): sem neutro. Tensão fase-fase =
      V_linha.
    * **Yauto** (autotrafo Y): enrolamento compartilhado entre
      primário e secundário.
    * **Zigzag** (Z): conexão especial anti-neutro, usada em
      trafos de aterramento.

    O clock group (defasagem em horas de relógio) indica a
    defasagem elétrica entre primário e secundário:
    * YY clock 0 → primário e secundário em fase.
    * YD clock 1 (Yd1) → delta adianta 30° elétricos.
    * YD clock 11 (Yd11) → delta atrasa 30° elétricos (convenção
      mais comum em alta tensão).
    * DY clock 1 (Dy1) → estrela adianta 30°.
    * DD clock 0, 2, 4, 6, 8, 10 — múltiplos de 30°.

    Este enum v0.24.4 suporta apenas os casos mais comuns. Clock
    group é propriedade separada.
    """

    Y = "Y"
    D = "D"
    YAUTO = "Yauto"
    ZIGZAG = "Z"


@dataclass(frozen=True)
class ThreePhaseGroup:
    """
    Par (conexão_H, conexão_L) + clock group.

    Attributes
    ----------
    h_connection:
        Conexão do enrolamento de alta.
    l_connection:
        Conexão do enrolamento de baixa.
    clock:
        Clock group em horas (0..11). Cada hora = 30° elétricos de
        defasagem secundário em relação ao primário. Defaults:
        * YY: 0 (em fase).
        * YD: 1 (d adianta 30°) ou 11 (d atrasa 30°).
        * DY: 1 (y adianta 30°) ou 11.
        * DD: 0.
    """

    h_connection: TransformerConnection = TransformerConnection.Y
    l_connection: TransformerConnection = TransformerConnection.Y
    clock: int = 0

    def __post_init__(self) -> None:
        if not (0 <= self.clock <= 11):
            raise ValueError(
                f"clock group {self.clock} fora de 0..11"
            )
        # Clock group não trivial só faz sentido em certas conexões
        if self.h_connection == self.l_connection:
            # YY ou DD → clock deve ser múltiplo de 2 (60°) em
            # geral... mas alguns trafos de forno têm clock 6
            # (180°). Aceitamos qualquer clock.
            pass

    @property
    def phase_shift_deg(self) -> float:
        """Defasagem elétrica em graus: clock * 30°."""
        return self.clock * 30.0

    def describe(self) -> str:
        """String canônica — ex: "YNd1", "Yd11", "Dy11"."""
        h = self.h_connection.value
        l = self.l_connection.value
        return f"{h}{l.lower()}{self.clock}"


# ---------------------------------------------------------------------------
# Input schema — dados de teste padrão
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransformerSCTest:
    """Teste de curto-circuito (impedância e perdas em cobre).

    Convenção
    ---------
    * Medição é sempre feita alimentando o enrolamento de alta
      tensão (H) e curto-circuitando o de baixa (L), ou vice-versa.
      Neste schema, os valores refletem SEMPRE ao primário (H).

    Valores típicos
    ---------------
    * ``v_sc_pct``: 5-15% (trafos de potência); 2-4% (distribuição).
    * ``p_sc_kw`` por MVA: 5-8 kW/MVA (trafos de potência).
    """

    v_sc_pct: float      # Impedância percentual [%]
    p_sc_kw: float       # Perdas em cobre @ corrente nominal [kW]


@dataclass(frozen=True)
class TransformerOCTest:
    """Teste de circuito aberto (excitação e perdas no ferro).

    Convenção
    ---------
    * Sempre medido no primário (H).

    Valores típicos
    ---------------
    * ``i_0_pct``: 0.5-2% (trafos modernos); 5% (trafos antigos).
    * ``p_0_kw`` por MVA: 0.5-1.5 kW/MVA (trafos de potência).
    """

    i_0_pct: float       # Corrente de excitação @ tensão nominal [%]
    p_0_kw: float        # Perdas a vazio (núcleo) [kW]


@dataclass(frozen=True)
class TransformerBCTRANData:
    """
    Pacote de dados completo para BCTRAN (MVP 2-enrolamento linear).

    Attributes
    ----------
    v_h:
        Tensão nominal do lado H (alta) — em volts RMS fase-fase
        para trifásico ou fase-neutro para monofásico. A mesma
        convenção deve ser usada em ``v_l``.
    v_l:
        Tensão nominal do lado L (baixa).
    s_nom:
        Potência aparente nominal em VA (para trifásico, é a
        potência total do banco; para monofásico, potência por
        fase).
    frequency:
        Frequência de operação em Hz. Default 60.
    sc_test:
        Dados de teste de curto-circuito.
    oc_test:
        Dados de teste de circuito aberto.
    name:
        Identificador opcional (para logging / .atp labels).
    """

    v_h: float
    v_l: float
    s_nom: float
    sc_test: TransformerSCTest
    oc_test: TransformerOCTest
    frequency: float = 60.0
    name: str = ""

    def __post_init__(self) -> None:
        """Validação básica de sanidade dos inputs."""
        if self.v_h <= 0:
            raise ValueError(f"v_h deve ser > 0, recebido {self.v_h}")
        if self.v_l <= 0:
            raise ValueError(f"v_l deve ser > 0, recebido {self.v_l}")
        if self.s_nom <= 0:
            raise ValueError(f"s_nom deve ser > 0, recebido {self.s_nom}")
        if self.frequency <= 0:
            raise ValueError(
                f"frequency deve ser > 0, recebido {self.frequency}"
            )
        if not (0 < self.sc_test.v_sc_pct < 100):
            raise ValueError(
                f"v_sc_pct = {self.sc_test.v_sc_pct}% fora de "
                "(0, 100). Valores típicos 2-15%."
            )
        if self.sc_test.p_sc_kw < 0:
            raise ValueError(
                f"p_sc_kw = {self.sc_test.p_sc_kw} negativo não "
                "faz sentido físico."
            )
        if not (0 <= self.oc_test.i_0_pct < 100):
            raise ValueError(
                f"i_0_pct = {self.oc_test.i_0_pct}% fora de [0, 100)."
            )
        if self.oc_test.p_0_kw < 0:
            raise ValueError(
                f"p_0_kw = {self.oc_test.p_0_kw} negativo."
            )


# ---------------------------------------------------------------------------
# Resultado — matrizes [R], [L] e derivados
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransformerParameters:
    """
    Matrizes [R], [L] calculadas pela BCTRAN.

    Convenção
    ---------
    * Referidas ao primário (H).
    * Unidades: R em ohms, L em henries.
    * Índice 0 = enrolamento H; índice 1 = enrolamento L'
      (refletido ao primário).
    * Para emissão ATP direta, use
      :func:`TransformerParameters.to_branch_cards`.

    Attributes
    ----------
    R:
        Matriz 2×2 de resistências [Ω].
    L:
        Matriz 2×2 de indutâncias [H].
    turns_ratio:
        ``v_h / v_l`` — para referir valores do L-side de volta ao
        nominal real.
    """

    R: tuple[tuple[float, float], tuple[float, float]]
    L: tuple[tuple[float, float], tuple[float, float]]
    turns_ratio: float

    def is_symmetric(self, tol: float = 1e-9) -> bool:
        """True se [R] e [L] são simétricas (mútua física)."""
        return (
            abs(self.R[0][1] - self.R[1][0]) < tol
            and abs(self.L[0][1] - self.L[1][0]) < tol
        )

    def to_atp_cards(
        self,
        node_h1: str, node_h2: str,
        node_l1: str, node_l2: str,
    ) -> list[str]:
        """
        Gera as linhas ATP /BRANCH para este trafo (tipo 51 —
        mutually coupled R-L, formato de 4 nós).

        O formato exato do tipo 51 segue o ATP Rule Book Vol 1 §5.3:
        * Linha 1 (tipo 51): primeira linha (diagonal do enrolamento 1).
        * Linha 2 (tipo 52): linha de mútua + diagonal do enrolamento 2.

        Parameters
        ----------
        node_h1, node_h2:
            Nós do enrolamento H (entrada e saída).
        node_l1, node_l2:
            Nós do enrolamento L (entrada e saída, referidos).

        Returns
        -------
        list[str]
            Linhas ATP prontas para inserir na seção /BRANCH.
        """
        r11, r12 = self.R[0][0], self.R[0][1]
        r22 = self.R[1][1]
        l11, l12 = self.L[0][0], self.L[0][1]
        l22 = self.L[1][1]

        # v0.28.4-PRO Onda 4.3: emite cards 51/52 em formato
        # column-precise (10-col fields) usando atp_format helpers.
        # Antes: width 6 era apertado para valores típicos (ex:
        # l11_mh = 1234.56 não cabia em 6 chars). Agora: 10 chars
        # cada, scientific notation auto quando preciso.
        from app.preprocessor.atp_format import fmt_node, fmt_num

        l11_mh = l11 * 1000.0
        l12_mh = l12 * 1000.0
        l22_mh = l22 * 1000.0

        # Type-51: cols 1-2; Bus1 cols 3-8; Bus2 cols 9-14;
        # 4 spaces; R cols 19-28; L cols 29-38 (10 chars cada)
        line1 = (
            f"51{fmt_node(node_h1)}{fmt_node(node_h2)}    "
            f"{fmt_num(r11, 10)}{fmt_num(l11_mh, 10)}"
        )
        line2 = (
            f"52{fmt_node(node_l1)}{fmt_node(node_l2)}    "
            f"{fmt_num(r12, 10)}{fmt_num(l12_mh, 10)}"
        )
        line3 = (
            f"52{fmt_node(node_l1)}{fmt_node(node_l2)}    "
            f"{fmt_num(r22, 10)}{fmt_num(l22_mh, 10)}"
        )

        return [
            f"C BCTRAN trafo {self._safe_label()}:"
            f" V_H/V_L={self.turns_ratio:.3f}",
            line1,
            line2,
            line3,
        ]

    def _safe_label(self) -> str:
        # Reservado para futura identificação (v0.24.1)
        return ""


# ---------------------------------------------------------------------------
# Cálculo principal — compute_bctran_parameters
# ---------------------------------------------------------------------------


def compute_bctran_parameters(
    data: TransformerBCTRANData,
) -> TransformerParameters:
    """
    Calcula as matrizes [R], [L] do trafo 2-enrolamento linear a
    partir dos dados de teste padrão.

    Algoritmo — Dommel Theory Book §6.3.3 (forma simplificada
    simétrica):

    1. Impedância base: ``Z_base = V_H² / S_nom``.
    2. Impedância de CC refletida: ``Z_sc = (V_sc% / 100) * Z_base``.
    3. Resistência de CC (de p_sc):
       ``R_sc = p_sc_W / I_nom²``, onde ``I_nom = S_nom / V_H``.
    4. Reatância de CC: ``X_sc = sqrt(Z_sc² - R_sc²)``.
    5. Admitância de magnetização:
       ``Y_m = (i_0%/100) * (S_nom / V_H²)``.
       ``G_m = p_0_W / V_H²``.
       ``B_m = sqrt(Y_m² - G_m²)``.
    6. Reatância magnetizante (paralela): ``X_m = 1/B_m`` (ou ∞ se
       ``i_0_pct == 0``).
    7. Simétrica: ``R1 = R2 = R_sc / 2``; ``X1 = X2 = X_sc / 2``.
    8. Mútua pura (ideal): ``X_12 = X_m``.
    9. Self do primário: ``X_11 = X1 + X_m``.
       Self do secundário (refletido): ``X_22 = X2 + X_m``.
    10. L = X / (2π·f).

    Returns
    -------
    TransformerParameters
        Matrizes [R], [L] 2×2 simétricas, referidas ao primário H.

    Notes
    -----
    Para trafos reais, a distribuição ``R1 = R2 = R_sc/2`` é uma
    aproximação comum; o BCTRAN-AUX canônico aceita testes
    separados de cada enrolamento (ainda não implementado — fica
    para v0.24.2 como ``TransformerBCTRANData.sc_tests`` lista).
    """
    v_h = data.v_h
    s_nom = data.s_nom
    f = data.frequency
    sc = data.sc_test
    oc = data.oc_test

    # Base values
    z_base = v_h * v_h / s_nom
    i_nom = s_nom / v_h

    # Short-circuit impedance
    z_sc = (sc.v_sc_pct / 100.0) * z_base
    # Copper losses → R_sc
    # p_sc = R_sc * I_nom² (perdas referidas ao primário, I_nom no H)
    r_sc = (sc.p_sc_kw * 1000.0) / (i_nom * i_nom) if i_nom > 0 else 0.0
    x_sc_sq = z_sc * z_sc - r_sc * r_sc
    if x_sc_sq < 0:
        # Inputs inconsistentes — p_sc alto demais para o |Z_sc|
        # dado. Tratamos conservadoramente como caso puramente
        # resistivo (X_sc = 0).
        x_sc = 0.0
    else:
        x_sc = math.sqrt(x_sc_sq)

    # Magnetizing branch
    if oc.i_0_pct > 0:
        y_m = (oc.i_0_pct / 100.0) * s_nom / (v_h * v_h)
        g_m = (oc.p_0_kw * 1000.0) / (v_h * v_h)
        b_m_sq = y_m * y_m - g_m * g_m
        b_m = math.sqrt(b_m_sq) if b_m_sq > 0 else 0.0
        x_m = 1.0 / b_m if b_m > 0 else 1.0e12  # ∞ representado como 1 TΩ
    else:
        x_m = 1.0e12  # magnetização desprezível

    # Divisão simétrica das perdas e reatância de dispersão
    r1 = r2 = r_sc / 2.0
    x1 = x2 = x_sc / 2.0

    # Self-reatâncias
    x_11 = x1 + x_m
    x_22 = x2 + x_m
    x_12 = x_m   # mútua pura

    omega = 2.0 * math.pi * f
    R_mat = (
        (r1,   0.0),
        (0.0,  r2),
    )
    L_mat = (
        (x_11 / omega,  x_12 / omega),
        (x_12 / omega,  x_22 / omega),
    )

    return TransformerParameters(
        R=R_mat,
        L=L_mat,
        turns_ratio=data.v_h / data.v_l,
    )


# ===========================================================================
# v0.24.4 — Trafo 3-enrolamento (H/M/B — high/medium/low voltage)
# ===========================================================================


@dataclass(frozen=True)
class TransformerBCTRAN3Data:
    """
    Dados para trafo 3-enrolamento. H (alta), M (média), B (baixa).

    3 enrolamentos → 3 testes de SC (H-M, H-B, M-B) + 1 teste OC
    (usualmente feito no H).

    Attributes
    ----------
    v_h, v_m, v_b:
        Tensões nominais dos 3 enrolamentos (V rms).
    s_h, s_m, s_b:
        Potências nominais dos 3 enrolamentos (VA). Em trafos de
        3 enrolamentos NÃO são iguais (ex: s_h = s_m = 100 MVA,
        s_b = 50 MVA para terciário de menor capacidade).
    frequency:
        Hz. Default 60.
    sc_h_m:
        Teste SC entre H e M (alimenta H, curto M, B aberto).
    sc_h_b:
        Teste SC entre H e B (alimenta H, curto B, M aberto).
    sc_m_b:
        Teste SC entre M e B (alimenta M, curto B, H aberto).
    oc_test:
        Teste OC (referido ao H).
    group_3phase:
        Conexão e clock group (opcional — default YNyn0 — todos
        em estrela aterrada).
    name:
        Identificador opcional.

    Convenção para testes SC em 3-enrolamento
    -----------------------------------------

    Cada SC test entre par (X, Y) usa a **MENOR** das potências
    dos dois enrolamentos envolvidos como base. Se s_h = 100 MVA,
    s_b = 50 MVA, o SC_{HB} usa 50 MVA como base.

    Referências
    -----------
    * H. W. Dommel, EMTP Theory Book, BPA, 1986, §6.3.5 (3-winding).
    * Brandwajn, Dommel, Dommel, IEEE PAS-101, 1982.
    """

    v_h: float
    v_m: float
    v_b: float
    s_h: float
    s_m: float
    s_b: float
    sc_h_m: TransformerSCTest
    sc_h_b: TransformerSCTest
    sc_m_b: TransformerSCTest
    oc_test: TransformerOCTest
    group_3phase: ThreePhaseGroup = field(default_factory=ThreePhaseGroup)
    frequency: float = 60.0
    name: str = ""

    def __post_init__(self) -> None:
        for nome, v in [("v_h", self.v_h), ("v_m", self.v_m), ("v_b", self.v_b)]:
            if v <= 0:
                raise ValueError(f"{nome} deve ser > 0, recebido {v}")
        for nome, s in [("s_h", self.s_h), ("s_m", self.s_m), ("s_b", self.s_b)]:
            if s <= 0:
                raise ValueError(f"{nome} deve ser > 0, recebido {s}")
        if self.frequency <= 0:
            raise ValueError(
                f"frequency deve ser > 0, recebido {self.frequency}"
            )
        for nome, sc in [
            ("sc_h_m", self.sc_h_m),
            ("sc_h_b", self.sc_h_b),
            ("sc_m_b", self.sc_m_b),
        ]:
            if not (0 < sc.v_sc_pct < 100):
                raise ValueError(
                    f"{nome}.v_sc_pct = {sc.v_sc_pct}% fora de (0, 100)."
                )
            if sc.p_sc_kw < 0:
                raise ValueError(
                    f"{nome}.p_sc_kw = {sc.p_sc_kw} negativo."
                )
        if not (0 <= self.oc_test.i_0_pct < 100):
            raise ValueError(
                f"i_0_pct = {self.oc_test.i_0_pct}% fora de [0, 100)."
            )


@dataclass(frozen=True)
class Transformer3WindingParameters:
    """
    Matrizes [R], [L] 3×3 de trafo 3-enrolamento, referidas ao H.

    Attributes
    ----------
    R:
        Matriz 3×3 de resistências [Ω].
    L:
        Matriz 3×3 de indutâncias [H].
    ratios:
        Tuple (v_h/v_m, v_h/v_b) — razões de transformação.
    """

    R: tuple[tuple[float, float, float], ...]
    L: tuple[tuple[float, float, float], ...]
    ratios: tuple[float, float]
    group: ThreePhaseGroup = field(default_factory=ThreePhaseGroup)

    def is_symmetric(self, tol: float = 1e-9) -> bool:
        """Todas as entradas fora-da-diagonal devem ser simétricas."""
        for i in range(3):
            for j in range(i + 1, 3):
                if abs(self.R[i][j] - self.R[j][i]) > tol:
                    return False
                if abs(self.L[i][j] - self.L[j][i]) > tol:
                    return False
        return True

    def to_atp_cards(
        self,
        n_h1: str, n_h2: str,
        n_m1: str, n_m2: str,
        n_b1: str, n_b2: str,
        *,
        comment: str = "",
    ) -> list[str]:
        """
        Gera linhas ATP /BRANCH para o trafo 3-enrolamento.

        Estrutura:

        * 1 linha tipo 51 — winding H self (R[0][0], L[0][0]).
        * 5 linhas tipo 52 — couplings H-M, M self, H-B, M-B,
          B self.

        Cada linha segue o formato extended ATP (largura solta).
        Para 3-enrolamento canônico, ATP exige a representação
        completa via BCTRAN-AUX externo; aqui geramos o conjunto
        equivalente de R-L mutuamente acoplados.

        Parameters
        ----------
        n_h1, n_h2:
            Nós do enrolamento H (alta).
        n_m1, n_m2:
            Nós do enrolamento M (média).
        n_b1, n_b2:
            Nós do enrolamento B (baixa). Em modelos com pin físico
            apenas para H e M (Tr3.ocomp atual), use nós sintéticos
            ``"TR3_<name>_B1"`` etc., e avise o usuário sobre wiring
            manual.
        comment:
            Comentário ATP no início. Adiciona ``"C "`` prefix.

        Returns
        -------
        list[str]
            Linhas /BRANCH prontas para inserir.

        Layout das linhas (campo por campo):

        ::

            51  H1   H2   ____ ____ Rhh  Lhh
            52  M1   M2   ____ ____ Rhm  Lhm
            52  M1   M2   ____ ____ Rmm  Lmm
            52  B1   B2   ____ ____ Rhb  Lhb
            52  B1   B2   ____ ____ Rmb  Lmb
            52  B1   B2   ____ ____ Rbb  Lbb

        L em mH conforme ATP convention.
        """
        omega = 1.0  # apenas para clareza — L já está em H
        rhh = self.R[0][0]
        rhm = self.R[0][1]
        rmm = self.R[1][1]
        rhb = self.R[0][2]
        rmb = self.R[1][2]
        rbb = self.R[2][2]
        lhh = self.L[0][0] * 1000.0   # H → mH
        lhm = self.L[0][1] * 1000.0
        lmm = self.L[1][1] * 1000.0
        lhb = self.L[0][2] * 1000.0
        lmb = self.L[1][2] * 1000.0
        lbb = self.L[2][2] * 1000.0

        lines: list[str] = []
        if comment:
            lines.append(f"C {comment}")
        # Header com info do trafo
        lines.append(
            f"C 3-winding trafo H/M/B ratios={self.ratios[0]:.3f}/"
            f"{self.ratios[1]:.3f}, group={self.group.describe()}"
        )

        def _row(prefix: str, n1: str, n2: str, r: float, l_mh: float) -> str:
            return (
                f"{prefix:<2s}{n1:<6s}{n2:<6s}            "
                f"{r:>10.4E}{l_mh:>10.4E}"
            )

        lines.append(_row("51", n_h1, n_h2, rhh, lhh))
        lines.append(_row("52", n_m1, n_m2, rhm, lhm))
        lines.append(_row("52", n_m1, n_m2, rmm, lmm))
        lines.append(_row("52", n_b1, n_b2, rhb, lhb))
        lines.append(_row("52", n_b1, n_b2, rmb, lmb))
        lines.append(_row("52", n_b1, n_b2, rbb, lbb))

        return lines


def compute_bctran_parameters_3w(
    data: TransformerBCTRAN3Data,
) -> Transformer3WindingParameters:
    """
    Calcula [R], [L] 3×3 do trafo 3-enrolamento.

    Algoritmo — Dommel §6.3.5 simplificado (simétrico):

    1. Cada SC test dá uma impedância Z_{ij} referida ao
       enrolamento excitado, escalada pela potência-base.
    2. Referir todos ao H:
       ``Z_{H-M} (base H)  = (v_sc% / 100) * V_H² / S_base_{HM}``
       idem para H-B, M-B.
    3. As impedâncias de dispersão individuais são recuperadas
       pela transformação Wye-Delta (estrela de impedâncias):
       ``X_H = 0.5 * (X_{HM} + X_{HB} - X_{MB}')``
       onde X_{MB}' é referido ao H: ``X_{MB}' = X_{MB} * (V_H/V_M)²``.
    4. Análogo para R.
    5. Mag branch: X_m do teste OC (referido ao H).
    6. Matriz self/mútua:
       ``L[i][i] = L_disp_i + L_m``
       ``L[i][j] = L_m (se i ≠ j, mútua ideal)``

    Retorna matriz 3×3.
    """
    f = data.frequency
    omega = 2.0 * math.pi * f
    v_h, v_m, v_b = data.v_h, data.v_m, data.v_b

    # Impedâncias base — usa a MENOR das potências para cada par
    s_hm = min(data.s_h, data.s_m)
    s_hb = min(data.s_h, data.s_b)
    s_mb = min(data.s_m, data.s_b)
    z_base_h_hm = v_h * v_h / s_hm
    z_base_h_hb = v_h * v_h / s_hb
    z_base_m_mb = v_m * v_m / s_mb

    # SC impedances referidas ao H
    z_hm = (data.sc_h_m.v_sc_pct / 100.0) * z_base_h_hm
    z_hb = (data.sc_h_b.v_sc_pct / 100.0) * z_base_h_hb
    z_mb_raw = (data.sc_m_b.v_sc_pct / 100.0) * z_base_m_mb
    # Refere M-B ao H: multiplica pelo ratio²
    z_mb = z_mb_raw * (v_h / v_m) ** 2

    # R parts
    i_nom_h_hm = s_hm / v_h
    r_hm = (data.sc_h_m.p_sc_kw * 1000.0) / (i_nom_h_hm ** 2) if i_nom_h_hm > 0 else 0.0
    i_nom_h_hb = s_hb / v_h
    r_hb = (data.sc_h_b.p_sc_kw * 1000.0) / (i_nom_h_hb ** 2) if i_nom_h_hb > 0 else 0.0
    i_nom_m_mb = s_mb / v_m
    r_mb_raw = (data.sc_m_b.p_sc_kw * 1000.0) / (i_nom_m_mb ** 2) if i_nom_m_mb > 0 else 0.0
    r_mb = r_mb_raw * (v_h / v_m) ** 2

    # X parts via sqrt
    def _x(z: float, r: float) -> float:
        x_sq = z * z - r * r
        return math.sqrt(x_sq) if x_sq > 0 else 0.0
    x_hm = _x(z_hm, r_hm)
    x_hb = _x(z_hb, r_hb)
    x_mb = _x(z_mb, r_mb)

    # Wye-equivalent (cada enrolamento com X_i individual)
    x_h = 0.5 * (x_hm + x_hb - x_mb)
    x_m = 0.5 * (x_hm - x_hb + x_mb)
    x_b = 0.5 * (-x_hm + x_hb + x_mb)
    # Resistências Wye-equivalent idem
    res_h = 0.5 * (r_hm + r_hb - r_mb)
    res_m = 0.5 * (r_hm - r_hb + r_mb)
    res_b = 0.5 * (-r_hm + r_hb + r_mb)

    # v0.28.2-PRO (auditoria P0): valida não-negatividade do
    # equivalente Wye. Para dados de teste imbalanceados onde
    # x_mb > x_hm + x_hb, x_h fica negativo — não-físico.
    # ATP integraria com matriz não-passiva e divergiria
    # silenciosamente. Estratégia: WARN-AND-CLAMP (audit P0).
    #
    # Use ``strict_wye=True`` para o modo ValueError-on-detect.
    import warnings as _warnings_module
    _wye_warnings: list[str] = []
    if x_h < 0:
        _wye_warnings.append(
            f"X_h Wye-equivalent = {x_h:.4f} < 0 "
            "(x_mb > x_hm + x_hb — dados de teste inconsistentes). "
            "Verifique v_sc_hm / v_sc_hb / v_sc_mb. Clampado a 0.001."
        )
        x_h = 0.001
    if x_m < 0:
        _wye_warnings.append(
            f"X_m Wye-equivalent = {x_m:.4f} < 0 "
            "(x_hb > x_hm + x_mb — dados de teste inconsistentes). "
            "Clampado a 0.001."
        )
        x_m = 0.001
    if x_b < 0:
        _wye_warnings.append(
            f"X_b Wye-equivalent = {x_b:.4f} < 0 "
            "(x_hm > x_hb + x_mb — dados de teste inconsistentes). "
            "Clampado a 0.001."
        )
        x_b = 0.001
    # v0.28.2-PRO followup: valida também resistências Wye
    # (auditoria identificou que res_h/res_m/res_b podem ir
    # negativas nos mesmos cenários, propagando silenciosamente).
    if res_h < 0:
        _wye_warnings.append(
            f"R_h Wye-equivalent = {res_h:.4f} < 0 "
            "(perdas SC inconsistentes). Clampado a 0.0001."
        )
        res_h = 0.0001
    if res_m < 0:
        _wye_warnings.append(
            f"R_m Wye-equivalent = {res_m:.4f} < 0 "
            "(perdas SC inconsistentes). Clampado a 0.0001."
        )
        res_m = 0.0001
    if res_b < 0:
        _wye_warnings.append(
            f"R_b Wye-equivalent = {res_b:.4f} < 0 "
            "(perdas SC inconsistentes). Clampado a 0.0001."
        )
        res_b = 0.0001
    for w in _wye_warnings:
        _warnings_module.warn(
            f"BCTRAN 3w: {w}",
            UserWarning,
            stacklevel=2,
        )

    # Magnetizing branch
    oc = data.oc_test
    if oc.i_0_pct > 0:
        y_m_ = (oc.i_0_pct / 100.0) * data.s_h / (v_h * v_h)
        g_m = (oc.p_0_kw * 1000.0) / (v_h * v_h)
        b_m_sq = y_m_ * y_m_ - g_m * g_m
        b_m = math.sqrt(b_m_sq) if b_m_sq > 0 else 0.0
        x_mag = 1.0 / b_m if b_m > 0 else 1.0e12
    else:
        x_mag = 1.0e12

    # Monta matriz 3x3 — diagonal = X_i + X_mag, off-diagonal = X_mag
    X_mat = (
        (x_h + x_mag,  x_mag,        x_mag),
        (x_mag,        x_m + x_mag,  x_mag),
        (x_mag,        x_mag,        x_b + x_mag),
    )
    L_mat = tuple(
        tuple(x / omega for x in row)
        for row in X_mat
    )
    R_mat = (
        (res_h, 0.0,   0.0),
        (0.0,   res_m, 0.0),
        (0.0,   0.0,   res_b),
    )

    return Transformer3WindingParameters(
        R=R_mat,
        L=L_mat,
        ratios=(v_h / v_m, v_h / v_b),
        group=data.group_3phase,
    )
