from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import uuid
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')

socketio = SocketIO(app,
                    cors_allowed_origins="*",
                    async_mode='eventlet')

# Store active users and rooms
active_users = {}
rooms = {}


@app.route('/')
def index():
    return render_template('chat.html')


@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    username = active_users.get(request.sid)
    if username:
        # Remove user from active users
        del active_users[request.sid]
        # Notify all clients
        emit('user_left', {
            'username': username,
            'timestamp': datetime.now().strftime('%I:%M %p')
        }, broadcast=True)
        # Update user list
        emit('update_users', list(active_users.values()), broadcast=True)


@socketio.on('join')
def handle_join(data):
    username = data['username']
    active_users[request.sid] = username

    # Send welcome message
    emit('message', {
        'username': 'System',
        'text': f'Welcome {username} to the chat!',
        'timestamp': datetime.now().strftime('%I:%M %p'),
        'system': True
    })

    # Notify others
    emit('user_joined', {
        'username': username,
        'timestamp': datetime.now().strftime('%I:%M %p')
    }, broadcast=True, include_self=False)

    # Update user list for all
    emit('update_users', list(active_users.values()), broadcast=True)


@socketio.on('send_message')
def handle_message(data):
    username = active_users.get(request.sid, 'Anonymous')
    message_data = {
        'username': username,
        'text': data['text'],
        'timestamp': datetime.now().strftime('%I:%M %p'),
        'system': False
    }
    emit('message', message_data, broadcast=True)


@socketio.on('typing')
def handle_typing(data):
    username = active_users.get(request.sid)
    if username:
        emit('user_typing', {
            'username': username,
            'is_typing': data['is_typing']
        }, broadcast=True, include_self=False)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
