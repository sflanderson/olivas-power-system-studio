"""Campanha de manobras ponta a ponta: motor EMT → estresse → dano → vida.

Fecha a cadeia manobra → estresse → estado → vida sobre o caso de
referência, com a separação que o estudo estabeleceu:

* manobras abaixo do envelope de suportabilidade **envelhecem** a
  isolação e entram no acumulador de dano;
* manobras que o atravessam **encerram** a isolação e entram na taxa de
  eventos terminais.

O fim de vida é o MÍNIMO dos dois caminhos, e os dois são reportados —
ver :mod:`app.postprocessor.prognosis.switching_campaign`.

Sobre os números
=================

A taxa terminal é a grandeza **calibrada**: sai da contagem da varredura
e não depende de parâmetro de curva de vida. O caminho do envelhecimento
depende de ``DamageModelParams``, cujos parâmetros são NÃO CALIBRADOS
para mica-epóxi de MT [REPO: ``rul_params_not_calibrated``] — o número de
manobras por envelhecimento é, portanto, arquitetura com incerteza
propagada, não previsão.

Uso
====

.. code-block:: bash

    python scripts/campanha_rul.py --n 30 --dt 2e-7 --saida campanha.json
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.postprocessor.prognosis.damage_models import DamageModelParams  # noqa: E402
from app.postprocessor.prognosis.switching_campaign import (  # noqa: E402
    ManeuverOutcome,
    SwitchingCampaign,
)
from app.simulation.emt.cases.atp_reference import (  # noqa: E402
    FREQUENCY_HZ,
    AtpReferenceCase,
    load_reference,
)
from app.simulation.emt.flashover import iec_60034_15_levels  # noqa: E402
from app.simulation.emt.probes import to_stress_profile  # noqa: E402
from app.simulation.emt.vcb_scenarios import (  # noqa: E402
    LITERATURE_WORST_ARC_TIME_S,
    PoleCurrentZeros,
    scenario,
    sweep_three_pole_samples,
)

#: Piso do instante de separação [s].
PISO_SEPARACAO_S: float = 14.0e-3

#: Tensão nominal de linha da máquina [V].
RATED_VOLTAGE_V: float = 4160.0

#: Pico fase-terra [V] — base das conversões em pu.
V_BASE_V: float = RATED_VOLTAGE_V / math.sqrt(3.0) * math.sqrt(2.0)

#: Limiar de DETECÇÃO de excursão [kV]. É limiar de detecção, não de dano:
#: fica acima do pico de regime (3,4 kV) para não capturar a fundamental.
DETECTION_THRESHOLD_KV: float = 5.0

#: Impedância de surto do cabo a jusante [Ω], para a estimativa de energia
#: — o modo 1 do cabo do caso [REPO: downstream_cable_modal_data].
SURGE_IMPEDANCE_OHM: float = 46.99


def _executa(argumento: tuple[int, tuple, float, float, bool]) -> dict:
    """Uma manobra: simula, extrai o estresse e classifica o desfecho."""
    indice, amostras, dt_s, envelope_V, com_para_raios = argumento
    logging.disable(logging.WARNING)
    modelo = AtpReferenceCase(
        with_snubber=False,
        vcb_samples=amostras,
        dt_s=float(dt_s),
        motor_flashover_level_V=float(envelope_V),
        motor_arrester_system_voltage_V=(
            RATED_VOLTAGE_V if com_para_raios else None
        ),
    ).build()
    modelo.run()

    atravessou = any(f.controller.count > 0 for f in modelo.flashovers)
    pico_pu = max(modelo.motor_voltage_summary().values()) * 1.0e3 / V_BASE_V

    perfis = []
    if not atravessou:
        # Só a manobra de ENVELHECIMENTO tem estresse a integrar. Extrair o
        # perfil de uma manobra grampeada seria integrar uma forma de onda
        # que não existe.
        for fase, sonda in modelo.motor_probes.items():
            perfil = to_stress_profile(
                sonda,
                threshold_kV=DETECTION_THRESHOLD_KV,
                surge_impedance_ohm=SURGE_IMPEDANCE_OHM,
                label=f"manobra{indice}_fase{fase}",
            )
            if perfil.events:
                perfis.append(
                    {
                        "fase": fase,
                        "n_eventos": len(perfil.events),
                        "picos_kV": [e.V_pk_kV for e in perfil.events],
                        "T1_us": [e.T1_us for e in perfil.events],
                        "dvdt_kV_por_us": [e.dvdt_kV_per_us for e in perfil.events],
                        "energia_J": [e.energy_J for e in perfil.events],
                        "n_reignicoes": [e.n_reignitions for e in perfil.events],
                    }
                )
    return {
        "indice": int(indice),
        "com_para_raios": bool(com_para_raios),
        "pico_pu": float(pico_pu),
        "reignicoes": int(sum(modelo.reignition_counts.values())),
        "atravessou_envelope": bool(atravessou),
        "perfis": perfis,
    }


def _reconstroi(linha: dict) -> ManeuverOutcome:
    """Desfecho a partir do registro serializado."""
    from app.postprocessor.prognosis.stress_profile import StressEvent, StressProfile

    eventos = [
        StressEvent(
            V_pk_kV=p["picos_kV"][k],
            T1_us=p["T1_us"][k],
            dvdt_kV_per_us=p["dvdt_kV_por_us"][k],
            energy_J=p["energia_J"][k],
            n_reignitions=p["n_reignicoes"][k],
            source=f"emt:manobra{linha['indice']}:{p['fase']}",
        )
        for p in linha["perfis"]
        for k in range(p["n_eventos"])
    ]
    # Perfil VAZIO, e não ``None``: a manobra foi medida e não produziu
    # excursão acima do limiar de detecção. ``None`` significaria ausência
    # de medição, e impediria integrar o dano da campanha inteira.
    perfil = StressProfile(events=eventos, label=f"manobra{linha['indice']}")
    return ManeuverOutcome(
        index=int(linha["indice"]),
        peak_pu=float(linha["pico_pu"]),
        reignitions=int(linha["reignicoes"]),
        crossed_withstand=bool(linha["atravessou_envelope"]),
        profile=perfil,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=30, help="manobras por configuração")
    parser.add_argument("--seed", type=int, default=20260903)
    parser.add_argument("--dt", type=float, default=2.0e-7, help="passo [s]")
    parser.add_argument("--saida", type=Path, default=Path("campanha_rul.json"))
    parser.add_argument(
        "--para-raios",
        action="store_true",
        help="roda também a configuração com para-raios, para contraste",
    )
    parser.add_argument(
        "--processos", type=int, default=max(1, (os.cpu_count() or 1))
    )
    args = parser.parse_args(argv)
    if args.n <= 0:
        parser.error("--n deve ser > 0")

    envelope_V, _sfi = iec_60034_15_levels(RATED_VOLTAGE_V)
    zeros = tuple(
        PoleCurrentZeros.from_phasor(i, FREQUENCY_HZ)
        for i in load_reference().breaker_currents()
    )
    triplas = sweep_three_pole_samples(
        scenario("literatura"),
        n=args.n,
        zeros_abc=zeros,
        arc_time_window_s=LITERATURE_WORST_ARC_TIME_S,
        earliest_separation_s=PISO_SEPARACAO_S,
        seed=args.seed,
    )
    configs = [False] + ([True] if args.para_raios else [])
    tarefas = [
        (i, t, float(args.dt), envelope_V, com)
        for com in configs
        for i, t in enumerate(triplas)
    ]

    print(
        f"{len(tarefas)} manobras, envelope IEC 60034-15 = {envelope_V/1e3:.2f} kV "
        f"({envelope_V/V_BASE_V:.2f} pu), Δt = {args.dt*1e6:.2f} µs",
        flush=True,
    )
    linhas: list[dict] = []
    with ProcessPoolExecutor(max_workers=int(args.processos)) as pool:
        for j, linha in enumerate(pool.map(_executa, tarefas, chunksize=1), start=1):
            linhas.append(linha)
            if j % 10 == 0:
                print(f"  {j}/{len(tarefas)}", flush=True)

    def grava(resumos: dict) -> None:
        """Grava o JSON. Chamado ANTES do resumo e de novo depois dele.

        A simulação é a parte cara; o resumo é barato e pode falhar. Gravar
        antes garante que uma falha de pós-processamento não descarte horas
        de execução — foi o que aconteceu na primeira campanha de 150.
        """
        args.saida.write_text(
            json.dumps(
                {
                    "configuracao": {
                        "n": int(args.n),
                        "seed": int(args.seed),
                        "dt_s": float(args.dt),
                        "envelope_V": float(envelope_V),
                        "v_base_V": V_BASE_V,
                        "limiar_deteccao_kV": DETECTION_THRESHOLD_KV,
                        "impedancia_de_surto_ohm": SURGE_IMPEDANCE_OHM,
                    },
                    "resumo": resumos,
                    "manobras": linhas,
                },
                indent=1,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    grava({})
    print(f"execuções gravadas em {args.saida}; resumindo", flush=True)

    resumos = {}
    for com in configs:
        rotulo = "com_para_raios" if com else "sem_mitigacao"
        campanha = SwitchingCampaign(
            withstand_level_kV=envelope_V / 1.0e3, label=rotulo
        )
        campanha.extend(
            _reconstroi(l) for l in linhas if l["com_para_raios"] is com
        )
        taxa = campanha.terminal_rate()
        acumulador = campanha.accumulate(params=DamageModelParams())
        resumo = campanha.life_summary(acumulador)
        resumos[rotulo] = resumo
        print(f"\n{rotulo}")
        print(f"  {taxa.describe()}")
        print(
            f"  envelhecimento: D = {resumo['dano_acumulado']:.4g} em "
            f"{resumo['manobras_de_envelhecimento']} manobras → "
            f"{resumo['manobras_por_envelhecimento']:.4g} manobras até D = 1 "
            f"(parâmetros NÃO CALIBRADOS)"
        )
        print(f"  caminho dominante: {resumo['caminho_dominante']}")

    grava(resumos)
    print(f"\ngravado em {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
