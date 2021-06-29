from grammar_generator import parser, lark_generator, lark_reconstructor
from rules_generator import RulesGenerator


rg = RulesGenerator(parser)

pattern = parser.parse("""
start: "a"~5..5
start: ("b"~5)~5
""")
print(pattern.pretty())

rules = rg.get_rules(pattern)

hole_tree = lark_generator.start_build()
print(rules)

lark_generator.build_absolute_index(hole_tree, rules)

tree = hole_tree.tree()

print(tree.pretty())
print(lark_reconstructor.reconstruct(tree))
print(lark_reconstructor.reconstruct(pattern))
