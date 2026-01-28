"""
Google Gemini AI service for chat functionality.
"""

from google import genai
from config import get_config
from models.conversation import Conversation, Message
from services.search_service import SearchService

config = get_config()


class GeminiService:
    """Service for interacting with Google Gemini AI."""
    
    _client = None
    
    @classmethod
    def get_client(cls):
        """Get or create the Gemini client."""
        if cls._client is None:
            api_key = config.GEMINI_API_KEY
            if not api_key:
                raise ValueError("GEMINI_API_KEY not configured")
            
            cls._client = genai.Client(api_key=api_key)
        
        return cls._client
    
    @classmethod
    def _build_conversation_history(cls, messages):
        """
        Build conversation history for Gemini API.
        
        Args:
            messages: List of Message objects
            
        Returns:
            list: List of content dictionaries for Gemini
        """
        history = []
        
        for msg in messages:
            if msg.role == 'user':
                history.append({
                    'role': 'user',
                    'parts': [{'text': msg.content}]
                })
            elif msg.role == 'assistant':
                history.append({
                    'role': 'model',
                    'parts': [{'text': msg.content}]
                })
        
        return history
    
    @classmethod
    def _get_system_prompt(cls, user_preferences=None):
        """Generate system prompt with user preferences."""
        base_prompt = """You are an intelligent AI assistant powered by Google Gemini. You are helpful, harmless, and honest.

Key behaviors:
- Provide accurate, well-reasoned responses
- When given real-time search data, use it to provide up-to-date information
- Format responses with markdown when helpful (headers, lists, code blocks)
- Be conversational and engaging
- Acknowledge when you don't know something
- For real-time queries (prices, weather, news), clearly state the data source and time sensitivity"""
        
        if user_preferences:
            name = user_preferences.get('name', '')
            interests = user_preferences.get('interests', [])
            
            if name:
                base_prompt += f"\n\nThe user's name is {name}."
            
            if interests:
                base_prompt += f"\nUser interests: {', '.join(interests)}."
        
        return base_prompt
    
    @classmethod
    def chat(cls, conversation_id, user_message, user_id, user_preferences=None):
        """
        Send a message and get AI response.
        
        Args:
            conversation_id: ID of the conversation (string ObjectId)
            user_message: The user's message text
            user_id: ID of the user (string ObjectId)
            user_preferences: Optional user preferences dict
            
        Returns:
            dict: Response containing the AI message and metadata
        """
        try:
            client = cls.get_client()
            
            # Get or create conversation
            if conversation_id:
                conversation = Conversation.get_by_id(conversation_id)
                if not conversation or conversation.user_id != user_id:
                    return {'error': 'Conversation not found'}
            else:
                # Create new conversation
                conversation = Conversation.create(user_id)
            
            # Save user message
            user_msg = conversation.add_message('user', user_message)
            
            # Get conversation history
            messages = conversation.get_messages(limit=config.MAX_CONVERSATION_HISTORY)
            
            # Check if this is a real-time query
            search_context = ""
            search_data = None
            if SearchService.is_realtime_query(user_message):
                search_results = SearchService.search(user_message)
                search_context = SearchService.format_for_context(search_results)
                search_data = search_results
            
            # Build the prompt
            system_prompt = cls._get_system_prompt(user_preferences)
            
            # Build conversation history (excluding the last user message)
            history = cls._build_conversation_history(messages[:-1])
            
            # Prepare the current message with search context
            current_message = user_message
            if search_context:
                current_message = f"{user_message}\n\n{search_context}"
            
            # Create contents list for API call
            contents = []
            
            # Add history
            contents.extend(history)
            
            # Add current user message
            contents.append({
                'role': 'user',
                'parts': [{'text': current_message}]
            })
            
            # Generate response
            response = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=contents,
                config={
                    'system_instruction': system_prompt,
                    'temperature': 0.7,
                    'max_output_tokens': 2048
                }
            )
            
            # Extract response text
            ai_response = response.text
            
            # Save AI response
            metadata = {}
            if search_data:
                metadata['search_used'] = True
                metadata['search_query'] = search_data.get('query')
            
            assistant_msg = conversation.add_message('assistant', ai_response, metadata)
            
            # Update conversation title if it's the first exchange
            if len(messages) <= 1:
                # Generate a title from the first message
                title = user_message[:50] + ('...' if len(user_message) > 50 else '')
                conversation.update_title(title)
            
            return {
                'conversation_id': conversation.id,
                'message': assistant_msg.to_dict(),
                'search_used': bool(search_data),
                'conversation': conversation.to_dict()
            }
            
        except ValueError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Failed to generate response: {str(e)}'}
    
    @classmethod
    def get_conversation_with_history(cls, conversation_id, user_id):
        """
        Get a conversation with all messages.
        
        Args:
            conversation_id: ID of the conversation (string ObjectId)
            user_id: ID of the user (string ObjectId)
            
        Returns:
            dict: Conversation data with messages
        """
        conversation = Conversation.get_by_id(conversation_id)
        
        if not conversation:
            return {'error': 'Conversation not found'}
        
        if conversation.user_id != user_id:
            return {'error': 'Unauthorized'}
        
        return conversation.to_dict(include_messages=True)
    
    @classmethod
    def get_user_conversations(cls, user_id, limit=50):
        """
        Get all conversations for a user.
        
        Args:
            user_id: ID of the user (string ObjectId)
            limit: Maximum number of conversations
            
        Returns:
            list: List of conversation dictionaries
        """
        conversations = Conversation.get_by_user(user_id, limit=limit)
        return [conv.to_dict() for conv in conversations]
    
    @classmethod
    def delete_conversation(cls, conversation_id, user_id):
        """
        Delete a conversation.
        
        Args:
            conversation_id: ID of the conversation (string ObjectId)
            user_id: ID of the user (string ObjectId)
            
        Returns:
            dict: Success or error message
        """
        conversation = Conversation.get_by_id(conversation_id)
        
        if not conversation:
            return {'error': 'Conversation not found'}
        
        if conversation.user_id != user_id:
            return {'error': 'Unauthorized'}
        
        conversation.delete()
        return {'success': True}
