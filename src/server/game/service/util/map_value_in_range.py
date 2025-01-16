import math


def map_value_in_range(num_value: float, fmt: str, min_value: float, max_value: float, strings: list[str]):
    factor = (num_value - min_value) / (max_value - min_value)
    array_index = min(math.floor(len(strings) * factor), len(strings) - 1)
    value = strings[array_index]
    return fmt.format(value)
