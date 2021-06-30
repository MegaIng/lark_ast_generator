import random
from collections import defaultdict
from pprint import pprint
from random import randrange, choice

from ast_generator import ASTGenerator, depth
from lark import Lark, Tree, Token
from lark.grammar import Rule, NonTerminal, Symbol, Terminal
from lark.reconstruct import Reconstructor


def random_word(alphabet, length_range):
    length = randrange(*length_range)
    return ''.join(choice(alphabet) for _ in range(length))


def regexp_builder(term_def):
    if term_def.name == "RULE":
        return Token(term_def.name, random_word("abcdefghijklmnopqrstuvwxyz", (1, 2)))
    elif term_def.name == "TOKEN":
        return Token(term_def.name, random_word("ABCDEFGHIJKLMNOPQRSTUVWXYZ", (1, 2)))
    elif term_def.name == "NUMBER":
        return Token(term_def.name, random_word("0123456789", (1, 2)))
    elif term_def.name == "STRING":
        return Token(term_def.name, '"' + random_word("0123456789", (1, 2)) + '"')
    elif term_def.name == "REGEXP":
        return Token(term_def.name, '/' + random_word("0123456789", (1,2)) + '/')
    elif term_def.name == "OP":
        return Token(term_def.name, choice(("+", "*", "?")))
    elif term_def.name == "_NL":
        return Token(term_def.name, "\n")
    else:
        raise ValueError(term_def)


parser = Lark.open_from_package("lark", "lark.lark", ("grammars",), keep_all_tokens=True)

lark_generator = ASTGenerator(parser, regexp_builder)
lark_reconstructor = Reconstructor(parser, {
    "_NL": lambda _: "\n",
    "_VBAR": lambda _: "|",
})
