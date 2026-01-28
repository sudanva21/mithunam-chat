"""
Authentication service for user management.
"""

from flask_jwt_extended import create_access_token, create_refresh_token
from models.user import User


class AuthService:
    """Service for handling authentication operations."""
    
    @staticmethod
    def register(email, password, name):
        """
        Register a new user.
        
        Returns:
            tuple: (user, error_message)
        """
        # Check if user already exists
        existing_user = User.get_by_email(email)
        if existing_user:
            return None, 'Email already registered'
        
        # Validate inputs
        if not email or '@' not in email:
            return None, 'Invalid email address'
        
        if not password or len(password) < 6:
            return None, 'Password must be at least 6 characters'
        
        if not name or len(name.strip()) < 2:
            return None, 'Name must be at least 2 characters'
        
        # Create user
        try:
            user = User.create(email, password, name.strip())
            return user, None
        except Exception as e:
            return None, f'Failed to create user: {str(e)}'
    
    @staticmethod
    def login(email, password):
        """
        Authenticate user and generate tokens.
        
        Returns:
            tuple: (tokens_dict, error_message)
        """
        # Get user
        user = User.get_by_email(email)
        if not user:
            return None, 'Invalid email or password'
        
        # Verify password
        if not user.verify_password(password):
            return None, 'Invalid email or password'
        
        # Check if active
        if not user.is_active:
            return None, 'Account is deactivated'
        
        # Update last login
        user.update_last_login()
        
        # Generate tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }, None
    
    @staticmethod
    def get_user(user_id):
        """Get user by ID."""
        return User.get_by_id(user_id)
    
    @staticmethod
    def update_user_preferences(user_id, preferences):
        """
        Update user preferences (onboarding data).
        
        Returns:
            tuple: (user, error_message)
        """
        user = User.get_by_id(user_id)
        if not user:
            return None, 'User not found'
        
        try:
            user.update_preferences(preferences)
            return user, None
        except Exception as e:
            return None, f'Failed to update preferences: {str(e)}'
