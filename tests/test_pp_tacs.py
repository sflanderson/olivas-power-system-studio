"""
tests/test_pp_tacs.py — v0.26.0: parser e emissor de blocos TACS.

Cobre:

* Tokenizer: números, identifiers, operadores, parens, vírgulas,
  caracteres ilegais.
* Parser: precedência (^, * /, + -), associatividade, parênteses,
  funções com 1 e múltiplos args, unary +/-, expressões inválidas.
* AST: ``collect_variables`` ignora ``pi``/``e``, ``collect_functions``
  pega chamadas aninhadas.
* Validador: função desconhecida, aridade incorreta, variável
  não-declarada (quando ``declared_inputs`` fornecido).
* Pretty-printer: idempotente para expressões canônicas.
* TacsBlock: campos defaults, validação completa.
* Emissão ``/TACS HYBRID``: header + comentários + cartão type-88
  + BLANK CARD ENDING.
"""

from __future__ import annotations

import pytest

from app.preprocessor.tacs import (
    TacsBinOp, TacsBlock, TacsFuncCall, TacsNumber,
    TacsUnaryOp, TacsVar,
    Token,
    collect_functions, collect_variables,
    emit_tacs_section,
    parse_tacs_expression,
    render_tacs_expression,
    tokenize,
    validate_tacs_ast, validate_tacs_block,
)


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


class TestTokenizer:
    def test_numbers(self):
        toks = tokenize("3 3.14 1e5 2.5e-3 .5")
        kinds = [t.kind for t in toks if t.kind != "EOF"]
        values = [t.value for t in toks if t.kind != "EOF"]
        assert kinds == ["NUM"] * 5
        assert values == ["3", "3.14", "1e5", "2.5e-3", ".5"]

    def test_identifiers(self):
        toks = tokenize("x y_1 _t omega")
        idents = [t.value for t in toks if t.kind == "IDENT"]
        assert idents == ["x", "y_1", "_t", "omega"]

    def test_operators(self):
        toks = tokenize("+ - * / ^")
        ops = [t.value for t in toks if t.kind == "OP"]
        assert ops == ["+", "-", "*", "/", "^"]

    def test_parens_and_comma(self):
        toks = tokenize("(a, b)")
        kinds = [t.kind for t in toks if t.kind != "EOF"]
        assert kinds == ["LPAREN", "IDENT", "COMMA", "IDENT", "RPAREN"]

    def test_whitespace_skipped(self):
        toks = tokenize("  a   +   b  ")
        kinds = [t.kind for t in toks if t.kind != "EOF"]
        assert kinds == ["IDENT", "OP", "IDENT"]

    def test_illegal_char(self):
        with pytest.raises(SyntaxError, match="inválido"):
            tokenize("a # b")

    def test_eof_appended(self):
        toks = tokenize("x")
        assert toks[-1].kind == "EOF"

    def test_empty_string(self):
        toks = tokenize("")
        assert len(toks) == 1 and toks[0].kind == "EOF"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class TestParser:
    def test_simple_number(self):
        ast = parse_tacs_expression("42")
        assert isinstance(ast, TacsNumber)
        assert ast.value == 42.0

    def test_simple_var(self):
        ast = parse_tacs_expression("x")
        assert isinstance(ast, TacsVar)
        assert ast.name == "x"

    def test_addition(self):
        ast = parse_tacs_expression("a + b")
        assert isinstance(ast, TacsBinOp)
        assert ast.op == "+"
        assert ast.left.name == "a"
        assert ast.right.name == "b"

    def test_precedence_mul_over_add(self):
        """a + b * c → a + (b*c)."""
        ast = parse_tacs_expression("a + b * c")
        assert ast.op == "+"
        assert isinstance(ast.right, TacsBinOp) and ast.right.op == "*"

    def test_precedence_pow_over_mul(self):
        """a * b ^ c → a * (b^c)."""
        ast = parse_tacs_expression("a * b ^ c")
        assert ast.op == "*"
        assert isinstance(ast.right, TacsBinOp) and ast.right.op == "^"

    def test_pow_right_associative(self):
        """2 ^ 3 ^ 2 = 2 ^ (3^2) = 512, não (2^3)^2 = 64."""
        ast = parse_tacs_expression("2 ^ 3 ^ 2")
        # exterior: 2 ^ (3^2)
        assert ast.op == "^"
        assert isinstance(ast.left, TacsNumber) and ast.left.value == 2
        assert isinstance(ast.right, TacsBinOp) and ast.right.op == "^"

    def test_left_assoc_minus(self):
        """a - b - c = (a-b) - c."""
        ast = parse_tacs_expression("a - b - c")
        assert ast.op == "-"
        assert isinstance(ast.left, TacsBinOp) and ast.left.op == "-"

    def test_parentheses(self):
        ast = parse_tacs_expression("(a + b) * c")
        assert ast.op == "*"
        assert isinstance(ast.left, TacsBinOp) and ast.left.op == "+"

    def test_unary_minus(self):
        ast = parse_tacs_expression("-x")
        assert isinstance(ast, TacsUnaryOp)
        assert ast.op == "-"
        assert isinstance(ast.operand, TacsVar)

    def test_unary_plus(self):
        ast = parse_tacs_expression("+x")
        assert isinstance(ast, TacsUnaryOp)
        assert ast.op == "+"

    def test_unary_in_expression(self):
        ast = parse_tacs_expression("a + -b")
        assert ast.op == "+"
        assert isinstance(ast.right, TacsUnaryOp)

    def test_func_call_one_arg(self):
        ast = parse_tacs_expression("sin(x)")
        assert isinstance(ast, TacsFuncCall)
        assert ast.name == "sin"
        assert len(ast.args) == 1
        assert isinstance(ast.args[0], TacsVar)

    def test_func_call_multi_arg(self):
        ast = parse_tacs_expression("max(a, b, c)")
        assert isinstance(ast, TacsFuncCall)
        assert ast.name == "max"
        assert len(ast.args) == 3

    def test_nested_func_calls(self):
        ast = parse_tacs_expression("sin(cos(x))")
        assert ast.name == "sin"
        assert isinstance(ast.args[0], TacsFuncCall)
        assert ast.args[0].name == "cos"

    def test_complex_expression(self):
        """PID típico: Kp*err + Ki*int_err + Kd*deriv_err."""
        ast = parse_tacs_expression(
            "Kp * err + Ki * int_err + Kd * deriv_err"
        )
        # exterior: ((Kp*err + Ki*int_err) + Kd*deriv_err) — left-assoc
        assert ast.op == "+"
        assert isinstance(ast.left, TacsBinOp) and ast.left.op == "+"

    def test_empty_expression_error(self):
        with pytest.raises(SyntaxError, match="vazia"):
            parse_tacs_expression("")
        with pytest.raises(SyntaxError, match="vazia"):
            parse_tacs_expression("   ")

    def test_unbalanced_parens(self):
        with pytest.raises(SyntaxError):
            parse_tacs_expression("(a + b")

    def test_extra_tokens(self):
        with pytest.raises(SyntaxError, match="extras"):
            parse_tacs_expression("a + b c")

    def test_dangling_operator(self):
        with pytest.raises(SyntaxError):
            parse_tacs_expression("a + ")


