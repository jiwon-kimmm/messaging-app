from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

# basic setup for flask application
app = Flask(__name__)
app.config["SECRET_KEY"] = "lskdjflksj"
socketio = SocketIO(app)

rooms = {}

def generate_unique_code(Length):
    while True:
        code = ""
        # _ is anonymous iteration variable
        for _ in range(Length):
            code += random.choice(ascii_uppercase)

        # checks if code exists as key in dictionary
        if code not in rooms:
            break
    
    return code


# allowed methods to be sent to this route
@app.route("/", methods=["POST", "GET"])
def home():
    # if they type in another room or another page, delete anything inside the session
    session.clear()

    if request.method == "POST":
        #grab form data
        name = request.form.get("name")
        code = request.form.get("code")

        #attempt to get this out of dictionary
        # if create/join does not exist, return False
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            # give back the values so we can reenter values for our input field to home.html
            return render_template("home.html", error="Please enter a name.", code=code, name=name)
        
        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False: 
            room = generate_unique_code(4)
            # add room to dictionary
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        # session is a semi-permanent way of storing data
        # temporary data stored on a server
        session["room"] = room
        session["name"] = name

        return redirect(url_for("room"))

    return render_template("home.html")


@app.route("/room")
def room():
    room = session.get("room")
    # can't directly go to room page /room
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    
    # so that we know the room code when on room page
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }

    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    # use room code and room name to determine which to go into
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return 
    
    if room not in rooms:
        leave_room() # from socketio
        return
    
    join_room(room) # puts user in socket room
    # send to all people in this room
    send({"name": name, "message": "has entered the room"}, to=room)

    #increase number of members by 1 since someone has entered
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1

        # delete room if no more members
        if rooms[room]["members"] <= 0:
            del rooms[room]
        
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)