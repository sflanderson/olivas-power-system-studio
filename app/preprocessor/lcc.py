"""
app.preprocessor.lcc — rotina LCC (Line/Cable Constants) para
cálculo de matrizes [Z] e [Y] de linhas aéreas a partir da
geometria de condutores.

Rotina análoga ao BCTRAN, mas para linhas de transmissão. Recebe
posições, raios e resistências dos condutores + resistividade do
solo, retorna impedância série e admitância shunt por km.

Referências
-----------
* H. W. Dommel, EMTP Theory Book, BPA, 1986, Ch. 4 §4.1.
* J. R. Carson, "Wave propagation in overhead wires with ground
  return", Bell Syst. Tech. J., 1926.
* M. M. de Albuquerque-Mont'Alverne, EMTP-RV Reference Manual,
  Vol 9 (Line Constants).
* G. Deri & G. Tevan, "Complex ground return for transmission
  line calculations", IEEE Trans. PAS-100, 1981. — fórmula
  simplificada de profundidade complexa para correção Carson.
* ATP Rule Book Vol 2 §9 (LINE-PARAMETERS / LINE-MODEL).

Escopo (v0.25.0 — MVP)
----------------------

* **Single-frequency** — calcula [Z(ω)], [Y(ω)] num único f.
  Sweep frequencial + fitting rational-function (JMARTI .pch)
  ficam para v0.25.x+.
* **Linhas aéreas** — usa correção de Carson via complex ground
  depth (Deri-Tévan). Cabos subterrâneos com bainha (Cable
  Constants) ficam para v0.25.x+.
* **Sem bundling** — cada "conductor" é um único condutor físico.
  Phase grouping e bundle reduction (eigenvalue) ficam para
  v0.25.2.
* **Solo homogêneo** — single ρ value. Soils estratificados
  (multilayer) — fora de escopo.

Dado:
* N condutores com (x_i, y_i, raio_i, R_dc_i) e altura acima do solo.
* Resistividade do solo ρ (Ω·m).
* Frequência f (Hz).

Saída:
* [Z(ω)] complexa, N×N, em Ω/km — impedância série.
* [Y(ω)] complexa, N×N, em S/km — admitância shunt.

Algoritmo
---------

**Self-impedance** (Carson simplificado / Deri-Tévan):
``Z_ii = R_dc + jω(μ₀/2π) [ln(2h_i / GMR_i) + ln(1 + p/h_i)]``

onde:
* μ₀/(2π) = 2×10⁻⁷ H/m
* h_i = altura acima do solo (m)
* GMR_i = raio médio geométrico ≈ 0.7788 × r_outer (condutor sólido)
* p = profundidade complexa de penetração no solo
       = √(ρ / (jωμ₀))

**Mutual-impedance**:
``Z_ij = jω(μ₀/2π) [ln(D_ij' / d_ij) + ln(1 + p/H_ij)]``

onde:
* d_ij = distância entre condutores i, j
* D_ij' = distância de i até a IMAGEM de j (no solo)
* H_ij = (h_i + h_j)/2 — altura média

**Shunt admittance** (Maxwell, sem correção Carson — usual em
linhas aéreas onde G ≈ 0):
``[P]_ii = (1/2πε₀) ln(2h_i / r_outer_i)``
``[P]_ij = (1/2πε₀) ln(D_ij' / d_ij)``
``[C] = [P]⁻¹``  (capacitância por m)
``[Y] = G + jω[C] ≈ jω[C]``
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass, field
from typing import Optional, Sequence


# Constantes físicas
MU_0_OVER_2PI = 2.0e-7   # H/m
EPS_0 = 8.8541878128e-12  # F/m
INV_2PI_EPS0 = 1.0 / (2.0 * math.pi * EPS_0)  # ~1.79767e10


# ---------------------------------------------------------------------------
# Schema: condutor e geometria de linha
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Conductor:
    """
    Um condutor físico de uma linha aérea.

    Attributes
    ----------
    name:
        Nome humano (ex: "phase_a", "neutral", "shield").
    x:
        Coordenada horizontal em metros (eixo perpendicular à linha).
    y:
        Altura acima do solo em metros (eixo vertical, > 0).
    radius_outer:
        Raio externo do condutor em metros (ex: 0.015 = 15 mm de
        raio para um condutor ACSR típico).
    R_dc_per_km:
        Resistência DC ou de baixa-frequência em Ω/km. Para AC
        aproximada, multiplique por fator de skin se necessário.
    gmr:
        Geometric Mean Radius em metros. Default = 0.7788 ×
        radius_outer (condutor sólido cilíndrico). Para condutores
        encordoados (ACSR, AAAC), use o valor do datasheet —
        tipicamente 0.7×r ... 0.85×r.
    """

    name: str
    x: float
    y: float
    radius_outer: float
    R_dc_per_km: float
    gmr: Optional[float] = None

    def __post_init__(self) -> None:
        if self.y <= 0:
            raise ValueError(
                f"Conductor {self.name!r}: y = {self.y} (deve ser > 0; "
                "altura acima do solo)"
            )
        if self.radius_outer <= 0:
            raise ValueError(
                f"Conductor {self.name!r}: radius_outer = {self.radius_outer} "
                "(deve ser > 0)"
            )
        if self.R_dc_per_km < 0:
            raise ValueError(
                f"Conductor {self.name!r}: R_dc_per_km negativo"
            )

    def effective_gmr(self) -> float:
        """GMR efetivo — fornecido ou calculado para condutor sólido."""
        if self.gmr is not None and self.gmr > 0:
            return self.gmr
        return 0.7788 * self.radius_outer


@dataclass(frozen=True)
class LineGeometry:
    """
    Geometria completa de uma linha aérea.

    Attributes
    ----------
    conductors:
        Lista de condutores físicos (≥ 1).
    soil_resistivity:
        Resistividade do solo em Ω·m. Valores típicos:
        100 (terra molhada), 1000 (média), 10000 (rocha).
    frequency:
        Frequência de operação em Hz para cálculo Carson-Deri-Tévan.
        Default 60.
    """

    conductors: list[Conductor]
    soil_resistivity: float = 100.0
    frequency: float = 60.0

    def __post_init__(self) -> None:
        if not self.conductors:
            raise ValueError("conductors não pode ser vazio")
        if self.soil_resistivity <= 0:
            raise ValueError(
                f"soil_resistivity = {self.soil_resistivity} ≤ 0"
            )
        if self.frequency <= 0:
            raise ValueError(
                f"frequency = {self.frequency} ≤ 0"
            )
        # Verifica nomes únicos
        names = [c.name for c in self.conductors]
        if len(set(names)) != len(names):
            raise ValueError(
                f"Nomes de condutores duplicados em {names}"
            )


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LineConstants:
    """
    Matrizes [Z(ω)] e [Y(ω)] complexas, por km.

    Attributes
    ----------
    Z:
        Matriz N×N de impedância série complexa em Ω/km.
        ``Z[i][j] = R_ij(ω) + j·ωL_ij(ω)``.
    Y:
        Matriz N×N de admitância shunt complexa em S/km.
        ``Y[i][j] = G_ij + j·ωC_ij ≈ j·ωC_ij``.
    frequency:
        Frequência usada no cálculo (Hz).
    conductor_names:
        Nomes dos condutores na ordem das linhas/colunas das
        matrizes — útil para debug e relatórios.
    """

    Z: tuple[tuple[complex, ...], ...]
    Y: tuple[tuple[complex, ...], ...]
    frequency: float
    conductor_names: tuple[str, ...]

    @property
    def n(self) -> int:
        """Número de condutores (dimensão das matrizes)."""
        return len(self.conductor_names)

    def is_symmetric(self, tol: float = 1e-9) -> bool:
        """[Z] e [Y] devem ser simétricas (linhas reciprocas)."""
        for i in range(self.n):
            for j in range(i + 1, self.n):
                if abs(self.Z[i][j] - self.Z[j][i]) > tol:
                    return False
                if abs(self.Y[i][j] - self.Y[j][i]) > tol:
                    return False
        return True


# ---------------------------------------------------------------------------
# Geometric helpers
# ---------------------------------------------------------------------------


def distance_between(c1: Conductor, c2: Conductor) -> float:
    """Distância euclidiana 3D entre dois condutores (mesma linha)."""
    return math.hypot(c1.x - c2.x, c1.y - c2.y)


def image_distance(c1: Conductor, c2: Conductor) -> float:
    """
    Distância entre c1 e a IMAGEM de c2 (refletida através do
    plano do solo, y → -y).
    """
    return math.hypot(c1.x - c2.x, c1.y + c2.y)


def complex_ground_depth(rho: float, frequency: float) -> complex:
    """
    Profundidade complexa de penetração no solo (Deri-Tévan):
    ``p = √(ρ / (jωμ₀))``.

    Para correção de Carson em linhas aéreas. Unidade: metros.
    """
    omega = 2.0 * math.pi * frequency
    mu_0 = 4.0 * math.pi * 1.0e-7   # H/m
    # p² = ρ / (jωμ₀)
    p_sq = rho / (1j * omega * mu_0)
    return cmath.sqrt(p_sq)


# ---------------------------------------------------------------------------
# Algoritmo principal — compute_line_constants
# ---------------------------------------------------------------------------


def compute_line_constants(geometry: LineGeometry) -> LineConstants:
    """
    Calcula matrizes [Z] e [Y] da linha à frequência ``geometry.frequency``.

    Parameters
    ----------
    geometry:
        Geometria completa da linha.

    Returns
    -------
    LineConstants
        Matrizes Z (Ω/km) e Y (S/km), simétricas.

    Algorithm
    ---------
    Para cada par (i, j):

    * **i == j** (self):
        Z_ii = (R_dc_i + jωL_air_self) + Z_ground_correction
      onde:
        L_air_self = (μ₀/2π) ln(2h_i / GMR_i)
        Z_ground_correction = jω(μ₀/2π) ln(1 + p/h_i)

    * **i != j** (mutual):
        Z_ij = jω(μ₀/2π) ln(D_ij' / d_ij)
              + jω(μ₀/2π) ln(1 + p / H_ij_avg)

    Para Y:
        P_ii = INV_2PI_EPS0 · ln(2h_i / r_i)
        P_ij = INV_2PI_EPS0 · ln(D_ij' / d_ij)
        C = P^(-1)
        Y = jω·C

    Os valores são em Ω/m e S/m, multiplicados por 1000 no fim
    para converter à convenção ATP de Ω/km e S/km.
    """
    conductors = geometry.conductors
    n = len(conductors)
    f = geometry.frequency
    omega = 2.0 * math.pi * f
    rho = geometry.soil_resistivity

    p_complex = complex_ground_depth(rho, f)

    # ── [Z] série (Ω/m) ──────────────────────────────────────
    Z_per_m: list[list[complex]] = [
        [0.0 + 0j for _ in range(n)] for _ in range(n)
    ]
    # ── [P] potential coefficient (m/F = 1/(F/m)) ────────────
    P: list[list[float]] = [[0.0] * n for _ in range(n)]

    for i in range(n):
        ci = conductors[i]
        gmr_i = ci.effective_gmr()
        # Self impedance
        # R_dc per km → per m: divide por 1000
        r_dc_per_m = ci.R_dc_per_km / 1000.0
        # Indutância do ar (self): L_air = (μ₀/2π) ln(2h/GMR)
        l_air_self = MU_0_OVER_2PI * math.log(2.0 * ci.y / gmr_i)
        # Correção do solo: jω(μ₀/2π) ln(1 + p/h)
        z_ground_self = (
            1j * omega * MU_0_OVER_2PI
            * cmath.log(1.0 + p_complex / ci.y)
        )
        Z_per_m[i][i] = r_dc_per_m + 1j * omega * l_air_self + z_ground_self

        # Self potential
        P[i][i] = INV_2PI_EPS0 * math.log(2.0 * ci.y / ci.radius_outer)

        # Mutuals (j > i; depois copiamos por simetria)
        for j in range(i + 1, n):
            cj = conductors[j]
            d_ij = distance_between(ci, cj)
            D_img = image_distance(ci, cj)
            if d_ij <= 0:
                raise ValueError(
                    f"Condutores {ci.name!r} e {cj.name!r} estão na "
                    "mesma posição (distância zero)"
                )
            # Mutual indutância do ar
            l_air_mut = MU_0_OVER_2PI * math.log(D_img / d_ij)
            # Correção do solo (uses média geométrica das alturas)
            h_avg = math.sqrt(ci.y * cj.y)  # geometric mean — robust para alturas similares
            z_ground_mut = (
                1j * omega * MU_0_OVER_2PI
                * cmath.log(1.0 + p_complex / h_avg)
            )
            Z_per_m[i][j] = 1j * omega * l_air_mut + z_ground_mut
            Z_per_m[j][i] = Z_per_m[i][j]

            # Mutual potential
            P[i][j] = INV_2PI_EPS0 * math.log(D_img / d_ij)
            P[j][i] = P[i][j]

    # ── [Y] shunt: Y = jω · P^(-1) ──────────────────────────
    # Inverte P (matriz real, simétrica, pos-definida)
    C_per_m = _invert_symmetric_real(P)
    Y_per_m: list[list[complex]] = [
        [1j * omega * C_per_m[i][j] for j in range(n)] for i in range(n)
    ]

    # ── Convert para per km ────────────────────────────────
    Z_per_km = tuple(
        tuple(z * 1000.0 for z in row) for row in Z_per_m
    )
    Y_per_km = tuple(
        tuple(y * 1000.0 for y in row) for row in Y_per_m
    )

    return LineConstants(
        Z=Z_per_km,
        Y=Y_per_km,
        frequency=f,
        conductor_names=tuple(c.name for c in conductors),
    )


# ---------------------------------------------------------------------------
# Helper: inversão de matriz real simétrica via Gauss-Jordan
# ---------------------------------------------------------------------------


def _invert_symmetric_real(P: list[list[float]]) -> list[list[float]]:
    """
    Inverte matriz N×N real simétrica via Gauss-Jordan com
    pivoteamento parcial. N pequeno (< 10 condutores típicos),
    então não precisamos de numpy.

    Levanta ValueError se a matriz for singular.
    """
    n = len(P)
    # Cria matriz aumentada [P | I]
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)]
           for i, row in enumerate(P)]

    for col in range(n):
        # Pivot — encontra linha com maior |valor| nesta coluna
        pivot_row = col
        for r in range(col + 1, n):
            if abs(aug[r][col]) > abs(aug[pivot_row][col]):
                pivot_row = r
        if abs(aug[pivot_row][col]) < 1e-15:
            raise ValueError(
                f"Matriz P singular na coluna {col} — verifique "
                "geometria (condutores muito próximos do solo?)."
            )
        # Troca linhas
        aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        # Normaliza linha do pivot
        pivot = aug[col][col]
        for k in range(2 * n):
            aug[col][k] /= pivot
        # Elimina coluna nas outras linhas
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor == 0:
                continue
            for k in range(2 * n):
                aug[r][k] -= factor * aug[col][k]

    # Extrai inversa
    return [row[n:] for row in aug]


# ===========================================================================
# v0.25.1 — Componentes de sequência positiva (linha 3φ transposta)
# ===========================================================================


@dataclass(frozen=True)
class PositiveSequenceParams:
    """
    Parâmetros de sequência positiva de uma linha 3φ transposta.

    Para uma linha 3φ TRANSPOSTA, a impedância vista de uma fase é:
    ``Z_pos = Z_self_avg - Z_mutual_avg``
    onde:
    * Z_self_avg = média das diagonais.
    * Z_mutual_avg = média das off-diagonais.

    A relação z = (R + jωL) é separável:
    ``R_pos_per_km = Re(Z_pos)``
    ``L_pos_per_km = Im(Z_pos) / ω``

    Idem para Y_pos:
    ``Y_pos_per_km = Y_self_avg - Y_mutual_avg``
    ``C_pos_per_km = Im(Y_pos) / ω``

    Para linhas NÃO-transpostas, esta aproximação introduz erro
    (assimetria entre fases é ignorada). Para MVP da v0.25.1
    é aceitável como aproximação para PI lumped.

    Attributes
    ----------
    R_per_km, L_per_km, C_per_km:
        Parâmetros de sequência positiva por km. R em Ω/km,
        L em H/km, C em F/km (note: F/km, multiplicar por
        comprimento dá farads totais).
    frequency:
        Frequência usada no cálculo.
    """

    R_per_km: float
    L_per_km: float
    C_per_km: float
    frequency: float


def compute_positive_sequence(lc: LineConstants) -> PositiveSequenceParams:
    """
    Reduz uma matriz [Z][Y] 3×3 (ou maior) a parâmetros de
    sequência positiva, assumindo linha transposta.

    Para n condutores: pega a média das diagonais (Z_self_avg) e
    a média das off-diagonais (Z_mutual_avg). Z_pos = avg_self -
    avg_mutual.

    Levanta ValueError se ``lc.n < 1`` ou se ω = 0 (não pode
    extrair L/C de uma medição DC).
    """
    if lc.n < 1:
        raise ValueError("LineConstants vazio")
    omega = 2.0 * math.pi * lc.frequency
    if omega == 0:
        raise ValueError("frequency=0 — não pode extrair L/C")

    n = lc.n
    z_diag_sum = sum(lc.Z[i][i] for i in range(n))
    y_diag_sum = sum(lc.Y[i][i] for i in range(n))

    if n == 1:
        # Caso degenerado: 1 condutor → não há mútua
        z_pos = z_diag_sum
        y_pos = y_diag_sum
    else:
        # n > 1: tira off-diagonais
        z_off_count = n * (n - 1)
        y_off_count = z_off_count
        z_off_sum = complex(0)
        y_off_sum = complex(0)
        for i in range(n):
            for j in range(n):
                if i != j:
                    z_off_sum += lc.Z[i][j]
                    y_off_sum += lc.Y[i][j]
        z_self_avg = z_diag_sum / n
        z_mutual_avg = z_off_sum / z_off_count
        y_self_avg = y_diag_sum / n
        y_mutual_avg = y_off_sum / y_off_count
        z_pos = z_self_avg - z_mutual_avg
        y_pos = y_self_avg - y_mutual_avg

    return PositiveSequenceParams(
        R_per_km=z_pos.real,
        L_per_km=z_pos.imag / omega,
        C_per_km=y_pos.imag / omega,
        frequency=lc.frequency,
    )


# ---------------------------------------------------------------------------
# v0.25.1 — Helper para construir LineGeometry de uma linha 3φ horizontal
# ou vertical típica
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BergeronParams:
    """
    Parâmetros do modelo Bergeron (linha distribuída sem perdas
    + dependência de frequência) — sequência positiva.

    Attributes
    ----------
    Z_char_pos:
        Impedância característica em Ω. Para linha sem perdas:
        ``Z_c = √(L/C)``. Com perdas leves, parte real de
        ``√(Z/Y)``.
    travel_time:
        Tempo de propagação ``τ = ℓ/v = ℓ·√(LC)`` em segundos.
        ``v = 1/√(LC)`` em m/s.
    R_total:
        Resistência total da linha (Ω) — concentrada nas duas
        extremidades + meio para minimizar erro de Bergeron sem
        perdas.
    velocity:
        Velocidade de propagação ``v`` em m/s. Para linhas
        aéreas tipicamente próximo a c (3×10⁸ m/s) com fator
        ~0.95 - 0.97.
    length_km:
        Comprimento da linha em km — útil para validação visual.
    """

    Z_char_pos: float
    travel_time: float
    R_total: float
    velocity: float
    length_km: float


def compute_bergeron_pos_sequence(
    geometry: LineGeometry,
    length_km: float,
) -> BergeronParams:
    """
    Computa parâmetros Bergeron de sequência positiva para a
    linha descrita por ``geometry`` com comprimento ``length_km``.

    Algoritmo:

    1. Computa ``[Z]``, ``[Y]`` via ``compute_line_constants``.
    2. Reduz a seq+ via ``compute_positive_sequence``: R, L, C
       por km.
    3. Z_char = √(L/C) (linha sem perdas, OK para Bergeron com
       perdas concentradas).
    4. v = 1/√(L·C) m/s.
    5. τ = comprimento / v = (length_km × 1000) / v segundos.
    6. R_total = R_pos × length_km — concentrada (Bergeron
       distribui em 2-3 pontos).

    Returns
    -------
    BergeronParams
    """
    if length_km <= 0:
        raise ValueError(f"length_km = {length_km} ≤ 0")
    lc = compute_line_constants(geometry)
    ps = compute_positive_sequence(lc)

    if ps.L_per_km <= 0 or ps.C_per_km <= 0:
        raise ValueError(
            f"L_per_km = {ps.L_per_km}, C_per_km = {ps.C_per_km} — "
            "L e C devem ser > 0 para Bergeron"
        )

    z_char = math.sqrt(ps.L_per_km / ps.C_per_km)
    # Velocidade em m/s. L em H/km = H/(1000m) → L_per_m = L_per_km/1000.
    # v = 1/√(L_per_m · C_per_m) = 1/√((L_pkm/1000)·(C_pkm/1000))
    # = 1000/√(L_pkm·C_pkm)
    v = 1000.0 / math.sqrt(ps.L_per_km * ps.C_per_km)
    tau = (length_km * 1000.0) / v   # segundos
    r_total = ps.R_per_km * length_km

    return BergeronParams(
        Z_char_pos=z_char,
        travel_time=tau,
        R_total=r_total,
        velocity=v,
        length_km=length_km,
    )


@dataclass(frozen=True)
class FrequencySweep:
    """
    Resultado de um varredura frequencial: para cada frequência,
    armazena a LineConstants correspondente.

    Útil para fittings rational-function (vector-fitting,
    Marti, Gustavsen-Semlyen) que precisam de Z(ω) e A(ω) em
    múltiplos pontos.

    Attributes
    ----------
    frequencies:
        Tupla de frequências (Hz) em ordem crescente.
    constants:
        Tupla de LineConstants — uma por frequência.
    """

    frequencies: tuple[float, ...]
    constants: tuple[LineConstants, ...]

    @property
    def n_freq(self) -> int:
        return len(self.frequencies)


def compute_frequency_sweep(
    geometry: LineGeometry,
    frequencies: Sequence[float],
) -> FrequencySweep:
    """
    Calcula LineConstants em múltiplas frequências.

    A geometry original é usada como template; para cada
    ``f`` em ``frequencies``, criamos uma cópia da geometry com
    ``frequency`` substituído e chamamos ``compute_line_constants``.

    Parameters
    ----------
    geometry:
        Geometria base (a frequency original é IGNORADA — só
        os condutores e ρ são usados).
    frequencies:
        Lista de frequências em Hz, em ordem crescente.

    Returns
    -------
    FrequencySweep
    """
    if not frequencies:
        raise ValueError("frequencies não pode ser vazio")
    sorted_freqs = tuple(sorted(set(frequencies)))
    if any(f <= 0 for f in sorted_freqs):
        raise ValueError("frequências devem ser > 0")

    results = []
    for f in sorted_freqs:
        # Cria nova geometry com frequência específica
        geom_at_f = LineGeometry(
            conductors=geometry.conductors,
            soil_resistivity=geometry.soil_resistivity,
            frequency=f,
        )
        results.append(compute_line_constants(geom_at_f))
    return FrequencySweep(
        frequencies=sorted_freqs,
        constants=tuple(results),
    )


@dataclass(frozen=True)
class PropagationFunction:
    """
    Função de propagação A(ω) e impedância característica Z_c(ω)
    para sequência positiva — entradas para fitting JMARTI.

    Convenções (Marti 1982):
    * ``A(ω) = exp(-γ·ℓ)`` onde ``γ = √((R + jωL)(G + jωC))``.
      Função de transferência da onda viajante.
    * ``Z_c(ω) = √((R + jωL)/(G + jωC))`` — impedância
      característica.

    Em alta frequência, Z_c → √(L/C) (real puro) e A magnitude
    → ``e^(-α·ℓ)`` onde α = R/(2Z_c) (atenuação suave).

    Attributes
    ----------
    frequencies:
        Hz em ordem crescente.
    Zc:
        Tupla de Z_c(ω) complexos por frequência. Ω.
    A:
        Tupla de A(ω) complexos por frequência. Adimensional
        (≤ 1 em magnitude para linhas com perdas).
    length_km:
        Comprimento usado no cálculo de A.
    """

    frequencies: tuple[float, ...]
    Zc: tuple[complex, ...]
    A: tuple[complex, ...]
    length_km: float


def compute_propagation_pos(
    sweep: FrequencySweep,
    length_km: float,
) -> PropagationFunction:
    """
    Extrai Z_c(ω) e A(ω) de sequência positiva a partir de um
    sweep frequencial.

    Para cada frequência do sweep:
    1. Reduz [Z][Y] a Z_pos = R+jωL e Y_pos = G+jωC via
       ``compute_positive_sequence``.
    2. ``γ = √(Z_pos · Y_pos)``.
    3. ``Z_c = √(Z_pos / Y_pos)``.
    4. ``A = exp(-γ · ℓ)`` com ℓ em metros.

    Parameters
    ----------
    sweep:
        Resultado de compute_frequency_sweep.
    length_km:
        Comprimento da linha em km.

    Returns
    -------
    PropagationFunction
    """
    if length_km <= 0:
        raise ValueError(f"length_km = {length_km} ≤ 0")

    length_m = length_km * 1000.0
    Zc_list: list[complex] = []
    A_list: list[complex] = []

    for f, lc in zip(sweep.frequencies, sweep.constants):
        ps = compute_positive_sequence(lc)
        omega = 2.0 * math.pi * f
        # Z_pos e Y_pos por unidade de comprimento (Ω/km e S/km).
        # Convertemos para por-metro para γ.
        Z_pos_per_m = (ps.R_per_km + 1j * omega * ps.L_per_km) / 1000.0
        Y_pos_per_m = (1j * omega * ps.C_per_km) / 1000.0   # G ≈ 0

        # Garantir não-zero (curto-circuito hipotético)
        if abs(Y_pos_per_m) < 1e-30:
            raise ValueError(f"Y_pos ≈ 0 em f = {f} Hz")

        gamma = cmath.sqrt(Z_pos_per_m * Y_pos_per_m)
        Zc = cmath.sqrt(Z_pos_per_m / Y_pos_per_m)
        A = cmath.exp(-gamma * length_m)

        Zc_list.append(Zc)
        A_list.append(A)

    return PropagationFunction(
        frequencies=sweep.frequencies,
        Zc=tuple(Zc_list),
        A=tuple(A_list),
        length_km=length_km,
    )


def make_3phase_geometry(
    *,
    x_a: float, y_a: float,
    x_b: float, y_b: float,
    x_c: float, y_c: float,
    radius: float,
    R_dc_per_km: float,
    soil_resistivity: float = 100.0,
    frequency: float = 60.0,
    gmr: Optional[float] = None,
) -> LineGeometry:
    """
    Constrói LineGeometry padrão para linha 3φ (3 condutores
    iguais com posições distintas).

    Util para casos onde os condutores das 3 fases são do mesmo
    tipo (ACSR Linnet, AAAC Cardinal, etc.) e diferem só na
    posição. Reduz boilerplate.
    """
    return LineGeometry(
        conductors=[
            Conductor("A", x_a, y_a, radius, R_dc_per_km, gmr=gmr),
            Conductor("B", x_b, y_b, radius, R_dc_per_km, gmr=gmr),
            Conductor("C", x_c, y_c, radius, R_dc_per_km, gmr=gmr),
        ],
        soil_resistivity=soil_resistivity,
        frequency=frequency,
    )
