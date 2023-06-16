import time
from flask_sqlalchemy import SQLAlchemy

from flask import Flask, render_template
from flask_socketio import SocketIO, send,join_room
from flask_cors import CORS
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@127.0.0.1/python'
db = SQLAlchemy(app)
socketio = SocketIO(app)
messageList=[]
room_list=[]
CORS(app)  # 实现跨域


class Chat(db.Model):
    __tablename__ = 'chathistory'
    id = db.Column(db.Integer, primary_key=True)  # id，为唯一标识符
    from_id = db.Column(db.Integer)  #用户id
    to_id = db.Column(db.Integer)  # 用户id
    time = db.Column(db.String(16), nullable=False)  # 帖子名
    message = db.Column(db.String(1000), nullable=False)  # 帖子内容


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)


@socketio.on('connect')
def test_connect():
    print("连接成功！")


@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')


@socketio.on('message')
def handle_message(data):
    data=eval(data)
    msg=data['message']
    from_user = data['from']
    to_user = data['to']
    room = to_user
    date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    print(date)
    print(f'from {from_user} receive message {msg} to {to_user}')
    dict = {"from": from_user, "message": msg, "date": date}
    last_record = Chat.query.order_by(Chat.id.desc()).first()
    print(last_record)
    try:
        last_record = Chat.query.order_by(Chat.id.desc()).first()
        id = int(last_record.id) + 1
    except:
        id = 1
    new_Chat = Chat(from_id=from_user, to_id=to_user, id=id, message=msg, time=date)
    db.session.add(new_Chat)
    db.session.commit()
    if room in room_list:
        send(dict, room=room)
    else:
        messageList.append({'msg': dict, 'to': room})


@socketio.on('join')
def on_join(data):
    data = eval(data)
    from_user = data['id']
    room = from_user
    print(room)
    join_room(room)
    if room not in room_list:
        room_list.append(room)
        print("新来了id"+str(room))
    send("加入房间成功", room=room)
    for i in messageList:
        if i['to'] == room:
            send(i['msg'])


