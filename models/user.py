"""
User model and database operations with MongoDB.
"""

from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from models import get_db


class User:
    """User model for authentication and profile management."""
    
    COLLECTION = 'users'
    
    def __init__(self, _id=None, email=None, password_hash=None, name=None, 
                 preferences=None, created_at=None, last_login=None, is_active=True):
        self.id = str(_id) if _id else None
        self._id = _id
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.preferences = preferences or {}
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login
        self.is_active = is_active
    
    @staticmethod
    def create(email, password, name):
        """Create a new user."""
        db = get_db()
        password_hash = generate_password_hash(password)
        
        user_doc = {
            'email': email.lower().strip(),
            'password_hash': password_hash,
            'name': name.strip(),
            'preferences': {},
            'created_at': datetime.utcnow(),
            'last_login': None,
            'is_active': True
        }
        
        result = db[User.COLLECTION].insert_one(user_doc)
        user_doc['_id'] = result.inserted_id
        return User._from_doc(user_doc)
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID."""
        db = get_db()
        try:
            doc = db[User.COLLECTION].find_one({'_id': ObjectId(user_id)})
            if doc:
                return User._from_doc(doc)
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email."""
        db = get_db()
        doc = db[User.COLLECTION].find_one({'email': email.lower().strip()})
        if doc:
            return User._from_doc(doc)
        return None
    
    @staticmethod
    def _from_doc(doc):
        """Create User instance from MongoDB document."""
        return User(
            _id=doc.get('_id'),
            email=doc.get('email'),
            password_hash=doc.get('password_hash'),
            name=doc.get('name'),
            preferences=doc.get('preferences', {}),
            created_at=doc.get('created_at'),
            last_login=doc.get('last_login'),
            is_active=doc.get('is_active', True)
        )
    
    def verify_password(self, password):
        """Verify user password."""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update user's last login timestamp."""
        db = get_db()
        self.last_login = datetime.utcnow()
        db[User.COLLECTION].update_one(
            {'_id': ObjectId(self.id)},
            {'$set': {'last_login': self.last_login}}
        )
    
    def update_preferences(self, preferences):
        """Update user preferences."""
        db = get_db()
        self.preferences = preferences
        db[User.COLLECTION].update_one(
            {'_id': ObjectId(self.id)},
            {'$set': {'preferences': preferences}}
        )
    
    def to_dict(self):
        """Convert user to dictionary for API responses."""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'preferences': self.preferences,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }
