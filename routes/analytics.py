"""
Analytics routes for dashboard data with MongoDB.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime, timedelta
from models import get_db

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@analytics_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """Get user statistics for the dashboard."""
    user_id = get_jwt_identity()
    db = get_db()
    
    try:
        user_oid = ObjectId(user_id)
        
        # Total conversations
        total_conversations = db.conversations.count_documents({'user_id': user_oid})
        
        # Get all conversation IDs for this user
        conv_ids = [c['_id'] for c in db.conversations.find({'user_id': user_oid}, {'_id': 1})]
        
        # Total messages
        total_messages = db.messages.count_documents({'conversation_id': {'$in': conv_ids}}) if conv_ids else 0
        
        # Messages today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        messages_today = db.messages.count_documents({
            'conversation_id': {'$in': conv_ids},
            'created_at': {'$gte': today_start}
        }) if conv_ids else 0
        
        # Active conversations (updated in last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_conversations = db.conversations.count_documents({
            'user_id': user_oid,
            'updated_at': {'$gte': week_ago}
        })
        
        # Average messages per conversation
        avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
        
        # Search queries used
        search_queries = db.messages.count_documents({
            'conversation_id': {'$in': conv_ids},
            'metadata.search_used': True
        }) if conv_ids else 0
        
        return jsonify({
            'stats': {
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'messages_today': messages_today,
                'active_conversations': active_conversations,
                'avg_messages_per_conversation': round(avg_messages, 1),
                'search_queries_used': search_queries
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/usage', methods=['GET'])
@jwt_required()
def get_usage_over_time():
    """Get usage data over time for charts."""
    user_id = get_jwt_identity()
    days = request.args.get('days', 30, type=int)
    db = get_db()
    
    try:
        user_oid = ObjectId(user_id)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all conversation IDs for this user
        conv_ids = [c['_id'] for c in db.conversations.find({'user_id': user_oid}, {'_id': 1})]
        
        # Aggregate messages by day
        pipeline = [
            {
                '$match': {
                    'conversation_id': {'$in': conv_ids},
                    'created_at': {'$gte': start_date}
                }
            },
            {
                '$group': {
                    '_id': {
                        '$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}
                    },
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'_id': 1}}
        ]
        
        daily_messages_raw = list(db.messages.aggregate(pipeline)) if conv_ids else []
        date_counts = {item['_id']: item['count'] for item in daily_messages_raw}
        
        # Fill in missing days with 0
        filled_data = []
        for i in range(days + 1):
            date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            filled_data.append({
                'date': date,
                'count': date_counts.get(date, 0)
            })
        
        # Aggregate conversations by day
        conv_pipeline = [
            {
                '$match': {
                    'user_id': user_oid,
                    'created_at': {'$gte': start_date}
                }
            },
            {
                '$group': {
                    '_id': {
                        '$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}
                    },
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'_id': 1}}
        ]
        
        daily_conversations = [
            {'date': item['_id'], 'count': item['count']}
            for item in db.conversations.aggregate(conv_pipeline)
        ]
        
        return jsonify({
            'usage': {
                'daily_messages': filled_data,
                'daily_conversations': daily_conversations
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/topics', methods=['GET'])
@jwt_required()
def get_conversation_topics():
    """Get popular conversation topics based on titles."""
    user_id = get_jwt_identity()
    limit = request.args.get('limit', 10, type=int)
    db = get_db()
    
    try:
        user_oid = ObjectId(user_id)
        
        # Get recent conversations with message counts
        pipeline = [
            {'$match': {'user_id': user_oid}},
            {'$sort': {'updated_at': -1}},
            {'$limit': limit},
            {
                '$lookup': {
                    'from': 'messages',
                    'localField': '_id',
                    'foreignField': 'conversation_id',
                    'as': 'messages'
                }
            },
            {
                '$project': {
                    'title': 1,
                    'created_at': 1,
                    'updated_at': 1,
                    'message_count': {'$size': '$messages'}
                }
            }
        ]
        
        topics = []
        for doc in db.conversations.aggregate(pipeline):
            topics.append({
                'id': str(doc['_id']),
                'title': doc.get('title', 'Untitled'),
                'message_count': doc.get('message_count', 0),
                'created_at': doc['created_at'].isoformat() if doc.get('created_at') else None,
                'updated_at': doc['updated_at'].isoformat() if doc.get('updated_at') else None
            })
        
        return jsonify({'topics': topics}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/insights', methods=['GET'])
@jwt_required()
def get_insights():
    """Get AI usage insights."""
    user_id = get_jwt_identity()
    db = get_db()
    
    try:
        user_oid = ObjectId(user_id)
        
        # Get all conversation IDs for this user
        conv_ids = [c['_id'] for c in db.conversations.find({'user_id': user_oid}, {'_id': 1})]
        
        if not conv_ids:
            return jsonify({
                'insights': {
                    'most_active_hour': None,
                    'most_active_day': None,
                    'avg_response_length': 0,
                    'longest_conversation': None
                }
            }), 200
        
        # Most active hour
        hour_pipeline = [
            {
                '$match': {
                    'conversation_id': {'$in': conv_ids},
                    'role': 'user'
                }
            },
            {
                '$group': {
                    '_id': {'$hour': '$created_at'},
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'count': -1}},
            {'$limit': 1}
        ]
        
        hour_result = list(db.messages.aggregate(hour_pipeline))
        most_active_hour = str(hour_result[0]['_id']).zfill(2) if hour_result else None
        
        # Most active day of week
        day_pipeline = [
            {
                '$match': {
                    'conversation_id': {'$in': conv_ids},
                    'role': 'user'
                }
            },
            {
                '$group': {
                    '_id': {'$dayOfWeek': '$created_at'},
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'count': -1}},
            {'$limit': 1}
        ]
        
        day_result = list(db.messages.aggregate(day_pipeline))
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        most_active_day = day_names[day_result[0]['_id'] - 1] if day_result else None
        
        # Average response length
        avg_pipeline = [
            {
                '$match': {
                    'conversation_id': {'$in': conv_ids},
                    'role': 'assistant'
                }
            },
            {
                '$group': {
                    '_id': None,
                    'avg_length': {'$avg': {'$strLenCP': '$content'}}
                }
            }
        ]
        
        avg_result = list(db.messages.aggregate(avg_pipeline))
        avg_response_length = round(avg_result[0]['avg_length']) if avg_result and avg_result[0]['avg_length'] else 0
        
        # Longest conversation
        longest_pipeline = [
            {'$match': {'user_id': user_oid}},
            {
                '$lookup': {
                    'from': 'messages',
                    'localField': '_id',
                    'foreignField': 'conversation_id',
                    'as': 'messages'
                }
            },
            {
                '$project': {
                    'title': 1,
                    'message_count': {'$size': '$messages'}
                }
            },
            {'$sort': {'message_count': -1}},
            {'$limit': 1}
        ]
        
        longest_result = list(db.conversations.aggregate(longest_pipeline))
        longest_conversation = {
            'id': str(longest_result[0]['_id']),
            'title': longest_result[0].get('title', 'Untitled'),
            'message_count': longest_result[0].get('message_count', 0)
        } if longest_result else None
        
        return jsonify({
            'insights': {
                'most_active_hour': most_active_hour,
                'most_active_day': most_active_day,
                'avg_response_length': avg_response_length,
                'longest_conversation': longest_conversation
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
