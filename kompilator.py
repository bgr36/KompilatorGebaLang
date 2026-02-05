import sys
from lexer import MyLexer
from parser import MyParser
from generator import CodeGenerator

def main():
    if len(sys.argv) != 3:
        print("Użycie: python compiler.py <wejście> <wyjście>")
        return

    with open(sys.argv[1], 'r') as f:
        data = f.read()

    lexer = MyLexer()
    parser = MyParser()
    
    ast = parser.parse(lexer.tokenize(data))
    if ast:
        gen = CodeGenerator()
        gen.walk(ast)
        
        with open(sys.argv[2], 'w') as f:
            f.write("\n".join(gen.instructions) + "\n")
        print(f"Kompilacja zakończona sukcesem -> {sys.argv[2]}")

if __name__ == "__main__":
    main()