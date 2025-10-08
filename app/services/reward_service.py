from typing import Optional, Tuple
from app.models.game_result import GameResult, GameResultResponse
from app.database.user_repository import UserRepository
from app.database.game_repository import GameRepository
from app.models.game import GameStatus
import logging

logger = logging.getLogger(__name__)


class RewardService:
    """Service for managing game rewards and user progression"""
    
    def __init__(self):
        self.user_repo = None
        self.game_repo = None
    
    def _get_repos(self):
        """Lazy initialization of repositories"""
        if self.user_repo is None:
            self.user_repo = UserRepository()
        if self.game_repo is None:
            self.game_repo = GameRepository()
        return self.user_repo, self.game_repo
    
    async def process_game_result(self, game_id: str, player1_id: str,
                                  player2_id: str) -> Tuple[Optional[GameResult], Optional[GameResult]]:
        """
        Process game results and calculate rewards for both players
        
        Returns:
            Tuple of (player1_result, player2_result) or (None, None) if game not found
        """
        try:
            # Get repositories
            user_repo, game_repo = self._get_repos()
            
            # Get game session
            game = await game_repo.find_by_id(game_id)
            if not game or game.status != GameStatus.FINISHED:
                logger.warning(f"Game {game_id} not found or not finished")
                return None, None
            
            # Get both players' data
            player1 = await user_repo.find_by_unique_id(player1_id)
            player2 = await user_repo.find_by_unique_id(player2_id)
            
            if not player1 or not player2:
                logger.error(f"One or both players not found: {player1_id}, {player2_id}")
                return None, None
            
            # Calculate rewards for player 1
            player1_result = GameResult.calculate_rewards(
                player_score=game.player1_score,
                opponent_score=game.player2_score,
                current_trophies=player1.trophies,
                current_money=player1.coins,
                current_stars=player1.stars
            )
            player1_result.game_id = game_id
            player1_result.player_id = player1_id
            player1_result.player_name = player1.name
            player1_result.opponent_id = player2_id
            player1_result.opponent_name = player2.name
            
            # Calculate rewards for player 2
            player2_result = GameResult.calculate_rewards(
                player_score=game.player2_score,
                opponent_score=game.player1_score,
                current_trophies=player2.trophies,
                current_money=player2.coins,
                current_stars=player2.stars
            )
            player2_result.game_id = game_id
            player2_result.player_id = player2_id
            player2_result.player_name = player2.name
            player2_result.opponent_id = player1_id
            player2_result.opponent_name = player1.name
            
            # Apply rewards to both players
            await user_repo.update_rewards(
                unique_id=player1_id,
                trophies_change=player1_result.trophies_gained,
                money_change=player1_result.money_gained,
                stars_change=player1_result.stars_earned
            )
            
            await user_repo.update_rewards(
                unique_id=player2_id,
                trophies_change=player2_result.trophies_gained,
                money_change=player2_result.money_gained,
                stars_change=player2_result.stars_earned
            )
            
            logger.info(f"Processed rewards for game {game_id}: "
                       f"Player1: +{player1_result.trophies_gained} trophies, "
                       f"+{player1_result.money_gained} money, "
                       f"+{player1_result.stars_earned} stars")
            
            return player1_result, player2_result
            
        except Exception as e:
            logger.error(f"Error processing game result for {game_id}: {e}")
            return None, None
    
    async def get_game_result_for_player(self, game_id: str, player_id: str) -> Optional[GameResultResponse]:
        """
        Get game result response for a specific player
        """
        try:
            # Get repositories
            user_repo, game_repo = self._get_repos()
            
            # Get game session
            game = await game_repo.find_by_id(game_id)
            if not game or game.status != GameStatus.FINISHED:
                return None
            
            # Determine which player this is
            if game.player1_id == player_id:
                player_score = game.player1_score
                opponent_score = game.player2_score
                player_name = game.player1_name
                opponent_name = game.player2_name
            elif game.player2_id == player_id:
                player_score = game.player2_score
                opponent_score = game.player1_score
                player_name = game.player2_name
                opponent_name = game.player1_name
            else:
                logger.warning(f"Player {player_id} not found in game {game_id}")
                return None
            
            # Get current player data
            player = await user_repo.find_by_unique_id(player_id)
            if not player:
                return None
            
            # Calculate rewards
            game_result = GameResult.calculate_rewards(
                player_score=player_score,
                opponent_score=opponent_score,
                current_trophies=player.trophies,
                current_money=player.coins,
                current_stars=player.stars
            )
            game_result.game_id = game_id
            game_result.player_id = player_id
            game_result.player_name = player_name
            game_result.opponent_id = game.player1_id if game.player1_id != player_id else game.player2_id
            game_result.opponent_name = opponent_name
            
            # Create response
            return GameResultResponse.from_game_result(game_result)
            
        except Exception as e:
            logger.error(f"Error getting game result for player {player_id} in game {game_id}: {e}")
            return None
    
    async def get_player_rewards(self, player_id: str) -> Optional[dict]:
        """
        Get current player rewards
        """
        try:
            user_repo, _ = self._get_repos()
            return await user_repo.get_user_rewards(player_id)
        except Exception as e:
            logger.error(f"Error getting player rewards for {player_id}: {e}")
            return None
    
    async def simulate_game_rewards(self, player_score: int, opponent_score: int,
                                    current_trophies: int = 0, current_money: int = 0,
                                    current_stars: int = 0) -> GameResultResponse:
        """
        Simulate game rewards without updating database (for testing/preview)
        """
        try:
            # Create temporary game result
            game_result = GameResult.calculate_rewards(
                player_score=player_score,
                opponent_score=opponent_score,
                current_trophies=current_trophies,
                current_money=current_money,
                current_stars=current_stars
            )
            
            # Set dummy values
            game_result.game_id = "simulation"
            game_result.player_id = "simulation"
            game_result.player_name = "Player"
            game_result.opponent_id = "opponent"
            game_result.opponent_name = "Opponent"
            
            return GameResultResponse.from_game_result(game_result)
            
        except Exception as e:
            logger.error(f"Error simulating game rewards: {e}")
            raise
