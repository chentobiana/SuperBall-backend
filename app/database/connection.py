from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

# יצירת חיבור למסד הנתונים
async def connect_to_mongo():
    """יוצר חיבור למסד הנתונים MongoDB"""
    try:
        MongoDB.client = AsyncIOMotorClient(settings.MONGODB_URL)
        MongoDB.database = MongoDB.client[settings.DATABASE_NAME]
        
        # בדיקת חיבור
        await MongoDB.client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB: {settings.DATABASE_NAME}")
        
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """סוגר את החיבור למסד הנתונים"""
    if MongoDB.client:
        MongoDB.client.close()
        logger.info("MongoDB connection closed")

def get_database():
    """מחזיר את מסד הנתונים"""
    return MongoDB.database
