from sudoku_as_a_service import utils


def test_convert_puzzle_to_list() -> None:
    """
    Testing convert_puzzle_to_list
    """
    input_string = "111111111222222222333333333444444444555555555666666666777777777888888888999999999"
    assert utils.convert_puzzle_to_list(input_string) == [[i] * 9 for i in range(1, 10)]
