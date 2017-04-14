import argparse
from pycparser import parse_file, c_ast, c_generator
from pycparser.c_ast import Constant


# CFFI cannot parse enum value that are not just number (e.g.
# `GODOT_BUTTON_MASK_LEFT = 1 << (GODOT_BUTTON_LEFT - 1)`), so we have
# to do the computation here.
class CookComplexEnumsVisitor(c_ast.NodeVisitor):

    def visit_Enum(self, node):
        if not node.values:
            return
        generator = c_generator.CGenerator()
        for i, elem in enumerate(node.values.enumerators):
            if not elem.value:
                continue
            try:
                raw_val = generator.visit(elem.value)
                for item in node.values.enumerators:
                    try:
                        if item.value and item.value.type == 'int':
                            raw_val = raw_val.replace(item.name, item.value.value)
                    except:
                        pass
                cooked_value = eval(raw_val)
                elem.value = Constant(type='int', value=str(cooked_value))
            except:
                pass


def generate(godot_root):
    gdnative_header = '%s/modules/gdnative/godot.h' % godot_root
    gdnative_include = '%s/modules/gdnative/godot' % godot_root
    ast = parse_file(gdnative_header, use_cpp=True, cpp_args=['-I' + gdnative_include, '-Ifake_libc_include'])
    v = CookComplexEnumsVisitor()
    v.visit(ast)
    generator = c_generator.CGenerator()
    splitted_src = generator.visit(ast).split('\n')
    # First lines are typedefs not related with godot creating compile time errors
    first_line = next(i for i, line in enumerate(splitted_src) if 'godot' in line.lower())
    return '\n'.join(splitted_src[first_line:])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate cdef.gen.h file (needed to generate'
                                                 ' CFFI bindings) from the gdnative headers.')
    parser.add_argument('godot_root_path', help='Path to Godot root project')
    parser.add_argument('--output', '-o', default='cdef.gen.h')
    args = parser.parse_args()
    with open(args.output, 'w') as fd:
        fd.write('/********************************************************/\n')
        fd.write('/* AUTOGENERATED by tools/generate_gdnative_cffidefs.py */\n')
        fd.write('/********************************************************/\n')
        fd.write(generate(args.godot_root_path))
