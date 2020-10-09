from datetime import datetime
import numpy as np


def split_date(d):
    try:
        return d.strftime("%Y-%m-%d")
    except ValueError:
        return np.nan


def split_time(d):
    try:
        return d.strftime("%H:%M")
    except ValueError:
        return np.nan


def convert_string_to_num(value):
    try:
        return int(value)
    except ValueError:
        return value
