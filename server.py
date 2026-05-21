from flask import Flask, render_template, request, Response, jsonify, session
from datetime import datetime
import json
import os
import uuid
import secrets
from queue import Queue
import signal
import sys

app = Flask(__name__)
# Use environment variable for secret key in production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Store data structures
active_users = {}  # session_id -> username
message_queue = []  # Store all messages
broadcast_queues = {}  # session_id -> queue
message_id_counter = 0


def generate_message_id():
    global message_id_counter
    message_id_counter += 1
    return message_id_counter


@app.route('/')
def index():
    session['user_id'] = str(uuid.uuid4())
    return render_template('chat.html')


@app.route('/health')
def health():
    """Health check endpoint for production"""
    return jsonify({'status': 'healthy', 'users': len(active_users)}), 200


@app.route('/join', methods=['POST'])
def join_chat():
    """Handle user joining the chat"""
    data = request.get_json()
    username = data.get('username', '').strip()

    if not username or len(username) > 20:
        return jsonify({'error': 'Invalid username'}), 400

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Session error'}), 400

    # Check for duplicate username
    if username in active_users.values():
        return jsonify({'error': 'Username already taken'}), 400

    active_users[user_id] = username

    # Add system message
    system_message = {
        'id': generate_message_id(),
        'username': 'System',
        'text': f'{username} joined the chat',
        'timestamp': datetime.now().strftime('%I:%M %p'),
        'system': True
    }
    message_queue.append(system_message)

    # Keep only last 200 messages
    if len(message_queue) > 200:
        message_queue.pop(0)

    # Notify all connected clients
    notify_all_clients('user_joined', {
        'username': username,
        'users': list(active_users.values())
    })

    return jsonify({
        'success': True,
        'username': username,
        'users': list(active_users.values()),
        'messages': message_queue[-50:]
    })


@app.route('/send_message', methods=['POST'])
def send_message():
    """Handle sending a new message"""
    data = request.get_json()
    text = data.get('text', '').strip()
    user_id = session.get('user_id')

    if not text:
        return jsonify({'error': 'Empty message'}), 400

    username = active_users.get(user_id)
    if not username:
        return jsonify({'error': 'User not found'}), 400

    # Basic spam protection
    if len(text) > 500:
        return jsonify({'error': 'Message too long'}), 400

    message = {
        'id': generate_message_id(),
        'username': username,
        'text': text[:500],
        'timestamp': datetime.now().strftime('%I:%M %p'),
        'system': False
    }
    message_queue.append(message)

    # Keep only last 200 messages
    if len(message_queue) > 200:
        message_queue.pop(0)

    # Broadcast to all clients
    notify_all_clients('new_message', message)

    return jsonify({'success': True})


@app.route('/typing', methods=['POST'])
def typing_indicator():
    """Handle typing indicators"""
    data = request.get_json()
    is_typing = data.get('is_typing', False)
    user_id = session.get('user_id')

    username = active_users.get(user_id)
    if username:
        notify_all_clients('user_typing', {
            'username': username,
            'is_typing': is_typing
        }, exclude_user_id=user_id)

    return jsonify({'success': True})


@app.route('/leave', methods=['POST'])
def leave_chat():
    """Handle user leaving"""
    user_id = session.get('user_id')
    username = active_users.pop(user_id, None)

    if username:
        system_message = {
            'id': generate_message_id(),
            'username': 'System',
            'text': f'{username} left the chat',
            'timestamp': datetime.now().strftime('%I:%M %p'),
            'system': True
        }
        message_queue.append(system_message)

        if len(message_queue) > 200:
            message_queue.pop(0)

        notify_all_clients('user_left', {
            'username': username,
            'users': list(active_users.values())
        })

    return jsonify({'success': True})


@app.route('/stream')
def stream():
    """Server-Sent Events endpoint for real-time updates"""
    user_id = session.get('user_id')

    if not user_id or user_id not in active_users:
        return Response("Unauthorized", status=401)

    def event_stream():
        # Create a queue for this client
        client_queue = Queue()
        broadcast_queues[user_id] = client_queue

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"

            while True:
                # Wait for events with timeout
                try:
                    event = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except Exception:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

        except GeneratorExit:
            pass
        finally:
            # Clean up
            if user_id in broadcast_queues:
                del broadcast_queues[user_id]

    return Response(event_stream(),
                    mimetype="text/event-stream",
                    headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })


def notify_all_clients(event_type, data, exclude_user_id=None):
    """Send event to all connected clients"""
    event_data = {
        'type': event_type,
        'data': data
    }

    disconnected = []
    for user_id, queue in broadcast_queues.items():
        if user_id != exclude_user_id:
            try:
                queue.put_nowait(event_data)
            except:
                disconnected.append(user_id)

    # Clean up disconnected clients
    for user_id in disconnected:
        if user_id in broadcast_queues:
            del broadcast_queues[user_id]

# Clean shutdown handling


def shutdown_handler(signum, frame):
    print("Shutting down gracefully...")
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
