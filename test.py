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
        return Token(term_def.name, random_word("abcdefghijklmnopqrstuvwxyz", (1,6)))
    elif term_def.name == "TOKEN":
        return Token(term_def.name, random_word("ABCDEFGHIJKLMNOPQRSTUVWXYZ", (1,6)))
    elif term_def.name == "NUMBER":
        return Token(term_def.name, random_word("0123456789", (1,3)))
    elif term_def.name == "STRING":
        return Token(term_def.name, '"'+random_word("0123456789", (1,2))+'"')
    elif term_def.name == "REGEXP":
        return Token(term_def.name, '/'+random_word("0123456789", (5,6))+'/')
    elif term_def.name == "OP":
        return Token(term_def.name, choice(("+", "*", "?")))
    else:
        raise ValueError(term_def)


parser = Lark.open_from_package("lark", "lark.lark", ["grammars"])

ast_builder = ASTGenerator(parser, regexp_builder)
hole_tree = ast_builder.start_build()

rule_seq1 = [0, 2, 1]
track = [1, 3, 0, 0, 1, 2, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 2, 0, 0, 2, 2, 1, 1, 1, 1, 3, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1]

meaning = ast_builder.build_relative_index(hole_tree, track)

pprint(ast_builder.rule_by_symbol)
pprint(meaning)
# track = ast_builder.build_picker(hole_tree, depth(min_depth=5, max_depth=10))
assert not hole_tree.any_holes
print(track)

print(hole_tree.tree(True).pretty())

text = Reconstructor(parser, {
    "_NL": lambda _: "\n",
    "_VBAR": lambda _: "|",
}).reconstruct(hole_tree.tree(), None, True)  # has string "aa"
print(text)
print(parser.parse(text).pretty())
print(len(text))
