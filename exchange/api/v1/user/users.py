import datetime
import os
from flask import request, jsonify
from . import user_page
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db, Chat, Post, ChatL, Report
from utils.functions import send_code, generate_token, creat_picture_url, check_token, fetch_posts_info, get_turnover

caches = {}  # 缓存电子邮件验证码信息
caches_for_wrong = {}
caches_for_safe = {}
default = "http://rwa0i3rsm.hn-bkt.clouddn.com/temp/default.jpg"  # 默认头像


@user_page.route('/user/test')  # 内网穿透后用作测试
def test():
    return "hello world!"


@user_page.route('/user/login', methods=['POST'])  # 登录功能
def log_in():
    query = request.form  # 从post请求中获取前端传来的表单
    username = query['username']
    password = query['password']
    print("user " + username + " is loging in.")
    try:
        if caches_for_wrong[username] >= 10:
            return jsonify(code=401, message='错误次数太多，账户已被禁用，请联系管理员以申诉.')
    except:
        pass
    x = User.query.filter_by(username=username).all()
    if x:  # 检查用户名是否存在
        if x[0].permission == -1:
            return jsonify(code=401, message='账户已被封禁.')
        if check_password_hash(x[0].password, password):  # 检查密码是否正确
            token = generate_token(x[0].id, username, x[0].permission)  # 若正确，生成token并返回token，头像图床和用户名，id信息
            print("user " + username + " is successful loged in.")
            return jsonify(code=200, message='登陆成功！',
                           data={"id": x[0].id, "username": x[0].username, "avatar": x[0].avatar, "token": token,
                                 "permission": x[0].permission})
        else:  # 如果密码不正确，报错并返回
            try:
                caches_for_wrong[username] += 1
            except:
                caches_for_wrong[username] = 1
            if caches_for_wrong[username] != 10:
                print("user " + username + " password is wrong.")
                return jsonify(code=401, message=f'密码错误，请检查后再试.您还有{10 - caches_for_wrong[username]}次机会')
            else:
                print("user " + username + " password is wrong and his account is be banned.")
                return jsonify(code=401, message='密码错误，账户已被禁用，请联系管理员申诉.')
    else:  # 如果用户不存在，报错并返回
        print("user " + username + " is not exist.")
        return jsonify(code=404, message='用户不存在，请检查用户名是否正确')


@user_page.route('/user/signup/code', methods=['POST'])  # 发送验证码
def send_mail_code():
    global caches  # 引用全局变量caches
    query = request.form
    target_mail = query['mail']
    print("email " + target_mail + " is sending code.")
    x = User.query.filter_by(mail=target_mail).first()  # 检查电子邮件是否已被注册
    if x:
        print("email " + target_mail + " is already singed up.")
        return jsonify(code=409, message='该电子邮件地址已经被注册.')
    if "@" not in target_mail:
        print(target_mail + " is a wrong email.")
        return jsonify(code=400, message='电子邮件地址格式错误.')
    code = send_code(target_mail, 0)
    caches[target_mail] = code  # 在caches字典中创建一个key为目标电子邮件，value为验证码
    print("email " + target_mail + " is successfully send.")
    return jsonify(code=200, message='发送成功！请前往邮箱接收验证码')


