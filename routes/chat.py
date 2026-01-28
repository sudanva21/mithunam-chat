"""
Chat routes for AI conversation functionality.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.gemini_service import GeminiService
from services.auth_service import AuthService

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


@chat_bp.route('/message', methods=['POST'])
@jwt_required()
def send_message():
    """Send a message and get AI response."""
    user_id = get_jwt_identity()  # String (MongoDB ObjectId)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')
    
    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Get user preferences for personalization
    user = AuthService.get_user(user_id)
    preferences = user.preferences if user else None
    
    result = GeminiService.chat(conversation_id, message, user_id, preferences)
    
    if 'error' in result:
        return jsonify({'error': result['error']}), 400
    
    return jsonify(result), 200


@chat_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """Get all conversations for the current user."""
    user_id = get_jwt_identity()  # String (MongoDB ObjectId)
    limit = request.args.get('limit', 50, type=int)
    
    conversations = GeminiService.get_user_conversations(user_id, limit=limit)
    
    return jsonify({'conversations': conversations}), 200


@chat_bp.route('/conversations', methods=['POST'])
@jwt_required()
def create_conversation():
    """Create a new conversation."""
    user_id = get_jwt_identity()  # String (MongoDB ObjectId)
    data = request.get_json() or {}
    
    title = data.get('title', 'New Conversation')
    
    from models.conversation import Conversation
    conversation = Conversation.create(user_id, title)
    
    return jsonify({'conversation': conversation.to_dict()}), 201


@chat_bp.route('/conversations/<conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation(conversation_id):
    """Get a specific conversation with messages."""
    user_id = get_jwt_identity()  # String (MongoDB ObjectId)
    
    result = GeminiService.get_conversation_with_history(conversation_id, user_id)
    
    if 'error' in result:
        status = 404 if result['error'] == 'Conversation not found' else 403
        return jsonify({'error': result['error']}), status
    
    return jsonify({'conversation': result}), 200


@chat_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(conversation_id):
    """Delete a conversation."""
    user_id = get_jwt_identity()  # String (MongoDB ObjectId)
    
    result = GeminiService.delete_conversation(conversation_id, user_id)
    
    if 'error' in result:
        status = 404 if result['error'] == 'Conversation not found' else 403
        return jsonify({'error': result['error']}), status
    
    return jsonify({'message': 'Conversation deleted'}), 200


@chat_bp.route('/conversations/<conversation_id>/title', methods=['PUT'])
@jwt_required()
def update_conversation_title(conversation_id):
    """Update conversation title."""
    user_id = get_jwt_identity()  # String (MongoDB ObjectId)
    data = request.get_json()
    
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    
    from models.conversation import Conversation
    conversation = Conversation.get_by_id(conversation_id)
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    if conversation.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    conversation.update_title(data['title'])
    
    return jsonify({'conversation': conversation.to_dict()}), 200
