"""Varredura Monte Carlo dos parâmetros do disjuntor a vácuo.

Objetivo
========

Responder, sobre o caso de referência, três perguntas que um valor único
de parâmetro não responde:

1. Qual a DISTRIBUIÇÃO de sobretensão no terminal do motor quando os
   parâmetros do disjuntor entram como as faixas da literatura, e não
   como as constantes de um caso?
2. Quanto da severidade publicada vem do disjuntor escolhido e quanto
   vem do circuito?
3. O ramo amortecedor desloca essa distribuição, e em que sentido?

Desenho do experimento
======================

* Os parâmetros do arco — corrente de corte, capacidade de extinção de
  alta frequência e taxa de recuperação dielétrica — são sorteados por
  polo dentro das faixas publicadas
  (:mod:`app.simulation.emt.vcb_scenarios`).
* O instante de separação é COMUM às três fases: um disjuntor tripolar
  tem um acionamento só. O que difere entre os polos é o tempo de arco,
  porque cada fase tem seus próprios zeros de corrente.
* O sorteio é feito sobre o TEMPO DE ARCO do polo condutor, na janela de
  0 a 100 µs em que a escalada é mais severa
  [LITERATURA: Wong, Snider e Lo, IPST 2003, p. 5-6]. Sortear o instante
  absoluto no ciclo cobriria essa janela em 1,2 % das realizações
  [CÁLCULO PRÓPRIO].
* Três cenários entram na comparação: ``literatura`` (faixas publicadas),
  ``medido`` (disjuntor comercial caracterizado por Abdulahovic, 2011) e
  ``caso_de_referencia`` (os valores do arquivo ``.atp``, fora da faixa
  publicada nos três parâmetros).
* Cada cenário roda com e sem o ramo amortecedor.

Uso
===

.. code-block:: bash

    python scripts/varredura_vcb.py --n 150 --saida resultado.json

O resultado é um JSON com uma linha por realização e o resumo por
cenário. Nada é impresso como conclusão: a leitura fica no documento de
estudo.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.simulation.emt.cases.atp_reference import (  # noqa: E402
    FREQUENCY_HZ,
    AtpReferenceCase,
    load_reference,
)
from app.simulation.emt.vcb_scenarios import (  # noqa: E402
    FIELD_PEAK_CEILING_PU,
    LITERATURE_WORST_ARC_TIME_S,
    PoleCurrentZeros,
    VcbSample,
    scenario,
    sweep_three_pole_samples,
)

#: Piso do instante de separação [s]: fim da janela de acomodação do
#: regime permanente do caso.
PISO_SEPARACAO_S: float = 14.0e-3

#: Cenários confrontados.
CENARIOS: tuple[str, ...] = ("literatura", "medido", "caso_de_referencia")

#: Tensão de base para a conversão em pu: pico fase-terra do sistema de
#: 4,16 kV [FATO: caso de referência].
V_BASE_FASE_TERRA_V: float = 4160.0 / np.sqrt(3.0) * np.sqrt(2.0)


def zeros_do_caso() -> tuple[PoleCurrentZeros, ...]:
    """Zeros da corrente dos três polos, da solução fasorial publicada."""
    ref = load_reference()
    return tuple(
        PoleCurrentZeros.from_phasor(i, FREQUENCY_HZ) for i in ref.breaker_currents()
    )


def _executa(argumento: tuple[str, bool, int, tuple]) -> dict:
    """Uma realização. Isolada em função de topo por causa do pool."""
    nome, com_snubber, indice, amostras = argumento
    logging.disable(logging.WARNING)
    modelo = AtpReferenceCase(
        with_snubber=bool(com_snubber), vcb_samples=amostras
    ).build()
    modelo.run()
    motor = modelo.motor_voltage_summary()
    trv = modelo.trv_summary()
    return {
        "cenario": nome,
        "com_snubber": bool(com_snubber),
        "indice": int(indice),
        "separacao_s": float(amostras[0].separation_time_s),
        "tempo_de_arco_us": [float(a.arc_time_s) * 1.0e6 for a in amostras],
        "corte_A": [float(a.chopping_current_A) for a in amostras],
        "didt_A_por_us": [float(a.didt_capability_A_per_us) for a in amostras],
        "rrds_kV_por_ms": [float(a.rrds_a_kV_per_ms) for a in amostras],
        "reignicoes": modelo.reignition_counts,
        "motor_kV": {k: float(v) for k, v in motor.items()},
        "motor_pu": {
            k: float(v) * 1.0e3 / V_BASE_FASE_TERRA_V for k, v in motor.items()
        },
        "trv_pico_kV": {k: float(v[0]) for k, v in trv.items()},
        "trv_dvdt_kV_por_us": {k: float(v[1]) for k, v in trv.items()},
    }


def _resumo(linhas: list[dict]) -> dict:
    """Estatística descritiva de um grupo de realizações."""
    pico_pu = np.array([max(l["motor_pu"].values()) for l in linhas])
    reign = np.array([sum(l["reignicoes"].values()) for l in linhas])
    return {
        "n": int(len(linhas)),
        "pico_motor_pu": {
            "min": float(pico_pu.min()),
            "p50": float(np.percentile(pico_pu, 50)),
            "p95": float(np.percentile(pico_pu, 95)),
            "max": float(pico_pu.max()),
            "media": float(pico_pu.mean()),
        },
        "reignicoes_totais": {
            "min": int(reign.min()),
            "p50": float(np.percentile(reign, 50)),
            "max": int(reign.max()),
            "fracao_com_reignicao": float(np.mean(reign > 0)),
        },
        "fracao_acima_do_teto_de_campo": float(
            np.mean(pico_pu > FIELD_PEAK_CEILING_PU)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=150, help="realizações por cenário")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--saida", type=Path, default=Path("varredura_vcb.json"), help="JSON de saída"
    )
    parser.add_argument(
        "--processos",
        type=int,
        default=max(1, (os.cpu_count() or 1)),
        help="processos do pool",
    )
    args = parser.parse_args(argv)
    if args.n <= 0:
        parser.error("--n deve ser > 0")

    zeros = zeros_do_caso()
    tarefas: list[tuple[str, bool, int, tuple]] = []
    amostragem: dict[str, list] = {}
    for k, nome in enumerate(CENARIOS):
        triplas = sweep_three_pole_samples(
            scenario(nome),
            n=args.n,
            zeros_abc=zeros,
            arc_time_window_s=LITERATURE_WORST_ARC_TIME_S,
            earliest_separation_s=PISO_SEPARACAO_S,
            seed=args.seed + k,
        )
        amostragem[nome] = [[asdict(a) for a in t] for t in triplas]
        for com_snubber in (False, True):
            for i, t in enumerate(triplas):
                tarefas.append((nome, com_snubber, i, t))

    print(f"{len(tarefas)} realizações em {args.processos} processos", flush=True)
    linhas: list[dict] = []
    with ProcessPoolExecutor(max_workers=int(args.processos)) as pool:
        for j, linha in enumerate(pool.map(_executa, tarefas, chunksize=4), start=1):
            linhas.append(linha)
            if j % 25 == 0:
                print(f"  {j}/{len(tarefas)}", flush=True)

    resumos = {
        f"{nome}|{'com' if s else 'sem'}_snubber": _resumo(
            [l for l in linhas if l["cenario"] == nome and l["com_snubber"] is s]
        )
        for nome in CENARIOS
        for s in (False, True)
    }
    args.saida.write_text(
        json.dumps(
            {
                "configuracao": {
                    "n_por_cenario": int(args.n),
                    "seed": int(args.seed),
                    "piso_separacao_s": PISO_SEPARACAO_S,
                    "janela_tempo_de_arco_s": list(LITERATURE_WORST_ARC_TIME_S),
                    "v_base_fase_terra_V": float(V_BASE_FASE_TERRA_V),
                    "fases_da_corrente_deg": [
                        float(np.degrees(z.phase_angle_rad)) for z in zeros
                    ],
                },
                "resumo": resumos,
                "realizacoes": linhas,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    for chave, r in resumos.items():
        p = r["pico_motor_pu"]
        print(
            f"{chave:38s} n={r['n']:4d}  pico[pu] p50={p['p50']:.2f} "
            f"p95={p['p95']:.2f} max={p['max']:.2f}  "
            f"reig>0={r['reignicoes_totais']['fracao_com_reignicao']:.0%}"
        )
    print(f"gravado em {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
