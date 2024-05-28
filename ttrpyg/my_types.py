from typing import NewType, TypedDict, Union, Optional, Required, Any


class Curly(TypedDict):
    match: str
    quantity_dice: str
    table_dice: str
    entity: str
    quantity: int
    table_result: Union[int, None]


class Table(TypedDict, total=False):
    roll: Optional[str]
    outcomes: dict[Union[int, str], str]  # required
    expanded_outcomes: dict[int, str]


class Entity(TypedDict, total=False):
    attacks: list
    clean_name: str
    cost: str
    effect: str
    encumbrance: str
    flavor_text: str
    holds: str
    hp: str
    meta_tags: list
    name: Required[str]
    requirements: list
    scores: list
    skills: list
    speed: str
    tags: list
    target: str
    to_hit: str
    full_text: str
    table: Table


class Formatting(TypedDict, total=False):
    attacks: dict[str, Any]
    clean_name: dict[str, Any]
    cost: dict[str, Any]
    effect: dict[str, Any]
    encumbrance: dict[str, Any]
    flavor_text: dict[str, Any]
    holds: dict[str, Any]
    hp: dict[str, Any]
    meta_tags: dict[str, Any]
    name: dict[str, Any]
    requirements: dict[str, Any]
    scores: dict[str, Any]
    skills: dict[str, Any]
    speed: dict[str, Any]
    tags: dict[str, Any]
    target: dict[str, Any]
    to_hit: dict[str, Any]
    full_text: dict[str, Any]
    table: dict[str, Any]


Entities = NewType("Entities", dict[str, Entity])


class NonUniqueEntity(TypedDict):
    text: str
    count: int


NonUniqueEntities = NewType("NonUniqueEntities", dict[str, NonUniqueEntity])


class TreeEntry(TypedDict):
    id: int
    entity: str
    children: list[int]
    unique: bool
    text: str
    curly: Curly


EntityTree = NewType("EntityTree", list[TreeEntry])


## The next types are from the old doc-generation workflow which will be removed soon.


class ES(TypedDict, total=False):
    text: str
    clean_name: str
    include_full_text: bool
    fi: str
    fx: str


ESs = NewType("ESs", list[ES])


class Doc(TypedDict, total=False):
    # not used anymore!
    entity_sections: ESs
    front_text: str
    end_text: str
    text_type: str
    html_characters: bool
    skip_feature_generation: bool


class DocPath(TypedDict, total=False):
    doc: Doc
    path: str


DocsToUpdate = NewType("DocsToUpdate", list[DocPath])
