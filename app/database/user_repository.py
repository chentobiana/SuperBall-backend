from typing import Optional
from datetime import datetime
from app.database.connection import get_database
from app.models.user import UserCreate, UserInDB, UserUpdate
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self):
        self.db = get_database()
        self.collection = self.db[settings.USERS_COLLECTION]

    async def find_by_unique_id(self, unique_id: str) -> Optional[UserInDB]:
        """
        Find user by unique_id
        """
        try:
            user_data = await self.collection.find_one({
                "$or": [
                    {"uniqId": unique_id},
                    {"unique_id": unique_id}
                ]
            })
            if user_data:
                # Convert ObjectId to string
                user_data["_id"] = str(user_data["_id"])
                return UserInDB(**user_data)
            return None
        except Exception as e:
            logger.error(f"Error finding user by unique_id {unique_id}: {e}")
            raise

    async def create_user(self, user_data: UserCreate) -> UserInDB:
        """
        Creates a new user in the database
        """
        try:
            # Create new user object
            from app.models.user import generate_player_name
            new_user = UserInDB(
                uniqId=user_data.uniqId,
                created_at=datetime.utcnow(),
                name=user_data.name if user_data.name else generate_player_name(),
            )

            # Convert to dict for MongoDB
            user_dict = new_user.model_dump(by_alias=True, exclude_unset=True)

            # Insert into database
            result = await self.collection.insert_one(user_dict)

            # Return new user with generated ID
            user_dict["_id"] = str(result.inserted_id)
            return UserInDB(**user_dict)
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    async def update_user(self, unique_id: str, update_data: UserUpdate) -> Optional[UserInDB]:
        """
        Updates user data
        """
        try:
            # Prepare update data
            update_dict = update_data.model_dump(exclude_unset=True)
            if update_dict:
                update_dict["updated_at"] = datetime.utcnow()

                # Update in database
                result = await self.collection.update_one(
                    {"$or": [
                        {"uniqId": unique_id},
                        {"unique_id": unique_id}
                    ]},
                    {"$set": update_dict}
                )

                if result.modified_count > 0:
                    # Return updated user
                    return await self.find_by_unique_id(unique_id)

            return None
        except Exception as e:
            logger.error(f"Error updating user {unique_id}: {e}")
            raise

    async def update_last_login(self, unique_id: str) -> bool:
        """
        Updates the last login time
        """
        try:
            result = await self.collection.update_one(
                {"$or": [
                    {"uniqId": unique_id},
                    {"unique_id": unique_id}
                ]},
                {"$set": {"last_login": datetime.utcnow(), "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating last login for user {unique_id}: {e}")
            raise

    async def user_exists(self, unique_id: str) -> bool:
        """
        Checks if user exists in the database
        """
        try:
            count = await self.collection.count_documents({
                "$or": [
                    {"uniqId": unique_id},
                    {"unique_id": unique_id}
                ]
            })
            return count > 0
        except Exception as e:
            logger.error(f"Error checking if user exists {unique_id}: {e}")
            raise

    async def get_user_stats(self, unique_id: str) -> Optional[dict]:
        """
        Returns user statistics
        """
        try:
            user = await self.find_by_unique_id(unique_id)
            if user:
                return {
                    "level": user.level,
                    "score": user.score,
                    "coins": user.coins,
                    "lives": user.lives,
                    "trophies": user.trophies,
                    "stars": user.stars
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user stats {unique_id}: {e}")
            raise

    async def update_rewards(self, unique_id: str, trophies_change: int,
                             money_change: int, stars_change: int) -> Optional[UserInDB]:
        """
        Update user rewards (trophies, money, stars)
        """
        try:
            # Get current user data
            user = await self.find_by_unique_id(unique_id)
            if not user:
                return None
            
            # Calculate new values
            new_trophies = max(0, user.trophies + trophies_change)  # Don't go below 0
            new_money = user.coins + money_change
            new_stars = user.stars + stars_change
            
            # Update in database
            result = await self.collection.update_one(
                {"$or": [
                    {"uniqId": unique_id},
                    {"unique_id": unique_id}
                ]},
                {"$set": {
                    "trophies": new_trophies,
                    "coins": new_money,
                    "stars": new_stars,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            if result.modified_count > 0:
                # Return updated user
                return await self.find_by_unique_id(unique_id)
            
            return None
        except Exception as e:
            logger.error(f"Error updating rewards for user {unique_id}: {e}")
            raise

    async def get_user_rewards(self, unique_id: str) -> Optional[dict]:
        """
        Get user rewards data
        """
        try:
            user = await self.find_by_unique_id(unique_id)
            if user:
                return {
                    "trophies": user.trophies,
                    "coins": user.coins,
                    "stars": user.stars
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user rewards {unique_id}: {e}")
            raise
