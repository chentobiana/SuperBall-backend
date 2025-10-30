from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorCollection
from app.database.connection import get_database
from app.models.game_result import GameResult
import logging

logger = logging.getLogger(__name__)


class GameResultRepository:
    """Repository for game result operations.

    Handles CRUD operations for game results in MongoDB, including:
    - Saving game results after a game finishes
    - Finding results by game ID or player ID
    - Retrieving player's game history
    """

    def __init__(self):
        self._collection: Optional[AsyncIOMotorCollection] = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the game_results collection, initializing it if needed."""
        if self._collection is None:
            db = get_database()
            self._collection = db["game_results"]
        return self._collection

    async def save_result(self, game_result: GameResult) -> GameResult:
        """Save a game result to the database.

        Args:
            game_result: The game result to save

        Returns:
            The saved game result with its ID populated

        Raises:
            Exception: If the save operation fails
        """
        try:
            collection = self.collection
            # Convert to dict
            result_dict = game_result.model_dump(by_alias=True, exclude_none=True)
            
            # Insert into database
            result = await collection.insert_one(result_dict)
            
            # Fetch the created result
            created_result = await collection.find_one({"_id": result.inserted_id})
            if created_result:
                created_result["_id"] = str(created_result["_id"])
                return GameResult(**created_result)
            
            raise Exception("Failed to retrieve saved game result")
        except Exception as e:
            logger.error(f"Error saving game result: {e}")
            raise

    async def find_by_game_id(self, game_id: str) -> List[GameResult]:
        """Find all results for a specific game.

        Args:
            game_id: The ID of the game

        Returns:
            List of game results (should be 2 - one for each player)
        """
        try:
            collection = self.collection
            cursor = collection.find({"game_id": game_id})
            results = []
            async for result_doc in cursor:
                result_doc["_id"] = str(result_doc["_id"])
                results.append(GameResult(**result_doc))
            return results
        except Exception as e:
            logger.error(f"Error finding results for game {game_id}: {e}")
            return []

    async def find_by_player_id(self, player_id: str, limit: int = 20) -> List[GameResult]:
        """Find game results for a specific player.

        Args:
            player_id: The unique ID of the player
            limit: Maximum number of results to return (default 20)

        Returns:
            List of game results, sorted by creation time (newest first)
        """
        try:
            collection = self.collection
            cursor = collection.find(
                {"player_id": player_id}
            ).sort("created_at", -1).limit(limit)
            
            results = []
            async for result_doc in cursor:
                result_doc["_id"] = str(result_doc["_id"])
                results.append(GameResult(**result_doc))
            return results
        except Exception as e:
            logger.error(f"Error finding results for player {player_id}: {e}")
            return []

    async def get_player_stats(self, player_id: str) -> dict:
        """Get aggregated statistics for a player.

        Args:
            player_id: The unique ID of the player

        Returns:
            Dictionary with wins, losses, ties, total games
        """
        try:
            collection = self.collection
            results = await self.find_by_player_id(player_id, limit=1000)
            
            wins = sum(1 for r in results if r.outcome.value == "win")
            losses = sum(1 for r in results if r.outcome.value == "lose")
            ties = sum(1 for r in results if r.outcome.value == "tie")
            
            return {
                "total_games": len(results),
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "win_rate": round(wins / len(results) * 100, 2) if results else 0
            }
        except Exception as e:
            logger.error(f"Error getting player stats for {player_id}: {e}")
            return {
                "total_games": 0,
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "win_rate": 0
            }

