from __future__ import annotations

from collections import defaultdict
from random import choice
from typing import Optional, Callable

from lark import Lark, Token, Tree, Transformer
from lark.grammar import Terminal, NonTerminal, Rule
from lark.lexer import TerminalDef
from lark.visitors import Interpreter


class ASTGenerator:
    def __init__(self, parser: Lark, term_builder=None):
        self.parser = parser
        self.term_builder = term_builder
        self.term_by_name = {t.name: t for t in self.parser.terminals}
        self.rule_by_symbol = defaultdict(list)
        for r in self.parser.rules:
            self.rule_by_symbol[r.origin].append(r)

    def _term_builder(self, term: Terminal):
        term_def: TerminalDef = self.term_by_name[term.name]
        if term_def.pattern.type == "str":
            return Token(term.name, term_def.pattern.value)
        elif self.term_builder:
            return self.term_builder(term_def)
        else:
            raise ValueError("Can't build Token for Terminal %r" % term.name)

    def _rule_builder(self, rule: Rule, hole: Hole):
        children = []
        for sym in rule.expansion:
            if sym.is_term:
                if not sym.filter_out or rule.options.keep_all_tokens:
                    children.append(self._term_builder(sym))
            else:
                children.append(sym)
        name = rule.alias or rule.origin.name
        if not rule.alias and (name.startswith("_") or (rule.options.expand1 and len(children) == 1)):
            tree = InlineTree(name, children)
        else:
            tree = Tree(name, children)
        hole.fill(tree)

    def start_build(self, start=None):
        # We could just copy the code
        start = self.parser.parser._verify_start(start)
        return HoleTree(NonTerminal(start))

    def build_absolute_index(self, hole_tree: HoleTree, rules: list[int]):
        for i in rules:
            r = self.parser.rules[i]
            hole = hole_tree.get_for_symbol(r.origin)
            self._rule_builder(r, hole)

    def build_relative_index(self, hole_tree: HoleTree, rules: list[int]):
        meaning = []
        for i in rules:
            hole = hole_tree.bfs_first_hole
            options = self.rule_by_symbol[hole.symbol]
            rule = options[i]
            meaning.append((i, hole.path, rule))
            self._rule_builder(rule, hole)
        return meaning

    def build_picker(self, hole_tree: HoleTree, picker: Callable[[list[Rule], Hole], Rule], n: int = None):
        track = []
        i = 0
        while hole_tree.any_holes and (n is None or i < n):
            hole = hole_tree.bfs_first_hole
            options = self.rule_by_symbol[hole.symbol]
            rule = picker(options, hole)
            track.append(options.index(rule))
            self._rule_builder(rule, hole)
            i += 1
        return track


class InlineTree(Tree):
    pass


class Hole:
    def __init__(self, target: Optional[Tree], index: int, hole_tree: HoleTree, path: tuple[int, ...]):
        self.target = target
        if target is None:
            self.symbol = index
            self.index = 0
        else:
            self.symbol = target.children[index]
            self.index = index
        assert isinstance(self.symbol, NonTerminal), self.symbol
        self.hole_tree = hole_tree
        self.path = path

    def _get_holes(self, values, target):
        for i, v in enumerate(values):
            if isinstance(v, NonTerminal):
                yield Hole(target, i, self.hole_tree, (*self.path, i))

    def fill(self, tree: Tree):
        if self.target is None:
            self.hole_tree.set_start(tree)
        else:
            self.target.children[self.index] = tree
        self.hole_tree.filled(self, self._get_holes(tree.children, tree))


def flatten_inline_tree(items):
    """Yield items from any nested iterable; see Reference."""
    for x in items:
        if isinstance(x, InlineTree):
            for sub_x in flatten_inline_tree(x.children):
                yield sub_x
        else:
            yield x


class _InlineExpands(Interpreter):
    def __default__(self, tree):
        new_tree = Tree(tree.data, list(flatten_inline_tree(tree.children)), tree.meta)
        new_tree.children = self.visit_children(new_tree)
        return new_tree


class HoleTree:
    def __init__(self, start_symbol):
        self._tree = None
        self.holes_by_path = {}
        self.holes_by_symbol = defaultdict(list)
        self.holes_by_path[()] = Hole(None, start_symbol, self, ())
        self.holes_by_symbol[start_symbol].append(self.holes_by_path[()])

    def set_start(self, tree):
        assert self._tree is None
        self._tree = tree

    def filled(self, old_hole, new_holes):
        self.holes_by_symbol[old_hole.symbol].remove(old_hole)
        assert self.holes_by_path.pop(old_hole.path) is old_hole
        for nh in new_holes:
            self.holes_by_symbol[nh.symbol].append(nh)
            assert nh.path not in self.holes_by_path
            self.holes_by_path[nh.path] = nh

    def tree(self, raw: bool = False):
        return _InlineExpands().visit(self._tree) if not raw else self._tree

    @property
    def bfs_first_hole(self):
        return self.holes_by_path[min(self.holes_by_path, key=lambda t: (len(t), t))]

    @property
    def any_holes(self):
        return bool(self.holes_by_path)

    def get_for_symbol(self, symbol):
        return self.holes_by_symbol[symbol][0]


def random_picker(options, hole):
    return choice(options)


def depth(min_depth=3, max_depth=5, base=random_picker):
    def picker(options: list[Rule], hole):
        current = len(hole.path)
        if current < min_depth:
            new_options = [o for o in options
                           if any(not s.is_term for s in o.expansion)]
            if new_options:
                options = new_options
        if current + 1 > max_depth:
            new_options = [o for o in options
                           if all(s.is_term for s in o.expansion)]
            if new_options:
                options = new_options
        return base(options, hole)

    return picker
