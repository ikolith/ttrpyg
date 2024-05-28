import itertools
import re
import random
from typing import Union
from collections import Counter
import heapq
from functools import cache
from random import randint
import logging

import pandas as pd

import ttrpyg.my_types as ty


def all_rolls(
    dice: list,
    result_type: str = "all",
) -> dict[int, Union[int, float, list[tuple[int]]]]:
    """Pass in a list where each die is represented by an integer corresponding to its maximum value.
    Returns a dictionary where keys are the totals (or result) of the rolls.
    The values are dependent on result_type.
    If 'all', all possible combinations that resulted in that roll.
    If 'count' a count of how many distinct combinations there are.
    If 'probabilities', the probability of the result."""
    dice_ranges = [range(1, die + 1) for die in dice]
    all_rolls: dict = {}

    for i in itertools.product(*dice_ranges):
        if sum(i) in all_rolls.keys():
            all_rolls[sum(i)].append(i)
        else:
            all_rolls[sum(i)] = [i]
    if result_type == "all":
        return all_rolls
    elif result_type == "counts":
        return {i: len(all_rolls[i]) for i in all_rolls}
    elif result_type == "probabilities":
        roll_counts = {i: len(all_rolls[i]) for i in all_rolls}
        return {i: roll_counts[i] / sum(roll_counts.values()) for i in roll_counts}
    else:
        raise Exception("Invalid result_type passed.")


def check_conditions(adv_range: int = 3, passing_value: int = 7):
    if passing_value < 2 or passing_value > 12:
        raise ValueError(
            f"passing_value of {passing_value} is outside of the range of a 2d6 check."
        )

    @cache
    def condition_test(rolled: tuple) -> tuple[bool, bool, bool, bool, bool]:
        pm, phc, m, hc, fc = False, False, False, False, False
        counts = Counter(rolled)
        if counts[6] >= 1:
            hc = True
            if counts[6] >= 2:
                fc = True
                phc = True
            elif heapq.nlargest(2, rolled)[-1] + 6 >= passing_value:
                phc = True
        for number, count in counts.items():
            if count >= 2 and number != 1:  # total failures dont count as matching!
                m = True
                if number * 2 >= passing_value:
                    pm = True
                    break
        return (pm, phc, m, hc, fc)

    res: dict = {
        "adv_level": [],
        "total_rolls": [],
        "passing_matching": [],
        "passing_halfcrit": [],
        "matching": [],
        "halfcrit": [],
        "fullcrit": [],
    }

    for dice in range(2, 3 + adv_range):
        res["adv_level"].append(dice - 2)
        res["total_rolls"].append(6**dice)
        res["passing_matching"].append(0)
        res["passing_halfcrit"].append(0)
        res["matching"].append(0)
        res["halfcrit"].append(0)
        res["fullcrit"].append(0)
        rolls = all_rolls([6] * dice)

        for k, v in rolls.items():
            for rolled in v:
                # advantage
                # gotta cast to tuple so its hashable...
                pm, phc, m, hc, fc = condition_test(tuple(rolled))
                res["passing_matching"][-1] += pm
                res["passing_halfcrit"][-1] += phc
                res["matching"][-1] += m
                res["halfcrit"][-1] += hc
                res["fullcrit"][-1] += fc

        if dice == 2:
            continue

        res["adv_level"].append(2 - dice)
        res["total_rolls"].append(6**dice)
        res["passing_matching"].append(0)
        res["passing_halfcrit"].append(0)
        res["matching"].append(0)
        res["halfcrit"].append(0)
        res["fullcrit"].append(0)
        rolls = all_rolls([6] * dice)

        for k, v in rolls.items():
            for rolled in v:
                # disadvantage
                pm, phc, m, hc, fc = condition_test(tuple(heapq.nsmallest(2, rolled)))
                res["passing_matching"][-1] += pm
                res["passing_halfcrit"][-1] += phc
                res["matching"][-1] += m
                res["halfcrit"][-1] += hc
                res["fullcrit"][-1] += fc

    df = pd.DataFrame(res)
    df = df.sort_values(by="adv_level", ascending=False)
    df["prob_pm"] = df["passing_matching"] / df["total_rolls"]
    df["prob_phc"] = df["passing_halfcrit"] / df["total_rolls"]
    df["prob_m"] = df["matching"] / df["total_rolls"]
    df["prob_hc"] = df["halfcrit"] / df["total_rolls"]
    df["prob_fc"] = df["fullcrit"] / df["total_rolls"]
    return df


def roll_on_table(entity: ty.Entity, curly: ty.Curly, bound_roll: bool = True) -> str:
    # bound_roll means that if the roll is lower than min, it becomes min, if it is higher than max, it becomes max
    table = entity["table"]
    roll_min = int(min(table["expanded_outcomes"].keys()))
    roll_max = int(max(table["expanded_outcomes"].keys()))
    if curly["table_dice"]:
        roll = curly["table_result"]
    elif "roll" in table.keys():
        roll = die_parser_roller((table["roll"]))
    else:
        roll = randint(
            roll_min,
            roll_max,
        )
    if bound_roll:
        roll = max(roll_min, min(roll, roll_max))
    # doesnt seem like the preprocess buys as much as i thought it might!
    return table["expanded_outcomes"][str(roll)]


def get_ev(dice: list, mod="") -> float:
    if mod == "":
        return float(sum(dice) / len(dice) + (len(dice) * 0.5))
    elif mod == "double_on_max":
        return float(sum(dice) / len(dice) + (len(dice) * 0.5) + len(dice))
    elif mod == "exploding":
        ev = 0
        for die in dice:
            ev += (die * (die + 1)) / (2 * (die - 1))
        return float(ev)
    else:
        raise Exception("Invalid modifier (mod) argument passed.")


def get_cumulative_probability(roll_probabilities: dict) -> dict:
    cum_prob = {}
    run_sum = 0
    for roll in roll_probabilities:
        run_sum += roll_probabilities[roll]
        cum_prob[roll] = run_sum
    return cum_prob


def score_adjustment(roll_df: dict, adjustment: int) -> dict:
    return {roll + adjustment: v for roll, v in roll_df.items()}


# I feel like this is going to be used often enough that I might as well keep this around.
std_check_probabilities = {
    2: 1 / 36,
    3: 2 / 36,
    4: 3 / 36,
    5: 4 / 36,
    6: 5 / 36,
    7: 6 / 36,
    8: 5 / 36,
    9: 4 / 36,
    10: 3 / 36,
    11: 2 / 36,
    12: 1 / 36,
}


def get_pass_probability(score: int, dc: int) -> float:
    cum_prob = score_adjustment(
        get_cumulative_probability(std_check_probabilities), score
    )
    if max(cum_prob.keys()) < dc - 1:
        return 0.0
    elif min(cum_prob.keys()) > dc - 1:
        return 1.0
    else:
        return 1 - cum_prob[dc - 1]


def die_parser_roller(curly_match: str) -> int:
    if result := re.search(r"(\d*)d(\d+)(x?)([-+]?\d*)", curly_match):
        quantity, top_face, x, mod = result.groups()
    assert top_face
    top_face = int(top_face)
    if not quantity:
        quantity = 1
    else:
        quantity = int(quantity)
    roll = 0
    for i in range(0, quantity):
        just_rolled = random.randint(1, top_face)
        if x and top_face > 1:
            while just_rolled == top_face:
                roll += just_rolled
                just_rolled = random.randint(1, top_face)
        roll += just_rolled
    if not mod:
        pass
    else:
        roll += int(mod)
    return max(
        roll, 0
    )  # Here following the ttrpg convention that you cannot roll a negative number.