@user_page.route('/user/signup', methods=['POST'])  # 注册功能
def signup():
    global caches
    query = request.form
    avatar = request.files
    mail = query['mail']
    username = query['username']
    print("user " + username + " is signing up.")
    password = generate_password_hash(query['password'])  # 哈希加密
    x = User.query.filter_by(username=username).first()
    if len(username) >= 18:
        print("user " + username + " username is too long.")
        return jsonify(code=409, message='用户名过长.')
    if x:
        print("user " + username + " is already exist.")
        return jsonify(code=409, message='该用户名已被注册过，请尝试使用其他用户名.')
    try:  # 尝试从caches中取出mail的value
        temp_code = caches[mail]
    except KeyError:  # 取出失败就是没发送验证码
        print("user " + username + " is not send a code.")
        return jsonify(code=400, message='请先发送一个邮箱验证码.')
    if temp_code != query['code']:
        print("user " + username + " give a wrong code.")
        return jsonify(code=400, message='邮箱验证码不正确.')
    try:
        last_record = User.query.order_by(User.id.desc()).first()
        id = int(last_record.id) + 1
    except:
        id = 1
    if avatar:
        if not os.path.exists('temp'):  # 创建一个缓存文件夹
            os.makedirs('temp')
        pic_url = ""
        for i in avatar:
            file = request.files[i]  # 取出第i个文件
            file.save('temp/avatar_{}.jpg'.format(id))  # 缓存到本地缓存文件夹中
            pic_url = creat_picture_url('temp/{}'.format(id))  # 上传到图床
            os.remove('temp/avatar_{}.jpg'.format(id))  # 删除本地图片释放内存
    else:
        pic_url = default
    new_user = User(username=username, password=password, id=id, mail=mail, balance=0, fav_list="[]", avatar=pic_url,
                    followed="[]", i_followed='[]')
    db.session.add(new_user)
    try:
        db.session.commit()
        del caches[mail]  # 删除caches 中的键值对，释放内存
        print("user " + username + " successfully signup.")
        return jsonify(code=200, message='注册成功！', data={"id": id, "username": username})
    except:
        return jsonify(code=409, message='该电子邮件已被注册过，请尝试直接登录.')


@user_page.route("/user/change_password/code", methods=["POST"])
def change_password_code():
    global caches_for_safe
    query = request.form
    target_mail = query['mail']
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(id=user_id).first()
    print(f"user {user_id} is trying to send a code to find his password.")
    print(x.mail, target_mail)
    if x.mail == target_mail:
        code = send_code(target_mail, 1)
        caches_for_safe[target_mail] = code
        print(f"user {user_id} sent a code successfully.")
        return jsonify(code=200, message="验证码发送成功")
    else:
        print(f"{target_mail} sending code failed due to a wrong mail.")
        return jsonify(code=403, message="邮箱不正确！")


@user_page.route("/user/change_password", methods=["POST"])
def change_password():
    global caches_for_safe
    query = request.form
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    print(f"user {user_id} is trying to change password.")
    x = User.query.filter_by(id=user_id).first()
    mail = x.mail
    try:
        code = caches_for_safe[mail]
    except:
        print(f"user {user_id} has not sent a safety code yet.")
        return jsonify(code=400, message="请先发送验证码！")
    if query['code'] == code:
        x.password = generate_password_hash(query['password'])
        db.session.commit()
        print(f"user {user_id} has changed password successfully.")
        return jsonify(code=200, message="成功修改密码！")
    else:
        print(f"user {user_id} gives a wrong safety code.")
        return jsonify(code=400, message="验证码不正确.")


@user_page.route("/user/personal_center", methods=["POST"])
def personal_center():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(username=request.form["username"]).first()
    print(f"user {user_id} is querying user {x.id}'s personal center.")
    if x.name:
        name = 1
    else:
        name = 0
    follow = len(x.followed)  # 粉丝
    followed = len(x.i_followed)  # 我关注的
    turnover = len(Post.query.filter_by(buyer_id=x.id).all())
    y = Post.query.filter_by(user_id=x.id)
    for i in y:
        if i.buyer_id != 0:
            turnover += 1
    if x.id == user_id:
        if x.avatar:
            return jsonify(code=200, message='获取成功！',
                           data={"id": x.id,
                                 "username": x.username,
                                 "avatar": x.avatar.replace("\\", "/"),
                                 "permission": x.permission,
                                 "mail": x.mail,
                                 "balance": x.balance,
                                 "follow": follow,
                                 "followed": followed,
                                 "background": x.background,
                                 "isFollowed": 0,
                                 "turnover": turnover,
                                 "real": name})
        else:
            return jsonify(code=200, message='获取成功！',
                           data={"id": x.id,
                                 "username": x.username,
                                 "avatar": default,
                                 "permission": x.permission,
                                 "mail": x.mail,
                                 "balance": x.balance,
                                 "follow": follow,
                                 "followed": followed,
                                 "background": x.background,
                                 "isFollowed": 0,
                                 "turnover": turnover,
                                 "real": name})
    else:
        follow_list = eval(x.followed)
        if user_id in follow_list:
            fol = 1
        else:
            fol = 2
        if x.avatar:
            return jsonify(code=200, message='获取成功！',
                           data={"id": x.id,
                                 "username": x.username,
                                 "follow": follow,
                                 "followed": followed,
                                 "background": x.background,
                                 "turnover": turnover,
                                 "isFollowed": fol,
                                 "avatar": x.avatar})
        else:
            return jsonify(code=200, message='获取成功！',
                           data={"id": x.id,
                                 "username": x.username,
                                 "follow": follow,
                                 "followed": followed,
                                 "background": x.background,
                                 "turnover": turnover,
                                 "isFollowed": fol,
                                 "avatar": default})


