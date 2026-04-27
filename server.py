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
