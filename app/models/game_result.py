from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class GameOutcome(str, Enum):
    """Game outcome enumeration.

    Values:
        WIN: Player won the game
        LOSE: Player lost the game
        TIE: Game ended in a tie
    """
    WIN = "win"
    LOSE = "lose"
    TIE = "tie"


class GameResult(BaseModel):
    """Game result with rewards calculation.

    Stores game outcome and rewards earned.
    This is saved to the database for game history.
    """
    game_id: str
    player_id: str
    player_name: str
    opponent_id: str
    opponent_name: str
    player_score: int
    opponent_score: int
    outcome: GameOutcome  # "win" / "lose" / "tie"
    trophies_gained: int  # +50 for win, -50 for lose, 0 for tie
    money_gained: int  # Based on player's score
    stars_earned: int  # 1-3 stars based on performance
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def calculate_rewards(cls, player_score: int, opponent_score: int,
                          current_trophies: int, current_money: int) -> 'GameResult':
        """Calculate rewards based on game scores.

        Args:
            player_score: The player's final score
            opponent_score: The opponent's final score
            current_trophies: Player's current trophy count (for validation only)
            current_money: Player's current money count (for validation only)

        Returns:
            A GameResult object with calculated rewards
        """
        # Determine outcome
        if player_score > opponent_score:
            outcome = GameOutcome.WIN
            trophies_gained = 50
        elif player_score < opponent_score:
            outcome = GameOutcome.LOSE
            trophies_gained = -50
        else:
            outcome = GameOutcome.TIE
            trophies_gained = 0
        
        score_difference = player_score - opponent_score
        
        # Calculate money based on player's score
        # Base formula: money = player_score * 0.1 (10% of score)
        money_gained = max(0, int(player_score * 0.1))
        
        # Calculate stars based on performance
        if outcome == GameOutcome.WIN:
            if abs(score_difference) >= 10:
                stars_earned = 3
            else:
                stars_earned = 2
        else:  # LOSE or TIE
            stars_earned = 1
        
        return cls(
            game_id="",  # Will be set when creating the result
            player_id="",  # Will be set when creating the result
            player_name="",  # Will be set when creating the result
            opponent_id="",  # Will be set when creating the result
            opponent_name="",  # Will be set when creating the result
            player_score=player_score,
            opponent_score=opponent_score,
            outcome=outcome,
            trophies_gained=trophies_gained,
            money_gained=money_gained,
            stars_earned=stars_earned
        )


class GameResultResponse(BaseModel):
    """Response model for game results API.

    Provides a user-friendly view of game results for client-side display.
    """
    game_id: str
    player_name: str
    opponent_name: str
    player_score: int
    opponent_score: int
    outcome: GameOutcome
    trophies_gained: int
    money_gained: int
    stars_earned: int
    created_at: datetime

    @classmethod
    def from_game_result(cls, game_result: GameResult) -> 'GameResultResponse':
        """Create a response from a GameResult.

        Args:
            game_result: The game result to convert

        Returns:
            A GameResultResponse for API response
        """
        return cls(
            game_id=game_result.game_id,
            player_name=game_result.player_name,
            opponent_name=game_result.opponent_name,
            player_score=game_result.player_score,
            opponent_score=game_result.opponent_score,
            outcome=game_result.outcome,
            trophies_gained=game_result.trophies_gained,
            money_gained=game_result.money_gained,
            stars_earned=game_result.stars_earned,
            created_at=game_result.created_at
        )
