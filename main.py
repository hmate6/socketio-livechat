from flask import Flask, render_template, request, make_response, redirect, url_for, session, abort
from flask_socketio import SocketIO, emit, join_room
from os import listdir
from random import choice
from time import time
from get_country import get_country_from_ip
import os
import secrets
import bleach
from os import getenv
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import datetime


# 127.0.0.1:5000 címen elérhető
connected_clients = {}
names = []
load_dotenv()
HOST_IP = getenv("HOST_IP", "127.0.0.1:5000")
app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or secrets.token_hex(32)

if not "127.0.0.1" in HOST_IP:
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True

# Nincs használva mert .txt fájlba vannak mentve a csevegések
#app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///app.db"
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app, cors_allowed_origins="*", transports=['websocket'])
CORS(app)
CURRENT_YEAR=str(datetime.now().year)

if not os.path.exists("msg.txt"):
    open("msg.txt", mode="w", encoding="utf-8").close()


@app.route("/")
def homepage():
    try:
        session["ipaddress"] = request.headers.get('X-Forwarded-For', '').split(",")[0] or "127.0.0.1"
    except KeyError:
        session["ipaddress"] = "127.0.0.1"

    selection = choice(listdir("static/img/patterns/"))

    return render_template("index.html", selection=selection, accepted="True")


@app.route("/global")
def chat():
    name = session.get('name', '')
    if not name:
        return redirect(url_for('homepage'))

    with open("msg.txt", mode="r", encoding="utf-8") as f:
        chatlist = f.readlines()

    selection = choice(listdir("static/img/patterns/"))

    return render_template("ind.html", name=name, room="globalroom",
                           length_of_name=len(name), chat_history=chatlist, selection=selection,
                           HOST_IP=HOST_IP, CURRENT_YEAR=CURRENT_YEAR)

@app.route("/joining")
def redirect_to_chat():
    return redirect(url_for("chat"))

@app.route("/joining", methods=["POST"])
def join_chat():
    tim1 = time()
    name = bleach.clean(request.form.get('name', 'Anonymous'))

    if name in names:
        names_filtered = [x for x in names if x.startswith(name) and x.endswith(")")]

        numbers = []
        for n in names_filtered:
            start = n.rfind("(") + 1
            end = n.rfind(")")
            num_str = n[start:end]
            if num_str.isdigit():
                numbers.append(int(num_str))

        counter = max(numbers, default=-1) + 1
        name = f"{name} ({counter})"

    names.append(name)

    session["name"] = name

    session["ipaddress"] = request.headers.get('X-Forwarded-For', "").split(",")[0] or "127.0.0.1"
    session["countrycode"] = get_country_from_ip(session.get("ipaddress"))

    tim2 = time()
    print("Loading time /joining: ", tim2 - tim1)

    resp = make_response(redirect(url_for("chat")))
    resp.set_cookie('accepted_warning', 'True', secure=True, httponly=True)
    return resp



@socketio.on('joined', namespace='/chat')
def joined(message):
    name = session.get("name")
    sid = request.sid
    connected_clients[sid] = name

    join_room("globalroom")
    emit('message',
         {'msg': session.get("countrycode", "us") + bleach.clean(name) + ' has entered the chat.'},
         room="globalroom", safe=True)


@socketio.on('disconnect', namespace='/chat')
def on_disconnect():
    sid = request.sid
    name = connected_clients.get(sid)

    connected_clients.pop(sid, None)

    emit('message', {'msg': session.get("countrycode", "us") + bleach.clean(name) + ' has left the chat.'},
         room="globalroom", safe=True)


@socketio.on('text', namespace='/chat')
def text(message):
    msg = bleach.clean(message['msg'])
    user = session.get("name", "Anonymous")
    country_code = session.get("countrycode", "us")

    with open("msg.txt", mode="a") as f:
        f.write(f"{country_code}{user}: {msg};{datetime.now()}\n")

    emit('message', {'msg': f'{country_code}{user}: {msg}'}, room="globalroom", safe=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", allow_unsafe_werkzeug=True)
