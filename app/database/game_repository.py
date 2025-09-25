from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorCollection
from app.database.connection import get_database
from app.models.game import GameSession, GameStatus
from app.config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GameRepository:
    """Repository for game session operations"""
    
    def __init__(self):
        self._collection: Optional[AsyncIOMotorCollection] = None
    
    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the games collection"""
        if self._collection is None:
            db = get_database()
            self._collection = db[settings.GAME_SESSIONS_COLLECTION]
        return self._collection
    
    async def create_game(self, game_session: GameSession) -> GameSession:
        """Create a new game session"""
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
        """Find game by ID"""
        try:
            from bson import ObjectId
            collection = self.collection
            
            game_doc = await collection.find_one({"_id": ObjectId(game_id)})
            if game_doc:
                game_doc["_id"] = str(game_doc["_id"])
                return GameSession(**game_doc)
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding game by id {game_id}: {e}")
            return None
    
    async def find_by_player(self, player_uniq_id: str, status: Optional[GameStatus] = None) -> List[GameSession]:
        """Find games by player ID"""
        try:
            collection = self.collection
            
            query = {
                "$or": [
                    {"player1_id": player_uniq_id},
                    {"player2_id": player_uniq_id}
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
            logger.error(f"Error finding games for player {player_uniq_id}: {e}")
            return []
    
    async def update_game(self, game_id: str, update_data: dict) -> Optional[GameSession]:
        """Update game session"""
        try:
            from bson import ObjectId
            collection = self.collection
            
            # Add updated_at timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            result = await collection.update_one(
                {"_id": ObjectId(game_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                return await self.find_by_id(game_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating game {game_id}: {e}")
            return None
    
    async def delete_game(self, game_id: str) -> bool:
        """Delete game session"""
        try:
            from bson import ObjectId
            collection = self.collection
            
            result = await collection.delete_one({"_id": ObjectId(game_id)})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting game {game_id}: {e}")
            return False
    
    async def find_active_games(self) -> List[GameSession]:
        """Find all active games"""
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
