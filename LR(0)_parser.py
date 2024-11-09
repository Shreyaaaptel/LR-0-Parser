class Grammar:
    def __init__(self):
        self.productions = {}
        self.symbols = set()
        self.terminals = set()
        self.nonterminals = set()
        self.start_symbol = None
        self.production_list = []

    def add_production(self, lhs, rhs):
        if not self.start_symbol:
            self.start_symbol = lhs
        if lhs not in self.productions:
            self.productions[lhs] = []
        self.productions[lhs].append(tuple(rhs))
        self.production_list.append((lhs, tuple(rhs)))
        self.nonterminals.add(lhs)
        self.symbols.add(lhs)
        for symbol in rhs:
            self.symbols.add(symbol)
    
    def compute_terminals(self):
        self.terminals.clear()
        for symbol in self.symbols:
            if symbol not in self.nonterminals:
                self.terminals.add(symbol)

class State:
    def __init__(self, items):
        self.items = frozenset(items)
        self.transitions = {}  # symbol -> state_id
        self.actions = {}      # terminal -> (action, value)

    def __eq__(self, other):
        return self.items == other.items

    def __hash__(self):
        return hash(self.items)

    def add_transition(self, symbol, state_id):
        self.transitions[symbol] = state_id

    def add_action(self, symbol, action_pair):
        self.actions[symbol] = action_pair

class Item:
    def __init__(self, lhs, rhs, dot_pos, prod_id):
        self.lhs = lhs
        self.rhs = tuple(rhs)
        self.dot_pos = dot_pos
        self.prod_id = prod_id

    def __eq__(self, other):
        return (self.lhs == other.lhs and
                self.rhs == other.rhs and
                self.dot_pos == other.dot_pos)

    def __hash__(self):
        return hash((self.lhs, self.rhs, self.dot_pos))

    def is_complete(self):
        return self.dot_pos == len(self.rhs)

    def next_symbol(self):
        return self.rhs[self.dot_pos] if self.dot_pos < len(self.rhs) else None

    def advance(self):
        return Item(self.lhs, self.rhs, self.dot_pos + 1, self.prod_id)

    def to_string(self):
        rhs_with_dot = list(self.rhs)
        rhs_with_dot.insert(self.dot_pos, '•')
        return f"{self.lhs} -> {' '.join(rhs_with_dot)}"

