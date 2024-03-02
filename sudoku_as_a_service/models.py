from pydantic import BaseModel


class Puzzle(BaseModel):
    id: str
    puzzle: list[list[int]]
