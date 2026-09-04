"""Empacota o módulo RUL de isolação para entrega.

Reúne num único ZIP tudo que a linha de trabalho produziu, na forma que a
diretriz de fechamento pede: **texto em Markdown, código em Python**, mais
os dados brutos que sustentam cada número.

O que entra
============

* ``DIRETRIZES_ADDON.md`` — as diretrizes de construção para o agente do
  Olivas PSS, na raiz do pacote, porque é o primeiro arquivo a ler.
* ``docs/`` — os documentos do estudo e todos os anexos, incluindo os
  conjuntos de dados brutos em ``docs/anexos/dados/``.
* ``codigo/`` — os pacotes ``app/simulation/emt/`` e
  ``app/postprocessor/prognosis/``, os scripts de varredura e campanha, e
  as suítes de teste, preservando a estrutura de diretórios do
  repositório para que possam ser aplicados sem tradução de caminho.
* ``MANIFESTO.md`` — a lista completa, com tamanho e SHA-256 de cada
  arquivo, para que o destinatário possa verificar a integridade.

O que NÃO entra
================

Nada de ``__pycache__``, nada de artefato de build e nada fora das listas
declaradas em :data:`CONJUNTOS`. O empacotador é explícito por decisão:
uma varredura por padrão glob arrastaria arquivo alheio ao módulo e o
destinatário não teria como saber o que é do estudo e o que não é.

Uso
====

.. code-block:: bash

    python scripts/empacotar_rul.py --saida entrega/olivas_rul_isolamento.zip
"""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: Nome do diretório-raiz dentro do ZIP. Um ZIP que se descompacta
#: derramando arquivos no diretório corrente é hostil ao destinatário.
PREFIXO: str = "olivas_rul_isolamento"


@dataclass(frozen=True)
class Conjunto:
    """Um grupo de arquivos a incluir.

    Attributes
    ----------
    rotulo:
        Nome do grupo no manifesto.
    origem:
        Diretório de origem, relativo à raiz do repositório.
    destino:
        Diretório de destino dentro do pacote.
    padroes:
        Padrões glob aplicados sob ``origem``.
    descricao:
        O que o grupo contém, para o manifesto.
    """

    rotulo: str
    origem: str
    destino: str
    padroes: tuple[str, ...]
    descricao: str


CONJUNTOS: tuple[Conjunto, ...] = (
    Conjunto(
        rotulo="Estudo",
        origem="docs/research/rul_isolamento",
        destino="docs",
        padroes=("*.md", "anexos/**/*.md"),
        descricao=(
            "Documentos do estudo, das três etapas iniciais à linha de "
            "validação (08 a 11), mais os anexos de fichamento, pesquisa "
            "normativa, mapas do repositório e veredictos de verificação"
        ),
    ),
    Conjunto(
        rotulo="Dados",
        origem="docs/research/rul_isolamento/anexos/dados",
        destino="docs/anexos/dados",
        padroes=("*.json",),
        descricao=(
            "Conjuntos brutos das varreduras e campanhas. Cada um traz um "
            "bloco 'configuracao' com semente, passo e bases, suficiente "
            "para reproduzir qualquer linha"
        ),
    ),
    Conjunto(
        rotulo="Motor EMT",
        origem="app/simulation/emt",
        destino="codigo/app/simulation/emt",
        padroes=("*.py", "cases/*.py"),
        descricao=(
            "Motor de transitórios eletromagnéticos dedicado: kernel de "
            "Dommel, MNA, CDA, linhas Bergeron e JMarti, disjuntor a "
            "vácuo, snubber, compensação de não linearidades, para-raios "
            "e disrupção de isolação"
        ),
    ),
    Conjunto(
        rotulo="Prognóstico",
        origem="app/postprocessor/prognosis",
        destino="codigo/app/postprocessor/prognosis",
        padroes=("*.py",),
        descricao=(
            "Perfil de estresse, modelos de dano, RUL, Asset Health Index "
            "e a campanha de manobras com os dois caminhos de fim de vida"
        ),
    ),
    Conjunto(
        rotulo="Scripts",
        origem="scripts",
        destino="codigo/scripts",
        padroes=(
            "varredura_vcb.py",
            "varredura_rrds.py",
            "campanha_rul.py",
            "empacotar_rul.py",
        ),
        descricao="Drivers reprodutíveis das varreduras, da campanha e deste pacote",
    ),
    Conjunto(
        rotulo="Testes",
        origem="tests",
        destino="codigo/tests",
        # Explícito, e não por glob: ``test_pp_*`` é o prefixo de TODA a
        # suíte do pós-processador — 230 arquivos, dos quais dois são
        # deste módulo. Um glob arrastaria 228 arquivos alheios e o
        # destinatário não teria como distinguir.
        padroes=(
            "test_emt_arrester.py",
            "test_emt_caso_referencia_atp.py",
            "test_emt_flashover.py",
            "test_emt_jmarti.py",
            "test_emt_kernel.py",
            "test_emt_nonlinear.py",
            "test_emt_referencia_eee873.py",
            "test_emt_steady_state.py",
            "test_emt_vcb_scenarios.py",
            "test_emt_vcb_snubber.py",
            "test_pp_prognosis_core.py",
            "test_pp_switching_campaign.py",
        ),
        descricao=(
            "Suítes do módulo. São parte do entregável: os testes são onde "
            "os achados do estudo estão fixados contra regressão"
        ),
    ),
)