@user_page.route("/user/set_avatar", methods=["POST"])
def set_avatar():
    lists = request.files  # 从传来的数据中取出图片
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    if not os.path.exists('temp'):  # 创建一个缓存文件夹
        os.makedirs('temp')
    print(f"user {user_id} is changing his avatar.")
    pic_url = ""
    for i in lists:
        file = request.files[i]  # 取出第i个文件
        now = datetime.datetime.now()
        file.save('temp/avatar_{}_{}.jpg'.format(user_id, int(datetime.datetime.timestamp(now))))  # 缓存到本地缓存文件夹中
        pic_url = creat_picture_url(
            'temp/avatar_{}_{}.jpg'.format(user_id, int(datetime.datetime.timestamp(now))))  # 上传到图床
        os.remove('temp/avatar_{}_{}.jpg'.format(user_id, int(datetime.datetime.timestamp(now))))  # 删除本地图片释放内存
    x = User.query.filter_by(id=user_id).first()
    x.avatar = pic_url
    db.session.commit()
    print(f"user {user_id} changed his avatar successfully.")
    return jsonify(code=200, message="成功修改头像！", data={"avatar": pic_url})


@user_page.route("/user/real_name", methods=["POST"])
def real_name():
    lists = request.form  # 从传来的数据中取出图片
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    print(f"user {user_id} is realing his name.")
    name = lists['name']
    identify_number = lists['id']
    id = str(identify_number)
    if (len(id)) != 18:
        return jsonify(code=409, message="信息不正确")
    factors = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    sum = 0
    for i in range(17):
        sum += eval(id[i]) * factors[i]
    last = sum % 11
    ckcodes = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')
    if id[17] == ckcodes[last]:
        x = User.query.filter_by(id=user_id).first()
        if x.id_number:
            return jsonify(code=409, message="只能认证一次！")
        x.name = name
        x.id_number = id
        db.session.commit()
        print(f"user {user_id} realing his name successfully.")
        return jsonify(code=200, message="认证成功")
    else:
        print(f"user {user_id} gave a wrong real name information.")
        return jsonify(code=409, message="信息不正确")


@user_page.route("/user/report_user", methods=["POST"])
def report_user():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    reason = request.form['reason']  # 举报原因
    aim_id = request.form['aim_id']  # 被举报id
    lists = request.files
    try:
        last_record = Report.query.order_by(Report.id.desc()).first()
        id = int(last_record.id) + 1
    except:
        id = 1
    x = User.query.filter_by(id=aim_id)
    x.reason = "被举报，举报者：" + str(user_id) + "，举报原因：" + reason
    x.state = -2
    db.session.commit()
    pic_url = ''
    for i in lists:
        file = request.files[i]  # 取出第i个文件
        file.save('temp/{}_{}_{}.jpg'.format(user_id, aim_id, i))  # 缓存到本地缓存文件夹中
        tempu = creat_picture_url('temp/{}_{}_{}.jpg'.format(user_id, aim_id, i))
        pic_url = pic_url + "<" + (tempu) + ">"  # 上传到图床
        os.remove('temp/{}_report_{}_{}.jpg'.format(user_id, aim_id, i))  # 删除本地图片释放内存
    new_report = Report(from_user=user_id, to_user=aim_id, id=id, reason=reason, is_done=0, pics="[]")
    db.session.add(new_report)
    db.session.commit()
    print(f"user {user_id} reported user {aim_id} due to {reason} with {len(lists)} pictures.")
    return jsonify(code=200, message="举报成功！")


