"""
app.standards.ansi_devices — codificação dos números de dispositivos
de proteção conforme **ANSI/IEEE C37.2** (IEEE Standard for
Electrical Power System Device Function Numbers).

Esta padronização é universalmente adotada por fabricantes de
relés (SEL, ABB, Schneider, GE, Siemens, etc.) — vide manuais
em ``LIBRARY/library_relay/``.

Visão geral
============

Cada função de proteção tem um **número** (1–99 + sufixos) e
um **nome canônico**. Examples:

* **27** — Undervoltage relay
* **50** — Instantaneous overcurrent relay
* **51** — Time-delayed overcurrent relay
* **51N** — Neutral time-delayed overcurrent
* **67** — Directional overcurrent
* **87** — Differential protection
* **86** — Lockout

Sufixos comuns:

* **N** — neutral / ground
* **G** — ground (sometimes interchangeable with N)
* **P** — phase
* **V** — voltage-restrained / voltage-controlled
* **T** — transformer
* **B** — bus
* **F** — feeder
* **BF** — breaker failure

Aplicações
===========

* **Catálogo de funções** suportadas pelos relés comerciais
  (SEL-751, ABB RE_615, Schneider P3U).
* **Documentação** de coordenação (saber qual função opera
  quando).
* **Coordenação automática**: agrupar relés por device number
  (ex: comparar 51-51 entre upstream/downstream).

Referências
============

* IEEE/ANSI C37.2 — Standard for Electrical Power System
  Device Function Numbers, Acronyms, and Contact Designations
* IEEE 242:2001 (Buff Book) — guia para coordenação de proteção
* Schneider Easergy P3U manual (LIBRARY/library_relay/SCHNEIDER)
* ABB RE_615 Manual Técnico (LIBRARY/library_relay/ABB)
* SEL-751 Instruction Manual (LIBRARY/library_relay/SEL)
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Função de proteção
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnsiDeviceFunction:
    """
    Função de proteção identificada por número ANSI/IEEE C37.2.

    Attributes
    ----------
    number:
        Número padrão (ex: ``"50"``, ``"51N"``, ``"50BF"``).
    name_pt:
        Nome canônico em português.
    name_en:
        Nome canônico em inglês.
    description:
        Texto descritivo curto.
    typical_application:
        Onde tipicamente é usada.
    standard:
        Norma de origem (ANSI/IEEE C37.2 sempre, mas pode ter
        complementação IEC).
    """
    number: str
    name_pt: str
    name_en: str
    description: str
    typical_application: str = ""
    standard: str = "ANSI/IEEE C37.2"


# ---------------------------------------------------------------------------
# Catálogo principal (subset cobrindo as funções suportadas pelos
# 3 relés comerciais analisados no v0.27.4 — SEL-751, ABB RE_615,
# Schneider P3U).
# ---------------------------------------------------------------------------


ANSI_DEVICE_FUNCTIONS: dict[str, AnsiDeviceFunction] = {
    "21":   AnsiDeviceFunction(
        number="21",
        name_pt="Relé de distância",
        name_en="Distance relay",
        description="Mede impedância para detectar faltas",
        typical_application="Linhas de transmissão",
    ),
    "24":   AnsiDeviceFunction(
        number="24",
        name_pt="Sobre-excitação",
        name_en="Overexcitation V/Hz",
        description="Detecta V/Hz alto (saturação core)",
        typical_application="Geradores, transformadores",
    ),
    "25":   AnsiDeviceFunction(
        number="25",
        name_pt="Verificador de sincronismo",
        name_en="Synchronism check",
        description="Verifica condições de sincronismo",
        typical_application="Religamento automático, paralelismo",
    ),
    "27":   AnsiDeviceFunction(
        number="27",
        name_pt="Subtensão",
        name_en="Undervoltage",
        description="Detecta tensão abaixo do limite",
        typical_application="Motores, carga sensível",
    ),
    "32":   AnsiDeviceFunction(
        number="32",
        name_pt="Potência direcional",
        name_en="Directional power",
        description="Detecta fluxo de potência reverso",
        typical_application="Geração distribuída anti-ilhamento",
    ),
    "37":   AnsiDeviceFunction(
        number="37",
        name_pt="Subcorrente",
        name_en="Undercurrent",
        description="Detecta corrente baixa (perda de carga)",
        typical_application="Bombas, motores",
    ),
    "40":   AnsiDeviceFunction(
        number="40",
        name_pt="Perda de campo",
        name_en="Loss of field",
        description="Detecta perda da excitação do gerador",
        typical_application="Geradores síncronos",
    ),
    "46":   AnsiDeviceFunction(
        number="46",
        name_pt="Sobrecorrente de seq. negativa",
        name_en="Negative-sequence overcurrent",
        description="Detecta desbalanço de fases",
        typical_application="Motores (proteção contra rotor invertido)",
    ),
    "46BC": AnsiDeviceFunction(
        number="46BC",
        name_pt="Condutor rompido",
        name_en="Broken conductor",
        description="Razão I2/I1 alta indica condutor aberto",
        typical_application="Linhas de distribuição",
    ),
    "47":   AnsiDeviceFunction(
        number="47",
        name_pt="Sobretensão de seq. negativa",
        name_en="Phase-sequence voltage / NS overvoltage",
        description="Sequência de fases incorreta ou desbalanço",
        typical_application="Motores",
    ),
    "48":   AnsiDeviceFunction(
        number="48",
        name_pt="Supervisão de partida de motor",
        name_en="Motor starting supervision",
        description="Tempo de partida excedido",
        typical_application="Motores grandes",
    ),
    "49":   AnsiDeviceFunction(
        number="49",
        name_pt="Sobrecarga térmica",
        name_en="Thermal overload (RMS)",
        description="Modelo térmico I²t com constante de tempo",
        typical_application="Motores, transformadores, cabos",
    ),
    "50":   AnsiDeviceFunction(
        number="50",
        name_pt="Sobrecorrente instantânea",
        name_en="Instantaneous overcurrent",
        description="Trip imediato sem retardo proposital",
        typical_application="Faltas francas próximas",
    ),
    "50N":  AnsiDeviceFunction(
        number="50N",
        name_pt="Sobrecorrente neutro instantânea",
        name_en="Instantaneous neutral overcurrent",
        description="Detecta corrente de neutro alta",
        typical_application="Faltas à terra",
    ),
    "50BF": AnsiDeviceFunction(
        number="50BF",
        name_pt="Falha de disjuntor",
        name_en="Breaker failure",
        description="Backup quando disjuntor falha em abrir",
        typical_application="Backup local de proteção",
    ),
    "50HS": AnsiDeviceFunction(
        number="50HS",
        name_pt="Switch-on-to-fault",
        name_en="Switch-on-to-fault",
        description="Falta detectada na energização",
        typical_application="Linhas (detectar falta nas chaves)",
    ),
    "51":   AnsiDeviceFunction(
        number="51",
        name_pt="Sobrecorrente temporizada",
        name_en="Time-delayed overcurrent",
        description="TC curve IEC ou IEEE",
        typical_application="Coordenação seletiva (Buff Book)",
    ),
    "51N":  AnsiDeviceFunction(
        number="51N",
        name_pt="Sobrecorrente neutro temporizada",
        name_en="Time-delayed neutral overcurrent",
        description="TC curve para corrente de neutro",
        typical_application="Coordenação de faltas à terra",
    ),
    "51V":  AnsiDeviceFunction(
        number="51V",
        name_pt="Sobrecorrente com restrição/controle de tensão",
        name_en="Voltage-restrained / voltage-controlled overcurrent",
        description="Pickup ajustado por tensão (51VR/51VC)",
        typical_application="Geradores (faltas trifásicas vs sobrecargas)",
    ),
    "51LR": AnsiDeviceFunction(
        number="51LR",
        name_pt="Rotor bloqueado",
        name_en="Locked rotor",
        description="Detecta rotor parado em motor (I alta + tempo)",
        typical_application="Motores de indução",
    ),
    "59":   AnsiDeviceFunction(
        number="59",
        name_pt="Sobretensão",
        name_en="Overvoltage",
        description="Detecta tensão acima do limite",
        typical_application="Carga sensível, isolação",
    ),
    "59N":  AnsiDeviceFunction(
        number="59N",
        name_pt="Sobretensão de neutro",
        name_en="Neutral overvoltage",
        description="Tensão de deslocamento de neutro (3V0)",
        typical_application="Faltas à terra em sistemas isolados",
    ),
    "64REF": AnsiDeviceFunction(
        number="64REF",
        name_pt="Falta restrita à terra",
        name_en="Restricted earth fault",
        description="Diferencial de neutro de transformador",
        typical_application="Transformadores Y-aterrados",
    ),
    "66":   AnsiDeviceFunction(
        number="66",
        name_pt="Inibição de partida de motor",
        name_en="Motor restart inhibition",
        description="Limita número de partidas/hora",
        typical_application="Motores grandes",
    ),
    "67":   AnsiDeviceFunction(
        number="67",
        name_pt="Sobrecorrente direcional",
        name_en="Directional overcurrent",
        description="Sobrecorrente apenas em uma direção",
        typical_application="Linhas em anel, alimentadores duplos",
    ),
    "67N":  AnsiDeviceFunction(
        number="67N",
        name_pt="Sobrecorrente neutro direcional",
        name_en="Directional neutral overcurrent",
        description="Direção de I0 (faltas à terra)",
        typical_application="Sistemas com aterramento ressonante",
    ),
    "67NI": AnsiDeviceFunction(
        number="67NI",
        name_pt="Falta intermitente à terra",
        name_en="Transient intermittent ground fault",
        description="Detecta arcos intermitentes à terra",
        typical_application="Cabos subterrâneos",
    ),
    "68F2": AnsiDeviceFunction(
        number="68F2",
        name_pt="Inrush de 2ª harmônica",
        name_en="2nd harmonic inrush detection",
        description="Bloqueia trip durante energização",
        typical_application="Diferencial 87T de transformador",
    ),
    "68H5": AnsiDeviceFunction(
        number="68H5",
        name_pt="Detecção de 5ª harmônica",
        name_en="5th harmonic detection",
        description="Indica sobre-excitação V/Hz",
        typical_application="Bloqueio em transformadores",
    ),
    "78V":  AnsiDeviceFunction(
        number="78V",
        name_pt="Vector shift",
        name_en="Vector shift / vector surge",
        description="Variação súbita de fase",
        typical_application="Geração distribuída anti-ilhamento",
    ),
    "79":   AnsiDeviceFunction(
        number="79",
        name_pt="Religamento automático",
        name_en="Auto-recloser",
        description="Tenta religamento após trip",
        typical_application="Linhas aéreas (faltas transitórias)",
    ),
    "81":   AnsiDeviceFunction(
        number="81",
        name_pt="Frequência (acima/abaixo)",
        name_en="Over/Under-frequency",
        description="Detecta f fora dos limites",
        typical_application="Anti-ilhamento, load-shedding",
    ),
    "81R":  AnsiDeviceFunction(
        number="81R",
        name_pt="Taxa de variação de frequência",
        name_en="Rate of change of frequency (df/dt)",
        description="Detecta perturbações rápidas",
        typical_application="Anti-ilhamento avançado",
    ),
    "86":   AnsiDeviceFunction(
        number="86",
        name_pt="Lockout",
        name_en="Lockout (master trip)",
        description="Memoriza trip; rearme manual",
        typical_application="Backup de proteção crítica",
    ),
    "87":   AnsiDeviceFunction(
        number="87",
        name_pt="Diferencial",
        name_en="Differential protection",
        description="Compara corrente de entrada vs saída",
        typical_application="Geradores, transformadores, barras",
    ),
    "87T":  AnsiDeviceFunction(
        number="87T",
        name_pt="Diferencial de transformador",
        name_en="Transformer differential",
        description="87 com bloqueio por harmônica",
        typical_application="Transformadores",
    ),
    "87L":  AnsiDeviceFunction(
        number="87L",
        name_pt="Diferencial de linha",
        name_en="Line differential",
        description="87 com comunicação fim-a-fim",
        typical_application="Linhas de transmissão",
    ),
    "87B":  AnsiDeviceFunction(
        number="87B",
        name_pt="Diferencial de barramento",
        name_en="Bus differential",
        description="87 multi-terminal",
        typical_application="Barramentos de subestação",
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_function(number: str) -> AnsiDeviceFunction | None:
    """Retorna função ANSI pelo número, ou None se desconhecido."""
    return ANSI_DEVICE_FUNCTIONS.get(number.upper())


def all_function_numbers() -> tuple[str, ...]:
    """Retorna tupla com todos os números de função catalogados."""
    return tuple(ANSI_DEVICE_FUNCTIONS.keys())


def search_by_keyword(keyword: str) -> list[AnsiDeviceFunction]:
    """Busca funções por palavra-chave em qualquer campo textual."""
    kw = keyword.lower()
    results = []
    for f in ANSI_DEVICE_FUNCTIONS.values():
        searchable = (
            f.name_pt + " " + f.name_en + " "
            + f.description + " " + f.typical_application
        ).lower()
        if kw in searchable:
            results.append(f)
    return results
