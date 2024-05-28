import os
import re
from copy import deepcopy
from collections.abc import Callable

from pylatex.utils import NoEscape

import ttrpyg.my_types as ty
import ttrpyg.text as tx
import ttrpyg.dice_utils as du

# parsing


def parse_curlies(text: str) -> list[ty.Curly]:
    curlies = re.findall(r"{[^}]*}", text)
    dice_pattern = r"\d*?d\d+x?[+-]?\d*"
    curlies_parsed = []
    if curlies:
        for match in curlies:
            # Check for entity...
            quantity = 1
            if (e := re.search(r"(?<=\s|{)([a-zA-Z_',;:\-()\s]+)", match)) is not None:
                entity = tx.get_clean_name(e.group())
            else:
                entity = ""
            # Check for quantity dice (leading dice)...
            if q := re.search(rf"(?<={{){dice_pattern}", match):
                quantity_dice = q.group()
                quantity = du.die_parser_roller(quantity_dice)
            # Check for number
            else:
                if entity == "":
                    continue
                elif (n := re.search(r"(?<={)\d+(?=\s)", match)) is not None:
                    quantity_dice = ""
                    quantity = int(n.group())
                else:
                    quantity_dice = ""
            if entity and (t := re.search(rf"({dice_pattern})(?=}})", match)):
                table_dice = t.group()
                table_result = du.die_parser_roller(table_dice)
            elif entity and (t := re.search(r"(\d+)(?=})", match)):
                table_dice = ""
                table_result = int(t.group())
            else:
                table_dice = ""
                table_result = None
            curlies_parsed.append(
                ty.Curly(
                    {
                        "match": match,
                        "quantity_dice": quantity_dice,
                        "table_dice": table_dice,
                        "entity": entity,
                        "quantity": quantity,
                        "table_result": table_result,
                    }
                )
            )
    return curlies_parsed


# cleaning


def get_clean_name(name: str) -> str:
    """Returns a name in lowercase with numbers left alone, whitespace stripped, " " and "-" replaced with "_", and every other character removed."""
    return re.sub(
        r"[^a-z0-9_]", "", name.lower().strip().replace(" ", "_").replace("-", "_")
    )


# single entity text generators. used for cli and various utilities.

key_order = [
    "name",
    "clean_name",
    "hp",
    "scores",
    "skills",
    "holds",
    "tags",
    "requirements",
    "cost",
    "speed",
    "target",
    "to_hit",
    "attacks",
    "effect",
    "table",
    "flavor_text",
    "full_text",
    "encumbrance",
    "meta_tags",
]


def generate_entity_text(
    entity: ty.Entity,
    text_type: str = "md",
    html_characters: bool = False,
    include_full_text: bool = False,  # only used by .md right now..
    skip_table: bool = False,  # only used by .md right now..
    # TODO: the latex here is really only for cards... probably it should still be able to handle tables though
) -> str:
    def prep(entity: ty.Entity, text_type: str):
        html_arrow = "&#8658;"
        func_sets = {
            "latex": [
                # removes curlies as they shouldn't show up in latex. they'd have to be escaped for  tex anyhow
                (lambda v: re.sub(r"[{}]", "", v)),
                # escape "_" which will otherwise break the tex
                (lambda v: re.sub(r"([a-z0-9])(_)", r"\1\_", v)),
                # a nicer arrow :)
                (lambda v: re.sub(r"->", "$\\\Rightarrow$", v)),
            ],
            "html": [
                # escape * and _
                (lambda v: re.sub(r"[_]", r"\_", v)),
                (lambda v: re.sub("\*", r"\*", v)),
                # nicer arrow :)
                (lambda v: re.sub(r"->", f"{html_arrow}", v)),
            ],
        }
        for f in func_sets[text_type]:
            for k, v in entity.items():
                if type(v) == list:
                    entity[k] = map(lambda v: f(v), v)  # type: ignore
                elif type(v) == str:
                    entity[k] = f(v)  # type: ignore
        return entity

    def generate_md(
        entity: ty.Entity,
        formatting: ty.Formatting = formatting_dict_md,
        key_order: list = key_order,
    ) -> str:
        result_text = ""
        for k in key_order:
            if k in entity.keys():
                result_text += if_exists_format_md(text=entity[k], **formatting[k])  # type: ignore
        return result_text

    def generate_latex(
        entity: ty.Entity,
        formatting: ty.Formatting = formatting_dict_latex,
        footer: bool = True,
        key_order: list = key_order,
    ) -> str:
        result_text = ""
        for k in key_order:
            if k in entity.keys():
                result_text += if_exists_format_latex(text=entity[k], **formatting[k])  # type: ignore
        if footer and "encumbrance" in entity.keys():
            result_text += rf"""\vfill
            \hfill {"Enc: " + entity["encumbrance"]} 
            """
        return result_text

    entity_local = deepcopy(entity)
    if text_type == "md":
        formatting = deepcopy(formatting_dict_md)
        if not include_full_text:  # UNTESTED
            formatting["full_text"] = {"hide": True}
        if skip_table:
            formatting["table"] = {"hide": True}
        if html_characters:
            entity_local = prep(entity_local, "html")
        return generate_md(entity_local, formatting)
    elif text_type == "latex":
        formatting = deepcopy(formatting_dict_latex)
        if skip_table:
            formatting["table"] = {"hide": True}
        return generate_latex(prep(entity_local, "latex"), formatting)

    else:
        raise Exception("text_type needs to be either 'latex' or 'md'.")


