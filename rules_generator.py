from collections import defaultdict
from operator import neg
from typing import Iterable

from lark import Lark, Tree, Token
from lark.grammar import Symbol, NonTerminal, Terminal
from lark.reconstruct import Reconstructor, is_iter_empty
from lark.tree_matcher import is_discarded_terminal, TreeMatcher
from lark.visitors import Transformer_InPlace, Interpreter


class RulesGenerator(Interpreter):
    def __init__(self, parser):
        super(RulesGenerator, self).__init__()
        self.parser = parser
        self.rules_by_name = defaultdict(list)
        self.aliases = defaultdict(list)
        for i, r in enumerate(self.parser.rules):
            self.rules_by_name[r.origin.name].append((r, i))
            if r.alias is not None:
                self.rules_by_name[r.alias].append((r, i))
                self.aliases[r.alias].append(r.origin.name)
        for n, rs in self.rules_by_name.items():
            self.rules_by_name[n] = sorted(rs, key=lambda t: -len(t[0].expansion))
        self.tree_matcher = TreeMatcher(parser)
        self.current_path = []
        self.values = {}

    def _check_name(self, data, target):
        if data == target:
            return True
        elif data in self.aliases:
            return target in self.aliases[data]
        else:
            return False

    def _check_expansion(self, orig_expansion, expansion):
        return len(orig_expansion) == len(expansion) and all(o == e for o, e in zip(orig_expansion, expansion))

    def get_rule(self, tree):
        candidates = self.rules_by_name[tree.data]
        matches = [(r, i) for (r, i) in candidates
                   if self._check_expansion(tree.meta.orig_expansion, r.expansion)]
        if not matches:
            # Sometimes, tree_matcher returns weird self rules Tree('expansion', [Tree('expansion', [...])])
            if len(tree.meta.orig_expansion) == 1 and self._check_name(tree.meta.orig_expansion[0].name, tree.data):
                return None
            assert matches, ("No rule left that was applied", tree, candidates)
        assert len(matches) == 1, ("Can't decide which rule was applied", candidates, matches)
        return matches[0][1]

    def __default__(self, tree):
        if not getattr(tree.meta, 'match_tree', False):
            # print("|"*len(self.current_path), "old", tree)
            tree = self.tree_matcher.match_tree(tree, tree.data)
        # print("|"*len(self.current_path), tree)
        r = self.get_rule(tree)
        for i, c in enumerate(tree.children):
            if isinstance(c, Tree):
                self.current_path.append(i)
                tree.children[i] = self.visit(c)
                self.current_path.pop()
        # print("|"*len(self.current_path),"final", tree)
        if r is not None:
            self.values[tuple(self.current_path)] = r
        return tree

    def get_rules(self, tree) -> Iterable[int]:
        self.current_path = []
        self.values = {}
        self.visit(tree)
        return [i for k, i in sorted(self.values.items(), key=lambda t: tuple(map(neg, t[0])))]
