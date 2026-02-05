from platform import node


class SymbolTable:
    def __init__(self):
        self.global_symbols = {} 
        self.iterators = set()
        self.procedures = {}
        self.current_scope = "MAIN"
        self.next_address = 0

    def is_iterator(self, name):
        return name in self.iterators

    def remove_variable(self, name):
        if name in self.variables:
            del self.variables[name]
        if name in self.iterators:
            self.iterators.remove(name)

    @property
    def variables(self):
        """Zwraca słownik zmiennych dla aktualnego zasięgu (MAIN lub procedura)"""
        if self.current_scope == "MAIN":
            return self.global_symbols
        else:
            return self.procedures[self.current_scope]['locals']

    def declare_variable(self, name, lineno, is_param=False, p_type=None):
        if name in self.variables:
            raise Exception(f"Błąd w linii {lineno}: Redeklaracja zmiennej {name}") 
        
        is_initialized = False
        if is_param:
            if p_type != 'O':
                is_initialized = True

        if p_type == 'Iterator':
            is_initialized = True
        
        self.variables[name] = {
            'address': self.next_address,
            'is_param': is_param,
            'p_type': p_type,
            'initialized': is_initialized,
            'type': 'VAR'
        }
        self.next_address += 1

    def get_address(self, name, lineno):
        if name not in self.variables:
            if self.current_scope != "MAIN" and name in self.global_symbols:
                return self.global_symbols[name]['address']
            raise Exception(f"Błąd w linii {lineno}: Niezadeklarowana zmienna {name} w linii {lineno}")
        
        var_data = self.variables[name]
        if isinstance(var_data, dict):
            return var_data['address']
        return var_data
    
    def declare_array(self, name, first, last, lineno, is_param=False, p_type=None):
        if name in self.variables:
            raise Exception(f"Błąd w linii {lineno}: Druga deklaracja {name}")
        
        offset = self.next_address - first
        
        self.variables[name] = {
            'type': 'ARRAY',
            'first': first,
            'last': last,
            'offset': self.next_address - first,
            'is_param': is_param,
            'p_type': p_type,
            'initialized': True,
            'address': self.next_address
        }

        if is_param:
            self.next_address += 1
        else:
            self.next_address += (last - first + 1)
        
    def declare_hidden_variable(self):
        name = f"__hidden_{self.next_address}"
        self.declare_variable(name, 0, is_param=False, p_type='Iterator')
        return self.variables[name]['address']
    
    def declare_procedure(self, name, params, lineno):
        if name in self.procedures:
            raise Exception(f"Błąd...")
        
        ret_ptr = self.next_address
        self.next_address += 1
        
        self.procedures[name] = {
            'params': params,
            'locals': {},
            'start_address': None,
            'return_address_ptr': ret_ptr
        }
        
        old_scope = self.current_scope
        self.current_scope = name

        for p_type, p_name, p_line in params:
            if p_type == 'T':
                self.declare_array(p_name, 0, 0, p_line, is_param=True,p_type=p_type)
            elif p_type in ['I', 'O', None, '']:
                self.declare_variable(p_name, p_line, is_param=True,p_type=p_type)
            else:
                raise Exception(f"Błąd w linii {p_line}: Nieznany typ parametru {p_type}")

    
