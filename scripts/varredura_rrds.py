"""Dependência da escalada com a taxa de recuperação dielétrica (RRDS).

Critério de aceitação do modelo de escalada
============================================

Wong, Snider e Lo, sobre 48 disjuntores, mostram que a escalada é mais
severa para RRDS na faixa **intermediária** de 20 a 30 kV/ms: recuperação
rápida demais impede a reignição, lenta demais permite a extinção no
primeiro zero de alta frequência [LITERATURA: IPST 2003, p. 5-6].

A varredura anterior deste projeto encontrou o **oposto** — escalada
máxima no topo da faixa amostrada — porque nada no modelo representava o
limite dielétrico da carga e o pico simplesmente acompanhava a rampa
``RRDS·Δt`` [REPO:
``docs/research/rul_isolamento/08_VARREDURA_ESTATISTICA_VCB.md``, §3.2].
Com o para-raios no terminal do motor (:mod:`app.simulation.emt.arrester`)
esse mecanismo deixa de operar, e a pergunta volta a ter sentido.

Este script varre a RRDS em GRADE, não por sorteio, para que a dependência
seja legível: para cada valor de RRDS, ``n`` realizações com os demais
parâmetros sorteados e o tempo de arco na janela de Wong. A RRDS é comum
aos três polos — é a variável sob estudo.

Uso
====

.. code-block:: bash

    python scripts/varredura_rrds.py --n 20 --saida rrds.json
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.simulation.emt.cases.atp_reference import (  # noqa: E402
    FREQUENCY_HZ,
    AtpReferenceCase,
    load_reference,
)
from app.simulation.emt.vcb_scenarios import (  # noqa: E402
    LITERATURE_RRDS_RANGE_KV_PER_MS,
    LITERATURE_WORST_ARC_TIME_S,
    PoleCurrentZeros,
    scenario,
    sweep_three_pole_samples,
)

#: Piso do instante de separação [s].
PISO_SEPARACAO_S: float = 14.0e-3

#: Tensão de base: pico fase-terra do sistema de 4,16 kV [V].
V_BASE_V: float = 4160.0 / math.sqrt(3.0) * math.sqrt(2.0)

#: Tensão do sistema para o escalonamento do para-raios [V].
SYSTEM_VOLTAGE_V: float = 4160.0

#: Grade de RRDS [kV/ms], cobrindo a faixa da literatura.
RRDS_GRID_KV_PER_MS: tuple[float, ...] = tuple(
    float(x) for x in np.arange(5.0, 50.0 + 1e-9, 2.5)
)


def _executa(argumento: tuple[float, int, tuple, bool]) -> dict:
    """Uma realização com RRDS imposta."""
    rrds, indice, amostras, com_para_raios = argumento
    logging.disable(logging.WARNING)
    modelo = AtpReferenceCase(
        with_snubber=False,
        vcb_samples=amostras,
        motor_arrester_system_voltage_V=(
            SYSTEM_VOLTAGE_V if com_para_raios else None
        ),
    ).build()
    modelo.run()
    motor = modelo.motor_voltage_summary()
    linha = {
        "rrds_kV_por_ms": float(rrds),
        "com_para_raios": bool(com_para_raios),
        "indice": int(indice),
        "tempo_de_arco_us": [float(a.arc_time_s) * 1.0e6 for a in amostras],
        "reignicoes": modelo.reignition_counts,
        "pico_motor_pu": max(motor.values()) * 1.0e3 / V_BASE_V,
    }
    if com_para_raios:
        linha["energia_moa_J"] = max(a.energy_J for a in modelo.arresters)
        linha["moa_extrapolado"] = any(a.extrapolated for a in modelo.arresters)
    return linha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=20, help="realizações por RRDS")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--saida", type=Path, default=Path("varredura_rrds.json"))
    parser.add_argument(
        "--sem-para-raios",
        action="store_true",
        help="roda também a configuração sem para-raios, para contraste",
    )
    parser.add_argument(
        "--cenario",
        default="literatura",
        help=(
            "cenário das faixas: 'literatura' (capacidade de extinção "
            "CONSTANTE) ou 'wong' (lei di/dt = C·(t − t_sep) + D)"
        ),
    )
    parser.add_argument(
        "--rrds",
        nargs=3,
        type=float,
        metavar=("INICIO", "FIM", "PASSO"),
        default=None,
        help=(
            "grade de RRDS [kV/ms]; padrão 5 50 2.5, a faixa publicada. "
            "Estender além de 50 serve para localizar o máximo interior "
            "que Wong reporta, se ele existir fora da faixa"
        ),
    )
    parser.add_argument(
        "--processos", type=int, default=max(1, (os.cpu_count() or 1))
    )
    args = parser.parse_args(argv)
    if args.n <= 0:
        parser.error("--n deve ser > 0")

    grade = (
        RRDS_GRID_KV_PER_MS
        if args.rrds is None
        else tuple(
            float(x)
            for x in np.arange(args.rrds[0], args.rrds[1] + 1e-9, args.rrds[2])
        )
    )
    if len(grade) == 0:
        parser.error("--rrds produziu grade vazia")

    ref = load_reference()
    zeros = tuple(
        PoleCurrentZeros.from_phasor(i, FREQUENCY_HZ) for i in ref.breaker_currents()
    )
    faixas = scenario(str(args.cenario))

    configs = [True] + ([False] if args.sem_para_raios else [])
    tarefas: list[tuple[float, int, tuple, bool]] = []
    for k, rrds in enumerate(grade):
        # Sorteia corte, di/dt e tempo de arco; IMPÕE a RRDS aos três polos.
        triplas = sweep_three_pole_samples(
            faixas,
            n=args.n,
            zeros_abc=zeros,
            arc_time_window_s=LITERATURE_WORST_ARC_TIME_S,
            earliest_separation_s=PISO_SEPARACAO_S,
            seed=args.seed + k,
        )
        for i, t in enumerate(triplas):
            fixada = tuple(replace(a, rrds_a_kV_per_ms=float(rrds)) for a in t)
            for com in configs:
                tarefas.append((float(rrds), i, fixada, com))

    print(
        f"{len(tarefas)} realizações em {len(grade)} pontos de RRDS "
        f"({args.processos} processos)",
        flush=True,
    )
    linhas: list[dict] = []
    with ProcessPoolExecutor(max_workers=int(args.processos)) as pool:
        for j, linha in enumerate(pool.map(_executa, tarefas, chunksize=2), start=1):
            linhas.append(linha)
            if j % 50 == 0:
                print(f"  {j}/{len(tarefas)}", flush=True)

    resumo = []
    for com in configs:
        for rrds in grade:
            g = [
                l
                for l in linhas
                if l["com_para_raios"] is com and l["rrds_kV_por_ms"] == rrds
            ]
            pk = np.array([l["pico_motor_pu"] for l in g])
            rg = np.array([sum(l["reignicoes"].values()) for l in g])
            resumo.append(
                {
                    "com_para_raios": com,
                    "rrds_kV_por_ms": float(rrds),
                    "n": len(g),
                    "pico_p50": float(np.median(pk)),
                    "pico_p95": float(np.percentile(pk, 95)),
                    "pico_max": float(pk.max()),
                    "reign_p50": float(np.median(rg)),
                    "reign_max": int(rg.max()),
                }
            )

    args.saida.write_text(
        json.dumps(
            {
                "configuracao": {
                    "n_por_ponto": int(args.n),
                    "seed": int(args.seed),
                    "grade_rrds_kV_por_ms": list(grade),
                    "faixa_literatura_kV_por_ms": list(
                        LITERATURE_RRDS_RANGE_KV_PER_MS
                    ),
                    "janela_tempo_de_arco_s": list(LITERATURE_WORST_ARC_TIME_S),
                    "cenario": str(args.cenario),
                    "tensao_sistema_para_raios_V": SYSTEM_VOLTAGE_V,
                    "v_base_V": V_BASE_V,
                },
                "resumo": resumo,
                "realizacoes": linhas,
            },
            indent=1,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    for com in configs:
        print(f"\n{'COM' if com else 'SEM'} para-raios")
        print("  RRDS[kV/ms]  pico p50   p95    máx   reign p50  máx")
        for r in resumo:
            if r["com_para_raios"] is not com:
                continue
            print(
                f"  {r['rrds_kV_por_ms']:9.1f}  {r['pico_p50']:7.2f} "
                f"{r['pico_p95']:6.2f} {r['pico_max']:6.2f}  "
                f"{r['reign_p50']:8.1f} {r['reign_max']:4d}"
            )
    print(f"\ngravado em {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
