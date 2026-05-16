"""
tests/test_pp_tacs_logic.py — v0.26.1: comparações + lógica
boolean + funcs adicionais.

Cobre:

* Tokenizer: ``== != < > <= >=``, ``AND OR NOT`` (uppercase),
  dotted FORTRAN-77 (``.EQ. .NE. .LT. .GT. .LE. .GE. .AND.
  .OR. .NOT.``).
* Parser: precedência (OR < AND < NOT < compare < addsub),
  comparação **não-associativa** (``a < b < c`` falha).
* AST: comparações como ``TacsBinOp``, ``NOT`` como ``TacsUnaryOp``.
* Validador: novas funções (``step``, ``sign``, ``floor``,
  ``ceil``, ``mod``, ``if``) com aridades corretas.
* Renderer: forma canônica (``==``, ``AND``) vs ATP-style
  (``.EQ.``, ``.AND.``); idempotência preservada.
* Emissão: cartão device-88 emitido em forma ATP-style;
  comentário em forma canônica.
"""

from __future__ import annotations

import pytest

from app.preprocessor.tacs import (
    TacsBinOp, TacsBlock, TacsFuncCall, TacsNumber,
    TacsUnaryOp, TacsVar,
    emit_tacs_section,
    parse_tacs_expression,
    render_tacs_expression,
    tokenize,
    validate_tacs_ast,
)


# ---------------------------------------------------------------------------
# Tokenizer (v0.26.1)
# ---------------------------------------------------------------------------


class TestTokenizerOps:
    def test_eq_and_neq(self):
        toks = [t for t in tokenize("a == b != c") if t.kind != "EOF"]
        assert toks[1].value == "=="
        assert toks[3].value == "!="

    def test_lt_gt_le_ge(self):
        toks = [t for t in tokenize("a < b > c <= d >= e") if t.kind != "EOF"]
        assert toks[1].value == "<"
        assert toks[3].value == ">"
        assert toks[5].value == "<="
        assert toks[7].value == ">="

    def test_keyword_ops_uppercase(self):
        toks = [t for t in tokenize("a AND b OR NOT c") if t.kind != "EOF"]
        op_values = [t.value for t in toks if t.kind == "OP"]
        assert "AND" in op_values
        assert "OR" in op_values
        assert "NOT" in op_values

    def test_lowercase_and_is_ident(self):
        """``and`` (lowercase) não é keyword — vira identificador."""
        toks = [t for t in tokenize("and_signal") if t.kind != "EOF"]
        assert toks[0].kind == "IDENT"
        assert toks[0].value == "and_signal"

    def test_dotted_ops_normalized(self):
        toks = [t for t in tokenize(".EQ. .AND. .NOT.") if t.kind != "EOF"]
        assert toks[0].value == "=="
        assert toks[1].value == "AND"
        assert toks[2].value == "NOT"

    def test_dotted_ops_case_insensitive(self):
        toks = [t for t in tokenize(".eq. .And. .not.") if t.kind != "EOF"]
        assert toks[0].value == "=="
        assert toks[1].value == "AND"
        assert toks[2].value == "NOT"

    def test_unknown_dotted_op_error(self):
        with pytest.raises(SyntaxError, match="dot desconhecido"):
            tokenize("a .XOR. b")

    def test_dot_followed_by_number_still_works(self):
        """``.5`` continua sendo número, não operador dot."""
        toks = [t for t in tokenize(".5") if t.kind != "EOF"]
        assert toks[0].kind == "NUM"
        assert toks[0].value == ".5"

    def test_lt_gt_alone_with_operands(self):
        """``<`` e ``>`` sem ``=`` são tokens separados."""
        toks = [t for t in tokenize("a < b") if t.kind != "EOF"]
        assert toks[1].kind == "OP" and toks[1].value == "<"


# ---------------------------------------------------------------------------
# Parser (v0.26.1)
# ---------------------------------------------------------------------------


class TestParserCompare:
    def test_simple_comparison(self):
        ast = parse_tacs_expression("a == b")
        assert isinstance(ast, TacsBinOp)
        assert ast.op == "=="

    def test_all_comparison_ops(self):
        for op in ("==", "!=", "<", ">", "<=", ">="):
            ast = parse_tacs_expression(f"a {op} b")
            assert isinstance(ast, TacsBinOp)
            assert ast.op == op

    def test_compare_arithmetic_precedence(self):
        """``a + b == c * d`` → (a+b) == (c*d)."""
        ast = parse_tacs_expression("a + b == c * d")
        assert ast.op == "=="
        assert isinstance(ast.left, TacsBinOp) and ast.left.op == "+"
        assert isinstance(ast.right, TacsBinOp) and ast.right.op == "*"

    def test_chained_comparison_rejected(self):
        with pytest.raises(SyntaxError, match="encadeada"):
            parse_tacs_expression("a < b < c")
        with pytest.raises(SyntaxError, match="encadeada"):
            parse_tacs_expression("a == b == c")


