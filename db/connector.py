import logging
import motor.motor_asyncio
from decouple import config

class DbConnector:
    MONGO_URI = config("MONGO_URI", default="")

    def __init__(self):
        self.mongo_client = None
        self.db = None
        self.books_collection = None
        self.snapshots_collection = None
        self.changelog_collection = None

    async def connect_to_db(self):
        """Connects to MongoDB and sets up collection handles."""
        if not self.MONGO_URI:
            logging.error("❌ MONGO_URI is not set.")
            raise ValueError("Mongo connection string is required.")

        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(self.MONGO_URI)
        self.db = self.mongo_client["book_scraper_db"]
        self.books_collection = self.db["books"]
        self.snapshots_collection = self.db["html_snapshots"]
        self.changelog_collection = self.db["change_log"]

        logging.info(f"✅ Connected to MongoDB. DB: {self.db.name}")

        await self.books_collection.create_index("metadata.source_url", unique=True)
        await self.snapshots_collection.create_index("source_url", unique=True)
        await self.changelog_collection.create_index("crawl_timestamp")
