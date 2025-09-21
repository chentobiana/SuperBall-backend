import random
from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/game", tags=["game"])


class InitialBoardResponse(BaseModel):
    finalBoard: list[list[str]]


COLORS = [
    "Purple",
    "Green",
    "Blue",
    "Yellow",
    "Red",
    "Pink",
]


def generate_board(rows: int = 8, cols: int = 7) -> list[list[str]]:
    return [[random.choice(COLORS) for _ in range(cols)] for _ in range(rows)]


@router.get("/initial-board", response_model=InitialBoardResponse)
async def get_initial_board() -> InitialBoardResponse:
    board = generate_board(8, 7)
    return InitialBoardResponse(finalBoard=board)