class LRParser:
    def __init__(self, grammar=None):
        self.grammar = grammar if grammar else Grammar()
        self.original_productions = list(self.grammar.production_list)
        self.states = []
        self.follow_sets = {}
        self.first_sets = {}

        self._compute_first_sets()
        self._compute_follow_sets()
        self.build_parsing_table()
        self.save_item_sets()
        self.save_parse_table()

    def _compute_first_sets(self):
        self.first_sets = {symbol: set() for symbol in self.grammar.symbols}
        for terminal in self.grammar.terminals:
            self.first_sets[terminal] = {terminal}
            
        while True:
            changes = False
            for lhs, rhs_list in self.grammar.productions.items():
                for rhs in rhs_list:
                    if not rhs:  # Handle epsilon productions
                        if '' not in self.first_sets[lhs]:
                            self.first_sets[lhs].add('')
                            changes = True
                        continue
                        
                    # For each symbol in RHS, add its FIRST set to LHS's FIRST set
                    first_sym = rhs[0]
                    if first_sym in self.first_sets:
                        for symbol in self.first_sets[first_sym] - {''}:
                            if symbol not in self.first_sets[lhs]:
                                self.first_sets[lhs].add(symbol)
                                changes = True
            
            if not changes:
                break
                
    def _compute_follow_sets(self):
        self.follow_sets = {nt: set() for nt in self.grammar.nonterminals}
        self.follow_sets[self.grammar.start_symbol].add('$')
        
        while True:
            changes = False
            for lhs, rhs_list in self.grammar.productions.items():
                for rhs in rhs_list:
                    for i, symbol in enumerate(rhs):
                        if symbol in self.grammar.nonterminals:
                            remaining = rhs[i+1:]
                            if remaining:
                                first_of_remaining = self._get_first_of_sequence(remaining)
                                for first_sym in first_of_remaining - {''}:
                                    if first_sym not in self.follow_sets[symbol]:
                                        self.follow_sets[symbol].add(first_sym)
                                        changes = True
                            if not remaining or '' in self._get_first_of_sequence(remaining):
                                for follow_sym in self.follow_sets[lhs]:
                                    if follow_sym not in self.follow_sets[symbol]:
                                        self.follow_sets[symbol].add(follow_sym)
                                        changes = True
            
            if not changes:
                break

    def _get_first_of_sequence(self, sequence):
        if not sequence:
            return {''}
            
        first_set = set()
        all_can_be_empty = True
        
        for symbol in sequence:
            if symbol not in self.first_sets:
                return {symbol}
                
            symbol_first = self.first_sets[symbol]
            first_set.update(symbol_first - {''})
            
            if '' not in symbol_first:
                all_can_be_empty = False
                break
                
        if all_can_be_empty:
            first_set.add('')
            
        return first_set

    def error_recovery(self, state, stack, curr_token, pos, tokens, f):
        if pos >= len(tokens):
            return pos, stack, "Error: Unexpected end of input"
            
        error_message = f"Syntax error at position {pos}, unexpected token: {curr_token}"
        
        current_state = self.states[stack[-1][0]]
        possible_nonterminals = set(current_state.transitions.keys()) & self.grammar.nonterminals
        
        original_stack = stack.copy()
        while stack:
            state_id = stack[-1][0]
            state = self.states[state_id]
            
            for nt in possible_nonterminals:
                follow_symbols = self.follow_sets.get(nt, set())
                
                scan_pos = pos
                while scan_pos < len(tokens):
                    if tokens[scan_pos] in follow_symbols:
                        error_message += f"\nRecovered by synchronizing at '{tokens[scan_pos]}'"
                        return scan_pos, stack, error_message
                    scan_pos += 1
            
            if len(stack) > 1:  
                stack.pop()
            else:
                break
        
        stack = original_stack
        new_pos = pos + 1
        while new_pos < len(tokens):
            curr_token = tokens[new_pos]
            state = self.states[stack[-1][0]]
            if curr_token in state.actions:
                error_message += f"\nSkipped to token '{curr_token}'"
                return new_pos, stack, error_message
            new_pos += 1
        
        return pos + 1, [(0, '$')], error_message + "\nReset to initial state"

    def closure(self, items):
        result = set(items)
        while True:
            new_items = set()
            for item in list(result):
                if not item.is_complete():
                    next_sym = item.next_symbol()
                    if next_sym in self.grammar.nonterminals:
                        for i, (lhs, rhs) in enumerate(self.grammar.production_list):
                            if lhs == next_sym:
                                new_items.add(Item(lhs, rhs, 0, i))
            if not new_items - result:
                break
            result |= new_items
        return frozenset(result)

    def goto(self, state_items, symbol):
        next_items = set()
        for item in state_items:
            if not item.is_complete() and item.next_symbol() == symbol:
                next_items.add(item.advance())
        return self.closure(next_items) if next_items else None

    def build_parsing_table(self):
        augmented_start = f"{self.grammar.start_symbol}'"
        self.grammar.production_list.insert(0, (augmented_start, [self.grammar.start_symbol]))
        self.grammar.productions[augmented_start] = [(self.grammar.start_symbol)]
        
        initial_items = self.closure({Item(augmented_start, [self.grammar.start_symbol], 0, 0)})
        initial_state = State(initial_items)
        self.states = [initial_state]
        
        unprocessed_states = [0]  
        
        while unprocessed_states:
            state_idx = unprocessed_states.pop(0) 
            state = self.states[state_idx]
            
            next_symbols = set()
            for item in state.items:
                if not item.is_complete():
                    next_sym = item.next_symbol()
                    if next_sym:
                        next_symbols.add(next_sym)
            
            ordered_symbols = sorted(next_symbols, 
                                key=lambda x: (x in self.grammar.terminals, x))
            
            for symbol in ordered_symbols:
                next_state_items = self.goto(state.items, symbol)
                if next_state_items:
                    next_state = State(next_state_items)
                    if next_state not in self.states:
                        self.states.append(next_state)
                        unprocessed_states.append(len(self.states) - 1)
                    next_id = self.states.index(next_state)
                    state.add_transition(symbol, next_id)
                    if symbol in self.grammar.terminals:
                        state.add_action(symbol, ('shift', next_id))
            
            for item in state.items:
                if item.is_complete():
                    if item.lhs == augmented_start:
                        state.add_action('$', ('accept', None))
                    else:
                        for terminal in self.grammar.terminals | {'$'}:
                            if terminal not in state.actions:
                                state.add_action(terminal, ('reduce', item.prod_id))
    def save_parse_table(self):
        terminals = sorted(list(self.grammar.terminals)) 
        terminals = terminals + ['$']
        nonterminals = list(self.grammar.nonterminals - {self.grammar.production_list[0][0]}) 
        with open('parse_table.txt', 'w', encoding='utf-8') as f:
            f.write('STATE'.ljust(8))
            
            for terminal in terminals:
                f.write(f'|{terminal.center(8)}')
                
            for nonterminal in nonterminals:
                f.write(f'|{nonterminal.center(8)}')
            f.write('\n')
            f.write('-' * 8)
            f.write('+' + '-' * 8 * (len(terminals) + len(nonterminals)) + '\n')
            
            for i, state in enumerate(self.states):
                f.write(f'{str(i).ljust(8)}')
                
                for terminal in terminals:
                    action = state.actions.get(terminal, ('', ''))
                    cell_content = ''
                    if action[0] == 'shift':
                        cell_content = f's{action[1]}'
                    elif action[0] == 'reduce':
                        cell_content = f'r{action[1]}'
                    elif action[0] == 'accept':
                        cell_content = 'acc'
                    f.write(f'|{cell_content.center(8)}')
                
                for nonterminal in nonterminals:
                    goto = state.transitions.get(nonterminal, '')
                    cell_content = str(goto) if goto != '' else ''
                    f.write(f'|{cell_content.center(8)}')
                f.write('\n')
                f.write('-' * 8)
                f.write('+' + '-' * 8 * (len(terminals) + len(nonterminals)) + '\n')

    def save_item_sets(self):
        with open('lr0_item_sets.txt', 'w', encoding='utf-8') as f:
            f.write("Grammar Productions:\n")
            f.write("-" * 40 + "\n")
            for i, (lhs, rhs) in enumerate(self.grammar.production_list):
                f.write(f"{i}. {lhs} -> {' '.join(rhs)}\n")
            f.write("\n")

            for i, state in enumerate(self.states):
                f.write(f"I{i}:\n")
                f.write("-" * 40 + "\n")
                
                sorted_items = sorted(state.items, key=lambda item: (item.lhs != f"{self.grammar.start_symbol}'", item.prod_id))
                for item in sorted_items:
                    f.write(f"{item.to_string()}\n")

                ordered_transitions = []
                for item in sorted_items:
                    next_symbol = item.next_symbol()
                    if next_symbol and next_symbol in state.transitions and next_symbol not in [t[0] for t in ordered_transitions]:
                        ordered_transitions.append((next_symbol, state.transitions[next_symbol]))

                if ordered_transitions:
                    f.write("\nTransitions:\n")
                    for symbol, next_state in ordered_transitions:
                        f.write(f"goto(I{i},{symbol})=I{next_state}\n")
                f.write("-" * 40 + "\n")
                f.write("\n")

    def save_parsing_steps(self, filename, input_string):
        tokens = list(input_string) + ['$']
        stack = [(0, '$')] 
        pos = 0
        max_steps = len(tokens) * 3  
        step_count = 0
        
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(f"\nParsing of input string: {input_string}\n")
            f.write("-" * 60 + "\n")
            f.write(f"{'Stack'.ljust(25)}{'Input'.ljust(20)}{'Action'.ljust(15)}\n")
            f.write("-" * 60 + "\n")
            
            while pos <= len(tokens) and step_count < max_steps:
                step_count += 1
                
                stack_str = ''.join(f"{sym}{state}" for state, sym in stack)
                input_str = ''.join(tokens[pos:]) if pos < len(tokens) else "$"
                
                if not stack:
                    f.write(f"Error: Empty stack encountered\n")
                    return False
                
                state = self.states[stack[-1][0]]
                
                if pos >= len(tokens):
                    f.write(f"Error: Unexpected end of input\n")
                    return False
                    
                curr_token = tokens[pos]
                
                if curr_token not in state.actions:
                    f.write(f"{stack_str.ljust(25)}{input_str.ljust(20)}{'ERROR'.ljust(15)}\n")
                    try:
                        new_pos, new_stack, error_msg = self.error_recovery(state, stack, curr_token, pos, tokens, f)
                    except Exception as e:
                        f.write(f"Error recovery failed: {str(e)}\n")
                        return False
                    
                    f.write(f"Error Recovery: {error_msg}\n")
                    
                    if new_pos == pos and new_stack == stack:
                        f.write("Unable to recover from error\n")
                        return False
                    
                    pos = new_pos
                    stack = new_stack
                    continue
                
                action, value = state.actions[curr_token]
                
                if action == 'shift':
                    action_str = f"shift {value}"
                elif action == 'reduce':
                    lhs, rhs = self.grammar.production_list[value]
                    action_str = f"reduce {value}"
                elif action == 'accept':
                    action_str = "accept"
                else:
                    action_str = "ERROR"
                
                f.write(f"{stack_str.ljust(25)}{input_str.ljust(20)}{action_str.ljust(15)}\n")
                
                try:
                    if action == 'shift':
                        stack.append((value, curr_token))
                        pos += 1
                    elif action == 'reduce':
                        lhs, rhs = self.grammar.production_list[value]
                        if len(stack) < len(rhs):
                            f.write("Error: Stack underflow during reduction\n")
                            return False
                        for _ in range(len(rhs)):
                            stack.pop()
                        prev_state = self.states[stack[-1][0]]
                        if lhs not in prev_state.transitions:
                            f.write(f"Error: Invalid transition for {lhs}\n")
                            return False
                        next_state = prev_state.transitions[lhs]
                        stack.append((next_state, lhs))
                    elif action == 'accept':
                        f.write("Input accepted!\n")
                        return True
                    else:
                        f.write(f"Error: Invalid action {action}\n")
                        return False
                except Exception as e:
                    f.write(f"Error during parsing: {str(e)}\n")
                    return False
            
            if step_count >= max_steps:
                f.write("Error: Maximum parsing steps exceeded\n")
                return False
            
            return True

    def parse_and_save(self, test_strings, output_file='parsing_steps.txt'):
        try:
            # Clear the file first
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("Grammar Productions:\n")
                f.write("-" * 60 + "\n")
                for i, (lhs, rhs) in enumerate(self.grammar.production_list):
                    f.write(f"{i}. {lhs} -> {' '.join(rhs)}\n")
                f.write("\n")
            
            results = []
            for input_str in test_strings:
                try:
                    result = self.save_parsing_steps(output_file, input_str)
                    results.append((input_str, result))
                except Exception as e:
                    with open(output_file, 'a', encoding='utf-8') as f:
                        f.write(f"\nError parsing {input_str}: {str(e)}\n")
                    results.append((input_str, False))

            with open(output_file, 'a', encoding='utf-8') as f:
                f.write("\nParsing Summary\n")
                f.write("=" * 60 + "\n")
                for input_str, result in results:
                    f.write(f"Input: {input_str}\n")
                    f.write(f"Result: {'Accepted' if result else 'Rejected'}\n")
                    f.write("-" * 60 + "\n")
                    
        except Exception as e:
            print(f"Error during parsing: {str(e)}")
            raise
    
