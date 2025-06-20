# Predicate Query

This project demonstrates a querying system based on the language of first-order predicate logic to find items in a simulation dataset (SimObjects) that have certain properties.

## Installation

This project uses `uv` for dependency management and installation. If you haven't already, install `uv` ([see docs on astral.sh](https://docs.astral.sh/uv/getting-started/installation/)). Then clone this repo:

```bash
git clone https://github.com/Fdpr/predicate-query.git
cd predicate-query
```

Running any `uv` command from inside the project directory should then set up the environment. You can run

```bash
uv sync
```
to test if the install works.

## Usage

run `uv run src/main.py -h` for help.

```
usage: main.py [-h] {query,interactive,generate} ...

CLI for querying a SimObject dataset using PL1 logic.

positional arguments:
  {query,interactive,generate}
    query               Query a dataset with a formula and save the results to disk.
    interactive         Enter an interactive mode to query a dataset.
    generate            Generate a random dataset and save it to disk.

options:
  -h, --help            show this help message and exit
```

### Query mode

In query mode, you can either provide a single query or a batch of queries in an input file. The results are written to the output file as JSON.

```
usage: main.py query [-h] -f FILE -o OUTPUT (-q QUERY | -i INPUT)

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  Path to the dataset file.
  -o OUTPUT, --output OUTPUT
                        Path to save the results of the query, in JSON format.
  -q QUERY, --query QUERY
                        The PL1 to query the dataset with.
  -i INPUT, --input INPUT
                        Path to a file containing a PL1 query on each line.
```

### Interactive mode

In interactive mode, you load a single world model and query it using the command line.

```
usage: main.py interactive [-h] -f FILE

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  Path to the dataset file.
```

### Generate mode

Generate mode can be used to create new test datasets.

```
usage: main.py generate [-h] -o OUTPUT [--n_body N_BODY] [--n_con N_CON] [--n_par N_PAR] [--seed SEED]

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Path to save the generated dataset.
  --n_body N_BODY       Number of bodies to generate in the dataset.
  --n_con N_CON         Number of average connections between to generate in the dataset.
  --n_par N_PAR         Number of parameters to generate for each object in the dataset.
  --seed SEED           Seed for the random number generator.
```

## SimObject

The core dataset used by this project is a collection of simulation objects, managed by the `SimObjects` class (see [sim_objects.py](src/sim_objects.py)). Each SimObject represents an entity or component within a simulation, such as a physical body, force element, constraint, connection, or joint.

The `SimObjects` class is implemented as an abstract base class, so it can be extended to support more types of objects or even allow on-the-fly calculations. Right now, the dataset is assumed to be frozen.

A typical dataset consists of a list of objects, each with fields such as `id`, `type`, `parameters`, and references to other objects (e.g., connections or constraints). The dataset is usually stored in JSON format and can be generated or loaded using the provided CLI tools.

Example (simplified) dataset entry:
```json
{
    "obj_id": "#001",
    "name": "screw-1",
    "type": "screw",
    "parameters": [1.0, 2.0, 3.0],
    "connections": ["joint_1", "joint_2"]
}
```

The `SimObjects` class abstracts these details and provides a unified interface for interacting with all simulation entities in the system.

## Query grammar

The full grammar specification is written in lark syntax and can be found in [grammar.lark](src/grammar.lark). An overview is given here, using adapted EBNF notation:

- `::=` means "is defined as".
- `|` separates alternative choices.
- `"text"` denotes a literal terminal symbol.
- `[...]` denotes an optional group (0 or 1 occurrences).
- `<name>` denotes a non-terminal rule.

### High-Level Structure
The grammar is structured to enforce the standard order of operations in logic: ~ (negation) has the highest precedence, followed by `&` (conjunction), then `|` (disjunction), and finally `->` and `<->` (implication/equivalence) at the lowest precedence.

```
<formula>           ::= <implication>

<implication>       ::= <disjunct> [ ("->" | "<->") <implication> ]

<disjunct>          ::= <conjunct> [ "|" <disjunct> ]

<conjunct>          ::= <negation> [ "&" <conjunct> ]

<negation>          ::= "~" <negation> | <atom>

<atom>              ::= <predicate>
                    |   <quantified_formula>
                    |   "(" <formula> ")"
```
### Quantified Formulas

```
<quantified_formula> ::= ("exists" | "forall") <identifier> ":" <formula>
```
### Predicates
This rule defines all the atomic statements in the language.
```
<predicate>         ::= "Body" "(" <identifier> ")"
                    |   "ForceElement" "(" <identifier> ")"
                    |   "Constraint" "(" <identifier> ")"
                    |   "Connection" "(" <identifier> ")"
                    |   "Joint" "(" <identifier> ")"
                    |   "AreConnected" "(" <identifier> "," <identifier> ")"
                    |   "IsType" "(" <identifier> "," <string> ")"
                    |   "ParamIs" "(" <identifier> "," <integer> "," <literal> ")"
                    |   "ParamLt" "(" <identifier> "," <integer> "," <literal> ")"
                    |   "ParamGt" "(" <identifier> "," <integer> "," <literal> ")"
                    |   <identifier> "=" <identifier>
```
### Literals
A literal is a constant value, such as a number or a string.
```
<literal>           ::= <number> | <string>
```
### Lexical Definitions (Terminals)
These are the basic tokens that a lexer would recognize. They are treated as terminals in the grammar above.
- `<identifier>`: A C-style name, typically matching the regex `[a-zA-Z_][a-zA-Z0-9_]*`. Used for variable names.
- `<integer>`: A sequence of one or more digits `[0-9]+`.
- `<number>`: A signed floating-point or integer number.
- `<string>`: A sequence of characters enclosed in double quotes, e.g., "character".

## How to query
The system is made to find objects that satisfy certain conditions in the dataset. This is why each query must start with a modified existential quantification, written using `find <identifier>: ...`. The identifier given in this root quantification is the object to be searched. All objects that can appear in this quantification to satisfy the formula will be returned by the query. Apart from that, the inner formula can be any combination of connectives according to the grammar. A `find` statement must only appear as the root and not be placed anywhere in the inner formula.

### Examples
Find all ForceElements:
```
exists A: ForceElement(A)
```
Find all Body elements whose second positional parameter is greater than 2:
```
exists A: (Body(A) & ParamGt(A, 1, 2))
```
Find all elements that are connected to at least two other elements:
```
exists A: (exists B: (exists C:(AreConnected(A,B) & AreConnected(B,C) & ~(B=C))))
```

Try it out for yourself! Run: `uv run src/main.py query -f "examples/example_world.json" -o "out/query.json" -q "exists A: (exists B: (exists C:(AreConnected(A,B) & AreConnected(B,C) & ~(B=C))))"`