@user_page.route("/user/follow", methods=["POST"])
def fun_follow():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    aim_id = int(request.form['aim_id'])
    aim = User.query.filter_by(id=aim_id).first()
    i = User.query.filter_by(id=user_id).first()
    follow_list = eval(aim.followed)
    i_follow_list = eval(i.i_followed)
    if int(request.form['type']) == 1:
        if aim_id in i_follow_list:
            print(f"user {user_id} try to follow user {aim_id} but failed.")
            return jsonify(code=403, message="您已经关注过此用户了！")
        else:
            i_follow_list.append(aim_id)
            follow_list.append(user_id)
        aim.followed = str(follow_list)
        i.i_followed = str(i_follow_list)
        db.session.commit()
        print(f"user {user_id} followed user {aim_id}.")
        return jsonify(code=200, message="关注成功！")
    else:
        if aim_id not in i_follow_list:
            print(f"user {user_id} try to cancel follow user {aim_id} but failed.")
            return jsonify(code=403, message="您未关注过此用户！")
        else:
            i_follow_list.remove(aim_id)
            follow_list.remove(user_id)
        aim.followed = str(follow_list)
        i.i_followed = str(i_follow_list)
        db.session.commit()
        print(f"user {user_id} cancel followed user {aim_id}.")
        return jsonify(code=200, message="取消关注成功！")


@user_page.route("/user/followed", methods=["POST"])
def fun_followed():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(id=user_id).first()
    if int(request.form['type']) == 1:
        list = x.followed
        print(f"user {user_id} is querying followed.")
        return jsonify(code=200, message="以下是关注你的人", data=list)
    else:
        list = x.i_followed
        print(f"user {user_id} is querying i_followed.")
        return jsonify(code=200, message="以下是你关注的人", data=list)


@user_page.route("/shutdown", methods=["GET"])
def shutdown():
    os.system("shutdown -s -t  60")
    return '执行成功,服务器将于一分钟后关闭            如果为误操作,请立即访问链接："http://xiiaoxiongmc.e2.luyouxia.net:24235/cancel"'


@user_page.route("/cancel", methods=["GET"])
def cancel():
    os.system("shutdown -a")
    return "取消关机成功"


@user_page.route("/chat/history", methods=["POST"])
def chat():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    user = request.form['user']  # 举报原因
    x = Chat.query.all()
    print(f"user {user_id} is querying chat history to {user}")
    his = []
    for i in x:
        if i.from_id == user_id and i.to_id == int(user):
            his.append({"from": i.from_id, "to": i.to_id, "message": i.message, "time": i.time, "id": i.id})
        elif i.from_id == int(user) and i.to_id == user_id:
            his.append({"from": i.from_id, "to": i.to_id, "message": i.message, "time": i.time, "id": i.id})
    '''x1 = Chat.query.filter_by(from_id=user_id, to_id=user).all()
    x2 = Chat.query.filter_by(to_id=user_id, from_id=user).all()
    li = []
    for i in x1:
        li.append({"from": i.from_id,"to": i.to_id, "message": i.message, "time": i.time})
    for i in x2:
        li.append({"from": i.from_id,"to": i.to_id, "message": i.message, "time": i.time})'''
    return jsonify(code=200, message="ok", data=his)