class CodeGenerator:
    def __init__(self):
      self.symbols = SymbolTable()
      self.calls_to_patch = []
      self.instructions = []
      self.symbols.declare_variable("__tmp1", 0)
      self.symbols.declare_variable("__tmp2", 0)
      self.symbols.declare_variable("__mult_a", 0)
      self.symbols.declare_variable("__mult_b", 0)
      self.symbols.declare_variable("__mult_res", 0)
      self.symbols.declare_variable("__div_a", 0)
      self.symbols.declare_variable("__div_b", 0)
      self.symbols.declare_variable("__div_res", 0)
      self.symbols.declare_variable("__div_m", 0) 

    def emit(self, instr):
      self.instructions.append(instr)

    def generate_constant(self, value):
        value = int(value)
        self.emit("RST a")
        if value == 0: return
        
        binary = bin(value)[2:]
        for bit in binary:
            self.emit("SHL a")
            if bit == '1':
                self.emit("INC a")

    def walk(self, node):
        tag = node[0]
            
        if tag == 'PROGRAM_ALL':
            procedures = node[1]
            main = node[2]
            for reg in ['a','b','c','d','e','f','g','h']:
                self.emit(f"RST {reg}") 

            # Rejestracja nazw procedur w SymbolTable
            for proc in procedures:
                name, params = proc[1]
                self.symbols.declare_procedure(name, params, proc[4])

            #Skok do Main
            jump_main_idx = len(self.instructions)
            self.emit("JUMP placeholder")

            #Generowanie kodu procedur
            for proc in procedures:
                self.walk(proc)

            #Powrót do skoku do Main
            self.instructions[jump_main_idx] = f"JUMP {len(self.instructions)}"
            
            #Generowanie Main
            self.walk(main)
            self.emit("HALT")

            #wypełnianie CALL placehloder
            for instr_idx, proc_name in self.calls_to_patch:
                real_addr = self.symbols.procedures[proc_name]['start_address']
                self.instructions[instr_idx] = f"CALL {real_addr}"

        elif tag == 'MAIN':
            declarations = node[1]
            commands = node[2]

            # Przetwarzaie deklaracji
            for decl in declarations:
                #('VAR', 'a', lineno) lub ('ARRAY', 'tab', 10, 20, lineno)
                type_decl = decl[0]
                if type_decl == 'VAR':
                    self.symbols.declare_variable(decl[1], decl[2])
                elif type_decl == 'ARRAY':
                    self.symbols.declare_array(decl[1], int(decl[2]), int(decl[3]), decl[4])

            for cmd in commands:
                self.walk(cmd)

        elif tag == 'NUM':
            # node: ('NUM', value, lineno)
            value = int(node[1])
            self.generate_constant(value)

        elif tag == 'READ':
            # node: ('READ', ('ID', name),lineno)
            name = node[1][1]
            lineno = node[2]
            var = self.symbols.variables.get(name)

            if self.symbols.is_iterator(name):
                raise Exception(f"Błąd: Nie można wczytać wartości do iteratora {name}")
            
            if var:
                if var.get('p_type') == 'I':
                    raise Exception(f"Błąd w linii {lineno}: Próba modyfikacji parametru wejściowego (I) '{name}'")
                
                if var.get('p_type') == 'O':
                    var['initialized'] = True


            addr = self.symbols.get_address(name, lineno)
            self.emit("READ")
            self.emit(f"STORE {addr}")

            var = self.symbols.variables.get(name)
            if var:
                var['initialized'] = True

        elif tag == 'WRITE':
            val_node = node[1]
            lineno = node[2]
            
            if val_node[0] == 'NUM':
                self.generate_constant(val_node[1])
            
            elif val_node[0] in ['ID', 'ARRAY_ID']:
                var = self.symbols.variables.get(val_node[1])
                if var and var.get('p_type') == 'O' and not var.get('initialized'):
                    raise Exception(f"Błąd w linii {lineno}: Próba wypisania (WRITE) niezainicjalizowanego parametru wyjściowego (O) '{val_node[1]}'")
                elif var and not var.get('initialized'):
                    raise Exception(f"Błąd w linii {lineno}: Próba wypisania (WRITE) niezainicjalizowanej zmiennej '{val_node[1]}'")
                
                self.generate_address_to_rb(val_node)
                self.emit("RLOAD b")
            
            self.emit("WRITE")

        elif tag == 'ASSIGN':
            target_id = node[1] # ('ID', name, lineno) or ('ARRAY_ID', name, index, lineno)
            expression = node[2]
            lineno = node[-1]

            name = target_id[1]
            var = self.symbols.variables.get(name)

            if var:
                if var.get('p_type') == 'I':
                    raise Exception(f"Błąd w linii {lineno}: Próba modyfikacji parametru wejściowego (I) '{name}'")
                
                if var.get('p_type') == 'O':
                    var['initialized'] = True

            if target_id[0] == 'ID' and self.symbols.is_iterator(name):
                raise Exception(f"Błąd: Próba modyfikacji iteratora {name}")

            self.walk(node[2]) 
            self.emit("SWP g") 
            self.generate_address_to_rb(node[1]) 
            self.emit("SWP g") 
            self.emit("RSTORE b")

            if var:
                var['initialized'] = True

        elif tag == 'BINARY_OP':
            op = node[1]

            self.walk(node[2]) 
            self.emit("SWP g")

            self.walk(node[3]) 
            self.emit("SWP b")
            self.emit("SWP g")

            if op == '+':
                self.emit("ADD b")
            elif op == '-':
                self.emit("SUB b")
            elif op == '*':
                m_a = self.symbols.get_address("__mult_a", 0)
                m_b = self.symbols.get_address("__mult_b", 0)
                res = self.symbols.get_address("__mult_res", 0)

                self.emit(f"STORE {m_a}")
                self.emit("SWP b") 
                self.emit(f"STORE {m_b}")
                
                self.emit("RST a")
                self.emit(f"STORE {res}")

                start_mult = len(self.instructions)
                self.emit(f"LOAD {m_b}")
                jump_out = len(self.instructions)
                self.emit("JZERO ???") 

                self.emit("SHR a")
                self.emit("SHL a")
                self.emit("SWP b")
                self.emit(f"LOAD {m_b}")
                self.emit("SUB b")
                
                jump_skip_add = len(self.instructions)
                self.emit("JZERO ???") 
                
                self.emit(f"LOAD {res}")
                self.emit("SWP b")
                self.emit(f"LOAD {m_a}")
                self.emit("ADD b")
                self.emit(f"STORE {res}")

                target_skip = len(self.instructions)
                self.instructions[jump_skip_add] = f"JZERO {target_skip}"
                self.emit(f"LOAD {m_a}")
                self.emit("SHL a")
                self.emit(f"STORE {m_a}")
                self.emit(f"LOAD {m_b}")
                self.emit("SHR a")
                self.emit(f"STORE {m_b}")
                self.emit(f"JUMP {start_mult}")
                
                self.instructions[jump_out] = f"JZERO {len(self.instructions)}"
                self.emit(f"LOAD {res}")

            elif op in ['/', '%']:
                d_a = self.symbols.get_address("__div_a", 0)
                d_b = self.symbols.get_address("__div_b", 0)
                d_res = self.symbols.get_address("__div_res", 0)
                d_m = self.symbols.get_address("__div_m", 0)

                self.emit(f"STORE {d_a}")
                self.emit("SWP b")
                self.emit(f"STORE {d_b}")

                self.emit(f"LOAD {d_b}")
                jump_div_zero = len(self.instructions)
                self.emit("JZERO ???")

                self.emit("RST a")
                self.emit(f"STORE {d_res}")
                self.emit("INC a")
                self.emit(f"STORE {d_m}")

                loop_shl_start = len(self.instructions)
                self.emit(f"LOAD {d_a}")
                self.emit("SWP b")
                self.emit(f"LOAD {d_b}")
                self.emit("SHL a")
                self.emit("SUB b") 
                
                jump_shl_end = len(self.instructions)
                self.emit("JPOS ???")

                self.emit(f"LOAD {d_b}")
                self.emit("SHL a")
                self.emit(f"STORE {d_b}")
                self.emit(f"LOAD {d_m}")
                self.emit("SHL a")
                self.emit(f"STORE {d_m}")
                self.emit(f"JUMP {loop_shl_start}")
                
                self.instructions[jump_shl_end] = f"JPOS {len(self.instructions)}"

                loop_main_start = len(self.instructions)
                self.emit(f"LOAD {d_m}")
                jump_main_end = len(self.instructions)
                self.emit("JZERO ???") 

                self.emit(f"LOAD {d_a}")
                self.emit("SWP b")
                self.emit(f"LOAD {d_b}")
                self.emit("SUB b") 
                
                jump_skip_sub = len(self.instructions)
                self.emit("JPOS ???") 

                self.emit(f"LOAD {d_a}")
                self.emit("SWP b")
                self.emit(f"LOAD {d_b}")
                self.emit("SWP b")
                self.emit("SUB b")
                self.emit(f"STORE {d_a}")
                
                self.emit(f"LOAD {d_res}")
                self.emit("SWP b")
                self.emit(f"LOAD {d_m}")
                self.emit("ADD b")
                self.emit(f"STORE {d_res}")

                target_skip_sub = len(self.instructions)
                self.instructions[jump_skip_sub] = f"JPOS {target_skip_sub}"
                self.emit(f"LOAD {d_b}")
                self.emit("SHR a")
                self.emit(f"STORE {d_b}")
                self.emit(f"LOAD {d_m}")
                self.emit("SHR a")
                self.emit(f"STORE {d_m}")
                self.emit(f"JUMP {loop_main_start}")

                self.instructions[jump_main_end] = f"JZERO {len(self.instructions)}"
                
                if op == '/':
                    self.emit(f"LOAD {d_res}")
                else: # %
                    self.emit(f"LOAD {d_a}")

                jump_after_all = len(self.instructions)
                self.emit("JUMP ???")
                
                target_div_zero = len(self.instructions)
                self.instructions[jump_div_zero] = f"JZERO {target_div_zero}"
                self.emit("RST a") 
                
                self.instructions[jump_after_all] = f"JUMP {len(self.instructions)}"

        elif tag == 'ID' or tag == 'ARRAY_ID':
            name = node[1]
            lineno = node[-1] 
            
            var = self.symbols.variables.get(name)

            if var and var.get('p_type') == 'O' and not var.get('initialized'):
                raise Exception(f"Błąd w linii {lineno}: Parametr wyjściowy (O) '{name}' jest używany, zanim przypisano mu wartość.")
            elif var and not var.get('initialized'):
                raise Exception(f"Błąd w linii {lineno}: Zmienna '{name}' jest używana, zanim przypisano jej wartość.")
            
            self.generate_address_to_rb(node)
            self.emit("RLOAD b")

        elif tag == 'IF':
            self.walk_condition(node[1])
            jump_idx = len(self.instructions)
            self.emit("JZERO ???")
            for cmd in node[2]:
                self.walk(cmd)
            self.instructions[jump_idx] = f"JZERO {len(self.instructions)}"

        elif tag == 'IF_ELSE':

            self.walk_condition(node[1])
            
            jump_to_else_idx = len(self.instructions)
            self.emit("JZERO ???")
            
            for cmd in node[2]:
                self.walk(cmd)
            
            jump_to_end_idx = len(self.instructions)
            self.emit("JUMP ???")
            
            self.instructions[jump_to_else_idx] = f"JZERO {len(self.instructions)}"
            
            for cmd in node[3]:
                self.walk(cmd)
            
            self.instructions[jump_to_end_idx] = f"JUMP {len(self.instructions)}"

        elif tag == 'WHILE':
            start_addr = len(self.instructions)
            self.walk_condition(node[1])
            jump_out_idx = len(self.instructions)

            self.emit("JZERO ???") 
            for cmd in node[2]:
                self.walk(cmd)

            self.emit(f"JUMP {start_addr}")
            self.instructions[jump_out_idx] = f"JZERO {len(self.instructions)}"

        elif tag == 'REPEAT':
            start_address = len(self.instructions)
            
            for cmd in node[1]:
                self.walk(cmd)

            self.walk_condition(node[2])
            
            self.emit(f"JZERO {start_address}")

        elif tag == 'CONDITION':
          self.walk_condition(node)

        elif tag in ['FOR_TO', 'FOR_DOWNTO']:
            #(tag, iterator_name, start_expr, end_expr, commands, lineno)
            it_name = node[1]
            start_expr = node[2]
            end_expr = node[3]
            commands = node[4]
            lineno = node[5]

            self.symbols.declare_variable(it_name, lineno, p_type='Iterator')
            self.symbols.iterators.add(it_name)
            
            it_addr = self.symbols.get_address(it_name, lineno)
            limit_addr = self.symbols.declare_hidden_variable()

            self.walk(start_expr)
            self.emit(f"STORE {it_addr}")
            self.walk(end_expr)
            self.emit(f"STORE {limit_addr}")

            start_loop_addr = len(self.instructions)

            if tag == 'FOR_TO':
                self.emit(f"LOAD {limit_addr}")
                self.emit("SWP b")
                self.emit(f"LOAD {it_addr}")
                self.emit("SUB b")
            else:
                self.emit(f"LOAD {it_addr}")
                self.emit("SWP b")
                self.emit(f"LOAD {limit_addr}")
                self.emit("SUB b")

            jump_out_idx = len(self.instructions)
            self.emit("JPOS ???")

            for cmd in commands:
                self.walk(cmd)

            self.emit(f"LOAD {it_addr}")
            if tag == 'FOR_TO':
                self.emit("INC a")
                self.emit(f"STORE {it_addr}")
                self.emit(f"JUMP {start_loop_addr}")
            else:
                jump_stop_idx = len(self.instructions)
                self.emit("JZERO ???") 
                
                self.emit("DEC a")
                self.emit(f"STORE {it_addr}")
                self.emit(f"JUMP {start_loop_addr}")
                
                self.instructions[jump_stop_idx] = f"JZERO {len(self.instructions)}"

            self.instructions[jump_out_idx] = f"JPOS {len(self.instructions)}"

            self.symbols.remove_variable(it_name)

        elif tag == 'CALL':
            self.walk_call(node)

        elif tag == 'PROCEDURE':
            self.walk_procedure(node)

    def generate_address_to_rb(self, id_node):
        tag = id_node[0]
        name = id_node[1]
        lineno = id_node[-1]

        if name not in self.symbols.variables:
            raise Exception(f"Błąd w linii {lineno}: Użycie niezadeklarowanej zmiennej/tablicy '{name}'")
        
        var = self.symbols.variables[name]

        if tag == 'ARRAY_ID' and var['type'] == 'VAR':
            raise Exception(f"Błąd w linii {lineno}: Niewłaściwe użycie zmiennej '{name}' jako tablicy")

        if tag == 'ARRAY_ID':
            index_node = id_node[2]
            if index_node[0] == 'NUM':
                idx_val = int(index_node[1])
                if idx_val < var['first'] or idx_val > var['last']:
                    raise Exception(f"Błąd w linii {lineno}: Indeks {idx_val} poza zakresem tablicy {name}({var['first']}:{var['last']})")

        var = self.symbols.variables[name]

        if tag == 'ID':
            if var.get('is_param', False):
                self.emit(f"LOAD {var['address']}")
                self.emit("SWP b")
            else:
                self.generate_constant(var['address'])
                self.emit("SWP b")
        
        elif tag == 'ARRAY_ID':
            index_node = id_node[2]
            self.generate_array_address_to_rb(name, index_node)

    def generate_array_address_to_rb(self, name, index_node):
        var = self.symbols.variables[name]
        
        if var.get('is_param', False):
            self.emit(f"LOAD {var['address']}")
        else:
            self.generate_constant(var['offset'])
        
        self.emit("SWP h") # rh = offset

        if isinstance(index_node, int):
            self.generate_constant(index_node)
        elif index_node[0] == 'NUM':
            self.generate_constant(int(index_node[1]))
        else:
            self.walk(index_node) 
            
        self.emit("SWP b")
        self.emit("SWP h") 
        self.emit("ADD b") 
        self.emit("SWP b") 

    def walk_condition(self, node):
            # node: ('CONDITION', rel_op, left_val, right_val, lineno)
            rel_op = node[1]
            left = node[2]
            right = node[3]

            t1 = self.symbols.get_address("__tmp1", 0)
            t2 = self.symbols.get_address("__tmp2", 0)

            self.walk(right)
            self.emit(f"STORE {t1}")
            self.walk(left)
            self.emit(f"STORE {t2}")

            if rel_op == '=':
                # (a-b) + (b-a).
                self.emit(f"LOAD {t2}")
                self.emit("SWP b")
                self.emit(f"LOAD {t1}")
                self.emit("SUB b")
                self.emit("SWP c") 
                self.emit(f"LOAD {t1}")
                self.emit("SWP b"); 
                self.emit(f"LOAD {t2}")
                self.emit("SUB b")
                self.emit("ADD c") 
                self.emit("SWP c")
                self.emit("RST a")
                self.emit("INC a")
                self.emit("SUB c")

            elif rel_op == '!=':
                # |a-b|. Jeśli > 0 -> różne
                self.emit(f"LOAD {t2}")
                self.emit("SWP b")
                self.emit(f"LOAD {t1}")
                self.emit("SUB b")
                self.emit("SWP c")
                self.emit(f"LOAD {t1}")
                self.emit("SWP b")
                self.emit(f"LOAD {t2}")
                self.emit("SUB b")
                self.emit("ADD c") 

            elif rel_op == '<':
                # Prawda gdy b - a > 0
                self.emit(f"LOAD {t2}")
                self.emit("SWP b")
                self.emit(f"LOAD {t1}")
                self.emit("SUB b")

            elif rel_op == '>':
                # Prawda gdy a - b > 0
                self.emit(f"LOAD {t1}")
                self.emit("SWP b")
                self.emit(f"LOAD {t2}")
                self.emit("SUB b")

            elif rel_op == '<=':
                # Prawda gdy a - b == 0 -> (1 - (a - b))
                self.emit(f"LOAD {t1}")
                self.emit("SWP b")
                self.emit(f"LOAD {t2}")
                self.emit("SUB b")
                self.emit("SWP c")
                self.emit("RST a")
                self.emit("INC a") 
                self.emit("SUB c")

            elif rel_op == '>=': # GE (a >= b)
                # Prawda gdy b - a == 0 -> (1 - (b - a))
                self.emit(f"LOAD {t2}")
                self.emit("SWP b")
                self.emit(f"LOAD {t1}")
                self.emit("SUB b")
                self.emit("SWP c")
                self.emit("RST a") 
                self.emit("INC a") 
                self.emit("SUB c")

    def walk_call(self, node):
        # node: ('CALL', name, args, lineno)
        name = node[1]
        args = node[2]
        lineno = node[3]
    
        if name not in self.symbols.procedures:
            raise Exception(f"Błąd w linii {lineno}: Nieznana procedura {name}")

        proc_info = self.symbols.procedures[name]

        if len(args) != len(proc_info['params']):
            raise Exception(f"Błąd w linii {lineno}: Procedura {name} oczekuje {len(proc_info['params'])} parametrów, podano {len(args)}")
        
        for i, (arg_name, arg_line) in enumerate(args):

            source_var = self.symbols.variables.get(arg_name)
            if not source_var:
                raise Exception(f"Błąd w linii {arg_line}: Użycie niezadeklarowanej zmiennej {arg_name}")
            
            source_p_type = source_var.get('p_type') 
            param_spec = proc_info['params'][i] 
            target_p_type = param_spec[0]
            param_name = param_spec[1]

            if target_p_type == 'I':
                if not source_var.get('initialized', False):
                    raise Exception(f"Błąd w linii {arg_line}: Próba przekazania niezainicjalizowanej zmiennej '{arg_name}' jako wejście 'I'")
            
            if source_p_type == 'I' and target_p_type != 'I':
                raise Exception(f"Błąd w linii {arg_line}: Parametr 'I' ({arg_name}) nie może trafić do modyfikowalnego celu")

            if source_p_type == 'O' and target_p_type == 'I':
                raise Exception(f"Błąd w linii {arg_line}: Parametr 'O' ({arg_name}) nie może być użyty jako wejście 'I'")

            if target_p_type == 'T' and source_var.get('type') != 'ARRAY':
                raise Exception(f"Błąd w linii {arg_line}: Oczekiwano tablicy dla {param_name}")
            
            if target_p_type != 'T' and source_var.get('type') == 'ARRAY':
                raise Exception(f"Błąd w linii {arg_line}: Nie można przekazać tablicy jako skalar")
            
            if target_p_type == 'T':
                self.generate_constant(source_var['offset'])
            else:
                self.generate_address_to_rb(('ID', arg_name, arg_line))
                self.emit("SWP b")      

            param_addr = proc_info['locals'][param_name]['address']
            
            self.emit(f"STORE {param_addr}")

            if target_p_type != 'I':
                source_var['initialized'] = True

        self.calls_to_patch.append((len(self.instructions), name))
        self.emit("CALL placeholder")

    def walk_procedure(self, node):
        #('PROCEDURE', (name, params), decls, cmds, lineno)
        name, params = node[1]

        self.symbols.procedures[name]['params'] = params

        self.symbols.current_scope = name
        self.symbols.procedures[name]['start_address'] = len(self.instructions)

        ret_ptr = self.symbols.procedures[name]['return_address_ptr']
        self.emit(f"STORE {ret_ptr}")

        for d in node[2]: 
            d_tag = d[0]
            if d_tag == 'VAR':
                self.symbols.declare_variable(d[1], d[2])
            elif d_tag == 'ARRAY':
                self.symbols.declare_array(d[1], int(d[2]), int(d[3]), d[4])

        for cmd in node[3]:
            self.walk(cmd)

        self.emit(f"LOAD {ret_ptr}") 
        self.emit("RTRN")
        self.symbols.current_scope = "MAIN"
