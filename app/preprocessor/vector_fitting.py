"""
app.preprocessor.vector_fitting — Vector Fitting (Gustavsen-Semlyen
1999) para ajustar funções complexas amostradas em frequência por
modelos racionais.

Usado pelo JMARTI line model: ajusta Z_c(ω) e A(ω) (saída de
:mod:`app.preprocessor.lcc`) por aproximações racionais que o ATP
consegue integrar no domínio do tempo.

Modelo
------

    f(s) ≈ Σ_k [c_k / (s - p_k)] + d + s·h

onde:
* ``s = jω`` (variável de Laplace).
* ``p_k`` são polos (estáveis: Re(p_k) < 0).
* ``c_k`` são resíduos.
* ``d`` é um termo constante real.
* ``h`` é um termo proporcional (geralmente 0 para Z_c, A).

Algoritmo iterativo
-------------------

Gustavsen 1999 propõe duas etapas:

1. **Pole identification**: dado um chute inicial de polos, monta
   um sistema linear LSQ que resolve simultaneamente para os
   resíduos da função desejada e para os resíduos de uma "sigma
   function" σ(s) = 1 + Σ c̃_k/(s - a_k). Os zeros de σ são os
   novos polos.

2. **Residue identification**: dados os polos finais, resolve um
   LSQ simples para encontrar c_k, d, h.

Iteração: 2-5 passes do step 1 normalmente bastam para LT
típica.

Referências
-----------
* B. Gustavsen, A. Semlyen, "Rational approximation of frequency
  domain responses by vector fitting", IEEE Trans. PWRD, 14(3),
  1999.
* B. Gustavsen, "Improving the pole relocating properties of
  vector fitting", IEEE Trans. PWRD, 21(3), 2006 — relaxed VF.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np


# ---------------------------------------------------------------------------
# Resultado: modelo racional ajustado
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RationalFit:
    """
    Modelo racional ajustado por VF.

    Attributes
    ----------
    poles:
        Polos complexos (estáveis) — Re(p) < 0.
    residues:
        Resíduos correspondentes (mesma ordem de poles).
    d:
        Termo constante real.
    h:
        Termo proporcional s·h. Geralmente 0 para Z_c, A.
    rms_error:
        RMS do erro de ajuste sobre as amostras (|f_data - f_fit|).
    """

    poles: tuple[complex, ...]
    residues: tuple[complex, ...]
    d: float
    h: float
    rms_error: float

    def evaluate(self, s: complex) -> complex:
        """Avalia o modelo em um ponto ``s = σ + jω``."""
        result = self.d + s * self.h
        for p, c in zip(self.poles, self.residues):
            result += c / (s - p)
        return result

    @property
    def n_poles(self) -> int:
        return len(self.poles)


# ---------------------------------------------------------------------------
# Initial pole guess
# ---------------------------------------------------------------------------


def initial_poles(
    frequencies: Sequence[float],
    n_poles: int,
) -> np.ndarray:
    """
    Chute inicial de polos: pares conjugados complexos com parte
    real pequena (estável) e parte imaginária log-espaçada na
    faixa de frequências.

    Garantia: ``n_poles`` é forçado a ser PAR (cada par conjugado
    conta como 2 polos). Se ímpar, adiciona 1.

    Parameters
    ----------
    frequencies:
        Faixa de amostragem (Hz). Usa min e max para definir a
        faixa dos polos.
    n_poles:
        Número total de polos desejado.

    Returns
    -------
    np.ndarray (complex)
        Vetor de polos iniciais com ``n_poles`` elementos.
    """
    if n_poles % 2 != 0:
        n_poles += 1
    if n_poles < 2:
        n_poles = 2

    f_min = min(frequencies)
    f_max = max(frequencies)
    if f_min <= 0 or f_max <= 0:
        raise ValueError("Frequências devem ser > 0")

    n_pairs = n_poles // 2
    # Frequências dos polos: log-espaçadas
    if n_pairs == 1:
        omega_pole = np.array([math.sqrt(f_min * f_max) * 2 * math.pi])
    else:
        omega_pole = 2 * math.pi * np.logspace(
            math.log10(f_min), math.log10(f_max), n_pairs,
        )
    # alpha = parte real (estabilidade): ~1% da parte imaginária
    alpha = -omega_pole / 100.0
    poles_complex_pos = alpha + 1j * omega_pole
    # Pares conjugados
    poles = np.concatenate([poles_complex_pos, np.conj(poles_complex_pos)])
    return poles


# ---------------------------------------------------------------------------
# Algoritmo principal
# ---------------------------------------------------------------------------


def vector_fit(
    frequencies: Sequence[float],
    f_data: Sequence[complex],
    n_poles: int = 6,
    *,
    n_iterations: int = 5,
    fit_h: bool = False,
    fit_d: bool = True,
    initial_poles_override: Optional[np.ndarray] = None,
    normalize_frequency: bool = True,
) -> RationalFit:
    """
    Vector-fitting de uma função complexa f(jω) amostrada em
    múltiplas frequências.

    Parameters
    ----------
    frequencies:
        Frequências em Hz, ordem crescente.
    f_data:
        Valores complexos f(jω_k) — mesma ordem que ``frequencies``.
    n_poles:
        Quantidade de polos no modelo. Deve ser par; será forçado
        para par adicionando 1 se necessário. Default 6.
    n_iterations:
        Iterações do algoritmo Gustavsen-Semlyen. Default 5.
    fit_h:
        Se True, ajusta termo s·h. Default False (geralmente 0
        para Z_c, A).
    fit_d:
        Se True, ajusta constante d. Default True.
    initial_poles_override:
        Polos iniciais customizados (numpy array). Se None, usa
        ``initial_poles(frequencies, n_poles)``.
    normalize_frequency:
        v0.28.2-PRO (auditoria P0): se True (default), normaliza
        ω para ω/ω_max antes do LSQ e desnormaliza polos depois.
        Resolve ill-conditioning para faixas amplas (>10⁶ Hz).
        Standard practice em VF papers (Gustavsen 1999).

    Returns
    -------
    RationalFit
    """
    freq_array = np.asarray(frequencies, dtype=float)
    s = 1j * 2.0 * math.pi * freq_array
    f = np.asarray(f_data, dtype=complex)

    if len(s) != len(f):
        raise ValueError(
            f"frequencies tem {len(s)} pontos, f_data tem {len(f)}"
        )
    if len(s) < n_poles:
        raise ValueError(
            f"Pelo menos {n_poles} amostras necessárias, "
            f"recebido {len(s)}"
        )

    # v0.28.2-PRO: amostragem mínima recomendada por Gustavsen
    # samples >= 2·n_poles + (1 if fit_d else 0) + (1 if fit_h else 0)
    n_extras = (1 if fit_d else 0) + (1 if fit_h else 0)
    min_samples = 2 * n_poles + n_extras
    if len(s) < min_samples:
        raise ValueError(
            f"Vector-fitting recomenda ≥ {min_samples} amostras "
            f"(2×{n_poles} polos + {n_extras} extras), "
            f"recebido {len(s)}. Aumente n_poles ou colete mais "
            "pontos de frequência."
        )

    # v0.28.2-PRO: normalização de frequência para reduzir
    # ill-conditioning do LSQ.
    omega_max = float(np.max(np.abs(s.imag)))
    if normalize_frequency and omega_max > 0:
        scale = omega_max
        s = s / scale
    else:
        scale = 1.0

    # Polos iniciais
    if initial_poles_override is not None:
        poles = np.asarray(initial_poles_override, dtype=complex)
    else:
        poles = initial_poles(frequencies, n_poles)
    if len(poles) % 2 != 0:
        # Garantia interna
        poles = np.append(poles, np.conj(poles[-1]))

    # v0.28.2-PRO: normaliza polos iniciais à mesma escala de s
    if scale != 1.0:
        poles = poles / scale

    n_p = len(poles)

    # Iterações de Gustavsen-Semlyen — pole identification
    for _iter in range(n_iterations):
        poles = _vf_pole_iteration(s, f, poles, fit_d=fit_d, fit_h=fit_h)
        poles = _enforce_stability(poles)

    # Residue identification (resíduos finais para os polos
    # convergidos)
    residues, d_val, h_val = _vf_residue_solve(
        s, f, poles, fit_d=fit_d, fit_h=fit_h,
    )

    # RMS error (calculado em escala normalizada)
    f_fit = np.zeros_like(f)
    for k in range(n_p):
        f_fit += residues[k] / (s - poles[k])
    f_fit += d_val + s * h_val
    rms_err = float(np.sqrt(np.mean(np.abs(f - f_fit) ** 2)))

    # v0.28.2-PRO: desnormaliza polos e resíduos antes de retornar
    # Forma: H_norm(s/scale) = H_real(s).
    # Para pole p_norm em escala normalizada: p_real = p_norm × scale.
    # Para residue r_norm: r_real = r_norm × scale.
    # h_norm = h_real / scale. d_real = d_norm.
    if scale != 1.0:
        poles_real = poles * scale
        residues_real = residues * scale
        h_real = h_val / scale
        d_real = d_val
    else:
        poles_real = poles
        residues_real = residues
        h_real = h_val
        d_real = d_val

    return RationalFit(
        poles=tuple(complex(p) for p in poles_real),
        residues=tuple(complex(r) for r in residues_real),
        d=float(d_real.real),
        h=float(h_real.real),
        rms_error=rms_err,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _vf_pole_iteration(
    s: np.ndarray,
    f: np.ndarray,
    poles: np.ndarray,
    *,
    fit_d: bool,
    fit_h: bool,
) -> np.ndarray:
    """
    Uma iteração do pole identification do Gustavsen-Semlyen.

    Resolve o sistema:

        Σ c_k/(s_n - a_k) + d + s_n h - σ_n · Σ c̃_k/(s_n - a_k)
            = f(s_n)
        com σ_n = 1 + Σ c̃_k/(s_n - a_k)

    Os zeros de σ(s) são os novos polos.
    """
    n_s = len(s)
    n_p = len(poles)
    n_extra = (1 if fit_d else 0) + (1 if fit_h else 0)
    # Colunas: [residues(c_k)] + [d?] + [h?] + [residues sigma (c̃_k)]
    n_cols = n_p + n_extra + n_p
    # Matriz complexa
    A = np.zeros((n_s, n_cols), dtype=complex)

    # Bloco 1: 1/(s_n - a_k) para residues c_k
    for k in range(n_p):
        A[:, k] = 1.0 / (s - poles[k])

    col = n_p
    if fit_d:
        A[:, col] = 1.0
        col += 1
    if fit_h:
        A[:, col] = s
        col += 1

    # Bloco 2: -f(s_n) / (s_n - a_k) para residues c̃_k
    for k in range(n_p):
        A[:, col + k] = -f / (s - poles[k])

    # RHS: f(s_n)
    b = f.copy()

    # Solve LSQ on real form (separa parte real e imaginária)
    A_real = np.vstack([A.real, A.imag])
    b_real = np.concatenate([b.real, b.imag])

    # Usar lstsq
    x_real, *_ = np.linalg.lstsq(A_real, b_real, rcond=None)

    # Os últimos n_p elementos de x são os c̃_k
    sigma_residues = x_real[-n_p:].astype(complex)

    # Novos polos = zeros de σ(s) = 1 + Σ c̃_k/(s - a_k)
    # Equivalente a um problema de autovalor:
    #   A_diag(poles) - b·c̃^T → seus autovalores são os zeros
    # onde b é vetor de 1s e c̃ é o vetor de resíduos.
    A_mat = np.diag(poles) - np.ones((n_p, 1)) @ sigma_residues.reshape(1, -1)

    # Garantir estrutura conjugada se polos vinham em pares: aqui
    # vamos calcular autovalores diretamente (são complex)
    new_poles = np.linalg.eigvals(A_mat)

    return new_poles


def _enforce_stability(poles: np.ndarray) -> np.ndarray:
    """Polos com Re > 0 são instáveis — espelha para Re < 0."""
    poles = np.asarray(poles, dtype=complex)
    out = poles.copy()
    bad = poles.real > 0
    out[bad] = -poles[bad].real + 1j * poles[bad].imag
    return out


def _vf_residue_solve(
    s: np.ndarray,
    f: np.ndarray,
    poles: np.ndarray,
    *,
    fit_d: bool,
    fit_h: bool,
) -> tuple[np.ndarray, complex, complex]:
    """
    Dado polos fixos, resolve LSQ para os resíduos + d + h.

    Σ c_k/(s_n - a_k) + d + s_n h = f(s_n)
    """
    n_s = len(s)
    n_p = len(poles)
    n_extra = (1 if fit_d else 0) + (1 if fit_h else 0)
    A = np.zeros((n_s, n_p + n_extra), dtype=complex)
    for k in range(n_p):
        A[:, k] = 1.0 / (s - poles[k])
    col = n_p
    if fit_d:
        A[:, col] = 1.0
        col += 1
    if fit_h:
        A[:, col] = s
        col += 1

    # LSQ real
    A_real = np.vstack([A.real, A.imag])
    b_real = np.concatenate([f.real, f.imag])
    x_real, *_ = np.linalg.lstsq(A_real, b_real, rcond=None)

    residues = x_real[:n_p].astype(complex)
    idx = n_p
    d_val = complex(x_real[idx]) if fit_d else complex(0)
    if fit_d:
        idx += 1
    h_val = complex(x_real[idx]) if fit_h else complex(0)
    return residues, d_val, h_val


# ---------------------------------------------------------------------------
# JMARTI helper: VF de A(s) com delay extraction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DelayedRationalFit:
    """
    Modelo ``A(s) ≈ exp(-s·τ) · A_residual(s)`` onde A_residual
    é uma função racional ajustada por VF.

    Útil para JMARTI: separa o atraso puro de transporte (τ via
    Bergeron) e ajusta apenas a "parte lenta" da função de
    propagação por funções racionais — VF tem ordem MUITO menor
    porque A_residual ≈ 1 em magnitude e quase constante em
    fase.

    Attributes
    ----------
    tau:
        Travel time em segundos (atraso de transporte puro).
    fit_residual:
        RationalFit de A_residual(s) = A(s) · exp(+s·τ).
    """

    tau: float
    fit_residual: RationalFit

    def evaluate(self, s: complex) -> complex:
        """Avalia A(s) = exp(-s·τ) · A_residual(s)."""
        import cmath
        return cmath.exp(-s * self.tau) * self.fit_residual.evaluate(s)


def vector_fit_delayed(
    frequencies: Sequence[float],
    A_data: Sequence[complex],
    tau: float,
    n_poles: int = 6,
    *,
    n_iterations: int = 5,
) -> DelayedRationalFit:
    """
    VF de A(s) com extração prévia do delay.

    Algoritmo:
    1. Computa A_residual(s_k) = A(s_k) · exp(+s_k·τ) — remove
       o atraso de transporte conhecido.
    2. VF normal sobre A_residual.

    O resultado é um modelo ``A(s) = exp(-s·τ) · A_residual(s)``
    onde A_residual ≈ 1 em magnitude (atenuação suave) e tem
    fase quase constante em alta frequência. VF converge MUITO
    melhor.

    Parameters
    ----------
    frequencies, A_data:
        Sample data de A(jω).
    tau:
        Travel time em segundos (de Bergeron ou similar).
    n_poles, n_iterations:
        Parâmetros do VF.

    Returns
    -------
    DelayedRationalFit
    """
    import cmath
    s = 1j * 2.0 * math.pi * np.asarray(frequencies, dtype=float)
    A = np.asarray(A_data, dtype=complex)
    A_res = A * np.exp(s * tau)   # remove o atraso

    fit = vector_fit(
        frequencies, A_res.tolist(),
        n_poles=n_poles, n_iterations=n_iterations,
        fit_d=True, fit_h=False,
    )
    return DelayedRationalFit(tau=float(tau), fit_residual=fit)
