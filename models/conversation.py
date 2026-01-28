"""
Conversation and Message models for chat history management with MongoDB.
"""

from datetime import datetime
from bson import ObjectId
from models import get_db


class Message:
    """Message model for individual chat messages."""
    
    COLLECTION = 'messages'
    
    def __init__(self, _id=None, conversation_id=None, role=None, content=None,
                 metadata=None, created_at=None):
        self.id = str(_id) if _id else None
        self._id = _id
        self.conversation_id = str(conversation_id) if conversation_id else None
        self.role = role  # 'user', 'assistant', or 'system'
        self.content = content
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
    
    @staticmethod
    def create(conversation_id, role, content, metadata=None):
        """Create a new message."""
        db = get_db()
        
        message_doc = {
            'conversation_id': ObjectId(conversation_id),
            'role': role,
            'content': content,
            'metadata': metadata or {},
            'created_at': datetime.utcnow()
        }
        
        result = db[Message.COLLECTION].insert_one(message_doc)
        message_doc['_id'] = result.inserted_id
        
        # Update conversation's updated_at timestamp
        db['conversations'].update_one(
            {'_id': ObjectId(conversation_id)},
            {'$set': {'updated_at': datetime.utcnow()}}
        )
        
        return Message._from_doc(message_doc)
    
    @staticmethod
    def get_by_id(message_id):
        """Get message by ID."""
        db = get_db()
        try:
            doc = db[Message.COLLECTION].find_one({'_id': ObjectId(message_id)})
            if doc:
                return Message._from_doc(doc)
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_by_conversation(conversation_id, limit=None):
        """Get all messages for a conversation."""
        db = get_db()
        try:
            query = {'conversation_id': ObjectId(conversation_id)}
            cursor = db[Message.COLLECTION].find(query).sort('created_at', 1)
            
            if limit:
                cursor = cursor.limit(limit)
            
            return [Message._from_doc(doc) for doc in cursor]
        except Exception:
            return []
    
    @staticmethod
    def _from_doc(doc):
        """Create Message instance from MongoDB document."""
        return Message(
            _id=doc.get('_id'),
            conversation_id=doc.get('conversation_id'),
            role=doc.get('role'),
            content=doc.get('content'),
            metadata=doc.get('metadata', {}),
            created_at=doc.get('created_at')
        )
    
    def to_dict(self):
        """Convert message to dictionary."""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Conversation:
    """Conversation model for managing chat sessions."""
    
    COLLECTION = 'conversations'
    
    def __init__(self, _id=None, user_id=None, title=None, created_at=None,
                 updated_at=None, is_archived=False):
        self.id = str(_id) if _id else None
        self._id = _id
        self.user_id = str(user_id) if user_id else None
        self.title = title or 'New Conversation'
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.is_archived = is_archived
    
    @staticmethod
    def create(user_id, title='New Conversation'):
        """Create a new conversation."""
        db = get_db()
        now = datetime.utcnow()
        
        conv_doc = {
            'user_id': ObjectId(user_id),
            'title': title,
            'created_at': now,
            'updated_at': now,
            'is_archived': False
        }
        
        result = db[Conversation.COLLECTION].insert_one(conv_doc)
        conv_doc['_id'] = result.inserted_id
        return Conversation._from_doc(conv_doc)
    
    @staticmethod
    def get_by_id(conversation_id):
        """Get conversation by ID."""
        db = get_db()
        try:
            doc = db[Conversation.COLLECTION].find_one({'_id': ObjectId(conversation_id)})
            if doc:
                return Conversation._from_doc(doc)
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_by_user(user_id, include_archived=False, limit=50):
        """Get all conversations for a user."""
        db = get_db()
        try:
            query = {'user_id': ObjectId(user_id)}
            if not include_archived:
                query['is_archived'] = False
            
            cursor = db[Conversation.COLLECTION].find(query).sort('updated_at', -1).limit(limit)
            return [Conversation._from_doc(doc) for doc in cursor]
        except Exception:
            return []
    
    @staticmethod
    def _from_doc(doc):
        """Create Conversation instance from MongoDB document."""
        return Conversation(
            _id=doc.get('_id'),
            user_id=doc.get('user_id'),
            title=doc.get('title'),
            created_at=doc.get('created_at'),
            updated_at=doc.get('updated_at'),
            is_archived=doc.get('is_archived', False)
        )
    
    def update_title(self, title):
        """Update conversation title."""
        db = get_db()
        self.title = title
        self.updated_at = datetime.utcnow()
        db[Conversation.COLLECTION].update_one(
            {'_id': ObjectId(self.id)},
            {'$set': {'title': title, 'updated_at': self.updated_at}}
        )
    
    def archive(self):
        """Archive the conversation."""
        db = get_db()
        self.is_archived = True
        db[Conversation.COLLECTION].update_one(
            {'_id': ObjectId(self.id)},
            {'$set': {'is_archived': True}}
        )
    
    def delete(self):
        """Delete the conversation and all its messages."""
        db = get_db()
        # Delete all messages first
        db[Message.COLLECTION].delete_many({'conversation_id': ObjectId(self.id)})
        # Delete conversation
        db[Conversation.COLLECTION].delete_one({'_id': ObjectId(self.id)})
    
    def get_messages(self, limit=None):
        """Get all messages in this conversation."""
        return Message.get_by_conversation(self.id, limit)
    
    def add_message(self, role, content, metadata=None):
        """Add a message to this conversation."""
        return Message.create(self.id, role, content, metadata)
    
    def get_message_count(self):
        """Get the number of messages in this conversation."""
        db = get_db()
        try:
            return db[Message.COLLECTION].count_documents({'conversation_id': ObjectId(self.id)})
        except Exception:
            return 0
    
    def to_dict(self, include_messages=False):
        """Convert conversation to dictionary."""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_archived': self.is_archived,
            'message_count': self.get_message_count()
        }
        
        if include_messages:
            data['messages'] = [msg.to_dict() for msg in self.get_messages()]
        
        return data