def get_user_grammar():
    print("\nEnter grammar productions in the format: LHS -> RHS")
    print("Use space to separate symbols in RHS")
    print("Enter an empty line to finish input")
    print("Example: S -> a B\n")
    
    grammar = Grammar()
    while True:
        production = input("Enter production (or empty line to finish): ").strip()
        if not production:
            break
        try:
            lhs, rhs = production.split('->')
            lhs = lhs.strip()
            rhs_symbols = [sym.strip() for sym in rhs.strip().split()]
            
            if not lhs or not rhs_symbols:
                print("Invalid production format. Please try again.")
                continue
                
            grammar.add_production(lhs, rhs_symbols)
            print(f"Added production: {lhs} -> {' '.join(rhs_symbols)}")
            
        except ValueError:
            print("Invalid production format. Please use the format: LHS -> RHS")
            continue
    grammar.compute_terminals()
    return grammar

def get_test_strings():
    print("\nEnter strings to test (one per line)")
    print("Enter an empty line to finish input\n")
    
    test_strings = []
    while True:
        test_string = input("Enter test string (or empty line to finish): ").strip()
        if not test_string:
            break
        test_strings.append(test_string)
    
    return test_strings

def main():
    print("Welcome to the LR(0) Parser!")
    print("define your grammar.")
    
    grammar = get_user_grammar()
    
    if not grammar.productions:
        return
    parser = LRParser(grammar)    
    test_strings = get_test_strings()
    
    if not test_strings:
        return
    print("see \"parsing_steps.txt\" for results ;)")
    for input_str in test_strings:
        parser.parse_and_save(test_strings)
if __name__ == "__main__":
    main()
