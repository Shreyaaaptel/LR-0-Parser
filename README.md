# LR(0) Parser

This repository contains an implementation of an LR(0) parser in Python. The parser constructs an LR(0) parse table for a given context-free grammar (CFG) and parses input strings based on that table.

## Features

- **Grammar Handling**: Supports addition of productions and classification of terminals and non-terminals.
- **FIRST and FOLLOW Set Computation**: Automatically computes FIRST and FOLLOW sets for grammar symbols.
- **LR(0) Item Sets and Transitions**: Constructs the canonical LR(0) item sets and calculates the required transitions.
- **Parsing Table Generation**: Builds the shift-reduce parsing table for an LR(0) parser.
- **Error Recovery**: Attempts to recover from syntax errors by resynchronizing the parser.
- **Parsing Steps Logging**: Saves detailed parsing steps to a file, including actions taken at each step.

## Code Structure

- **Grammar**: Manages grammar productions, terminals, non-terminals, and computes FIRST and FOLLOW sets.
- **State**: Represents individual LR(0) states with items, transitions, and parsing actions.
- **Item**: Represents a single LR(0) item in the parser.
- **LRParser**: Main class to manage the entire LR(0) parsing process, build item sets, construct the parsing table, and handle parsing and error recovery.

## Usage

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/LR0-Parser.git
   cd LR0-Parser
2. Define Grammar: Define the grammar by adding productions using the `add_production` method.
3. Parse Input: Use the `save_parsing_steps` function to parse an input string and save the parsing steps.

## Example
Here is an example of defining a grammar, building the parsing table, and parsing an input string.
```python
  from lr0_parser import Grammar, LRParser
  
  # Define a grammar
  grammar = Grammar()
  grammar.add_production('E', ['E', '+', 'T'])
  grammar.add_production('E', ['T'])
  grammar.add_production('T', ['T', '*', 'F'])
  grammar.add_production('T', ['F'])
  grammar.add_production('F', ['(', 'E', ')'])
  grammar.add_production('F', ['id'])
  
  # Create the parser
  parser = LRParser(grammar)
  
  # Parse a string
  parser.save_parsing_steps('parsing_steps.txt', 'id+id*id')
```

## Output Files
- **lr0_item_sets.txt**: Contains all the LR(0) item sets with their transitions.
- **parse_table.txt**: The LR(0) parsing table with shift, reduce, and accept actions.
- **parsing_steps.txt**: Detailed parsing steps for an input string, including stack changes and actions.

## Error Handling
The parser includes a basic error recovery mechanism to handle syntax errors. In case of an unexpected token, it tries to resynchronize by skipping to the nearest follow set symbol.
