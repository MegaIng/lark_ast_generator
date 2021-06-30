from grammar_generator import parser, lark_generator, lark_reconstructor
from rules_generator import RulesGenerator


rg = RulesGenerator(parser)

pattern = parser.parse("""\
start: "a"~5..5
start: ("b"~5)~5
""")
print(pattern.pretty())
print(lark_reconstructor.reconstruct(pattern))

rules, terms = rg.get_rules(pattern)

print(rules)
print(terms)

hole_tree = lark_generator.start_build()

lark_generator.build_absolute_index(hole_tree, rules)

tree = hole_tree.tree()
tree_with_terms = hole_tree.tree(terminals=terms)

print(tree.pretty())
print(lark_reconstructor.reconstruct(tree))
print(tree_with_terms.pretty())
print(lark_reconstructor.reconstruct(tree_with_terms))
