"""
app.preprocessor.jmarti_pch — emissão de arquivo ``.pch`` para o
modelo JMARTI line model do ATP.

Saída: arquivo texto no formato JMARTI-compatible (draft), com:
* Cabeçalho com metadata (geometria, frequência base, autor).
* Lista de polos/resíduos para Z_c(s).
* Lista de polos/resíduos para A(s) (com τ extraído).

Limitação MVP v0.25.4
---------------------

O formato ``.pch`` strict do ATP usa colunagem fixa específica
do AUX-LCC. Esta implementação escreve um formato **legível e
documentado** que pode ser convertido manualmente ou via tool
externa para o formato strict. Foco MVP: a matemática do
fitting é o difícil; o formato exato é mecanico e pode evoluir
em sub-sprint.

Quando o ATP exige strict format, recomenda-se rodar o LCC
externo (ATPDraw + LineConstants) e usar este draft como
referência/verificação.

Referências
-----------
* J. R. Marti, "Accurate modelling of frequency-dependent
  transmission lines", IEEE Trans. PAS, 1982.
* ATP Rule Book Vol 2 §9.8 (Line Model + .pch format).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .vector_fitting import DelayedRationalFit, RationalFit


@dataclass(frozen=True)
class JMartiPchData:
    """
    Pacote completo de dados para um ``.pch`` JMARTI.

    Attributes
    ----------
    line_id:
        Identificador (ex: "LT_138_100km").
    length_km:
        Comprimento da linha em km — preservado no metadata.
    Zc_fit:
        Modelo racional para Z_c(s).
    A_fit:
        Modelo racional para A(s) com delay extraído.
    sample_freq_min, sample_freq_max:
        Faixa de frequências usada no ajuste — Hz.
    n_phases:
        Número de fases (1 = single-mode, 3 = balanced 3φ).
    """

    line_id: str
    length_km: float
    Zc_fit: RationalFit
    A_fit: DelayedRationalFit
    sample_freq_min: float
    sample_freq_max: float
    n_phases: int = 1


def emit_pch_text(data: JMartiPchData) -> str:
    """
    Gera o texto ``.pch`` como string.

    Formato (draft v0.25.4):

    ::

        C JMARTI .pch — gerado por Olivas ATP Studio
        C Line: <id>, length=<km> km, n_phases=<n>
        C Sample range: <fmin>..<fmax> Hz
        C
        C === Z_c(s) — characteristic impedance ===
        C   d (constant) = <d>
        C   h (s-term)   = <h>
        C   poles / residues:
        C     pole_1 = (re, im)    residue_1 = (re, im)
        C     ...
        C
        C === A(s) — propagation function (with delay tau) ===
        C   tau = <s> seconds
        C   d (constant) = <d>
        C   h (s-term)   = <h>
        C   poles / residues:
        C     ...
        C

    Returns
    -------
    str
        Conteúdo completo do arquivo.
    """
    lines: list[str] = []
    add = lines.append

    add("C JMARTI .pch — gerado por Olivas ATP Studio")
    add(f"C Line: {data.line_id}, length = {data.length_km:.3f} km, "
        f"n_phases = {data.n_phases}")
    add(f"C Sample range: {data.sample_freq_min:.2f} to "
        f"{data.sample_freq_max:.2f} Hz")
    add("C")
    add("C === Z_c(s) — characteristic impedance ===")
    add(f"C   d (constant) = {data.Zc_fit.d:.6e}")
    add(f"C   h (s-term)   = {data.Zc_fit.h:.6e}")
    add(f"C   rms_error    = {data.Zc_fit.rms_error:.6e}")
    add(f"C   {data.Zc_fit.n_poles} poles:")
    for p, r in zip(data.Zc_fit.poles, data.Zc_fit.residues):
        add(f"C     pole = ({p.real:.6e}, {p.imag:.6e})  "
            f"residue = ({r.real:.6e}, {r.imag:.6e})")
    add("C")
    add("C === A(s) — propagation function with delay extraction ===")
    add(f"C   tau (travel time) = {data.A_fit.tau:.6e} s")
    add(f"C   d (constant) = {data.A_fit.fit_residual.d:.6e}")
    add(f"C   h (s-term)   = {data.A_fit.fit_residual.h:.6e}")
    add(f"C   rms_error    = {data.A_fit.fit_residual.rms_error:.6e}")
    add(f"C   {data.A_fit.fit_residual.n_poles} poles (of A_residual):")
    for p, r in zip(
        data.A_fit.fit_residual.poles,
        data.A_fit.fit_residual.residues,
    ):
        add(f"C     pole = ({p.real:.6e}, {p.imag:.6e})  "
            f"residue = ({r.real:.6e}, {r.imag:.6e})")
    add("C")
    add("C NOTE: This is a JMARTI-compatible DRAFT format. ATP strict")
    add("C       formato requires conversion via AUX-LCC. Use this")
    add("C       file as reference/verification.")
    add("C")

    return "\n".join(lines) + "\n"


def emit_pch_file(data: JMartiPchData, path: str) -> None:
    """Escreve o ``.pch`` no caminho especificado (UTF-8)."""
    text = emit_pch_text(data)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
