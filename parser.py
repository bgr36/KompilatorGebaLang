from sly import Parser
from lexer import MyLexer

class MyParser(Parser):
    tokens = MyLexer.tokens
    
    precedence = (
        ('left', PLUS, MINUS),
        ('left', TIMES, DIV, MOD),
    )


    @_('procedures main')
    def program_all(self, p):
        return ('PROGRAM_ALL', p.procedures, p.main)

    @_('procedures PROCEDURE proc_head IS declarations IN commands END')
    def procedures(self, p):
        p.procedures.append(('PROCEDURE', p.proc_head, p.declarations, p.commands, p.lineno))
        return p.procedures

    @_('procedures PROCEDURE proc_head IS IN commands END')
    def procedures(self, p):
        p.procedures.append(('PROCEDURE', p.proc_head, [], p.commands, p.lineno))
        return p.procedures

    @_('')
    def procedures(self, p):
        return []

    @_('PROGRAM IS declarations IN commands END')
    def main(self, p):
        return ('MAIN', p.declarations, p.commands, p.lineno)

    @_('PROGRAM IS IN commands END')
    def main(self, p):
        return ('MAIN', [], p.commands, p.lineno)


    @_('declarations "," PIDENTIFIER')
    def declarations(self, p):
        p.declarations.append(('VAR', p.PIDENTIFIER, p.lineno))
        return p.declarations

    @_('declarations "," PIDENTIFIER "[" NUM ":" NUM "]"')
    def declarations(self, p):
        p.declarations.append(('ARRAY', p.PIDENTIFIER, p.NUM0, p.NUM1, p.lineno))
        return p.declarations

    @_('PIDENTIFIER')
    def declarations(self, p):
        return [('VAR', p.PIDENTIFIER, p.lineno)]

    @_('PIDENTIFIER "[" NUM ":" NUM "]"')
    def declarations(self, p):
        return [('ARRAY', p.PIDENTIFIER, p.NUM0, p.NUM1, p.lineno)]


    @_('PIDENTIFIER "(" args_decl ")"')
    def proc_head(self, p):
        return ( p.PIDENTIFIER, p.args_decl)

    @_('args_decl "," type PIDENTIFIER')
    def args_decl(self, p):
        p.args_decl.append((p.type, p.PIDENTIFIER, p.lineno))
        return p.args_decl

    @_('type PIDENTIFIER')
    def args_decl(self, p):
        return [(p.type, p.PIDENTIFIER, p.lineno)]

    @_('T', 'I', 'O','')
    def type(self, p):
        return p[0] if len(p) > 0 else None


    @_('commands command')
    def commands(self, p):
        p.commands.append(p.command)
        return p.commands

    @_('command')
    def commands(self, p):
        return [p.command]

    @_('identifier ASSIGN expression ";"')
    def command(self, p):
        return ('ASSIGN', p.identifier, p.expression, p.lineno)

    @_('IF condition THEN commands ELSE commands ENDIF')
    def command(self, p):
        return ('IF_ELSE', p.condition, p.commands0, p.commands1, p.lineno)

    @_('IF condition THEN commands ENDIF')
    def command(self, p):
        return ('IF', p.condition, p.commands, p.lineno)

    @_('WHILE condition DO commands ENDWHILE')
    def command(self, p):
        return ('WHILE', p.condition, p.commands, p.lineno)

    @_('REPEAT commands UNTIL condition ";"')
    def command(self, p):
        return ('REPEAT', p.commands, p.condition, p.lineno)

    @_('FOR PIDENTIFIER FROM value TO value DO commands ENDFOR')
    def command(self, p):
        return ('FOR_TO', p.PIDENTIFIER, p.value0, p.value1, p.commands, p.lineno)

    @_('FOR PIDENTIFIER FROM value DOWNTO value DO commands ENDFOR')
    def command(self, p):
        return ('FOR_DOWNTO', p.PIDENTIFIER, p.value0, p.value1, p.commands, p.lineno)

    @_('READ identifier ";"')
    def command(self, p):
        return ('READ', p.identifier, p.lineno)

    @_('WRITE value ";"')
    def command(self, p):
        return ('WRITE', p.value, p.lineno)

    @_('proc_call ";"')
    def command(self, p):
        return p.proc_call


    @_('PIDENTIFIER "(" args ")"')
    def proc_call(self, p):
        return ('CALL', p.PIDENTIFIER, p.args, p.lineno)

    @_('args "," PIDENTIFIER')
    def args(self, p):
        p.args.append((p.PIDENTIFIER, p.lineno))
        return p.args

    @_('PIDENTIFIER')
    def args(self, p):
        return [(p.PIDENTIFIER, p.lineno)]


    @_('value PLUS value', 'value MINUS value', 'value TIMES value', 'value DIV value', 'value MOD value')
    def expression(self, p):
        return ('BINARY_OP', p[1], p.value0, p.value1, p.lineno)

    @_('value')
    def expression(self, p):
        return p.value

    @_('value EQ value', 'value NEQ value', 'value GT value', 'value LT value', 'value GE value', 'value LE value')
    def condition(self, p):
        return ('CONDITION', p[1], p.value0, p.value1, p.lineno)


    @_('NUM')
    def value(self, p):
        return ('NUM', p.NUM, p.lineno)

    @_('identifier')
    def value(self, p):
        return p.identifier

    @_('PIDENTIFIER')
    def identifier(self, p):
        return ('ID', p.PIDENTIFIER, p.lineno)

    @_('PIDENTIFIER "[" value "]"')
    def identifier(self, p):
        return ('ARRAY_ID', p.PIDENTIFIER, p.value, p.lineno)

    def error(self, p):
        if p:
            print(f"Błąd składniowy w linii {p.lineno}: Nieoczekiwany token '{p.value}'")
        else:
            print("Błąd składniowy: Nieoczekiwany koniec pliku")