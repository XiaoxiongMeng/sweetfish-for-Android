import time
from flask_sqlalchemy import SQLAlchemy

from flask import Flask, render_template
from flask_socketio import SocketIO, send, join_room
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

    print(f'from {from_user} receive message {msg} to {to_user}')
    try:
        last_record = Chat.query.order_by(Chat.id.desc()).first()
        id = int(last_record.id) + 1
    except:
        id = 1
    send({"type": "receipt", "message": "信息发送成功！", "id": id})
    dict = {"from": from_user, "message": msg, "date": date, "type": "receive", "id": id}
    new_Chat = Chat(from_id=from_user, to_id=to_user, id=id, message=msg, time=date)
    db.session.add(new_Chat)
    db.session.commit()
    print(send(dict, room=room))
    if send(dict, room=room):
        print(1)
    else:
        print(0)
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
    send({"type": "receipt", "message":"加入成功！"})
    for i in messageList:
        if i['to'] == room:
            send(i['msg'])


@socketio.on('revocation')
def revocation(data):
    data = eval(data)
    id=data['id']
    msg = Chat.query.filter_by(id=id).first()
    to_id = msg.to_id
    send({"id": id, "type": "revocation"}, room=to_id)
    db.session.delete(msg)
    db.session.commit()
