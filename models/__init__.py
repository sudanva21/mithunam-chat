"""
Database models initialization and MongoDB connection handling.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import get_config
import ssl

config = get_config()

# MongoDB client (singleton)
_client = None
_db = None


def get_db():
    """Get MongoDB database connection."""
    global _client, _db
    
    if _db is None:
        try:
            # Connect using the URI which contains the SSL settings
            # We explicitly force tlsAllowInvalidCertificates=True here as well to be certain
            _client = MongoClient(
                config.MONGODB_URI,
                tls=True,
                tlsAllowInvalidCertificates=True, 
                serverSelectionTimeoutMS=30000
            )
            
            # Verify connection
            _client.admin.command('ping')
            _db = _client[config.MONGODB_DB_NAME]
            print(f"✓ Connected to MongoDB: {config.MONGODB_DB_NAME}")
            
            # Create indexes for better performance
            _create_indexes(_db)
            
        except ConnectionFailure as e:
            print(f"✗ MongoDB connection failed: {e}")
            raise
        except Exception as e:
            print(f"✗ MongoDB connection error: {e}")
            raise
    
    return _db


def _create_indexes(db):
    """Create indexes for collections."""
    # Users collection indexes
    db.users.create_index('email', unique=True)
    
    # Conversations collection indexes
    db.conversations.create_index('user_id')
    db.conversations.create_index([('updated_at', -1)])
    
    # Messages collection indexes
    db.messages.create_index('conversation_id')
    db.messages.create_index([('created_at', 1)])
    
    # Usage stats indexes
    db.usage_stats.create_index('user_id')
    db.usage_stats.create_index([('created_at', -1)])


def close_db():
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None


# Initialize connection on import
try:
    get_db()
except Exception as e:
    print(f"Warning: Could not connect to MongoDB on startup: {e}")