#: Arquivos avulsos, com destino explícito.
AVULSOS: tuple[tuple[str, str, str], ...] = (
    (
        "docs/HANDOFF_MODULO_RUL_ISOLAMENTO.md",
        "HANDOFF_ORIGINAL.md",
        "Handoff inicial de integração, anterior às diretrizes",
    ),
)


def _sha256(caminho: Path) -> str:
    """Digest SHA-256 do arquivo, em hexadecimal."""
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def coletar(raiz: Path) -> list[tuple[Path, str, str]]:
    """Lista ``(caminho absoluto, caminho no ZIP, rótulo do grupo)``.

    Raises
    ------
    FileNotFoundError
        Diretório de origem declarado que não existe — sinal de que o
        empacotador ficou desatualizado em relação ao repositório, e não
        de que o arquivo é opcional.
    """
    itens: list[tuple[Path, str, str]] = []
    vistos: set[str] = set()
    for c in CONJUNTOS:
        base = raiz / c.origem
        if not base.is_dir():
            raise FileNotFoundError(
                f"conjunto {c.rotulo!r}: diretório de origem inexistente: {c.origem}"
            )
        for padrao in c.padroes:
            for arquivo in sorted(base.glob(padrao)):
                if not arquivo.is_file() or "__pycache__" in arquivo.parts:
                    continue
                relativo = arquivo.relative_to(base)
                destino = f"{PREFIXO}/{c.destino}/{relativo.as_posix()}"
                if destino in vistos:
                    continue
                vistos.add(destino)
                itens.append((arquivo, destino, c.rotulo))
    for origem, destino, _descricao in AVULSOS:
        arquivo = raiz / origem
        if not arquivo.is_file():
            raise FileNotFoundError(f"arquivo avulso inexistente: {origem}")
        alvo = f"{PREFIXO}/{destino}"
        if alvo not in vistos:
            vistos.add(alvo)
            itens.append((arquivo, alvo, "Avulso"))
    return itens


def manifesto(itens: list[tuple[Path, str, str]], raiz: Path) -> str:
    """Manifesto em Markdown, com tamanho e SHA-256 de cada arquivo."""
    linhas = [
        "# Manifesto do pacote",
        "",
        "Lista completa do que este ZIP contém, com tamanho e digest SHA-256 de cada",
        "arquivo. Para conferir a integridade de um arquivo depois de extrair:",
        "",
        "```bash",
        "sha256sum <arquivo>",
        "```",
        "",
        "## Grupos",
        "",
        "| Grupo | Arquivos | Conteúdo |",
        "|---|---|---|",
    ]
    por_grupo: dict[str, int] = {}
    for _a, _d, rotulo in itens:
        por_grupo[rotulo] = por_grupo.get(rotulo, 0) + 1
    descricoes = {c.rotulo: c.descricao for c in CONJUNTOS}
    descricoes["Avulso"] = "; ".join(d for _o, _d, d in AVULSOS)
    for rotulo, n in por_grupo.items():
        linhas.append(f"| {rotulo} | {n} | {descricoes.get(rotulo, '')} |")

    total = sum((raiz / a.relative_to(raiz)).stat().st_size for a, _d, _r in itens)
    linhas += [
        "",
        f"**Total:** {len(itens)} arquivos, {total / 1024:.0f} KiB antes da compressão.",
        "",
        "## Arquivos",
        "",
        "| Arquivo | Bytes | SHA-256 |",
        "|---|---|---|",
    ]
    for arquivo, destino, _rotulo in sorted(itens, key=lambda x: x[1]):
        curto = destino[len(PREFIXO) + 1 :]
        linhas.append(
            f"| `{curto}` | {arquivo.stat().st_size} | `{_sha256(arquivo)}` |"
        )
    return "\n".join(linhas) + "\n"