# text formatters

# LATEX

# start of latex formatting section
smallskip = r"\smallskip "
skipline = smallskip + r" \hrule " + smallskip


def curry_wrap(latex: str) -> Callable[[str], str]:  # latex formatting wrapper
    """Sidëf̈ect: sounds delicious."""
    return lambda text: NoEscape("\\" + latex + r"{" + text + r"}")


bold = curry_wrap("textbf")
italic = curry_wrap("textit")
large = curry_wrap("large")
f_note = curry_wrap("footnotesize")
s_cap = curry_wrap("textsc")
t_normal = curry_wrap("textnormal")
emph = curry_wrap("emph")


def tag_latex(
    text: str,
) -> str:
    # havent gotten rid of this one because im not decided on whether ill use it, not using it for now
    return f_note("Tags: " + text) + "\n" + r" \normalsize" + "\n\n"


def attacks_latex(attacks: list) -> str:
    # for some reason they had "," replaced with "\n-" before... why?
    itemized_attacks = ""
    for attack in attacks:
        itemized_attacks += "    \item " + attack + "\n"
    return (
        skipline
        + emph(r"Attacks: ")
        + "\n"
        + r"\begin{itemize}"
        + "\n"
        + rf"{itemized_attacks}"
        + "\n"
        + r"\end{itemize}"
    )


def skill_latex(
    field: list,
) -> str:
    return NoEscape(skipline + ("\n" + r" \medskip" + "\n").join(field))


def footer_latex(clean_name: str, encumbrance: str = ""):
    enc = f_note("Enc: " + encumbrance) if encumbrance else ""
    return rf""" \vfill
    {f_note(clean_name)} \hfill {enc}"""


def format_table_latex(table: ty.Table) -> str:
    text = (
        f"""\n\nRoll {table["roll"]} on this table.\n\n"""
        if "roll" in table.keys()
        else ""
    )
    text += NoEscape(
        r"""\smallskip\begin{center}
\begin{tabularx}{\textwidth}{ | c | X | }"""
    )
    for roll, outcome in table["outcomes"].items():
        text += NoEscape(
            rf"""
\hline
{roll} & {outcome} \\"""
        )
    text += NoEscape(
        r"""
    \hline
\end{tabularx}
\end{center}"""
    )
    return text


# latex entity text generation


def if_exists_format_latex(
    text: str | list = "",
    text_formatter: Callable[[str | list], str] = lambda text: str(text),
    field_text: str = "",
    field_text_formatter: Callable[[str], str] = lambda text: str(text),
    add_newline: bool = True,
    add_skipline: bool = False,
    hide: bool = False,
) -> str:
    if hide or not text:
        return ""
    text = text_formatter(text)
    text = text + " \n \n" if add_newline else text
    text = text + skipline if add_skipline else text
    if field_text:
        text = field_text_formatter(field_text + ":") + " " + text
    return text