class TestParserBoolean:
    def test_simple_and(self):
        ast = parse_tacs_expression("a AND b")
        assert isinstance(ast, TacsBinOp)
        assert ast.op == "AND"

    def test_simple_or(self):
        ast = parse_tacs_expression("a OR b")
        assert ast.op == "OR"

    def test_simple_not(self):
        ast = parse_tacs_expression("NOT a")
        assert isinstance(ast, TacsUnaryOp)
        assert ast.op == "NOT"

    def test_not_higher_than_and(self):
        """``NOT a AND b`` → (NOT a) AND b."""
        ast = parse_tacs_expression("NOT a AND b")
        assert ast.op == "AND"
        assert isinstance(ast.left, TacsUnaryOp)
        assert ast.left.op == "NOT"

    def test_and_higher_than_or(self):
        """``a OR b AND c`` → a OR (b AND c)."""
        ast = parse_tacs_expression("a OR b AND c")
        assert ast.op == "OR"
        assert isinstance(ast.right, TacsBinOp) and ast.right.op == "AND"

    def test_compare_higher_than_and(self):
        """``a < b AND c > d`` → (a<b) AND (c>d)."""
        ast = parse_tacs_expression("a < b AND c > d")
        assert ast.op == "AND"
        assert isinstance(ast.left, TacsBinOp) and ast.left.op == "<"
        assert isinstance(ast.right, TacsBinOp) and ast.right.op == ">"

    def test_double_not(self):
        """NOT NOT x — NOT é right-associative."""
        ast = parse_tacs_expression("NOT NOT x")
        assert isinstance(ast, TacsUnaryOp)
        assert ast.op == "NOT"
        assert isinstance(ast.operand, TacsUnaryOp)

    def test_and_left_associative(self):
        """a AND b AND c → (a AND b) AND c."""
        ast = parse_tacs_expression("a AND b AND c")
        assert ast.op == "AND"
        assert isinstance(ast.left, TacsBinOp) and ast.left.op == "AND"

    def test_dotted_ops_parse(self):
        """.EQ./.AND. parseiam idênticos a ==/AND."""
        ast1 = parse_tacs_expression("a .EQ. b .AND. c .NE. 0")
        ast2 = parse_tacs_expression("a == b AND c != 0")
        assert ast1 == ast2


# ---------------------------------------------------------------------------
# Funções v0.26.1
# ---------------------------------------------------------------------------


class TestNewFunctions:
    def test_step(self):
        ast = parse_tacs_expression("step(t - 0.1)")
        errs = validate_tacs_ast(ast)
        assert errs == []

    def test_sign(self):
        ast = parse_tacs_expression("sign(x)")
        assert validate_tacs_ast(ast) == []

    def test_floor_ceil(self):
        for fn in ("floor", "ceil"):
            ast = parse_tacs_expression(f"{fn}(t * 1000)")
            assert validate_tacs_ast(ast) == []

    def test_mod_two_args(self):
        ast = parse_tacs_expression("mod(t, 0.01)")
        assert validate_tacs_ast(ast) == []

    def test_mod_wrong_arity(self):
        ast = parse_tacs_expression("mod(t)")
        errs = validate_tacs_ast(ast)
        assert any("mod" in e and "2 args" in e for e in errs)

        ast2 = parse_tacs_expression("mod(t, 1, 2)")
        errs2 = validate_tacs_ast(ast2)
        assert any("mod" in e and "2 args" in e for e in errs2)

    def test_if_three_args(self):
        ast = parse_tacs_expression("if(err > 0, err, 0)")
        assert validate_tacs_ast(ast) == []

    def test_if_wrong_arity(self):
        ast = parse_tacs_expression("if(err > 0, err)")
        errs = validate_tacs_ast(ast)
        assert any("if" in e and "3 args" in e for e in errs)

    def test_step_wrong_arity(self):
        ast = parse_tacs_expression("step(t, 1)")
        errs = validate_tacs_ast(ast)
        assert any("step" in e and "1 arg" in e for e in errs)


# ---------------------------------------------------------------------------
# Renderer (v0.26.1)
# ---------------------------------------------------------------------------


