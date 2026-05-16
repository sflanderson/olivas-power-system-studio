"""
app.preprocessor.tacs — parser e emissor de blocos TACS
(Transient Analysis of Control Systems) do ATP.

TACS é a linguagem de controle inline do ATP, usada para implementar
PIDs, filtros, lógica digital, geração de sinais customizados etc.
A seção do ``.atp`` é ``/TACS HYBRID`` (Section V do Rule Book).

MVP v0.26.0 — escopo
--------------------

* Tokenizer + parser de expressões aritméticas:
    operadores: ``+ - * / ^`` (potência)
    funções: ``sin cos tan asin acos atan sinh cosh tanh
              exp log log10 sqrt abs max min``
    constantes: ``pi e``
    parênteses, números (int/float/exp), identificadores.
* AST (frozen dataclasses) + validador de identificadores e funções.
* ``TacsBlock(name, inputs, expression, output, initial_value)``
  como dado para emissão.
* Emissão de bloco ``/TACS HYBRID`` com **device-88** (FORTRAN
  algebraic expression) — formato livre legível com comentários
  ``C `` documentando inputs/outputs.

Limitações conhecidas v0.26.0
-----------------------------

* Sem operadores lógicos (AND/OR/NOT) e comparações; ficam para
  v0.26.1 (PID / limiters / lógica digital).
* Sem transfer functions s-domain (devices 58/59) — v0.26.1.
* Apenas device-88; outras ATP TACS devices (integrador 58,
  derivador 59, somador 98) ficam para refinamento incremental.

Referências
-----------

* ATP Rule Book vol 2, Section V (TACS Hybrid).
* H. W. Dommel, *EMTP Theory Book* §14 (TACS background).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union


# ---------------------------------------------------------------------------
# Conjuntos reservados
# ---------------------------------------------------------------------------


_TACS_FUNCTIONS_UNARY = frozenset({
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sinh", "cosh", "tanh",
    "exp", "log", "log10", "sqrt",
    "abs",
    # v0.26.1: novos
    "step", "sign", "floor", "ceil",
})

_TACS_FUNCTIONS_BINARY = frozenset({
    # v0.26.1: 2 args exatos
    "mod",
})

_TACS_FUNCTIONS_TERNARY = frozenset({
    # v0.26.1: 3 args exatos — if(cond, then, else)
    "if",
})

_TACS_FUNCTIONS_VARIADIC = frozenset({
    # >= 2 args
    "max", "min",
})

_TACS_FUNCTIONS = (
    _TACS_FUNCTIONS_UNARY
    | _TACS_FUNCTIONS_BINARY
    | _TACS_FUNCTIONS_TERNARY
    | _TACS_FUNCTIONS_VARIADIC
)


_TACS_CONSTANTS = frozenset({"pi", "e"})


# v0.26.1: operadores keyword (case-sensitive UPPERCASE)
_TACS_KEYWORD_OPS = frozenset({"AND", "OR", "NOT"})

# v0.26.1: mapeamento dotted FORTRAN → forma canônica interna
_DOTTED_OP_MAP = {
    ".EQ.": "==", ".NE.": "!=",
    ".LT.": "<",  ".GT.": ">",
    ".LE.": "<=", ".GE.": ">=",
    ".AND.": "AND", ".OR.": "OR", ".NOT.": "NOT",
}

# v0.26.1: forma canônica → ATP-style (FORTRAN-77 dotted)
_OP_TO_ATP_STYLE = {
    "==": ".EQ.", "!=": ".NE.",
    "<": ".LT.",  ">": ".GT.",
    "<=": ".LE.", ">=": ".GE.",
    "AND": ".AND.", "OR": ".OR.", "NOT": ".NOT.",
}

_COMPARISON_OPS = frozenset({"==", "!=", "<", ">", "<=", ">="})


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Token:
    kind: str        # NUM, IDENT, OP, LPAREN, RPAREN, COMMA, EOF
    value: str
    pos: int = 0


def tokenize(expr: str) -> list[Token]:
    """
    Quebra a expressão em tokens. Levanta ``SyntaxError`` em
    caractere ilegal.

    v0.26.1
    -------
    Adiciona:

    * Operadores multi-char: ``== != <= >= < >``.
    * FORTRAN-77 dotted: ``.EQ. .NE. .LT. .GT. .LE. .GE.
      .AND. .OR. .NOT.`` — mapeados para a forma canônica
      interna (``== != < > <= >= AND OR NOT``).
    * Keywords UPPERCASE: ``AND OR NOT`` viram tokens ``OP``.
    """
    tokens: list[Token] = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c in " \t\n\r":
            i += 1
            continue
        # FORTRAN-style dotted operator: .WORD.
        # Detecta sequência ``. + letras + .``; cobre .EQ./.AND./etc.
        if c == "." and i + 1 < n and expr[i + 1].isalpha():
            start = i
            j = i + 1
            while j < n and expr[j].isalpha():
                j += 1
            if j < n and expr[j] == ".":
                tok_text = expr[start:j + 1].upper()
                normalized = _DOTTED_OP_MAP.get(tok_text)
                if normalized is None:
                    raise SyntaxError(
                        f"Operador dot desconhecido: {tok_text!r} pos {start}"
                    )
                tokens.append(Token("OP", normalized, start))
                i = j + 1
                continue
            # Caso degenerado (".XY" sem ponto final) — falha
            raise SyntaxError(
                f"Operador dot mal-formado pos {start}: faltou '.'"
            )
        # número (int, float, científico) — ``.5`` continua válido
        if c.isdigit() or (c == "." and i + 1 < n and expr[i + 1].isdigit()):
            start = i
            has_dot = c == "."
            i += 1
            while i < n:
                ch = expr[i]
                if ch.isdigit():
                    i += 1
                elif ch == "." and not has_dot:
                    has_dot = True
                    i += 1
                elif ch in "eE":
                    i += 1
                    if i < n and expr[i] in "+-":
                        i += 1
                    while i < n and expr[i].isdigit():
                        i += 1
                    break
                else:
                    break
            tokens.append(Token("NUM", expr[start:i], start))
            continue
        # identificador
        if c.isalpha() or c == "_":
            start = i
            while i < n and (expr[i].isalnum() or expr[i] == "_"):
                i += 1
            tok_text = expr[start:i]
            # AND/OR/NOT (uppercase) viram operadores
            if tok_text in _TACS_KEYWORD_OPS:
                tokens.append(Token("OP", tok_text, start))
            else:
                tokens.append(Token("IDENT", tok_text, start))
            continue
        # operadores multi-char (dois caracteres)
        if i + 1 < n:
            two = expr[i:i + 2]
            if two in ("==", "!=", "<=", ">="):
                tokens.append(Token("OP", two, i))
                i += 2
                continue
        # operadores 1 char (incluindo < e >)
        if c in "+-*/^<>":
            tokens.append(Token("OP", c, i))
            i += 1
            continue
        if c == "(":
            tokens.append(Token("LPAREN", c, i))
            i += 1
            continue
        if c == ")":
            tokens.append(Token("RPAREN", c, i))
            i += 1
            continue
        if c == ",":
            tokens.append(Token("COMMA", c, i))
            i += 1
            continue
        raise SyntaxError(
            f"Caractere inválido em expressão TACS: {c!r} pos {i}"
        )
    tokens.append(Token("EOF", "", n))
    return tokens


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TacsNumber:
    """Literal numérico."""
    value: float


@dataclass(frozen=True)
class TacsVar:
    """Referência a variável (input externo, ``pi``, ``e`` etc.)."""
    name: str


@dataclass(frozen=True)
class TacsBinOp:
    """Operação binária — op ∈ ``+ - * / ^``."""
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class TacsUnaryOp:
    """Sinal unário — op ∈ ``+ -``."""
    op: str
    operand: object


@dataclass(frozen=True)
class TacsFuncCall:
    """Chamada de função: ``name(arg, arg, …)``."""
    name: str
    args: tuple


TacsExpr = Union[TacsNumber, TacsVar, TacsBinOp, TacsUnaryOp, TacsFuncCall]


# ---------------------------------------------------------------------------
# Parser (recursive descent)
# ---------------------------------------------------------------------------


class _Parser:
    """Parser recursive-descent para a gramática (v0.26.1):

    ::

        expr     = orexpr
        orexpr   = andexpr ('OR' andexpr)*
        andexpr  = notexpr ('AND' notexpr)*
        notexpr  = 'NOT' notexpr | compare
        compare  = addsub (('==' | '!=' | '<' | '>' | '<=' | '>=') addsub)?
        addsub   = muldiv (('+' | '-') muldiv)*
        muldiv   = power  (('*' | '/') power)*
        power    = unary  ('^' power)?         (right-associative)
        unary    = ('+' | '-') unary | atom
        atom     = NUM
                 | IDENT '(' arglist? ')'      (função)
                 | IDENT                       (variável)
                 | '(' expr ')'
        arglist  = expr (',' expr)*

    Notas
    -----
    * Comparação é **não-associativa**: ``a < b < c`` é erro;
      use ``(a < b) AND (b < c)``.
    * ``OR`` é left-associative.
    * ``AND`` é left-associative; tem precedência maior que ``OR``.
    * ``NOT`` é unary, right-associative (``NOT NOT x`` válido).
    """

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    @property
    def cur(self) -> Token:
        return self.tokens[self.pos]

    def _eat(self, kind: str) -> Token:
        t = self.cur
        if t.kind != kind:
            raise SyntaxError(
                f"Esperado {kind}, achado {t.kind}({t.value!r}) pos {t.pos}"
            )
        self.pos += 1
        return t

    def parse_expr(self) -> TacsExpr:
        return self._parse_or()

    def _parse_or(self) -> TacsExpr:
        node = self._parse_and()
        while self.cur.kind == "OP" and self.cur.value == "OR":
            self.pos += 1
            right = self._parse_and()
            node = TacsBinOp("OR", node, right)
        return node

    def _parse_and(self) -> TacsExpr:
        node = self._parse_not()
        while self.cur.kind == "OP" and self.cur.value == "AND":
            self.pos += 1
            right = self._parse_not()
            node = TacsBinOp("AND", node, right)
        return node

    def _parse_not(self) -> TacsExpr:
        if self.cur.kind == "OP" and self.cur.value == "NOT":
            self.pos += 1
            operand = self._parse_not()
            return TacsUnaryOp("NOT", operand)
        return self._parse_compare()

    def _parse_compare(self) -> TacsExpr:
        node = self._parse_addsub()
        if self.cur.kind == "OP" and self.cur.value in _COMPARISON_OPS:
            op = self.cur.value
            pos = self.cur.pos
            self.pos += 1
            right = self._parse_addsub()
            # rejeita encadeamento a < b < c
            if (
                self.cur.kind == "OP"
                and self.cur.value in _COMPARISON_OPS
            ):
                raise SyntaxError(
                    f"Comparação encadeada não permitida pos {pos}: "
                    "use parens + AND."
                )
            return TacsBinOp(op, node, right)
        return node

    def _parse_addsub(self) -> TacsExpr:
        node = self._parse_muldiv()
        while self.cur.kind == "OP" and self.cur.value in "+-":
            op = self.cur.value
            self.pos += 1
            right = self._parse_muldiv()
            node = TacsBinOp(op, node, right)
        return node

    def _parse_muldiv(self) -> TacsExpr:
        node = self._parse_power()
        while self.cur.kind == "OP" and self.cur.value in "*/":
            op = self.cur.value
            self.pos += 1
            right = self._parse_power()
            node = TacsBinOp(op, node, right)
        return node

    def _parse_power(self) -> TacsExpr:
        node = self._parse_unary()
        # right-associative
        if self.cur.kind == "OP" and self.cur.value == "^":
            self.pos += 1
            right = self._parse_power()
            return TacsBinOp("^", node, right)
        return node

    def _parse_unary(self) -> TacsExpr:
        if self.cur.kind == "OP" and self.cur.value in "+-":
            op = self.cur.value
            self.pos += 1
            operand = self._parse_unary()
            return TacsUnaryOp(op, operand)
        return self._parse_atom()

    def _parse_atom(self) -> TacsExpr:
        t = self.cur
        if t.kind == "NUM":
            self.pos += 1
            return TacsNumber(float(t.value))
        if t.kind == "IDENT":
            self.pos += 1
            if self.cur.kind == "LPAREN":
                self._eat("LPAREN")
                args: list = []
                if self.cur.kind != "RPAREN":
                    args.append(self.parse_expr())
                    while self.cur.kind == "COMMA":
                        self._eat("COMMA")
                        args.append(self.parse_expr())
                self._eat("RPAREN")
                return TacsFuncCall(t.value, tuple(args))
            return TacsVar(t.value)
        if t.kind == "LPAREN":
            self._eat("LPAREN")
            node = self.parse_expr()
            self._eat("RPAREN")
            return node
        raise SyntaxError(
            f"Token inesperado {t.kind}({t.value!r}) pos {t.pos}"
        )


def parse_tacs_expression(expr: str) -> TacsExpr:
    """
    Faz parse de uma expressão TACS para AST.

    Levanta ``SyntaxError`` em caso de expressão mal-formada
    (caractere ilegal, parênteses desbalanceados, tokens extras).
    """
    if not expr or not expr.strip():
        raise SyntaxError("Expressão TACS vazia")
    tokens = tokenize(expr)
    p = _Parser(tokens)
    ast = p.parse_expr()
    if p.cur.kind != "EOF":
        raise SyntaxError(
            f"Tokens extras após expressão: {p.cur.value!r} pos {p.cur.pos}"
        )
    return ast


# ---------------------------------------------------------------------------
# Análise do AST
# ---------------------------------------------------------------------------


def collect_variables(ast: TacsExpr) -> set[str]:
    """
    Retorna o conjunto de nomes de variáveis (não-funções,
    não-constantes ``pi``/``e``) referenciados em ``ast``.
    """
    result: set[str] = set()

    def visit(node) -> None:
        if isinstance(node, TacsNumber):
            return
        if isinstance(node, TacsVar):
            if node.name not in _TACS_CONSTANTS:
                result.add(node.name)
            return
        if isinstance(node, TacsBinOp):
            visit(node.left)
            visit(node.right)
            return
        if isinstance(node, TacsUnaryOp):
            visit(node.operand)
            return
        if isinstance(node, TacsFuncCall):
            for a in node.args:
                visit(a)
            return

    visit(ast)
    return result


def collect_functions(ast: TacsExpr) -> set[str]:
    """Retorna nomes de funções chamadas em ``ast``."""
    result: set[str] = set()

    def visit(node) -> None:
        if isinstance(node, (TacsNumber, TacsVar)):
            return
        if isinstance(node, TacsBinOp):
            visit(node.left)
            visit(node.right)
            return
        if isinstance(node, TacsUnaryOp):
            visit(node.operand)
            return
        if isinstance(node, TacsFuncCall):
            result.add(node.name)
            for a in node.args:
                visit(a)
            return

    visit(ast)
    return result


def validate_tacs_ast(
    ast: TacsExpr,
    declared_inputs: Optional[set[str]] = None,
) -> list[str]:
    """
    Valida o AST e retorna lista de erros (vazia ⇒ ok).

    Erros detectados
    ----------------
    * Função desconhecida (não em ``_TACS_FUNCTIONS``).
    * Aridade incorreta:

        * 1 arg exato: ``sin cos tan asin acos atan sinh cosh tanh
          exp log log10 sqrt abs step sign floor ceil``.
        * 2 args exatos: ``mod``.
        * 3 args exatos: ``if``.
        * ≥ 2 args: ``max min``.

    * Variável não declarada nos inputs (apenas se
      ``declared_inputs`` for fornecido).
    """
    errors: list[str] = []

    def visit(node) -> None:
        if isinstance(node, TacsNumber):
            return
        if isinstance(node, TacsVar):
            if node.name in _TACS_CONSTANTS:
                return
            if declared_inputs is not None and node.name not in declared_inputs:
                errors.append(
                    f"Variável não declarada: {node.name!r}"
                )
            return
        if isinstance(node, TacsBinOp):
            visit(node.left)
            visit(node.right)
            return
        if isinstance(node, TacsUnaryOp):
            visit(node.operand)
            return
        if isinstance(node, TacsFuncCall):
            if node.name not in _TACS_FUNCTIONS:
                errors.append(f"Função TACS desconhecida: {node.name!r}")
            else:
                n_args = len(node.args)
                if node.name in _TACS_FUNCTIONS_VARIADIC:
                    if n_args < 2:
                        errors.append(
                            f"{node.name}() exige >= 2 args (achado {n_args})"
                        )
                elif node.name in _TACS_FUNCTIONS_TERNARY:
                    if n_args != 3:
                        errors.append(
                            f"{node.name}() exige 3 args (achado {n_args})"
                        )
                elif node.name in _TACS_FUNCTIONS_BINARY:
                    if n_args != 2:
                        errors.append(
                            f"{node.name}() exige 2 args (achado {n_args})"
                        )
                else:
                    # unary (1 arg)
                    if n_args != 1:
                        errors.append(
                            f"{node.name}() exige 1 arg (achado {n_args})"
                        )
            for a in node.args:
                visit(a)
            return

    visit(ast)
    return errors


# ---------------------------------------------------------------------------
# Pretty-printer (canonical TACS expression)
# ---------------------------------------------------------------------------


_PRECEDENCE = {
    "OR": 1,
    "AND": 2,
    "==": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3,
    "+": 4, "-": 4,
    "*": 5, "/": 5,
    "^": 6,
}


def render_tacs_expression(ast: TacsExpr, atp_style: bool = False) -> str:
    """
    Re-renderiza o AST como string canônica, com parênteses
    aplicados onde forem necessários para preservar precedência.

    Parameters
    ----------
    atp_style:
        Se True, usa FORTRAN-77 dotted operators (``.EQ.``, ``.AND.``,
        etc.) — formato esperado pelo device-88 do ATP. Se False
        (default), usa forma canônica curta (``==``, ``AND``, etc.)
        — útil para debug e display.
    """

    def fmt_number(v: float) -> str:
        if v == int(v) and abs(v) < 1e16:
            return str(int(v))
        return repr(v)

    def fmt_op(op: str) -> str:
        if atp_style and op in _OP_TO_ATP_STYLE:
            return _OP_TO_ATP_STYLE[op]
        return op

    def render(node, parent_prec: int = 0, is_right: bool = False) -> str:
        if isinstance(node, TacsNumber):
            return fmt_number(node.value)
        if isinstance(node, TacsVar):
            return node.name
        if isinstance(node, TacsBinOp):
            prec = _PRECEDENCE[node.op]
            # right-side de operadores não-comutativos exige
            # precedência estritamente maior; ^ é right-assoc
            right_prec = prec if node.op == "^" else prec + 1
            left = render(node.left, prec)
            right = render(node.right, right_prec, is_right=True)
            s = f"{left} {fmt_op(node.op)} {right}"
            need_parens = prec < parent_prec or (
                prec == parent_prec and is_right and node.op in ("-", "/")
            )
            if need_parens:
                return f"({s})"
            return s
        if isinstance(node, TacsUnaryOp):
            if node.op == "NOT":
                # NOT é palavra-chave: usa espaço para legibilidade
                inner = render(node.operand, _PRECEDENCE["NOT"]
                               if "NOT" in _PRECEDENCE else 100)
                return f"{fmt_op('NOT')} {inner}"
            return f"{node.op}{render(node.operand, 100)}"
        if isinstance(node, TacsFuncCall):
            args = ", ".join(render(a) for a in node.args)
            return f"{node.name}({args})"
        raise TypeError(f"Tipo de AST inesperado: {type(node)!r}")

    return render(ast)


# ---------------------------------------------------------------------------
# TacsBlock — pacote de dados para emissão
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TacsBlock:
    """
    Bloco TACS — uma expressão algébrica que produz um sinal.

    Attributes
    ----------
    name:
        Identificador interno do bloco (até 6 chars, convenção ATP).
    expression:
        Expressão TACS como string. Será re-validada na emissão.
    output:
        Nome do sinal de saída (até 6 chars).
    inputs:
        Nomes de sinais externos referenciados pela expressão.
    initial_value:
        Valor inicial do output em t = 0.
    """

    name: str
    expression: str
    output: str
    inputs: tuple = ()
    initial_value: float = 0.0


def validate_tacs_block(block: TacsBlock) -> list[str]:
    """
    Valida um ``TacsBlock`` (parse + AST + sanidade do header).

    Retorna lista de erros (vazia ⇒ ok).
    """
    errors: list[str] = []
    if not block.name:
        errors.append("name vazio")
    if not block.output:
        errors.append("output vazio")
    if len(block.output) > 6:
        errors.append(
            f"output {block.output!r} > 6 chars (limite ATP)"
        )
    if len(block.name) > 6:
        errors.append(
            f"name {block.name!r} > 6 chars (limite ATP)"
        )
    try:
        ast = parse_tacs_expression(block.expression)
    except SyntaxError as exc:
        errors.append(f"Erro de sintaxe: {exc}")
        return errors

    declared = set(block.inputs)
    errors.extend(validate_tacs_ast(ast, declared_inputs=declared))
    return errors


# ---------------------------------------------------------------------------
# Emissão /TACS HYBRID
# ---------------------------------------------------------------------------


def _emit_block_lines(blk: "TacsBlock") -> list[str]:
    """
    Renderiza um único ``TacsBlock`` como linhas (sem ``\\n``).
    Levanta ``ValueError`` se o bloco for inválido.
    """
    errs = validate_tacs_block(blk)
    if errs:
        raise ValueError(
            f"TacsBlock {blk.name!r} inválido: " + "; ".join(errs)
        )
    ast = parse_tacs_expression(blk.expression)
    canonical = render_tacs_expression(ast)
    atp_form = render_tacs_expression(ast, atp_style=True)

    inputs_str = ",".join(blk.inputs) if blk.inputs else "(none)"
    out: list[str] = []
    out.append(
        f"C  TACS block: {blk.name}  output={blk.output}  "
        f"inputs={inputs_str}"
    )
    out.append(f"C  expression: {canonical}")
    if blk.initial_value != 0.0:
        out.append(f"C  initial_value: {blk.initial_value:.6e}")

    # Card device-88 (FORTRAN expression).
    # Emite na forma ATP-style (.EQ./.AND./etc.) para
    # compatibilidade com o parser de device-88.
    # Layout legível: "88" + nome (6) + 4 espaços + expressão.
    out_padded = blk.output.ljust(6)[:6]
    out.append(f"88{out_padded}    {atp_form}")
    return out


def emit_tacs_section(items: list) -> str:
    """
    Gera o texto da seção ``/TACS HYBRID`` para uma lista de itens
    TACS — pode misturar ``TacsBlock`` (device-88, expressões) e
    ``TacsTransferFunction`` (device-1, transfer functions s-domain,
    v0.26.2+).

    Formato (draft v0.26.x):

    ::

        /TACS HYBRID
        C  TACS block: <name>  output=<output>  inputs=<csv>
        C  expression: <canonical>
        88<output>      <expression>
        ...
        C  TACS TF: <output> = K·N(s)/D(s)·<input>
         1<output>    <input>        gain = <K>
        C   numerator   = (n0, n1, ...)
        C   denominator = (d0, d1, ...)
        ...
        BLANK CARD ENDING TACS

    Item com configuração inválida levanta ``ValueError`` com a
    lista de erros encontrados.

    Returns
    -------
    str
        Texto pronto para concatenar nas ``raw_lines`` do
        ``AtpProject``. Vazio se ``items`` for vazia.
    """
    if not items:
        return ""

    # Imports locais para evitar dep circular eventual.
    from .tacs_tf import (
        TacsTransferFunction, emit_tf_lines, validate_tf,
    )
    from .tacs_blocks import (
        TacsDeadBand, TacsLimiter, TacsSum, TacsZOH,
        emit_dead_band_lines, emit_limiter_lines,
        emit_sum_lines, emit_zoh_lines,
        validate_dead_band, validate_limiter,
        validate_sum, validate_zoh,
    )
    from .tacs_interface import (
        TacsControlledSource, TacsControlledSwitch, TacsMeasuring,
        emit_controlled_source_lines, emit_controlled_switch_lines,
        emit_measuring_lines,
        validate_controlled_source, validate_controlled_switch,
        validate_measuring,
    )

    # Tabela de despacho: (tipo, validador, emissor, label).
    DISPATCH = (
        (TacsBlock,              None,                          None,                              "TacsBlock"),
        (TacsTransferFunction,   validate_tf,                   emit_tf_lines,                     "TacsTransferFunction"),
        (TacsLimiter,            validate_limiter,              emit_limiter_lines,                "TacsLimiter"),
        (TacsDeadBand,           validate_dead_band,            emit_dead_band_lines,              "TacsDeadBand"),
        (TacsZOH,                validate_zoh,                  emit_zoh_lines,                    "TacsZOH"),
        (TacsSum,                validate_sum,                  emit_sum_lines,                    "TacsSum"),
        (TacsMeasuring,          validate_measuring,            emit_measuring_lines,              "TacsMeasuring"),
        (TacsControlledSource,   validate_controlled_source,    emit_controlled_source_lines,      "TacsControlledSource"),
        (TacsControlledSwitch,   validate_controlled_switch,    emit_controlled_switch_lines,      "TacsControlledSwitch"),
    )

    lines: list[str] = []
    lines.append("/TACS HYBRID")

    for item in items:
        # TacsBlock tem caminho especial (parsing + render canônico).
        if isinstance(item, TacsBlock):
            lines.extend(_emit_block_lines(item))
            continue
        # Demais tipos: lookup na tabela.
        matched = False
        for cls, validator, emitter, label in DISPATCH[1:]:
            if isinstance(item, cls):
                errs = validator(item)
                if errs:
                    raise ValueError(
                        f"{label} {item.name!r} inválido: "
                        + "; ".join(errs)
                    )
                lines.extend(emitter(item))
                matched = True
                break
        if not matched:
            raise TypeError(
                f"Item TACS desconhecido: {type(item).__name__}. "
                "Esperado TacsBlock, TacsTransferFunction, TacsLimiter, "
                "TacsDeadBand, TacsZOH, TacsSum, TacsMeasuring, "
                "TacsControlledSource ou TacsControlledSwitch."
            )

    lines.append("BLANK CARD ENDING TACS")
    return "\n".join(lines) + "\n"
