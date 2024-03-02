from typing import Any


def convert_puzzle_to_list(puzzle_string: str) -> list[list[int]]:
    """
    Convert a sudoku puzzle from the single line dotted format to a list of lists
    representing columns and rows
    """
    output = []
    for i in range(9):
        current_row = []
        for j in range(9):
            current_row.append(int(puzzle_string[i * 9 + j].replace(".", "0")))
        output.append(current_row)
    return output


def stringify_list(input_list: list[Any]) -> str:
    """
    Convert a list of items into a string with no spacing
    """
    output = ""
    for entry in input_list:
        output += str(entry)
    return output


def convert_puzzle_to_string(puzzle_list: list[list[int]]) -> str:
    """
    Convert a puzzle from a list of lists back to string representation
    """
    output = "".join(stringify_list(i) for i in puzzle_list)
    return output
