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

    def _check_rule(self, rule, children):
        i = 0
        for e in rule.expansion:
            if e.is_term:
                if not e.filter_out:
                    if i >= len(children): return False
                    t = children[i]
                    if not (isinstance(t, Token) and t.type == e.name):
                        return False
                    i += 1
            else:
                if i >= len(children): return False
                t = children[i]
                if not (isinstance(t, Tree) and self._check_name(t.data, e.name)):
                    return False
                i += 1
        return i == len(children)

    def get_rule(self, tree):
        candidates = self.rules_by_name[tree.data]
        matches = [(r, i) for (r, i) in candidates
                   if self._check_rule(r, tree.children)]
        if not matches:
            # Sometimes, tree_matcher returns weird self rules Tree('expansion', [Tree('expansion', [...])])
            if len(tree.children) == 1 and isinstance(tree.children[0], Tree) and self._check_name(
                    tree.children[0].data, tree.data):
                return None
            assert matches, ("No rule left that was applied", tree, candidates)
        # assert len(matches) == 1, ("Can't decide which rule was applied", candidates, matches)
        return matches[0][1]

    def __default__(self, tree):
        if not getattr(tree.meta, 'match_tree', False):
            # print("|"*len(self.current_path), "old", tree)
            tree = self.tree_matcher.match_tree(tree, tree.data)
        # print("|"*len(self.current_path), tree)
        for i, c in enumerate(tree.children):
            if isinstance(c, Tree):
                self.current_path.append(i)
                tree.children[i] = self.visit(c)
                self.current_path.pop()
        # print("|"*len(self.current_path),"final", tree)
        r = self.get_rule(tree)
        if r is not None:
            self.values[tuple(self.current_path)] = r
        return tree

    def get_rules(self, tree) -> Iterable[int]:
        self.current_path = []
        self.values = {}
        self.visit(tree)
        return [i for k, i in sorted(self.values.items(), key=lambda t: tuple(map(neg, t[0])))]
