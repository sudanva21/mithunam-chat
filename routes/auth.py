"""
Authentication routes.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    
    user, error = AuthService.register(email, password, name)
    
    if error:
        return jsonify({'error': error}), 400
    
    # Auto-login after registration
    tokens, _ = AuthService.login(email, password)
    
    return jsonify({
        'message': 'Registration successful',
        'user': user.to_dict(),
        'access_token': tokens['access_token'],
        'refresh_token': tokens['refresh_token']
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return tokens."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    tokens, error = AuthService.login(email, password)
    
    if error:
        return jsonify({'error': error}), 401
    
    return jsonify(tokens), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information."""
    user_id = get_jwt_identity()  # This is now a string (MongoDB ObjectId)
    user = AuthService.get_user(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/onboarding', methods=['PUT'])
@jwt_required()
def update_onboarding():
    """Update user preferences from onboarding."""
    user_id = get_jwt_identity()  # This is now a string (MongoDB ObjectId)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    preferences = data.get('preferences', {})
    
    user, error = AuthService.update_user_preferences(user_id, preferences)
    
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({
        'message': 'Preferences updated',
        'user': user.to_dict()
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client-side token removal)."""
    # JWT tokens are stateless, so logout is handled client-side
    # This endpoint exists for API consistency
    return jsonify({'message': 'Logged out successfully'}), 200