# ---------------------------------------------------------------------------
# AST analysis
# ---------------------------------------------------------------------------


class TestCollectVariables:
    def test_simple(self):
        ast = parse_tacs_expression("a + b * c")
        assert collect_variables(ast) == {"a", "b", "c"}

    def test_constants_excluded(self):
        ast = parse_tacs_expression("pi * r ^ 2 + e")
        assert collect_variables(ast) == {"r"}

    def test_function_args(self):
        ast = parse_tacs_expression("sin(omega * t) + cos(phi)")
        assert collect_variables(ast) == {"omega", "t", "phi"}

    def test_no_vars(self):
        ast = parse_tacs_expression("3.14 + 2.71")
        assert collect_variables(ast) == set()


class TestCollectFunctions:
    def test_simple(self):
        ast = parse_tacs_expression("sin(x) + cos(y)")
        assert collect_functions(ast) == {"sin", "cos"}

    def test_nested(self):
        ast = parse_tacs_expression("exp(sin(sqrt(x)))")
        assert collect_functions(ast) == {"exp", "sin", "sqrt"}

    def test_no_functions(self):
        ast = parse_tacs_expression("a + b * c")
        assert collect_functions(ast) == set()


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class TestValidateAst:
    def test_valid_expression(self):
        ast = parse_tacs_expression("sin(omega * t)")
        errors = validate_tacs_ast(ast)
        assert errors == []

    def test_unknown_function(self):
        ast = parse_tacs_expression("foo(x)")
        errors = validate_tacs_ast(ast)
        assert len(errors) == 1
        assert "foo" in errors[0]

    def test_wrong_arity_unary(self):
        ast = parse_tacs_expression("sin(a, b)")
        errors = validate_tacs_ast(ast)
        assert any("sin" in e and "1 arg" in e for e in errors)

    def test_max_min_need_two(self):
        ast = parse_tacs_expression("max(a)")
        errors = validate_tacs_ast(ast)
        assert any("max" in e and ">= 2" in e for e in errors)

    def test_max_min_two_ok(self):
        ast = parse_tacs_expression("max(a, b)")
        errors = validate_tacs_ast(ast)
        assert errors == []

    def test_undeclared_variable(self):
        ast = parse_tacs_expression("a + foo_bar")
        errors = validate_tacs_ast(ast, declared_inputs={"a"})
        assert any("foo_bar" in e for e in errors)

    def test_declared_variable_ok(self):
        ast = parse_tacs_expression("a + b")
        errors = validate_tacs_ast(ast, declared_inputs={"a", "b"})
        assert errors == []

    def test_pi_e_always_ok(self):
        ast = parse_tacs_expression("pi * e")
        errors = validate_tacs_ast(ast, declared_inputs=set())
        assert errors == []


