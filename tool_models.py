from typing import NamedTuple

class Subject(NamedTuple):
    name : str
    acronym : str
    description : str
    teachers : str
    department : str
    evaluation : str

class Class(NamedTuple):
    name : str
    grupo : str
    dia_semana : str
    inicio : str
    durada : str
    tipo : str
    aula : str
