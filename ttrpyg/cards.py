import re
import os.path
from pprint import pprint

from pylatex import Document, Command, MiniPage, UnsafeCommand, NewPage
from pylatex.base_classes import Arguments, Options, CommandBase
from pylatex.package import Package
from pylatex.utils import NoEscape

import ttrpyg.my_types as ty
import ttrpyg.text as ge  # test this import
import ttrpyg.database as dt


def generate_cards(
    entities,
    card_type: str = "poker",
    output_filepath: str = os.path.join("output", "cards"),
) -> None:
    cards_per_page = {
        "quarter": 4,
        "tarot": 6,
        "poker": 9,
        "square": 12,
        "double_notecard": 2,
    }
    card_height = {
        "quarter": "130mm",
        "tarot": "110mm",
        "poker": "89mm",
        "square": "64mm",
        "double_notecard": "2.75in",
    }
    card_width = {
        "quarter": "100mm",
        "tarot": "64mm",
        "poker": "64mm",
        "square": "64mm",
        "double_notecard": "2.3in",
    }
    cards_per_row = {
        "quarter": 2,
        "tarot": 3,
        "poker": 3,
        "square": 3,
        "double_notecard": 2,
    }

    if card_type not in cards_per_page.keys():
        raise ValueError("Invalid card type.")

    if card_type == "double_notecard":
        geometry_options = {
            "paperwidth": "5in",
            "paperheight": "3in",
            "top": "0.1in",
            "left": "0.1in",
            "bottom": "0in",
            "right": "0in",
        }
    else:
        geometry_options = {"margin": ".07in"}


    # define the LaTex command to generate a minipage of given dimensions, and populate it with content
    class CardCommand(CommandBase):
        _latex_name = "card"

    if card_type == "double_notecard":
        minipage = (
            NoEscape(r"\begin{minipage}[t][#1][t]{#2} #3 \end{minipage}\hspace{0.1in}"),
        )
    else:
        minipage = (
            NoEscape(r"\fbox{\begin{minipage}[t][#1][t]{#2} #3 \end{minipage}}"),
        )

    card_com = UnsafeCommand(
        "newcommand",
        "\card",
        options=3,
        extra_arguments=minipage,
    )
    entity_texts = []
    for entity in entities:
        if "meta_tags" in entity and "no_card" in entity["meta_tags"]:
            continue
        entity_texts.append(NoEscape(ge.generate_entity_text(entity, "latex")))
    # setup document and generate the preamble
    doc = Document(geometry_options=geometry_options, indent=False)
    doc.append(card_com)
    doc.packages.append(Package("fdsymbol"))
    doc.packages.append(Package("tabularx"))
    for count, text in enumerate(entity_texts):
        count += 1
        doc.append(
            CardCommand(
                arguments=Arguments(card_height[card_type], card_width[card_type], text)
            )
        )
        if count % cards_per_row[card_type] == 0 and count > 1:
            doc.append(NoEscape("\\vspace{-1pt} \\newline "))
        if count % cards_per_page[card_type] == 0:
            doc.append(NewPage())
    doc.generate_pdf(output_filepath, clean_tex=False)
