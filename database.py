import motor.motor_asyncio
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv
import os

load_dotenv()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://mukul:1010@nodecluster0.hurza.mongodb.net/?retryWrites=true&w=majority&appName=NodeCluster0")
DATABASE_NAME = os.getenv("DATABASE_NAME", "rfp_platform")

# Async client for FastAPI
async_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
async_db = async_client[DATABASE_NAME]

# Sync client for utilities
sync_client = MongoClient(MONGODB_URL)
sync_db = sync_client[DATABASE_NAME]

async def get_db() -> Database:
    return async_db

def get_sync_db() -> Database:
    return sync_db

# Collections
users_collection = async_db.users
rfps_collection = async_db.rfps
qualification_rules_collection = async_db.qualification_rules
product_prices_collection = async_db.product_prices
test_prices_collection = async_db.test_prices
notifications_collection = async_db.notifications
cron_jobs_collection = async_db.cron_jobs
demo_centers_collection = async_db.demo_centers
demo_requests_collection = async_db.demo_requests
