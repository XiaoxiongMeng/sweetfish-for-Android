import os
from flask import request, jsonify
from . import user_page
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db, Chat, Post
from utils.functions import send_code, generate_token, creat_picture_url, check_token

caches = {}  # 缓存电子邮件验证码信息
caches_for_wrong = {}
caches_for_safe = {}


@user_page.route('/user/test')  # 内网穿透后用作测试
def test():
    return "hello world!"


@user_page.route('/user/login', methods=['POST'])  # 登录功能
def log_in():
    query = request.form  # 从post请求中获取前端传来的表单
    username = query['username']
    password = query['password']
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
            return jsonify(code=200, message='登陆成功！',
                           data={"id": x[0].id, "username": x[0].username, "avatar": x[0].avatar, "token": token,
                                 "permission": x[0].permission})
        else:  # 如果密码不正确，报错并返回
            try:
                caches_for_wrong[username] += 1
            except:
                caches_for_wrong[username] = 1
            if caches_for_wrong[username] != 10:
                return jsonify(code=401, message=f'密码错误，请检查后再试.您还有{10 - caches_for_wrong[username]}次机会')
            else:
                return jsonify(code=401, message='密码错误，账户已被禁用，请联系管理员申诉.')
    else:  # 如果用户不存在，报错并返回
        return jsonify(code=404, message='用户不存在，请检查用户名是否正确')


@user_page.route('/user/signup/code', methods=['POST'])  # 发送验证码
def send_mail_code():
    global caches  # 引用全局变量caches
    query = request.form
    target_mail = query['mail']
    x = User.query.filter_by(mail=target_mail).first()  # 检查电子邮件是否已被注册
    if x:
        return jsonify(code=409, message='该电子邮件地址已经被注册.')
    if "@" not in target_mail:
        return jsonify(code=400, message='电子邮件地址格式错误.')
    code = send_code(target_mail, 0)
    caches[target_mail] = code  # 在caches字典中创建一个key为目标电子邮件，value为验证码
    return jsonify(code=200, message='发送成功！请前往邮箱接收验证码')


@user_page.route('/user/signup', methods=['POST'])  # 注册功能
def signup():
    global caches
    query = request.form
    avatar = request.files
    mail = query['mail']
    username = query['username']
    password = generate_password_hash(query['password'])  # 哈希加密
    x = User.query.filter_by(username=username).first()
    if len(username) >= 18:
        return jsonify(code=409, message='用户名过长.')
    if x:
        return jsonify(code=409, message='该用户名已被注册过，请尝试使用其他用户名.')
    try:  # 尝试从caches中取出mail的value
        temp_code = caches[mail]
    except KeyError:  # 取出失败就是没发送验证码
        return jsonify(code=400, message='请先发送一个邮箱验证码.')
    if temp_code != query['code']:
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
        pic_url = "https://www.hualigs.cn/image/6454da18351aa.jpg"
    new_user = User(username=username, password=password, id=id, mail=mail, balance=0, fav_list="[]", avatar=pic_url,follow="[]",i_follow='[]')
    db.session.add(new_user)
    try:
        db.session.commit()
        del caches[mail]  # 删除caches 中的键值对，释放内存
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
    print(x.mail, target_mail)
    if x.mail == target_mail:
        code = send_code(target_mail, 1)
        caches_for_safe[target_mail] = code
        return jsonify(code=200, message="验证码发送成功")
    else:
        return jsonify(code=403, message="邮箱不正确！")


@user_page.route("/user/change_password", methods=["POST"])
def change_password():
    global caches_for_safe
    query = request.form
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(id=user_id).first()
    mail = x.mail
    try:
        code = caches_for_safe[mail]
    except:
        return jsonify(code=400, message="请先发送验证码！")
    if query['code'] == code:
        x.password = generate_password_hash(query['password'])
        db.session.commit()
        return jsonify(code=200, message="成功修改密码！")
    else:
        return jsonify(code=400, message="验证码不正确.")


