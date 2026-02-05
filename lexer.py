from sly import Lexer

class MyLexer(Lexer):
  ignore = ' \t'
  ignore_comment = r'\#.*'
  tokens = {
    'PIDENTIFIER', 'NUM',
    'PROCEDURE', 'IS', 'IN', 'END',
    'PROGRAM', 
    'IF', 'THEN', 'ELSE', 'ENDIF',
    'WHILE', 'DO', 'ENDWHILE',
    'REPEAT', 'UNTIL',
    'FOR', 'FROM', 'TO', 'DOWNTO', 'ENDFOR',
    'READ', 'WRITE',
    'T', 'I', 'O',
    'PLUS', 'MINUS', 'TIMES', 'DIV', 'MOD',
    'ASSIGN', 'EQ', 'NEQ', 'GT', 'LT', 'GE', 'LE',
  }

  PIDENTIFIER = r'[_a-z]+'
  NUM = r'\d+'

  PROCEDURE = r'PROCEDURE'
  IS = r'IS'
  IN = r'IN'


  PROGRAM = r'PROGRAM'

  ENDIF = r'ENDIF'
  IF = r'IF'
  THEN = r'THEN'
  ELSE = r'ELSE'

  ENDWHILE = r'ENDWHILE'
  WHILE = r'WHILE'


  REPEAT = r'REPEAT'
  UNTIL = r'UNTIL'

  FOR = r'FOR'
  FROM = r'FROM'
  DOWNTO = r'DOWNTO'
  DO = r'DO'
  ENDFOR = r'ENDFOR'
  TO = r'TO'

  READ = r'READ'
  WRITE = r'WRITE'

  T = r'T'
  I = r'I'
  O = r'O'

  PLUS = r'\+'
  MINUS = r'-'
  TIMES = r'\*'
  DIV = r'/'
  MOD = r'%'

  ASSIGN = r':='
  NEQ = r'!='
  GE = r'>='
  LE = r'<='
  EQ = r'='
  GT = r'>'
  LT = r'<'
  END = r'END'

  literals = { '(', ')', '[', ']', ':', ';', ',' }

  def error(self, t):
      print(f"Błąd leksykalny: Nielegalny znak '{t.value[0]}' w linii {self.lineno}")
      self.index += 1
  
  @_(r'\n+')
  def ignore_newline(self, t):
    self.lineno += t.value.count('\n')
  
