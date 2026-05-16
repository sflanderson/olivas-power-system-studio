"""
app.preprocessor.spec.models — modelos pydantic v2 para componentes.

Este módulo define o schema canônico de um componente do Olivas ATP
Studio no formato ``.ocomp``.

Arquitetura (Claude-first)
--------------------------
Os modelos pydantic aqui são o **ponto único da verdade**:

* YAML (``load_ocomp_file``) e JSON (``model_dump``) são apenas
  representações serializadas — o modelo em Python é o canônico.
* ``ComponentSpec.model_json_schema()`` é usado pelo
  :mod:`app.llm.agent` para gerar ``tools[].input_schema``, permitindo
  que o Claude gere specs novos obedecendo ao contrato.
* Todos os validators têm mensagens descritivas (preferíveis aos
  defaults do pydantic) para que erros de validação sejam
  consumíveis por Claude em tempo real.

Campos obrigatórios mínimos para um spec válido:

* ``code``: identificador único (ex. ``"R"``, ``"VCB3"``)
* ``label_pt``: rótulo humano em português
* ``category``: uma das categorias predefinidas
* ``symbol``: metadados gráficos
* ``pins``: pelo menos 1 pino
* ``atp_emission``: especificação de emissão ATP

Todos os outros campos são opcionais (têm default razoável).

Referências
-----------
- Política clean-room: ``docs/LICENSING.md``.
- Convenções de escrita de specs: ``docs/OCOMP_AUTHORING.md``
  (a criar em v0.21.9).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PinRole(str, Enum):
    """Papel elétrico de um pino."""

    TERMINAL = "terminal"
    """Terminal elétrico principal (conduz corrente)."""

    CONTROL = "control"
    """Sinal de controle TACS/MODELS (lógico, não condutor)."""

    GROUND = "ground"
    """Referência de terra."""

    OUTPUT = "output"
    """Saída de medidor / probe (publica um sinal)."""

    SHIELD = "shield"
    """Blindagem de cabo (LCC)."""


class PinPhase(str, Enum):
    """Fase associada ao pino (para multifásicos)."""

    A = "A"
    B = "B"
    C = "C"
    N = "N"
    """Neutro."""

    NONE = "none"
    """Monofásico / sem fase específica."""


class PropertyType(str, Enum):
    """Tipo de dado de uma propriedade."""

    FLOAT = "float"
    INT = "int"
    STRING = "string"
    BOOL = "bool"
    FILE = "file"
    """Caminho de arquivo (.pch, .mod, .lib)."""

    ENUM = "enum"
    """Seleção discreta — ver ``choices``."""

    TABLE = "table"
    """Tabela 2-coluna (ex. R(i) não-linear)."""

    EXPRESSION = "expression"
    """Expressão TACS (string livre com sintaxe específica)."""


class PropertyGroup(str, Enum):
    """Grupo para agrupamento visual no painel de propriedades."""

    MAIN = "main"
    TIMING = "timing"
    ELECTRICAL = "electrical"
    THERMAL = "thermal"
    NONLINEAR = "nonlinear"
    REIGNITION = "reignition"
    """Parâmetros do modelo estatístico de reignição (VCB)."""

    GEOMETRY = "geometry"
    """Dimensões físicas (LCC, XFMR)."""

    ADVANCED = "advanced"
    METADATA = "metadata"


class AtpEmissionKind(str, Enum):
    """
    Tipo de emissão ATP para um componente.

    Cada valor mapeia para um gerador dedicado em
    :mod:`app.preprocessor.bridge_to_atp`.
    """

    RESISTOR = "resistor"
    INDUCTOR = "inductor"
    CAPACITOR = "capacitor"
    RLC_SERIES = "rlc_series"
    """R-L-C em série em 1 ramo."""

    SWITCH_SIMPLE = "switch_simple"
    """Chave com Topen/Tclose em 1 ramo."""

    MULTI_SWITCH = "multi_switch"
    """N chaves (ex. VCB3 = 3 ramos independentes)."""

    DIODE = "diode"
    THYRISTOR = "thyristor"
    GTO = "gto"
    IGBT = "igbt"
    MOSFET = "mosfet"

    SOURCE_DC = "source_dc"
    SOURCE_AC = "source_ac"
    SOURCE_RAMP = "source_ramp"
    SOURCE_SURGE = "source_surge"

    LINE_PI = "line_pi"
    LINE_BERGERON = "line_bergeron"
    LINE_JMARTI = "line_jmarti"

    TRANSFORMER_2W = "transformer_2w"
    TRANSFORMER_3W = "transformer_3w"
    TRANSFORMER_COUPLED = "transformer_coupled"

    PROBE_V = "probe_v"
    PROBE_I = "probe_i"

    MODEL_USE = "model_use"
    """Gera cartão USE de MODELS referenciando um .mod."""

    TACS_SIGNAL = "tacs_signal"
    GROUND = "ground"

    NONLINEAR_R = "nonlinear_r"
    NONLINEAR_L = "nonlinear_l"
    ZNO = "zno"
    """Para-raios tipo-92."""

    CUSTOM = "custom"
    """Gerador dedicado — ver ``custom_emitter``."""


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class PinSpec(BaseModel):
    """
    Um pino elétrico (ou lógico) do componente.

    A posição é dada em coordenadas locais relativas ao "anchor" do
    componente (normalmente o centro do símbolo), usando a mesma
    unidade que a grade do editor (20 px).
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        description="Nome único do pino dentro do componente (ex. 'ANO', 'A_in').",
    )
    label: str = Field(
        ...,
        description="Rótulo humano visível (ex. 'Fase A - entrada').",
    )
    position: tuple[int, int] = Field(
        ...,
        description="Coordenadas (x, y) relativas ao anchor, em unidades de grade.",
    )
    phase: PinPhase = Field(
        default=PinPhase.NONE,
        description="Fase elétrica do pino (A/B/C/N) para multifásicos.",
    )
    role: PinRole = Field(
        default=PinRole.TERMINAL,
        description="Papel elétrico (terminal/control/ground/output/shield).",
    )
    description: str | None = Field(
        default=None,
        description="Descrição livre (mostrada em tooltip).",
    )

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("nome de pino não pode ser vazio")
        return v.strip()