@user_page.route("/user/personal_center", methods=["POST"])
def personal_center():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(username=request.form["username"]).first()
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
            print(i.id)
    if x.username == request.form["username"]:
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
                                 "turnover": turnover,
                                 "real": name})
        else:
            return jsonify(code=200, message='获取成功！',
                           data={"id": x.id,
                                 "username": x.username,
                                 "avatar": "http://rwa0i3rsm.hn-bkt.clouddn.com/temp/default.jpg",
                                 "permission": x.permission,
                                 "mail": x.mail,
                                 "balance": x.balance,
                                 "follow": follow,
                                 "followed": followed,
                                 "background": x.background,
                                 "turnover": turnover,
                                 "real": name})
    else:
        if x.avatar:
            return jsonify(code=200, message='获取成功！',
                           data={"id": x.id,
                                 "username": x.username,
                                 "follow": follow,
                                 "followed": followed,
                                 "background": x.background,
                                 "turnover": turnover,
                                 "avatar": x.avatar})
        else:
            return jsonify(code=200, message='获取成功！',
                           data={"id": x.id,
                                 "username": x.username,
                                 "follow": follow,
                                 "followed": followed,
                                 "background": x.background,
                                 "turnover": turnover,
                                 "avatar": "http://rwa0i3rsm.hn-bkt.clouddn.com/temp/default.jpg"})


@user_page.route("/user/set_avatar", methods=["POST"])
def set_avatar():
    lists = request.files  # 从传来的数据中取出图片
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    if not os.path.exists('temp'):  # 创建一个缓存文件夹
        os.makedirs('temp')
    pic_url = ""
    for i in lists:
        file = request.files[i]  # 取出第i个文件
        file.save('temp/avatar_{}.jpg'.format(user_id))  # 缓存到本地缓存文件夹中
        pic_url = creat_picture_url('temp/avatar_{}.jpg'.format(user_id))  # 上传到图床
        os.remove('temp/avatar_{}.jpg'.format(user_id))  # 删除本地图片释放内存
    x = User.query.filter_by(id=user_id).first()
    x.avatar = pic_url
    db.session.commit()
    return jsonify(code=200, message="成功修改头像！", data={"avatar": pic_url})


@user_page.route("/user/real_name", methods=["POST"])
def real_name():
    lists = request.form  # 从传来的数据中取出图片
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
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
        return jsonify(code=200, message="认证成功")
    else:
        return jsonify(code=409, message="信息不正确")


@user_page.route("/user/report_user", methods=["POST"])
def report_user():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    reason = request.form['reason']  # 举报原因
    aim_id = request.form['aim_id']  # 被举报id
    x = User.query.filter_by(id=aim_id)
    x.reason = "被举报，举报者：" + str(user_id) + "，举报原因：" + reason
    x.state = -2
    db.session.commit()
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
            return jsonify(code=403, message="您已经关注过此用户了！")
        else:
            i_follow_list.append(aim_id)
            follow_list.append(user_id)
        aim.followed = str(follow_list)
        i.i_followed = str(i_follow_list)
        db.session.commit()
        return jsonify(code=200, message="关注成功！")
    else:
        if aim_id not in i_follow_list:
            return jsonify(code=403, message="您未关注过此用户！")
        else:
            i_follow_list.remove(aim_id)
            follow_list.remove(user_id)
        aim.followed = str(follow_list)
        i.i_followed = str(i_follow_list)
        db.session.commit()
        return jsonify(code=200, message="取消关注成功！")


@user_page.route("/user/followed", methods=["POST"])
def fun_followed():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(id=user_id).first()
    if int(request.form['type'])==1:
        list = x.followed
        return jsonify(code=200, message="以下是关注你的人", data=list)
    else:
        list = x.i_followed
        return jsonify(code=200, message="以下是你关注的人", data=list)


@user_page.route("/shutdown", methods=["GET"])
def shutdown():
    os.system("shutdown -s -t  60")
    return '执行成功,服务器将于一分钟后关闭            如果为误操作,请立即访问链接："http://xiiaoxiongmc.e2.luyouxia.net:24235/cancel"'


@user_page.route("/cancel", methods=["GET"])
def cancel():
    os.system("shutdown -a")
    return "取消关机成功"


@user_page.route("/chat/history", methods=["GET"])
def chat():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    user1 = request.form['user1']  # 举报原因
    user2 = request.form['user2']  # 被举报id
    x1 = Chat.query.filter_by(from_user=user1, to_user=user2)
    x2 = Chat.query.filter_by(to_user=user2,from_user=user1)


@user_page.route("/cover", methods=["POST"])
def background():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    file = request.files['cover']  # 取出第i个文件
    file.save('temp/{}_bgp.jpg'.format(user_id))  # 缓存到本地缓存文件夹中
    tempu = creat_picture_url('temp/{}_bgp.jpg'.format(user_id))
    os.remove('temp/{}_bgp.jpg'.format(user_id))  # 删除本地图片释放内存
    x = User.query.filter_by(id=user_id).first()
    x.background = tempu
    db.session.commit()
    return jsonify(code=200,message="修改成功!")


