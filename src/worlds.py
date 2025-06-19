import jsonpickle
from sim_objects import SimObject, Body, ForceElement, Constraint, Connection, Joint
import random


def count_up():
    n = 0
    while True:
        yield f"#{str(n).zfill(4)}"
        n += 1


counter = count_up()

terms = ["dense", "angled", "spring", "rotational", "linear", "fixed", "dynamic", "static",
         "frictionless", "elastic", "rigid", "flexible", "compliant", "inertial", "non-inertial",
         "gravitational", "electromagnetic", "hydraulic", "pneumatic", "thermal", "acoustic"]


def create_random_parameters(n: int, random_generator: random.Random) -> list[str | float | int]:
    return list(map(lambda n: random_generator.randint(1, 10) if n == 0 else (.5 - random_generator.random()) * 5 if n == 1 else random_generator.choice(terms), [random_generator.randint(0, 2) for _ in range(n)]))


def create_random_connection(first: Body, second: Body, n_par, random_generator: random.Random) -> SimObject:
    connection_class = random_generator.choice(
        [ForceElement, Constraint, Connection, Joint])
    parameters = create_random_parameters(n_par, random_generator)
    return connection_class(obj_id=next(counter), parameters=parameters, connected_objects=[first, second])


def create_random_body(n_par: int, random_generator: random.Random) -> Body:
    parameters = create_random_parameters(n_par, random_generator)
    return Body(obj_id=next(counter), parameters=parameters)


def create_example_world(n_body: int = 10, n_con: int = 3, n_par: int = 10, seed: int | None = None) -> list[SimObject]:
    random_generator = random.Random(seed) if seed is not None else random.Random()
    items: list[Body] = [create_random_body(n_par, random_generator)
                         for _ in range(n_body)]
    connections: list[SimObject] = []
    for idx, body in enumerate(items):
        if idx % 2 == 0:
            continue
        connects = list(random_generator.sample(items, k=n_con))
        if body in connects:
            connects.remove(body)
        for con in connects:
            connections.append(create_random_connection(
                body, con, n_par, random_generator))
    return items + connections


def save_as_json(world: list[SimObject], filename: str) -> None:
    """
    Save the world as a JSON string using jsonpickle.
    """
    with open(filename, "w+") as f:
        f.write(str(jsonpickle.encode(world, indent=2)))


def load_from_json(filename: str) -> list[SimObject]:
    """
    Load the world from a JSON file using jsonpickle.
    """
    with open(filename, "r") as f:
        json_data = f.read()
    world = jsonpickle.decode(json_data)
    if not isinstance(world, list) or not all(isinstance(obj, SimObject) for obj in world):
        raise ValueError("Invalid world data loaded from JSON.")
    return world