class PropertySpec(BaseModel):
    """
    Uma propriedade editável do componente.

    Corresponde a uma linha no painel de propriedades do editor. Se
    ``visible == False``, é mantida no modelo mas não mostrada ao usuário
    (tipicamente parâmetros avançados ou derivados).
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        description="Nome único da propriedade (ex. 'R', 'T_open_A').",
    )
    label: str = Field(
        ...,
        description="Rótulo humano visível (ex. 'Resistência', 'T_open A').",
    )
    unit: str | None = Field(
        default=None,
        description="Unidade física (ex. 'Ω', 's', 'A/µs'). None = adimensional.",
    )
    type: PropertyType = Field(
        default=PropertyType.FLOAT,
        description="Tipo de dado da propriedade.",
    )
    default: Any = Field(
        default=None,
        description="Valor default quando o componente é instanciado.",
    )
    visible: bool = Field(
        default=True,
        description="Mostrar no painel de propriedades?",
    )
    group: PropertyGroup = Field(
        default=PropertyGroup.MAIN,
        description="Grupo para agrupamento visual no painel.",
    )
    min: float | None = Field(
        default=None,
        description="Valor mínimo permitido (apenas para tipos numéricos).",
    )
    max: float | None = Field(
        default=None,
        description="Valor máximo permitido (apenas para tipos numéricos).",
    )
    choices: list[Any] | None = Field(
        default=None,
        description="Lista de opções para type=ENUM. None para outros tipos.",
    )
    phase: PinPhase = Field(
        default=PinPhase.NONE,
        description="Fase associada (para propriedades multifásicas como T_open_A).",
    )
    description: str | None = Field(
        default=None,
        description="Descrição livre (mostrada em tooltip ou help contextual).",
    )
    example: Any = Field(
        default=None,
        description="Exemplo de valor típico (para LLM e help).",
    )
    widget_hint: str | None = Field(
        default=None,
        description=(
            "Hint opcional para o painel de propriedades escolher um "
            "widget customizado em vez do default por PropertyType. "
            "Ex.: 'saturation_curve' → editor de tabela (i, ψ) com preview."
        ),
    )

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("nome de propriedade não pode ser vazio")
        return v.strip()

    @model_validator(mode="after")
    def _validate_enum_choices(self) -> "PropertySpec":
        if self.type == PropertyType.ENUM and not self.choices:
            raise ValueError(
                f"propriedade {self.name!r}: type=ENUM exige 'choices' não-vazio"
            )
        if self.type != PropertyType.ENUM and self.choices is not None:
            raise ValueError(
                f"propriedade {self.name!r}: 'choices' só faz sentido com type=ENUM"
            )
        return self

    @model_validator(mode="after")
    def _validate_min_max(self) -> "PropertySpec":
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(
                f"propriedade {self.name!r}: min ({self.min}) > max ({self.max})"
            )
        return self


class SymbolSpec(BaseModel):
    """
    Geometria e renderização do símbolo gráfico.

    Dois modos de renderização:

    * ``renderer`` = nome de classe em :mod:`app.preprocessor.symbols`
      (ex. ``"VCB3PhaseSymbol"``) — usado para símbolos complexos que
      exigem código Python.
    * ``renderer`` = ``"svg"`` + ``icon_svg`` preenchido com string SVG —
      usado para símbolos simples declarativos.
    """

    model_config = ConfigDict(extra="forbid")

    size: tuple[int, int] = Field(
        ...,
        description="Tamanho (largura, altura) em unidades de grade.",
    )
    bounding_box: tuple[int, int, int, int] = Field(
        ...,
        description="Bounding box (x, y, w, h) relativo ao anchor.",
    )
    renderer: str = Field(
        ...,
        description=(
            "Nome da classe renderer em app.preprocessor.symbols, "
            "ou 'svg' para usar icon_svg."
        ),
    )
    icon_svg: str | None = Field(
        default=None,
        description="String SVG inline (apenas para renderer='svg').",
    )

    @model_validator(mode="after")
    def _svg_consistency(self) -> "SymbolSpec":
        if self.renderer == "svg" and not self.icon_svg:
            raise ValueError(
                "renderer='svg' exige 'icon_svg' preenchido com string SVG"
            )
        if self.renderer != "svg" and self.icon_svg:
            raise ValueError(
                f"renderer={self.renderer!r} não usa icon_svg; "
                "defina renderer='svg' se quiser SVG declarativo"
            )
        return self


class BranchMapping(BaseModel):
    """
    Mapeamento de 1 ramo ATP dentro de um componente multi-ramo.

    Usado por componentes como ``VCB3`` (3 chaves independentes) e
    futuros ``R3`` / ``L3`` / ``C3`` trifásicos.

    ``property_mapping`` traduz nomes de **propriedades do componente**
    (do `.ocomp`) para nomes de **parâmetros do gerador ATP**
    (ex. ``{"t_open": "T_open_A"}``).
    """

    model_config = ConfigDict(extra="forbid")

    phase: PinPhase | None = Field(
        default=None,
        description="Fase deste ramo (A/B/C/N). None = monofásico ou N/A.",
    )
    pins: list[str] = Field(
        ...,
        description=(
            "Lista de pin names (entry, exit) usados por este ramo. "
            "Mesmos pins definidos em 'pins' do componente."
        ),
    )
    property_mapping: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Mapa {nome_gerador_atp: nome_prop_componente}. "
            "Ex. {'t_open': 'T_open_A', 't_close': 'T_close_A'}."
        ),
    )


class AtpEmissionSpec(BaseModel):
    """Especificação de como o componente é emitido para o arquivo .atp."""

    model_config = ConfigDict(extra="forbid")

    kind: AtpEmissionKind = Field(
        ...,
        description="Tipo de emissão — mapeia para um gerador em bridge_to_atp.",
    )
    count: int = Field(
        default=1,
        ge=0,
        description=(
            "Número de elementos ATP gerados (ex. 3 para VCB3). "
            "Use count=0 para componentes que são apenas metadata "
            "(diretivas Qucs .TR/.DC/.AC/.SP/.SW, bloco Eqn)."
        ),
    )
    branches: list[BranchMapping] = Field(
        default_factory=list,
        description="Um item por ramo ATP (vazio para componentes 1-ramo).",
    )
    model_ref: str | None = Field(
        default=None,
        description="Nome do MODEL referenciado (apenas para kind=MODEL_USE).",
    )
    custom_emitter: str | None = Field(
        default=None,
        description="Nome de função em bridge_to_atp (apenas para kind=CUSTOM).",
    )

    @model_validator(mode="after")
    def _validate_model_use(self) -> "AtpEmissionSpec":
        if self.kind == AtpEmissionKind.MODEL_USE and not self.model_ref:
            raise ValueError("kind=MODEL_USE exige 'model_ref' preenchido")
        # kind=CUSTOM exige custom_emitter APENAS quando há emissão real
        # (count > 0). Componentes com count=0 (metadata: diretivas
        # Qucs .TR/.DC/.AC/.SW/.SP, Eqn) usam CUSTOM como "sentinela"
        # — o bridge simplesmente ignora.
        if (
            self.kind == AtpEmissionKind.CUSTOM
            and self.count > 0
            and not self.custom_emitter
        ):
            raise ValueError(
                "kind=CUSTOM com count>0 exige 'custom_emitter' preenchido"
            )
        return self

    @model_validator(mode="after")
    def _validate_branch_count(self) -> "AtpEmissionSpec":
        if self.branches and len(self.branches) != self.count:
            raise ValueError(
                f"count={self.count} mas branches tem {len(self.branches)} itens"
            )
        return self


class LLMHintsSpec(BaseModel):
    """
    Metadados para consumo pelo agente LLM (Claude API).

    Esses campos não afetam o comportamento do editor nem da bridge —
    servem apenas para dar contexto semântico ao Claude quando ele
    estiver raciocinando sobre um componente (ex. sugerindo valores,
    diagnosticando um modelo, propondo alternativas).
    """

    model_config = ConfigDict(extra="forbid")

    typical_applications: list[str] = Field(
        default_factory=list,
        description="Aplicações típicas (ex. 'Estudo de TRV', 'Energização de linha').",
    )
    references: list[str] = Field(
        default_factory=list,
        description="Referências bibliográficas (IEEE, CIGRE, IEC).",
    )
    common_mistakes: list[str] = Field(
        default_factory=list,
        description="Erros comuns que o Claude deve verificar / apontar.",
    )
    alternatives: list[str] = Field(
        default_factory=list,
        description="Códigos de componentes alternativos com funcionalidade similar.",
    )


# ---------------------------------------------------------------------------
# ComponentSpec (raiz)
# ---------------------------------------------------------------------------


class ComponentSpec(BaseModel):
    """
    Spec canônico de um componente Olivas.

    Este é o modelo-raiz de um arquivo ``.ocomp``. Todas as operações
    do editor (render, coalescência de nós, emissão ATP, painel de
    propriedades, integração Claude) derivam desta estrutura.

    **Escalabilidade para Claude API**
    Dois pontos de entrada para o LLM:

    1. ``ComponentSpec.llm_tool_schema()`` retorna um JSON Schema pronto
       para usar em ``tools[].input_schema``. Claude gera specs válidos.
    2. ``ComponentSpec.from_llm_dict(d)`` valida um dict (p.ex. vindo
       da resposta do Claude) e levanta ``ValidationError`` estruturada
       em caso de erro, que pode ser reenviada ao Claude para correção.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    schema_version: str = Field(
        default="1.0",
        description="Versão do schema .ocomp. Usar '1.0' até 1º break change.",
    )

    code: str = Field(
        ...,
        description="Código curto único (ex. 'R', 'VCB3'). Alfanumérico + . _ -.",
        min_length=1,
        max_length=32,
    )
    label_pt: str = Field(
        ...,
        description="Rótulo humano em português.",
    )
    label_en: str | None = Field(
        default=None,
        description="Rótulo humano em inglês (opcional).",
    )
    description: str | None = Field(
        default=None,
        description="Descrição longa do componente (Markdown permitido).",
    )
    category: str = Field(
        ...,
        description=(
            "Categoria na paleta. Valores esperados: "
            "passive, coupled, line, source, switch, power_el, "
            "nonlinear, meter, control, sim, machine, transformer."
        ),
    )
    atp_supported: bool = Field(
        default=True,
        description="Tem emissão ATP? False = apenas diretiva Qucs/metadata.",
    )

    symbol: SymbolSpec = Field(
        ...,
        description="Especificação gráfica do símbolo.",
    )
    pins: list[PinSpec] = Field(
        default_factory=list,
        description=(
            "Lista de pinos elétricos. Vazia para componentes sem pinos "
            "(diretivas de simulação .TR/.DC/.AC/.SW/.SP, bloco Eqn, "
            "blocos de controle TACS/MODEL que se conectam via nome de "
            "sinal em vez de pino elétrico)."
        ),
    )
    properties: list[PropertySpec] = Field(
        default_factory=list,
        description="Lista de propriedades editáveis (pode ser vazia).",
    )
    atp_emission: AtpEmissionSpec = Field(
        ...,
        description="Especificação de emissão para arquivo .atp.",
    )
    llm_hints: LLMHintsSpec = Field(
        default_factory=LLMHintsSpec,
        description="Metadados para consumo do agente LLM.",
    )

    # -- Validators --

    @field_validator("code")
    @classmethod
    def _code_valid_chars(cls, v: str) -> str:
        allowed = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
        )
        if not all(c in allowed for c in v):
            raise ValueError(
                f"code inválido: {v!r} (use apenas letras, dígitos, . _ -)"
            )
        return v

    @model_validator(mode="after")
    def _pin_names_unique(self) -> "ComponentSpec":
        names = [p.name for p in self.pins]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(
                f"nomes de pinos duplicados em {self.code!r}: {sorted(duplicates)}"
            )
        return self

    @model_validator(mode="after")
    def _property_names_unique(self) -> "ComponentSpec":
        names = [p.name for p in self.properties]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(
                f"nomes de propriedades duplicados em {self.code!r}: "
                f"{sorted(duplicates)}"
            )
        return self

    @model_validator(mode="after")
    def _emission_pins_exist(self) -> "ComponentSpec":
        pin_names = {p.name for p in self.pins}
        for i, branch in enumerate(self.atp_emission.branches):
            for pin_name in branch.pins:
                if pin_name not in pin_names:
                    raise ValueError(
                        f"{self.code!r}: atp_emission.branches[{i}] referencia "
                        f"pino inexistente {pin_name!r} "
                        f"(pinos válidos: {sorted(pin_names)})"
                    )
        return self

    @model_validator(mode="after")
    def _emission_props_exist(self) -> "ComponentSpec":
        prop_names = {p.name for p in self.properties}
        for i, branch in enumerate(self.atp_emission.branches):
            for target, source in branch.property_mapping.items():
                if source not in prop_names:
                    raise ValueError(
                        f"{self.code!r}: atp_emission.branches[{i}]."
                        f"property_mapping[{target!r}] referencia propriedade "
                        f"inexistente {source!r} "
                        f"(props válidos: {sorted(prop_names)})"
                    )
        return self

    # -- Helpers para LLM / API Claude --

    def to_llm_dict(self) -> dict[str, Any]:
        """
        Serializa para um dict JSON-friendly para envio à API Claude.

        Remove ``None`` para deixar o payload mais enxuto.
        """
        return self.model_dump(mode="json", exclude_none=True)

    @classmethod
    def from_llm_dict(cls, d: dict[str, Any]) -> "ComponentSpec":
        """
        Valida um dict vindo da API Claude e retorna ``ComponentSpec``.

        Levanta ``pydantic.ValidationError`` com erros estruturados em
        caso de falha — o caller pode converter para string e reenviar
        ao Claude para correção iterativa.
        """
        return cls.model_validate(d)

    @classmethod
    def llm_tool_schema(cls) -> dict[str, Any]:
        """
        Retorna JSON Schema para usar em ``tools[].input_schema`` da
        API Claude.

        Referência: https://docs.anthropic.com/en/docs/agents/tool-use
        """
        return cls.model_json_schema()

    # -- Helpers de acesso --

    def pin_by_name(self, name: str) -> PinSpec | None:
        """Retorna o ``PinSpec`` com o nome dado, ou None."""
        for p in self.pins:
            if p.name == name:
                return p
        return None

    def property_by_name(self, name: str) -> PropertySpec | None:
        """Retorna o ``PropertySpec`` com o nome dado, ou None."""
        for p in self.properties:
            if p.name == name:
                return p
        return None

    def pins_by_phase(self, phase: PinPhase) -> list[PinSpec]:
        """Retorna todos os pinos associados à fase dada."""
        return [p for p in self.pins if p.phase == phase]

    def properties_by_group(self, group: PropertyGroup) -> list[PropertySpec]:
        """Retorna todas as propriedades em um grupo."""
        return [p for p in self.properties if p.group == group]
