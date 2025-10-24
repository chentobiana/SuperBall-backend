"""MongoDB connection management module."""

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import logging


logger = logging.getLogger(__name__)


class MongoDB:
    """Global MongoDB connection state.

    Attributes:
        client: AsyncIOMotorClient instance for database connection
        database: Reference to the active database
    """
    client: AsyncIOMotorClient = None
    database = None


async def connect_to_mongo():
    """Establish connection to MongoDB and initialize database reference."""
    try:
        MongoDB.client = AsyncIOMotorClient(settings.MONGODB_URL)
        MongoDB.database = MongoDB.client[settings.DATABASE_NAME]

        # Verify connection
        await MongoDB.client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB: {settings.DATABASE_NAME}")

    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close the MongoDB connection and cleanup resources."""
    if MongoDB.client:
        MongoDB.client.close()
        logger.info("MongoDB connection closed")


def get_database():
    """Return the active database instance.

    Returns:
        The MongoDB database instance configured in settings.
    """
    return MongoDB.database
