from pprint import pprint
import pickle

import ipywidgets as widgets
from IPython.display import display, Markdown
from traitlets import traitlets

from ttrpyg.my_types import Entity
import ttrpyg.database as dt
import ttrpyg.cards as cr

# i shouldnt neetd do this, but for some reason i cant get Entity to be a normal dict! TODO: this
entity_dict = {
    "attacks": list,
    "clean_name": str,
    "cost": str,
    "effect": str,
    "encumbrance": str,
    "flavor_text": str,
    "holds": str,
    "hp": str,
    "meta_tags": list,
    "name": str,
    "requirements": list,
    "scores": list,
    "skills": list,
    "speed": str,
    "tags": list,
    "target": str,
    "to_hit": str,
    "full_text": str,
    #'table': ty.Table  # dont support filtering by table at the moment.
}

# Welcome to the worst code I've ever written.
# Globals dont work the way they should in the notebook, and are "bad practice".
# The widgets don't have proper event handlers.
# So here we are. I'm sorry.


# Builds UIs for collection processing
class LoadedButton(widgets.Button):
    """A button that can holds a value as an attribute."""

    def __init__(self, value=None, *args, **kwargs):
        super(LoadedButton, self).__init__(*args, **kwargs)
        self.add_traits(value=traitlets.Any(value))


def create_loaded_button_ui(run_on_submit: callable, description: str):
    text_widget = widgets.Text(
        description=description,
        style={"description_width": "initial", "width": "1000px"},
        ensure_option=False,
        value="basic",
    )
    loaded_submit_button = LoadedButton(description="Submit")
    output = widgets.Output()

    def submit_clicked(b):
        if tw_v := text_widget.value:
            run_on_submit(loaded_submit_button, tw_v)
            with output:
                output.clear_output()
                display(f"{str(run_on_submit)} ran successfully.")

    loaded_submit_button.on_click(submit_clicked)
    return (text_widget, loaded_submit_button, output)


def load_and_process_collection(
    loaded_submit_button, collection_name: str, run_on_submit: callable
):
    with open("./pickle_jar/" + collection_name + ".pickle", "rb") as handle:
        collection = pickle.load(handle)
    loaded_submit_button.value = collection
    run_on_submit(collection)


# UIs


def create_cards_ui():
    text_widget, collection_lb, output = create_loaded_button_ui(
        lambda lb, tw_v: load_and_process_collection(
            lb, tw_v, run_on_submit=cr.generate_cards
        ),
        "Collection -> Cards",
    )
    return widgets.VBox([text_widget, collection_lb, output])


def create_single_curly_ui(db):
    expand_entities_cb = widgets.Checkbox(
        value=False, description="Expand Entities", disabled=False
    )
    roll_dice_cb = widgets.Checkbox(
        value=False, description="Roll Dice", disabled=False
    )
    curly_tw = widgets.Text(description="Curly Input")
    submit_button = widgets.Button(description="Submit")
    output = widgets.Output()

    def submit_clicked(b):
        if tw_v := curly_tw.value:
            with output:
                output.clear_output()
                res = db.single_curly_parser(
                    curly_tw.value, expand_entities_cb.value, roll_dice_cb.value
                )
                display(Markdown(res))

    submit_button.on_click(submit_clicked)

    return widgets.VBox(
        [
            widgets.HBox(
                [
                    widgets.VBox([curly_tw, submit_button]),
                    widgets.VBox([expand_entities_cb, roll_dice_cb]),
                ]
            ),
            widgets.HBox(
                [output],
                layout=widgets.Layout(
                    display="flex",
                    flex_flow="column",
                    width="300px",  # "40%"?
                ),
            ),
        ]
    )


def create_filter_ui(db, fields, unique_array_field_values, preselect_basic=True):
    text_widgets, sm_widgets = [], []
    field_blacklist = [
        "flavor_text",
        "effect",
        "full_text",
        "skills",
        "attacks",
        "cost",
    ]
    if preselect_basic:
        field_blacklist.append("meta_tags")
        meta_tags_widget = [
            widgets.SelectMultiple(
                description="meta_tags",
                options=unique_array_field_values.get("meta_tags", []),
                ensure_option=False,
                rows=min(
                    len(unique_array_field_values["meta_tags"]), 20
                ),  # for MultiSelect
                value=["basic"],
            )
        ]
    else:
        meta_tags_widget = []
    for k, v in fields.items():
        if k in field_blacklist:
            continue
        elif k in unique_array_field_values.keys():
            sm_widgets.append(
                widgets.SelectMultiple(
                    description=k,
                    options=unique_array_field_values[k],
                    rows=min(len(unique_array_field_values[k]), 15),  # for MultiSelect
                    ensure_option=True,  # for Combobox
                )
            )
        else:
            text_widgets.append(widgets.Text(description=k))
    pickle_text_widget = widgets.Text(
        description="Name of Collection To Create",
        style={"description_width": "initial", "width": "600px"},
    )
    submit_button = widgets.Button(description="Submit")
    output = widgets.Output()

    def submit_clicked(b):
        if not pickle_text_widget.value:
            with output:
                output.clear_output()
                display("Need to name new collection.")
            return None
        filter_params = {}
        for widg in text_widgets + sm_widgets + meta_tags_widget:
            if v := widg.value:
                filter_params[widg.description] = v
        results = db.filter_entities(
            list(filter_params.keys()), list(filter_params.values())
        )
        with output:
            output.clear_output()
            display(
                f"Created collection {pickle_text_widget.value} in the /pickle_jar directory."
            )
        if p := pickle_text_widget.value:
            with open("./pickle_jar/" + p + ".pickle", "wb") as handle:
                pickle.dump(results, handle, protocol=pickle.HIGHEST_PROTOCOL)

    submit_button.on_click(submit_clicked)
    text_widget_column = [widgets.VBox(text_widgets + [submit_button])]
    dropdown_widget_column = [widgets.VBox(sm_widgets)]

    filter_ui = widgets.VBox(
        [
            pickle_text_widget,
            widgets.HBox(
                text_widget_column + meta_tags_widget + dropdown_widget_column
            ),
            output,
        ]
    )
    return filter_ui