formatting_dict_latex: ty.Formatting = {
    "attacks": {"text_formatter": attacks_latex},
    "clean_name": {"hide": True},
    "cost": {
        "field_text": "Cost",
        "field_text_formatter": emph,
        "text_formatter": lambda x: ", ".join(x),
    },
    "effect": {},
    "encumbrance": {"hide": True},
    # need to put this and maybe encumbrance on the footer..
    "meta_tags": {"hide": True},
    "flavor_text": {"text_formatter": lambda text: skipline + italic(text)},
    "holds": {"field_text": "Holds", "field_text_formatter": emph},
    "hp": {"field_text": "HP", "field_text_formatter": emph},
    "name": {"text_formatter": lambda text: NoEscape(bold(large(text)))},
    "requirements": {
        "field_text": "Requirements",
        "field_text_formatter": emph,
        "text_formatter": lambda x: ", ".join(x),
    },
    "scores": {
        "field_text": "Scores",
        "field_text_formatter": emph,
        "text_formatter": lambda x: ", ".join(x),
    },
    "skills": {
        "field_text": "Skills",
        "field_text_formatter": emph,
        "text_formatter": skill_latex,
    },
    "speed": {"field_text": "Speed", "field_text_formatter": emph},
    "tags": {
        "field_text": "Tags",
        "field_text_formatter": emph,
        "text_formatter": lambda x: ", ".join(x),
    },
    "target": {
        "field_text": "Target",
        "field_text_formatter": emph,
    },
    "to_hit": {"field_text": "To-Hit", "field_text_formatter": emph},
    "full_text": {"hide": True},  # TODO: create full_text formatter for latex
    "table": {"text_formatter": format_table_latex},
}

# MARKDOWN


def if_exists_format_md(
    text: str | list,
    text_wrapper: str = "",
    text_formatter: Callable[[str | list], str] = lambda text: str(text),
    field_text: str = "",
    field_text_wrapper: str = "**",  # note that this one is the only one that doesnt default empty
    prefix: str = "",
    add_newline: bool = True,
    hide: bool = False,
) -> str:
    if hide or not text:
        return ""
    a_newline = "  \n" if add_newline else ""
    text = text_formatter(text)
    if field_text:
        text = field_text_wrapper + field_text + ":" + field_text_wrapper + " " + text
    elif prefix:
        text = prefix + text
    return text_wrapper + text + text_wrapper + a_newline


def format_table_md(table: ty.Table) -> str:
    md_table = (
        f"""  \n\nUnless otherwise specified, roll {table["roll"]} on this table."""
        + "\n\n| Roll | Outcome |  \n| --- | --- |"
    )
    for roll, outcome in table["outcomes"].items():
        md_table += "\n" + f"| {roll} | {outcome} |  "
    return md_table + "\n"


def format_full_text_md(text) -> str:
    return text + "  \n\n\n"


formatting_dict_md: ty.Formatting = {
    "attacks": {"text_formatter": lambda x: ", ".join(x)},
    "clean_name": {"hide": True},
    "cost": {"field_text": "Cost", "text_formatter": lambda x: ", ".join(x)},
    "effect": {},
    "encumbrance": {"field_text": "Encumbrance"},
    "flavor_text": {"text_wrapper": "*"},
    "holds": {"field_text": "Holds"},
    "hp": {"field_text": "HP"},
    "meta_tags": {"hide": True},
    "name": {"prefix": "#### "},
    "requirements": {
        "field_text": "Requirements",
        "text_formatter": lambda x: ", ".join(x),
    },
    "scores": {"field_text": "Scores", "text_formatter": lambda x: ", ".join(x)},
    "skills": {"field_text": "Skills", "text_formatter": lambda x: ", ".join(x)},
    "speed": {"field_text": "Speed"},
    "tags": {"field_text": "Tags", "text_formatter": lambda x: ", ".join(x)},
    "target": {"field_text": "Target"},
    "to_hit": {"field_text": "To-Hit"},
    "full_text": {"text_formatter": format_full_text_md},
    "table": {"text_formatter": format_table_md},
}
