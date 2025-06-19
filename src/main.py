import argparse

def perform_query(args):
    from worlds import load_from_json
    from parser import Solver
    import jsonpickle

    world = load_from_json(args.file)
    solver = Solver(world)
    if args.query:
        results = solver.solve(args.query)
        with open(args.output, "w+") as f:
            f.write(str(jsonpickle.encode(
                {args.query: results}, indent=2)))
    elif args.input:
        results = {}
        with open(args.input, "r") as f:
            for line in f:
                new_query = line.strip()
                if not new_query:
                    continue
                try:
                    result = solver.solve(new_query)
                    results[new_query] = result
                except Exception as e:
                    print(f"Error processing query '{new_query}': {e}")
        with open(args.output, "w+") as f:
            f.write(str(jsonpickle.encode(results, indent=2)))

def perform_interactive(args):
    from parser import Solver
    from worlds import load_from_json
    
    world = load_from_json(args.file)
    solver = Solver(world)
    print("Solver loaded. Enter a query. Type 'exit' or 'quit' to exit.")
    while True:
        try:
            query = input("> ")
            if query.lower() in ['exit', 'quit']:
                break
            results = solver.solve(query)
            print(f"\nResults: {results}\n")
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="CLI for querying a SimObject dataset using PL1 logic.")
    subparsers = parser.add_subparsers(dest='mode', required=True)

    # Query mode
    query = subparsers.add_parser(
        'query', help='Query a dataset with a formula and save the results to disk.')
    query.add_argument('-f', "--file", type=str, required=True,
                       help='Path to the dataset file.')
    query.add_argument('-o', "--output", type=str, required=True,
                       help='Path to save the results of the query, in JSON format.')
    query_group = query.add_mutually_exclusive_group(required=True)
    query_group.add_argument('-q', "--query", type=str,
                             help='The PL1 to query the dataset with.')
    query_group.add_argument('-i', "--input", type=str,
                             help='Path to a file containing a PL1 query on each line.')
    # interactive mode
    interactive = subparsers.add_parser(
        'interactive', help='Enter an interactive mode to query a dataset.')
    interactive.add_argument('-f', "--file", type=str,
                             required=True, help='Path to the dataset file.')
    # generate mode
    generate = subparsers.add_parser(
        'generate', help='Generate a random dataset and save it to disk.')
    generate.add_argument("-o", "--output", type=str, required=True,
                          help='Path to save the generated dataset.')
    generate.add_argument("--n_body", type=int, default=10,
                          help='Number of bodies to generate in the dataset.')
    generate.add_argument("--n_con", type=int, default=3,
                          help='Number of average connections between to generate in the dataset.')
    generate.add_argument("--n_par", type=int, default=10,
                          help='Number of parameters to generate for each object in the dataset.')
    generate.add_argument("--seed", type=int, default=42,
                          help='Seed for the random number generator.')

    args = parser.parse_args()
    if args.mode == 'query':
        perform_query(args)
    elif args.mode == 'interactive':
        perform_interactive(args)
    elif args.mode == 'generate':
        from worlds import create_example_world, save_as_json
        world = create_example_world(
            n_body=args.n_body, n_con=args.n_con, n_par=args.n_par, seed=args.seed)
        save_as_json(world, args.output)


if __name__ == "__main__":
    main()
