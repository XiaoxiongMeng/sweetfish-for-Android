from models import User, Post, db
from utils.functions import check_token
from . import admin_operation
from ..user import users
from flask import request, jsonify
# *************************************************
# 所有管理员的操作都具有越权检测！ 基本不存在越权使用功能的情况
# *************************************************
@admin_operation.route("/admin/audit", methods=["GET"])
def get_audit():
    lists = []
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(id=user_id).first()
    if x.permission == 0:
        return jsonify(code=403, message="您不是系统管理员，无权对帖子进行审核！")
    posts = Post.query.filter_by(is_approved="0").all()
    for i in range(len(posts)):
        avatar = User.query.filter_by(id=posts[i].user_id).all()[0].avatar
        username = User.query.filter_by(id=posts[i].user_id).all()[0].username
        lists.append({"id": posts[i].id, "title": posts[i].title,
                      "content": posts[i].content, "buy_price": posts[i].buy_price, "price": posts[i].price,
                      "cover": posts[i].cover, "username": username, "avatar": avatar})
    return jsonify(code=200, message="以下是待审核的交易帖", data={"post_list": lists})


@admin_operation.route("/admin/allow", methods=["POST"])
def allow():
    username = request.form['username']
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(id=user_id).first()
    if x.permission == 0:
        return jsonify(code=403, message="您不是系统管理员，无权处理申诉信息！")
    try:
        del users.caches_for_wrong[username]
    except:
        return jsonify(code=404, message="该用户无需解封或不可解封")
    return jsonify(code=200, message="解封成功")


@admin_operation.route("/admin/audit/set", methods=["POST"])
def audit():
    post_id = request.form['postid']
    msg = request.form['msg']
    state = request.form['state']
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(id=user_id).first()
    if x.permission == 0:
        return jsonify(code=403, message="您不是系统管理员，无权对帖子进行审核！")
    temp_post = Post.query.filter_by(id=post_id).first()
    if temp_post is None:
        return jsonify(code=404, message="没有找到该帖")
    temp_post.msg=msg
    temp_post.is_approved = state
    db.session.commit()
    return jsonify(code=200, message="审核成功")


@admin_operation.route("/admin/ban", methods=["POST"])
def ban():
    id = request.form['id']
    state = request.form['state']
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(id=user_id).first()
    if x.permission == 0:
        return jsonify(code=403, message="您不是系统管理员，无权封禁用户！")
    temp_user = User.query.filter_by(id=id).first()
    if temp_user is None:
        return jsonify(code=404, message="没有找到该用户")
    temp_user.permission = state
    temp_user.reason = ''
    if state == -1:
        temp_user.username = "baned_"+temp_user.username+"_baned"
    else:
        temp_user.username = temp_user.username.strip("_baned").strip("baned_")
    db.session.commit()
    return jsonify(code=200, message="操作成功")


@admin_operation.route("/admin/report", methods=["GET"])
def report():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(id=user_id).first()
    if x.permission == 0:
        return jsonify(code=403, message="您不是系统管理员！")
    x = User.query.filter_by(permission=-2).all()
    lists=[]
    if x is None:
        return jsonify(code=200,message="暂无被举报用户")
    for i in x:
        temp = {"username": i.username,"id": i.id,"reason": i.reason}
        lists.append(temp)
    return jsonify(code=200,message="获取成功",data=lists)


@admin_operation.route("/admin/back_money", methods=["POST"])
def back_money():
    from_id = request.form['from']  # 从谁帐里扣钱
    to_id = request.form['to']  # 把钱给谁
    money = request.form['money']  # 退的金额
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x = User.query.filter_by(id=user_id).first()
    if x.permission == 0:
        return jsonify(code=403, message="您不是系统管理员！")
    from_user = User.query.filter_by(id=from_id).first()
    if from_user.balance >= money:
        from_user.balance = from_user.balance - money
    else:
        from_user.balance = 0
        from_user.permission = -3
    db.session.commit()
    to_user=User.query.filter_by(id=to_id).first()
    to_user.balance = to_user.balance + money
    db.session.commit()
    return jsonify(code=200,message="退钱成功")