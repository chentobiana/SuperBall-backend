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

    Stores game outcome and calculates rewards based on performance.
    Includes trophies, money, and stars earned during the game.
    """
    game_id: str
    player_id: str
    player_name: str
    opponent_id: str
    opponent_name: str
    # Game scores
    player_score: int
    opponent_score: int
    # Outcome
    outcome: GameOutcome
    score_difference: int  # player_score - opponent_score
    # Rewards
    trophies_gained: int  # +50 for win, -50 for lose, 0 for tie
    money_gained: int  # Based on player's score
    stars_earned: int  # 1-3 stars based on performance
    # Updated player stats
    new_trophy_count: int
    new_money_count: int
    new_star_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def calculate_rewards(cls, player_score: int, opponent_score: int,
                          current_trophies: int, current_money: int, current_stars: int) -> 'GameResult':
        """Calculate rewards based on game scores and current player stats.

        Args:
            player_score: The player's final score
            opponent_score: The opponent's final score
            current_trophies: Player's current trophy count
            current_money: Player's current money count
            current_stars: Player's current star count

        Returns:
            A GameResult object with calculated rewards and new totals
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
            if score_difference >= 10:
                stars_earned = 3
            else:
                stars_earned = 2
        else:  # LOSE or TIE
            stars_earned = 1
        # Calculate new totals
        new_trophy_count = max(0, current_trophies + trophies_gained)  # Don't go below 0
        new_money_count = current_money + money_gained
        new_star_count = current_stars + stars_earned
        return cls(
            game_id="",  # Will be set when creating the result
            player_id="",  # Will be set when creating the result
            player_name="",  # Will be set when creating the result
            opponent_id="",  # Will be set when creating the result
            opponent_name="",  # Will be set when creating the result
            player_score=player_score,
            opponent_score=opponent_score,
            outcome=outcome,
            score_difference=score_difference,
            trophies_gained=trophies_gained,
            money_gained=money_gained,
            stars_earned=stars_earned,
            new_trophy_count=new_trophy_count,
            new_money_count=new_money_count,
            new_star_count=new_star_count
        )


class GameResultResponse(BaseModel):
    """Response model for game results API.

    Provides a user-friendly view of game results with performance messages
    and updated player stats. Used for client-side display.
    """
    game_id: str
    player_name: str
    opponent_name: str
    player_score: int
    opponent_score: int
    outcome: GameOutcome
    score_difference: int
    # Rewards earned this game
    trophies_gained: int
    money_gained: int
    stars_earned: int
    # Updated totals
    total_trophies: int
    total_money: int
    total_stars: int
    # UI display data
    performance_message: str  # e.g., "Great victory!", "Close match!"

    @classmethod
    def from_game_result(cls, game_result: GameResult) -> 'GameResultResponse':
        """Create a user-friendly response from a GameResult.

        Args:
            game_result: The game result to convert

        Returns:
            A GameResultResponse with performance message and formatted stats
        """
        # Generate performance message
        if game_result.outcome == GameOutcome.WIN:
            if game_result.score_difference >= 10:
                performance_message = "Outstanding victory! 🏆"
            elif game_result.score_difference >= 5:
                performance_message = "Great win! 🎉"
            else:
                performance_message = "Good victory! 👍"
        elif game_result.outcome == GameOutcome.LOSE:
            if game_result.score_difference <= -10:
                performance_message = "Tough loss, keep trying! 💪"
            else:
                performance_message = "Close match! 🔥"
        else:  # TIE
            performance_message = "Even match! ⚖️"
        return cls(
            game_id=game_result.game_id,
            player_name=game_result.player_name,
            opponent_name=game_result.opponent_name,
            player_score=game_result.player_score,
            opponent_score=game_result.opponent_score,
            outcome=game_result.outcome,
            score_difference=game_result.score_difference,
            trophies_gained=game_result.trophies_gained,
            money_gained=game_result.money_gained,
            stars_earned=game_result.stars_earned,
            total_trophies=game_result.new_trophy_count,
            total_money=game_result.new_money_count,
            total_stars=game_result.new_star_count,
            performance_message=performance_message
        )
