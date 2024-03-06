import hashlib
import os
import pathlib
import random

import structlog
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import Counter, Summary, generate_latest
from redis import StrictRedis

from sudoku_as_a_service import models, solver, utils

logger = structlog.get_logger()

UNSOLVABLE_MARKER = "unsolvable"

# Used to receive puzzle data, likely should be a volume mounted into the container
DATA_DIRECTORY = pathlib.Path(__file__).absolute().parent / "data"
if not DATA_DIRECTORY.is_dir():
    raise RuntimeError("Puzzle data is missing")

REDIS_HOST = os.environ.get("REDIS_HOST")
if not REDIS_HOST:
    raise ValueError("REDIS_HOST must be set")

REDIS_PORT = os.environ.get("REDIS_PORT")
if not REDIS_PORT:
    raise ValueError("REDIS_PORT must be set")

PUZZLES_FLAVOUR = os.environ.get("PUZZLES_FLAVOUR", "puzzles1_unbiased")
puzzles = [i.strip() for i in open(DATA_DIRECTORY / PUZZLES_FLAVOUR, "r").readlines()]
redis_conn = StrictRedis(REDIS_HOST, int(REDIS_PORT))
app = FastAPI()

# Prometheus metrics
unsolvable_counter = Counter(
    "unsolvable_puzzles",
    "Number of puzzles in the dataset which have been found to be unsolvable",
)
generation_timer = Summary(
    "generation_time_seconds", "Time taken to generate a new puzzle"
)
solve_validation_timer = Summary(
    "solve_validation_seconds", "Time taken to validate a proposed solution"
)


@app.get("/api/v1/puzzle/generate")
@generation_timer.time()
def generate_puzzle() -> models.Puzzle:
    """
    Return a random puzzle along with it's hash as the unique ID
    """
    logger.info("Issuing new puzzle")
    while True:
        new_puzzle = random.choice(puzzles)
        new_puzzle_id = hashlib.md5(new_puzzle.encode("utf-8")).hexdigest()
        logger.info("Validating puzzle candidate", id=new_puzzle_id)

        # Check if this has already been solved
        cached_solution = redis_conn.get(new_puzzle_id)
        if cached_solution and cached_solution != UNSOLVABLE_MARKER:
            logger.debug(
                "Puzzle has already been solved, good to issue", id=new_puzzle_id
            )
            break

        # Check if puzzle is solvable
        converted_puzzle = utils.convert_puzzle_to_list(new_puzzle)
        if solver.sudoku(converted_puzzle, 0, 0):
            logger.info("Puzzle is solvable, good to issue", id=new_puzzle_id)
            redis_conn.set(
                new_puzzle_id, utils.convert_puzzle_to_string(converted_puzzle)
            )
            break
        else:
            logger.warning(
                "Puzzle is not solvable, caching as invalid", id=new_puzzle_id
            )
            redis_conn.set(new_puzzle_id, UNSOLVABLE_MARKER)
            unsolvable_counter.inc()
            continue

    return models.Puzzle(
        id=new_puzzle_id, puzzle=utils.convert_puzzle_to_list(new_puzzle)
    )


@app.post("/api/v1/puzzle/submit")
@solve_validation_timer.time()
def submit_puzzle(puzzle: models.Puzzle) -> dict[str, str]:
    """
    Process a submission to solve a puzzle
    """
    logger.info("Candidate solution propsed", id=puzzle.id)
    cached_solution = redis_conn.get(puzzle.id)
    if not cached_solution:
        logger.error("Invalid puzzle ID provided, unable to continue", id=puzzle.id)
        raise HTTPException(status_code=404, detail="Puzzle ID not recognised")

    proposed_solution = utils.convert_puzzle_to_string(puzzle.puzzle)
    if proposed_solution == cached_solution:
        logger.info("Solution is valid", id=puzzle.id)
        return {"status": "correct"}
    logger.info("Solution is invalid", id=puzzle.id)
    return {"status": "incorrect"}


@app.get("/api/v1/metrics")
def metrics():
    """
    Provide metrics for prometheus to scrape for observability
    """
    return Response(generate_latest(), headers={"Content-Type": "text/plain"})
