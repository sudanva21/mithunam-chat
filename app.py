"""
Gemini AI Chat Application
Main Flask application entry point.
"""

import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import get_config
from routes.auth import auth_bp
from routes.chat import chat_bp
from routes.analytics import analytics_bp

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Load configuration
config = get_config()
app.config.from_object(config)

# Initialize extensions
CORS(app, resources={r"/api/*": {"origins": "*"}})
jwt = JWTManager(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(analytics_bp)


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({'error': 'Token has expired'}), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({'error': 'Invalid token'}), 401


@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({'error': 'Authorization required'}), 401


# Static file serving
@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


# Health check endpoint
@app.route('/api/health')
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'healthy',
        'service': 'Gemini AI Chat',
        'version': '1.0.0'
    }), 200


if __name__ == '__main__':
    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)