def leia_me(itens: list[tuple[Path, str, str]]) -> str:
    """Índice do pacote — o primeiro arquivo que o destinatário abre."""
    n = len(itens)
    return f"""# Módulo RUL de isolação de estator — pacote de entrega

{n} arquivos. Texto em Markdown, código em Python, dados em JSON.

## Por onde começar

1. **`DIRETRIZES_ADDON.md`** — o que construir e em que ordem, para
   introduzir o módulo como add-on da licença Empresarial do Olivas PSS.
   É o primeiro arquivo a ler.
2. **`docs/00_INDICE.md`** — índice do estudo técnico, com a nota
   metodológica e o sistema de rótulos de evidência.
3. **`MANIFESTO.md`** — a lista completa com digest, para conferência.

## Estrutura

```
{PREFIXO}/
├── DIRETRIZES_ADDON.md      diretrizes de construção do add-on
├── HANDOFF_ORIGINAL.md      handoff inicial, anterior às diretrizes
├── MANIFESTO.md             lista de arquivos com SHA-256
├── docs/                    estudo técnico (Markdown) e anexos
│   └── anexos/dados/        conjuntos brutos (JSON)
└── codigo/                  Python, na estrutura do repositório
    ├── app/simulation/emt/          motor de transitórios dedicado
    ├── app/postprocessor/prognosis/ prognóstico e campanha de manobras
    ├── scripts/                     drivers reprodutíveis
    └── tests/                       suítes do módulo
```

A estrutura de `codigo/` reproduz a do repositório de origem: os arquivos
podem ser copiados para uma árvore do Olivas PSS sem tradução de caminho.

## Como reproduzir os números

Os drivers são determinísticos por semente. O conjunto de referência é
`docs/anexos/dados/varredura_vcb_n150_dt200ns.json`, reproduzível com:

```bash
python scripts/varredura_vcb.py --n 150 --seed 20260903 --dt 2e-7 \\
    --cenarios literatura --mitigacoes nenhuma,para_raios,disrupcao \\
    --saida varredura.json
```

A cadeia completa manobra → estresse → dano → vida:

```bash
python scripts/campanha_rul.py --n 150 --dt 2e-7 --para-raios \\
    --saida campanha.json
```

**Atenção ao passo.** `--dt 2e-7` não é preciosismo: com 1 µs o corpo da
distribuição sai 21 % abaixo. O custo é cinco vezes maior por execução.

## Aviso sobre os números

O estudo separa três graus de certeza, e misturá-los é o principal risco
de uso indevido:

* **Calibrado por contagem** — a taxa de travessia do envelope normativo
  e o instante da travessia. Não dependem de parâmetro de curva de vida.
* **Arquitetura com incerteza propagada** — o número de manobras por
  envelhecimento. Os parâmetros da curva de vida **não estão calibrados**
  para mica-epóxi pré-formada de média tensão; varrendo o expoente na
  faixa publicada a vida varia por três ordens de grandeza. Nunca exiba
  esse número sem a faixa.
* **Livre de calibração** — a decisão de mitigar, que se mantém em toda a
  faixa do expoente.

As limitações estão declaradas em `KNOWN_LIMITATIONS` de cada módulo do
código e nas seções de limitações de cada documento. Elas são parte do
entregável, não ressalva de rodapé.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("entrega") / f"{PREFIXO}.zip",
        help="caminho do ZIP a gerar",
    )
    parser.add_argument(
        "--diretrizes",
        type=Path,
        default=None,
        help=(
            "arquivo Markdown com as diretrizes de construção do add-on, "
            "incluído na raiz do pacote como DIRETRIZES_ADDON.md"
        ),
    )
    args = parser.parse_args(argv)

    itens = coletar(RAIZ)
    args.saida.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(
        args.saida, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as z:
        for arquivo, destino, _rotulo in itens:
            z.write(arquivo, destino)
        if args.diretrizes is not None:
            if not args.diretrizes.is_file():
                raise FileNotFoundError(
                    f"arquivo de diretrizes inexistente: {args.diretrizes}"
                )
            z.write(args.diretrizes, f"{PREFIXO}/DIRETRIZES_ADDON.md")
        z.writestr(f"{PREFIXO}/MANIFESTO.md", manifesto(itens, RAIZ))
        z.writestr(f"{PREFIXO}/LEIA-ME.md", leia_me(itens))

    tamanho = args.saida.stat().st_size
    print(f"{len(itens)} arquivos + manifesto + leia-me")
    print(f"gravado em {args.saida} ({tamanho / 1024:.0f} KiB)")
    por_grupo: dict[str, int] = {}
    for _a, _d, rotulo in itens:
        por_grupo[rotulo] = por_grupo.get(rotulo, 0) + 1
    for rotulo, n in por_grupo.items():
        print(f"  {rotulo:14s} {n:3d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