# ---------------------------------------------------------------------------
# Pretty-printer
# ---------------------------------------------------------------------------


class TestRender:
    def test_simple_var(self):
        ast = parse_tacs_expression("x")
        assert render_tacs_expression(ast) == "x"

    def test_simple_number(self):
        ast = parse_tacs_expression("42")
        assert render_tacs_expression(ast) == "42"

    def test_float_number(self):
        ast = parse_tacs_expression("3.14")
        assert "3.14" in render_tacs_expression(ast)

    def test_addition(self):
        ast = parse_tacs_expression("a + b")
        assert render_tacs_expression(ast) == "a + b"

    def test_function(self):
        ast = parse_tacs_expression("sin(x)")
        assert render_tacs_expression(ast) == "sin(x)"

    def test_max_multi_args(self):
        ast = parse_tacs_expression("max(a, b, c)")
        assert render_tacs_expression(ast) == "max(a, b, c)"

    def test_precedence_preserved(self):
        """(a+b)*c precisa de parens; a*b+c não."""
        ast1 = parse_tacs_expression("(a + b) * c")
        s1 = render_tacs_expression(ast1)
        assert "(" in s1
        # rerender + reparse → mesmo AST
        ast2 = parse_tacs_expression(s1)
        assert ast2 == ast1

    def test_idempotent_simple(self):
        for expr in ["a + b", "a * b + c", "sin(x)", "exp(-t)"]:
            ast = parse_tacs_expression(expr)
            rendered = render_tacs_expression(ast)
            ast2 = parse_tacs_expression(rendered)
            assert ast == ast2, f"Não-idempotente para {expr!r}"

    def test_unary_minus_renders(self):
        ast = parse_tacs_expression("-x")
        s = render_tacs_expression(ast)
        assert s.startswith("-")
        # reparse retorna AST equivalente
        assert parse_tacs_expression(s) == ast

    def test_subtraction_right_side_parens(self):
        """a - (b - c) deve emitir parens; a - b - c não."""
        ast = parse_tacs_expression("a - (b - c)")
        s = render_tacs_expression(ast)
        # reparse preserva semântica
        assert parse_tacs_expression(s) == ast


# ---------------------------------------------------------------------------
# TacsBlock + validate_tacs_block
# ---------------------------------------------------------------------------