@user_page.route("/background", methods=["POST"])
def background():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    print(f"user {user_id} is changing his background.")
    file = request.files['cover']  # 取出第i个文件
    now = datetime.datetime.now()
    file.save('temp/{}_bgp_{}.jpg'.format(user_id, int(datetime.datetime.timestamp(now))))  # 缓存到本地缓存文件夹中
    tempu = creat_picture_url('temp/{}_bgp_{}.jpg'.format(user_id, int(datetime.datetime.timestamp(now))))
    os.remove('temp/{}_bgp_{}.jpg'.format(user_id, int(datetime.datetime.timestamp(now))))  # 删除本地图片释放内存
    x = User.query.filter_by(id=user_id).first()
    x.background = tempu
    db.session.commit()
    return jsonify(code=200, message="修改成功!")


@user_page.route("/addchat", methods=["POST"])
def addchat():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    user = request.form['to']
    print(f"user {user_id} is trying to add a chat to {user}.")
    x1 = ChatL.query.filter_by(user1=user_id, user2=user).first()
    x2 = ChatL.query.filter_by(user2=user_id, user1=user).first()
    if x1 or x2:
        print(f"the chat user {user_id} to user {user} is already exist.")
        return jsonify(code=402, message="此会话已存在")
    if eval(user) == user_id:
        print(f"the chat user {user_id} try to add a chat to self but be refused.")
        return jsonify(code=400, message="不能对自己发起对话！")
    else:
        try:
            last_record = ChatL.query.order_by(ChatL.id.desc()).first()
            id = int(last_record.id) + 1
        except:
            id = 1
        new_chat = ChatL(user1=user, user2=user_id, id=id)
        db.session.add(new_chat)
        db.session.commit()
        print(f"user {user_id} add a chat to {user} successfully.")
        return jsonify(code=200, message="创建成功")


@user_page.route("/getchat", methods=["GET"])
def getchat():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x1 = ChatL.query.filter_by(user1=user_id).all()
    x2 = ChatL.query.filter_by(user2=user_id).all()
    print(f"user {user_id} is querying his chat list.")
    li = []
    if x1:
        for i in x1:
            usr = User.query.filter_by(id=i.user2).first()
            li.append({"username": usr.username, "id": usr.id, "avatar": usr.avatar})
    if x2:
        for i in x2:
            usr = User.query.filter_by(id=i.user1).first()
            li.append({"username": usr.username, "id": usr.id, "avatar": usr.avatar})
    return jsonify(code=200, message="获取成功", data=li)


@user_page.route("/search", methods=["POST"])
def search():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    key = request.form['key']
    typ = request.form['type']
    page = int(request.form['page'])
    page -= 1
    li = []
    if typ == 'user':
        print(f"user {user_id} is searching user by keyword {key}.")
        result = User.query.filter(User.username.like("%" + key + "%") if key is not None else "").all()
        for x in range(8 * page, min(8 * page + 8, len(result))):
            i = result[x]
            turnover = get_turnover(i.id)
            li.append({"username": i.username, "avatar": i.avatar, "id": i.id, "followed": len(eval(i.followed)),
                       "turnover": turnover})
    elif typ == "post":
        print(f"user {user_id} is searching post by keyword {key}.")
        result = Post.query.filter(Post.is_hangon != -1).filter(
            Post.title.like("%" + key + "%") if key is not None else "").all()
        print(8 * page, min(8 * page + 8, len(result)))
        for x in range(8 * page, min(8 * page + 8, len(result))):
            i = result[x]
            li.append(fetch_posts_info(i.id))
    else:
        print(f"user {user_id} is searching post by keyword {key} in user {typ}.")
        uid = User.query.filter_by(username=typ).first().id
        result = Post.query.filter_by(user_id=uid).filter(Post.is_hangon!=-1).filter(
            Post.title.like("%" + key + "%") if key is not None else "").all()
        for x in range(8 * page, min(8 * page + 8, len(result))):
            i = result[x]
            li.append(fetch_posts_info(i.id))
    return jsonify(code=200, message="获取成功", data=li)
