from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorCollection
from app.database.connection import get_database
from app.models.game import GameSession, GameStatus
from app.config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GameRepository:
    """Repository for game session operations.

    Handles CRUD operations for game sessions in MongoDB, including:
    - Creating new game sessions
    - Finding games by ID or player
    - Updating game state
    - Managing active games
    """

    def __init__(self):
        self._collection: Optional[AsyncIOMotorCollection] = None

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the games collection, initializing it if needed."""
        if self._collection is None:
            db = get_database()
            self._collection = db[settings.GAME_SESSIONS_COLLECTION]
        return self._collection

    async def create_game(self, game_session: GameSession) -> GameSession:
        """Create a new game session.

        Args:
            game_session: The game session to create

        Returns:
            The created game session with its ID populated

        Raises:
            Exception: If the game creation fails
        """
        try:
            collection = self.collection
            # Convert to dict and remove None id
            game_dict = game_session.model_dump(by_alias=True, exclude_none=True)
            if "_id" in game_dict and game_dict["_id"] is None:
                del game_dict["_id"]
            result = await collection.insert_one(game_dict)
            # Fetch the created game
            created_game = await collection.find_one({"_id": result.inserted_id})
            if created_game:
                created_game["_id"] = str(created_game["_id"])
                return GameSession(**created_game)
            raise Exception("Failed to retrieve created game")
        except Exception as e:
            logger.error(f"Error creating game session: {e}")
            raise

    async def find_by_id(self, game_id: str) -> Optional[GameSession]:
        """Find a game session by its ID.

        Args:
            game_id: The ID of the game to find

        Returns:
            The game session if found, None otherwise
        """
        try:
            from bson import ObjectId
            collection = self.collection
            try:
                oid = ObjectId(game_id)
            except Exception:
                logger.warning(f"Invalid ObjectId received: {game_id}")
                return None
            game_doc = await collection.find_one({"_id": oid})
            if game_doc:
                game_doc["_id"] = str(game_doc["_id"])
                return GameSession(**game_doc)
            return None
        except Exception as e:
            logger.error(f"Error finding game by id {game_id}: {e}")
            return None

    async def find_by_player(self, uniqId: str, status: Optional[GameStatus] = None) -> List[GameSession]:
        """Find all games for a specific player.

        Args:
            uniqId: The unique ID of the player
            status: Optional filter for game status

        Returns:
            List of game sessions where the player is a participant
        """
        try:
            collection = self.collection
            query = {
                "$or": [
                    {"player1_id": uniqId},
                    {"player2_id": uniqId}
                ]
            }
            if status:
                query["status"] = status.value
            cursor = collection.find(query).sort("created_at", -1)
            games = []
            async for game_doc in cursor:
                game_doc["_id"] = str(game_doc["_id"])
                games.append(GameSession(**game_doc))
            return games
        except Exception as e:
            logger.error(f"Error finding games for player {uniqId}: {e}")
            return []

    async def update_game(self, game_id: str, update_data: dict) -> Optional[GameSession]:
        """Update a game session's data.

        Args:
            game_id: The ID of the game to update
            update_data: Dictionary of fields to update

        Returns:
            The updated game session if successful, None otherwise
        """
        try:
            from bson import ObjectId
            collection = self.collection
            # Add updated_at timestamp
            update_data["updated_at"] = datetime.utcnow()
            try:
                oid = ObjectId(game_id)
            except Exception:
                logger.warning(f"Invalid ObjectId on update: {game_id}")
                return None
            await collection.update_one(
                {"_id": oid},
                {"$set": update_data}
            )
            # Always return the current document, even if nothing changed
            return await self.find_by_id(game_id)
        except Exception as e:
            logger.error(f"Error updating game {game_id}: {e}")
            return None

    async def delete_game(self, game_id: str) -> bool:
        """Delete a game session.

        Args:
            game_id: The ID of the game to delete

        Returns:
            True if the game was deleted, False otherwise
        """
        try:
            from bson import ObjectId
            collection = self.collection
            result = await collection.delete_one({"_id": ObjectId(game_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting game {game_id}: {e}")
            return False

    async def find_active_games(self) -> List[GameSession]:
        """Find all active (waiting or in-progress) games.

        Returns:
            List of active game sessions, sorted by creation time (newest first)
        """
        try:
            collection = self.collection
            cursor = collection.find({
                "status": {"$in": [GameStatus.WAITING.value, GameStatus.IN_PROGRESS.value]}
            }).sort("created_at", -1)
            games = []
            async for game_doc in cursor:
                game_doc["_id"] = str(game_doc["_id"])
                games.append(GameSession(**game_doc))
            return games
        except Exception as e:
            logger.error(f"Error finding active games: {e}")
            return []