class TestTacsBlock:
    def test_defaults(self):
        blk = TacsBlock(
            name="ctrl1", expression="a + b", output="y",
            inputs=("a", "b"),
        )
        assert blk.initial_value == 0.0
        assert blk.inputs == ("a", "b")

    def test_validate_ok(self):
        blk = TacsBlock(
            name="ctrl1", expression="sin(omega * t)",
            output="y", inputs=("omega", "t"),
        )
        assert validate_tacs_block(blk) == []

    def test_validate_empty_name(self):
        blk = TacsBlock(name="", expression="x", output="y", inputs=("x",))
        errs = validate_tacs_block(blk)
        assert any("name" in e for e in errs)

    def test_validate_long_name(self):
        blk = TacsBlock(
            name="abcdefgh", expression="x", output="y", inputs=("x",),
        )
        errs = validate_tacs_block(blk)
        assert any("> 6 chars" in e for e in errs)

    def test_validate_long_output(self):
        blk = TacsBlock(
            name="ok", expression="x", output="abcdefgh", inputs=("x",),
        )
        errs = validate_tacs_block(blk)
        assert any("output" in e and "> 6 chars" in e for e in errs)

    def test_validate_undeclared_var(self):
        blk = TacsBlock(
            name="bad", expression="a + missing",
            output="y", inputs=("a",),
        )
        errs = validate_tacs_block(blk)
        assert any("missing" in e for e in errs)

    def test_validate_syntax_error(self):
        blk = TacsBlock(
            name="bad", expression="a + + ",
            output="y", inputs=("a",),
        )
        errs = validate_tacs_block(blk)
        assert any("sintaxe" in e.lower() for e in errs)


# ---------------------------------------------------------------------------
# Emissão /TACS HYBRID
# ---------------------------------------------------------------------------


class TestEmitTacsSection:
    def test_empty_blocks_returns_empty(self):
        assert emit_tacs_section([]) == ""

    def test_header_present(self):
        blk = TacsBlock(
            name="b1", expression="a + b", output="y", inputs=("a", "b"),
        )
        text = emit_tacs_section([blk])
        assert "/TACS HYBRID" in text
        assert "BLANK CARD ENDING TACS" in text

    def test_comment_metadata(self):
        blk = TacsBlock(
            name="ctrl", expression="a + b", output="y", inputs=("a", "b"),
        )
        text = emit_tacs_section([blk])
        assert "C  TACS block: ctrl" in text
        assert "output=y" in text
        assert "a,b" in text

    def test_expression_canonical(self):
        blk = TacsBlock(
            name="b", expression="  a   +    b ",   # whitespace excessivo
            output="y", inputs=("a", "b"),
        )
        text = emit_tacs_section([blk])
        # canonical: "a + b" (sem whitespace excessivo)
        assert "a + b" in text

    def test_card_88_emitted(self):
        blk = TacsBlock(
            name="b1", expression="sin(omega*t)",
            output="ysig", inputs=("omega", "t"),
        )
        text = emit_tacs_section([blk])
        # cartão type-88 começa com "88"
        card_lines = [
            line for line in text.splitlines()
            if line.startswith("88")
        ]
        assert len(card_lines) == 1
        assert "ysig" in card_lines[0]

    def test_initial_value_in_comment(self):
        blk = TacsBlock(
            name="b", expression="a", output="y",
            inputs=("a",), initial_value=3.5,
        )
        text = emit_tacs_section([blk])
        assert "initial_value" in text
        assert "3.5" in text

    def test_initial_value_zero_omitted(self):
        blk = TacsBlock(
            name="b", expression="a", output="y", inputs=("a",),
        )
        text = emit_tacs_section([blk])
        assert "initial_value" not in text

    def test_invalid_block_raises(self):
        blk = TacsBlock(
            name="bad", expression="foo(x)",  # foo desconhecida
            output="y", inputs=("x",),
        )
        with pytest.raises(ValueError, match="inválido"):
            emit_tacs_section([blk])

    def test_multiple_blocks(self):
        blk1 = TacsBlock(
            name="b1", expression="a", output="y1", inputs=("a",),
        )
        blk2 = TacsBlock(
            name="b2", expression="b", output="y2", inputs=("b",),
        )
        text = emit_tacs_section([blk1, blk2])
        # 2 cartões 88
        card_lines = [
            line for line in text.splitlines()
            if line.startswith("88")
        ]
        assert len(card_lines) == 2

    def test_text_well_formed_lines(self):
        """Cada linha começa com 'C ', '88', '/TACS', ou 'BLANK'."""
        blk = TacsBlock(
            name="b", expression="a+b", output="y", inputs=("a", "b"),
        )
        text = emit_tacs_section([blk])
        for line in text.splitlines():
            if not line.strip():
                continue
            assert (
                line.startswith("C ")
                or line.startswith("C\t")
                or line.startswith("88")
                or line.startswith("/TACS")
                or line.startswith("BLANK")
            ), f"Linha mal-formada: {line!r}"
