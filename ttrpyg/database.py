import json
import os
from functools import reduce
import re

from tinydb import TinyDB, where, Query

import ttrpyg.my_types as ty
import ttrpyg.text as tx
import ttrpyg.dice_utils as du


class DB(TinyDB):
    def __init__(self, input_path: str = "./source", output_path: str = "db.json"):
        super().__init__(output_path)
        self.input_path = input_path
        self.output_path = output_path
        self._create_tinydb(input_path, output_path)

    def _create_tinydb(
        self, input_path: str = "./source", output_path: str = "db.json"
    ):
        """This function creates a flattened TinyDB db.
        !!! You should NOT write to this db !!!
        !!! The db is overwritten every time the function is run !!!
        The db does not preserve any hierarchy or table information.
        The function creates a db that is meant to be used only for querying, code functionality.
        This may be changed in the future.
        """

        def build_db(data):
            for k, v in data.items():
                if "name" in v:
                    v["clean_name"] = tx.get_clean_name(v["name"])
                    self.insert(v)
                else:
                    build_db(v)

        def wrangle_jsons(path: str, aggregated: dict = {}):
            # look into getting a path-type
            if os.path.isdir(path):
                for p in [os.path.join(path, entry) for entry in os.listdir(path)]:
                    aggregated = wrangle_jsons(p, aggregated)
            else:
                with open(path, "r") as f:
                    temp = json.loads(f.read())
                intersection = set(aggregated.keys()) & set(temp.keys())
                if intersection:
                    raise KeyError(f"Duplicate Key(s): {intersection}")
                aggregated = {**aggregated, **temp}
            return aggregated

        def get_expanded_outcomes(table: ty.Table):
            expanded_outcomes = {}
            for k, v in table["outcomes"].items():
                if (
                    type(k) == str
                    and (match_k := re.search(r"(\d*)-(\d*)", k)) is not None
                ):
                    start, end = match_k.groups()
                    for new_k in range(int(start), int(end) + 1):
                        expanded_outcomes[int(new_k)] = v
                else:
                    expanded_outcomes[int(k)] = v
            table["expanded_outcomes"] = expanded_outcomes
            return table

        if os.path.exists(output_path):
            os.remove(output_path)
        build_db(wrangle_jsons(input_path))

        for doc in self.all():
            if "table" in doc.keys():
                table = get_expanded_outcomes(doc["table"])
                self.update({"table": table}, doc_ids=[doc.doc_id])
                if "roll" not in doc["table"].keys():
                    table["roll"] = "1d" + str(max(table["expanded_outcomes"].keys()))
                    self.update({"table": table}, doc_ids=[doc.doc_id])
        return self

    # parsers! doesnt use the tinydb features

    def single_curly_parser(
        self,
        text: str,
        expand_entities: bool = False,
        roll_dice: bool = False,
    ) -> str:
        if not (text.startswith("{") and text.endswith("}")):
            text = "{" + text + "}"
        curlies_parsed = tx.parse_curlies(text)
        assert len(curlies_parsed) == 1
        base_curly = curlies_parsed[0]
        # case when only die roll is present
        if not base_curly["entity"]:
            return str(du.die_parser_roller(base_curly["quantity_dice"]))
        # all other cases
        return self.generate_entity_tree_text(base_curly, expand_entities, roll_dice)

    # tinydb querying

    def fetch_by_name(self, name: str):
        """Fetches an entity by name by first converting it to clean_name.
        As a result, passing a clean_name is fine too.
        This function should not change even if the db does.
        """
        # I really dont love this. Wish TinyDB let me set an index.
        result = self.search(where("clean_name") == tx.get_clean_name(name))
        assert len(result) == 1
        return result[0]

    def get_unique_array_field_values(self):
        unique_field_values = {}  # {..., "FIELDNAME": set()}
        for doc in self.all():
            for k, v in doc.items():
                if isinstance(v, list):
                    if k not in unique_field_values:
                        unique_field_values[k] = set()
                    for i in v:
                        unique_field_values[k].add(i)
        for k, v in unique_field_values.items():
            unique_field_values[k] = list(sorted(v))
        return unique_field_values

    def filter_entities(self, fields: list, params: list[list | str]):
        query = Query()
        assert len(fields) == len(params)
        field = fields[0]
        param = params[0]

        if len(fields) == 1:
            if isinstance(param, str):
                return self.search(query[field] == param)
            else:
                return self.search(query[field].all(param))

        if isinstance(param, str):
            final_query = query[field] == param
        else:
            final_query = query[field].all(param)

        for field, param in zip(fields[1:], params[1:]):
            if isinstance(param, str):
                condition = query[field] == param
            else:
                condition = query[field].all(param)
            final_query = final_query & condition

        # Use the final_query to search the database
        return self.search(final_query)

    # entity tree related stuff

    @staticmethod
    def get_replacement_text(
        base_text: str,
        curlies_parsed: list,
    ) -> str:
        for i, curly_match in enumerate(curlies_parsed):
            if curly_match["quantity"] == 0:
                base_text = base_text.replace(curly_match["match"], "", 1)
            else:
                base_text = base_text.replace(
                    curly_match["match"],
                    f"""{curly_match['quantity']} {curly_match['entity']}""".strip(),
                    1,
                )
        return base_text

    def generate_entity_tree_and_non_unique(
        self,
        base_curly: ty.Curly,
        expand_entities: bool = False,
        roll_dice: bool = False,
        html_characters: bool = False,
    ) -> tuple[ty.EntityTree, ty.NonUniqueEntities]:
        non_unique_entities = ty.NonUniqueEntities({})
        entity_tree = ty.EntityTree([])
        curly_queue = [[base_curly] * base_curly["quantity"]]
        while len(curly_queue) != 0 and len(entity_tree) < 100:
            # TODO: looking back up the tree to not recurse
            curlies = curly_queue.pop(0)
            parent_id = len(entity_tree) - 1
            for curly in curlies:  # note that this single element is a list of curlies
                # skips case where the curly is just a roll.
                if not curly["entity"]:
                    continue
                # uniqueness testing
                entity = self.fetch_by_name(curly["entity"])
                has_table = "table" in entity.keys()
                entity_text = tx.generate_entity_text(
                    entity,
                    text_type="md",
                    html_characters=html_characters,
                    skip_table=roll_dice,
                    # if we are rolling dice, then we dont want the whole table, instead we just handle the result of the table!
                )
                if roll_dice and has_table:  # now we handle that table we skipped!
                    entity_text += (
                        f"Table Result:  \n" + du.roll_on_table(entity, curly) + "\n"
                    )
                curlies_parsed = tx.parse_curlies(entity_text)
                if any(
                    [inner_curly["quantity_dice"] for inner_curly in curlies_parsed]
                ) or (has_table and roll_dice):
                    unique = True
                else:
                    unique = False
                    # this uniqueness detection is not perfect!
                    # two entities could end up rolling the same dice and/or have the same table result, so they would be identical, but both counted as "unique"
                    # "uniqueness" here is an anticipation of inherent randomness/randomization, its not a guarantee of not-being-identical!
                # deals with case where this is not unique...
                if not unique:
                    # ... and we have seen it before:
                    if curly["entity"] in non_unique_entities.keys():
                        non_unique_entities[curly["entity"]]["count"] += 1
                    # ... and we haven't seen it before:
                    else:
                        non_unique_entities[curly["entity"]] = {
                            "text": entity_text,
                            "count": 1,
                        }
                    entity_text = ""
                if roll_dice:
                    entity_text = self.get_replacement_text(
                        base_text=entity_text, curlies_parsed=curlies_parsed
                    )
                    for curly in curlies_parsed:
                        if not curly["entity"] or curly["quantity"] == 0:
                            pass
                        else:
                            curly_queue += [[curly] * curly["quantity"]]
                else:
                    curly_queue.append(tx.parse_curlies(entity_text))
                if parent_id >= 0:
                    entity_tree[parent_id]["children"].append(len(entity_tree) - 1)
                entity_tree.append(
                    ty.TreeEntry(
                        {
                            "id": len(entity_tree),
                            "entity": curly["entity"],
                            "children": [],
                            "unique": unique,
                            "text": entity_text,
                            "curly": curly,
                        }
                    )
                )
        return entity_tree, non_unique_entities

    def generate_entity_tree_text(
        self,
        base_curly: ty.Curly,
        expand_entities: bool = False,
        roll_dice: bool = False,
        html_characters: bool = False,
    ) -> str:
        def text_has_children(text: str) -> bool:
            return any([curly["entity"] for curly in tx.parse_curlies(text)])

        base_quantity = base_curly["quantity"]
        # just need this line for the fancy name:
        base_entity = self.fetch_by_name(base_curly["entity"])
        base_entity_text = tx.generate_entity_text(
            base_entity, html_characters=html_characters
        )
        if not expand_entities or not text_has_children(base_entity_text):
            if roll_dice:
                n_base_entity = str(base_quantity) + " " + base_entity["name"] + "  \n"
                curlies_parsed = tx.parse_curlies(base_entity_text)
                return n_base_entity + self.get_replacement_text(
                    base_text=base_entity_text, curlies_parsed=curlies_parsed
                )
            else:
                return base_entity_text
        entity_tree, non_unique_entities = self.generate_entity_tree_and_non_unique(
            base_curly, expand_entities, roll_dice
        )
        if not len(non_unique_entities) == 0:
            non_unique_text = """### Non Unique Entities:\n"""
            for clean_name, v in non_unique_entities.items():
                non_unique_text += f"\n{v['count']} {clean_name}  \n\n{v['text']}"
        else:
            non_unique_text = ""
        entity_text = """### Unique Entities, Full Tree:\n"""
        for n in entity_tree:
            if n["unique"]:
                entity_text += "\n" + n["text"]
        return (non_unique_text + "\n" + entity_text).strip()

    # docs

    def create_query_text_section(
        self,
        query=None,  # how do i type this
        text_type="md",  # enum "md" or "latex"
        # basic: bool = False,  # im lazy.
        sort: bool = True,
        deprecated: bool = False,
        html_characters: bool = False,
        include_full_text: bool = True,
        skip_table: bool = False,
    ) -> str:
        """!!! NOTICE: You probably need to set a non-default input_path when creating the db that you want to generate docs with !!!"""
        if query is None:
            query = Query()
        if text_type not in ["md", "latex"]:
            raise ValueError("text_type must be 'md' or 'latex'")
        if not deprecated:
            query = query & ~Query().meta_tags.any("deprecated")
        # db = dt.DB(input_path)
        # if basic:
        #     query = query & Query().meta_tags.any("basic")
        results = self.search(query)
        if sort:
            results = sorted(results, key=lambda x: x["name"])
        text = ""
        for e in results:
            text += (
                tx.generate_entity_text(
                    e, text_type, html_characters, include_full_text, skip_table
                )
                + "\n"
            )
        return text