class TestRendererCanonical:
    def test_simple_compare(self):
        ast = parse_tacs_expression("a == b")
        assert render_tacs_expression(ast) == "a == b"

    def test_simple_and(self):
        ast = parse_tacs_expression("a AND b")
        assert render_tacs_expression(ast) == "a AND b"

    def test_not_expression(self):
        ast = parse_tacs_expression("NOT (a > 0)")
        s = render_tacs_expression(ast)
        assert s.startswith("NOT")
        # reparse equivalent
        assert parse_tacs_expression(s) == ast

    def test_complex_expression_idempotent(self):
        cases = [
            "a == b",
            "x < y AND y < z",
            "a == 0 OR b != 0",
            "NOT (a > 0)",
            "step(t - 0.1)",
            "if(err > 0, err, 0)",
            "mod(t, 0.01)",
        ]
        for expr in cases:
            ast = parse_tacs_expression(expr)
            rendered = render_tacs_expression(ast)
            ast2 = parse_tacs_expression(rendered)
            assert ast == ast2, f"Não-idempotente: {expr!r} → {rendered!r}"

    def test_precedence_and_in_or(self):
        """a OR b AND c emitido com AND aninhado naturalmente."""
        ast = parse_tacs_expression("a OR b AND c")
        s = render_tacs_expression(ast)
        # reparse → mesmo AST
        assert parse_tacs_expression(s) == ast

    def test_or_in_and_needs_parens(self):
        """(a OR b) AND c precisa de parens."""
        ast = parse_tacs_expression("(a OR b) AND c")
        s = render_tacs_expression(ast)
        assert "(" in s
        assert parse_tacs_expression(s) == ast


class TestRendererAtpStyle:
    def test_eq_to_atp(self):
        ast = parse_tacs_expression("a == b")
        assert render_tacs_expression(ast, atp_style=True) == "a .EQ. b"

    def test_all_compare_ops_to_atp(self):
        mapping = {
            "==": ".EQ.", "!=": ".NE.",
            "<": ".LT.", ">": ".GT.",
            "<=": ".LE.", ">=": ".GE.",
        }
        for op, atp_op in mapping.items():
            ast = parse_tacs_expression(f"a {op} b")
            s = render_tacs_expression(ast, atp_style=True)
            assert atp_op in s, f"{op} → {atp_op} esperado em {s!r}"

    def test_logical_ops_to_atp(self):
        ast = parse_tacs_expression("a AND b OR NOT c")
        s = render_tacs_expression(ast, atp_style=True)
        assert ".AND." in s
        assert ".OR." in s
        assert ".NOT." in s

    def test_arithmetic_unchanged_in_atp(self):
        """+ - * / ^ não têm forma dotted — render identical."""
        ast = parse_tacs_expression("a + b * c")
        c1 = render_tacs_expression(ast, atp_style=False)
        c2 = render_tacs_expression(ast, atp_style=True)
        assert c1 == c2 == "a + b * c"

    def test_atp_style_reparseable(self):
        """ATP-style também faz round-trip via parser."""
        cases = ["a == b AND c < d", "NOT (x .LT. 0)", "a OR b"]
        for expr in cases:
            ast = parse_tacs_expression(expr)
            atp = render_tacs_expression(ast, atp_style=True)
            ast2 = parse_tacs_expression(atp)
            assert ast == ast2, f"ATP roundtrip falhou: {expr}"


# ---------------------------------------------------------------------------
# Emissão (v0.26.1)
# ---------------------------------------------------------------------------


class TestEmitWithLogic:
    def test_card_88_uses_atp_style(self):
        """Cartão 88 deve usar .EQ./.AND./etc."""
        blk = TacsBlock(
            name="b1", expression="err > 0 AND ena == 1",
            output="trig", inputs=("err", "ena"),
        )
        text = emit_tacs_section([blk])
        card_lines = [l for l in text.splitlines() if l.startswith("88")]
        assert len(card_lines) == 1
        card = card_lines[0]
        assert ".GT." in card
        assert ".AND." in card
        assert ".EQ." in card

    def test_comment_uses_canonical(self):
        """Comentário ``C  expression: ...`` usa forma curta canônica."""
        blk = TacsBlock(
            name="b1", expression="a > 0 AND b == 1",
            output="o", inputs=("a", "b"),
        )
        text = emit_tacs_section([blk])
        comment_lines = [
            l for l in text.splitlines() if l.startswith("C  expression")
        ]
        assert len(comment_lines) == 1
        comment = comment_lines[0]
        assert ">" in comment
        assert "AND" in comment
        assert "==" in comment
        # NÃO deve ter dotted no comentário
        assert ".AND." not in comment

    def test_step_function_in_card(self):
        blk = TacsBlock(
            name="trig", expression="step(t - 0.05)",
            output="trig", inputs=("t",),
        )
        text = emit_tacs_section([blk])
        assert "step(" in text

    def test_if_function_in_card(self):
        blk = TacsBlock(
            name="sat", expression="if(x > 1, 1, x)",
            output="y", inputs=("x",),
        )
        text = emit_tacs_section([blk])
        # corpo do if usa ATP-style para a condição
        assert ".GT." in text

    def test_invalid_function_rejected_in_emit(self):
        blk = TacsBlock(
            name="b", expression="bogus_func(x)",
            output="y", inputs=("x",),
        )
        with pytest.raises(ValueError, match="inválido"):
            emit_tacs_section([blk])
