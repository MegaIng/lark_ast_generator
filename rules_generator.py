from collections import defaultdict
from operator import neg
from typing import Iterable, Any, Optional

from lark import Tree, Token
from lark.grammar import Symbol
from lark.tree_matcher import TreeMatcher


def _match_expansion(expansion: list[Symbol], children: list[Any]) \
        -> Iterable[tuple[int, Symbol, Optional[tuple[int, Any]]]]:
    child_iter = iter(enumerate(children))
    for i, sym in enumerate(expansion):
        if sym.is_term and sym.filter_out:
            yield i, sym, None
        else:
            yield i, sym, next(child_iter)
    try:
        next(child_iter)
        assert False, "Wrong number of children"
    except StopIteration:
        pass


class RulesGenerator:
    def __init__(self, parser):
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
        self.rule_indices = {}
        self.terminals = {}

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
        """
        Uses tree.data and tree.meta.orig_expansion to get the original rule
        that was/can be applied to create this tree instance.
        """
        candidates = self.rules_by_name[tree.data]
        matches = [(r, i) for (r, i) in candidates
                   if self._check_expansion(tree.meta.orig_expansion, r.expansion)]
        if not matches:
            # Sometimes, tree_matcher returns weird self rules Tree('expansion', [Tree('expansion', [...])])
            if len(tree.meta.orig_expansion) == 1 and self._check_name(tree.meta.orig_expansion[0].name, tree.data):
                # Returning None because we can just fold this rule in without losing anything.
                return None
            assert matches, ("Could not find a rule that was applied", tree, candidates)
        assert len(matches) == 1, ("Can't decide which rule was applied", candidates, matches)
        return matches[0][1]

    def _traverse(self, tree):
        """ Called for every Tree top-down """
        # Check whether this node has already been matched to actual rules
        if not getattr(tree.meta, 'match_tree', False):
            # match the tree to a rule from the parser.
            # This also creates `tree.meta.orig_expansion`, which contains the
            # sequence of Symbols that match to tree.children.
            tree = self.tree_matcher.match_tree(tree, tree.data)
        r = self.get_rule(tree)
        if r is not None:
            # If this isn't a self rule, add it as rule_index for the current path.
            self.rule_indices[tuple(self.current_path)] = r
            for i, s, c in _match_expansion(tree.meta.orig_expansion, tree.children):
                if c is not None:
                    j, v = c
                    if isinstance(v, Tree):
                        self.current_path.append(j)
                        # Recursively do this algorithm top to bottom for all nodes.
                        tree.children[j] = self._traverse(v)
                        self.current_path.pop()
                    elif c is not None:
                        self.terminals[(*self.current_path, j)] = v
        else:
            # This is a self rule. Don't extend path, just recurse
            tree = self._traverse(tree.children[0])
        return tree

    def get_rules(self, tree) -> tuple[Iterable[int], dict[tuple[int, ...], Token]]:
        """
        Returns the rule ids (e.g. absolut indices) in BFS order to generate
        an equivalent Tree. Also returns the Terminals that were placed

        On a high level, the algorithm is:

        - For each Tree node top to bottom (in DFS order)
          - use tree_matcher to find the original expansion that was used to generate the node
          - use the expansion to find the rule (checking for aliases, and edge case Self-rules)
          - save the absolute index mapped to the unique path to the current node
          - recurse over the children newly unreduced Tree
        - By using the unique path, sort from DFS to BFS and return the rules indices.
        """
        # current_path is the path to the current node/Tree, e.g. the list of indices
        # for the `.children` starting from the tree instance passed here.
        # This is used to order rules BFS
        self.current_path = []

        # path -> rule index. Set in _traverse
        self.rule_indices = {}

        # path -> terminals
        self.terminals = {}

        # Collect the rule indices in .rule_indices and the terminals in .terminals
        self._traverse(tree)

        # Sort the rule indices BFS
        bfs_indices = [i for k, i in sorted(self.rule_indices.items(), key=lambda t: tuple(map(neg, t[0])))]

        return bfs_indices, self.terminals
