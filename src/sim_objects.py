from abc import ABC, abstractmethod
from dataclasses import dataclass, field, InitVar
from typing import Optional, Union
from collections import deque
from itertools import cycle
import random

from wuggy import WuggyGenerator
g = WuggyGenerator()
g.load("orthographic_english")
names = g.generate_classic(["object", "force", "constraint", "connection", "joint"], ncandidates_per_sequence=5)
random.seed(42)
random.shuffle(names)
names = cycle(names)
types = g.generate_classic(["screw", "part", "spring", "grease", "gear"], ncandidates_per_sequence=5)
random.seed(42)
random.shuffle(types)
types = cycle(types)

@dataclass(kw_only=True)
class SimObject(ABC):
    """
    Abstract base class for all simulation objects.
    """
    obj_id: str
    name: str = field(default_factory=lambda: str(next(names, {"pseudoword": "Object"})["pseudoword"]))
    object_type: str = field(default_factory=lambda: str(next(types, {"pseudoword": "Object"})["pseudoword"]))
    parameters: list[str | int | float] = field(default_factory=list)
    connections: list[str] = field(default_factory=list, init=False)
    connected_objects: InitVar[list[Union[str, "SimObject"]] | None] = None
    
    def __post_init__(self, connected_objects):
        if not isinstance(self.parameters, list):
            raise TypeError("Parameters must be a list.")
        if connected_objects and (not isinstance(connected_objects, list)):
            raise TypeError("Connected objects must be a list.")
        deque(map(lambda x: self.connect(x), connected_objects or list()))

    def get_param(self, index: int) -> Optional[str | int | float]:
        """
        Get a parameter by its index.

        :param index: Index of the parameter to retrieve.
        :return: The parameter at the specified index or None if the index is out of range.
        """
        return self.parameters[index] if 0 <= index < len(self.parameters) else None

    @abstractmethod
    def get_object_class(self) -> str:
        """
        Returns the class of the SimObject.
        """
        pass

    def connect(self, other: Union[str, 'SimObject']):
        """
        Connect this object to another SimObject. Ensures that both objects are aware of the connection.

        :param other: The SimObject to connect to. Alternatively, a string representing the object ID. In this case, the object must already be in the connected_objects list.
        :raises ValueError: If trying to connect an object to itself.
        """
        if isinstance(other, str):
            if other not in self.connections:
                self.connections.append(other)
            return
        if other is self:
            raise ValueError("Cannot connect an object to itself.")
        if other.obj_id not in self.connections:
            self.connections.append(other.obj_id)
        if self.obj_id not in other.connections:
            other.connections.append(self.obj_id)


@dataclass(kw_only=True)
class Body(SimObject):
    def get_object_class(self):
        return "Body"


@dataclass(kw_only=True)
class ForceElement(SimObject):
    def get_object_class(self):
        return "ForceElement"
    
@dataclass(kw_only=True)
class Constraint(SimObject):
    def get_object_class(self):
        return "Constraint"
    
@dataclass(kw_only=True)
class Connection(SimObject):
    def get_object_class(self):
        return "Connection"
    
@dataclass(kw_only=True)
class Joint(SimObject):
    def get_object_class(self):
        return "Joint"