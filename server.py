from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active users and rooms
active_users = {}
rooms = {}

@app.route('/')
def index():
    return render_template('chat.html')