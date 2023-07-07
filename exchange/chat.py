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


class ChatL(db.Model):
    __tablename__ = 'chatlist'
    user1 = db.Column(db.Integer)  # 用户id
    user2 = db.Column(db.Integer)  # 用户id
    id = db.Column(db.Integer, primary_key=True)  # id，为唯一标识符


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
    try:
        data = eval(data)
    except:
        data = data
    msg=data['message']
    from_user = int(data['from'])
    to_user = int(data['to'])
    room = to_user
    date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    print(f'from {from_user} receive message {msg} to {to_user}')
    try:
        last_record = Chat.query.order_by(Chat.id.desc()).first()
        id = int(last_record.id) + 1
    except:
        id = 1
    send({"type": "receipt", "message": "信息发送成功！", "id": id}, room=from_user)
    dict = {"from": from_user, "message": msg, "date": date, "type": "receive", "id": id}
    new_Chat = Chat(from_id=from_user, to_id=to_user, id=id, message=msg, time=date)
    db.session.add(new_Chat)
    db.session.commit()
    if room in room_list:
        send(dict, room=room)
        print(f'from {from_user} receive message {msg} to {to_user} send success.')
    else:
        messageList.append({'msg': dict, 'to': room})
        print(f'from {from_user} receive message {msg} to {to_user} will be sent.')


@socketio.on('join')
def on_join(data):
    try:
        data = eval(data)
    except:
        data = data
    from_user = int(data['id'])
    room = from_user
    print(type(room),room)
    join_room(room)
    if room not in room_list:
        room_list.append(room)
        print("新来了id"+str(room))
    send({"type": "joined", "message":"加入成功！"}, room=room)
    for i in messageList:
        if i['to'] == room:
            send(i['msg'])


@socketio.on('revocation')
def revocation(data):
    try:
        data = eval(data)
    except:
        data = data
    id=data['id']
    msg = Chat.query.filter_by(id=id).first()
    to_id = msg.to_id
    from_id = msg.from_id
    send({"id": id, "type": "revocation"}, room=to_id)
    send({"message": "撤回成功", "type": "receipt"}, room=from_id)
    db.session.delete(msg)
    db.session.commit()


'''@socketio.on('giveprice')
def confirm(data):
    try:
        data = eval(data)
    except:
        data = data
    buyer=data['buyer']
    seller=data['seller']
    id=
    try:
        new_chat = ChatL(user1=buyer, user2=seller, id=id)
        db.session.add(new_chat)
        db.session.commit()
    except:
        pass
    send({"id": pid, "type": "confirm", "message": f"有买家花费{price}购买你的商品：【{title}】，请前往确认"},
         room=seller,
         namespace="message")


@socketio.on('message')
def account_info(account, password, buyer, seller):
    try:
        new_chat = ChatL(user1=buyer, user2=seller, id=id)
        db.session.add(new_chat)
        db.session.commit()
    except:
        pass
    send({"account": account, "type": "account_info", "password": password},
         room=buyer,
         namespace="message")


@socketio.on('message')
def back(pid,buyer,seller):
    try:
        new_chat = ChatL(user1=buyer, user2=seller, id=id)
        db.session.add(new_chat)
        db.session.commit()
    except:
        pass
    send({"type": "back", "message": f"卖家驳回了你{pid}的申请"},
         room=buyer,
         namespace="message")'''