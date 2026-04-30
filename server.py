from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import uuid

app = Flask(__name__)
app.config["SECRET_KEY"] = "advaith"
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active users and rooms
active_users = {}
rooms = {}


@app.route("/")
def index():
    return render_template("chat.html")


@socketio.on("connect")
def handle_connect():
    print(f"Client connected: {request.sid}")

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