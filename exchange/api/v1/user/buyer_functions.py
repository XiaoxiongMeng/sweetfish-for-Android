from flask import request, jsonify

from chat import confirm
from models import Post, User, db
from . import buyer_operation
from utils.functions import fetch_posts_info, addview, check_token, show_posts


@buyer_operation.route("/buyer/bought", methods=["GET"])
def bought():
    lists = []
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    posts = Post.query.filter_by(buyer_id=user_id).all()
    for i in range(len(posts)):
        avatar = User.query.filter_by(id=posts[i].user_id).all()[0].avatar
        username = User.query.filter_by(id=posts[i].user_id).all()[0].username
        lists.append({"id": posts[i].id, "title": posts[i].title,
                      "content": posts[i].content, "buy_price": posts[i].buy_price, "price": posts[i].price,
                      "cover": posts[i].cover, "username": username, "avatar": avatar})
    return jsonify(code=200, message="以下是你购买过的商品.", data={"posts_lists": lists})


@buyer_operation.route("/buyer/fav", methods=["POST"])
def fav():
    query = request.form
    post_id = query["post_id"]
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    user = User.query.filter_by(id=user_id).first()
    fav_list = eval(user.fav_list)
    if post_id in fav_list:
        fav_list.remove(post_id)
        user.fav_list = str(fav_list)
        db.session.commit()
        post = Post.query.filter_by(id=post_id).first()
        fav_num = post.fav - 1
        post.fav = fav_num
        db.session.commit()
        return jsonify(code=200, message="取消收藏成功.", data="0")
    else:
        fav_list.append(post_id)
        user.fav_list = str(fav_list)
        db.session.commit()
        post = Post.query.filter_by(id=post_id).first()
        fav_num = post.fav + 1
        post.fav = fav_num
        db.session.commit()
        addview(post_id)
        return jsonify(code=200, message="收藏成功.", data="1")



@buyer_operation.route("/buyer/favposts", methods=["GET"])
def favposts():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    user = User.query.filter_by(id=user_id).first()
    fav_list = eval(user.fav_list)
    fav_detail_list = []
    for i in fav_list:
        temp = fetch_posts_info(i)

        temp2 = {"post_id": temp["post_id"], "username": temp['username'], "title": temp["title"],
                 "content": temp["content"], "price": temp["price"], "fav": temp["fav"], 'avatar': temp['avatar'],
                 "cover": temp['cover']}
        fav_detail_list.append(temp2)
    return jsonify(code=200, message="以下是你的收藏列表.", data={"fav_list": fav_detail_list})


@buyer_operation.route("/buyer/posts", methods=["GET"])
def posts():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    rank = show_posts()

    lists = []
    for i in rank:
        temp = fetch_posts_info(i[1])
        temp2 = {"post_id": temp["post_id"], "username": temp['username'], "title": temp["title"],
                 "content": temp["content"], "price": temp["price"], "fav": temp["fav"], 'avatar': temp['avatar'],
                 "cover": temp['cover']}
        lists.append(temp2)
    return jsonify(code="200", message="成功",data=lists)


@buyer_operation.route("/buyer/give_price", methods=["POST"])
def give_price():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    post_id = request.form["post_id"]
    price = round(eval(request.form["price"]),2)
    x=Post.query.filter_by(id=post_id).first()
    y=User.query.filter_by(id=user_id).first()
    if x.buyer_id != 0:
        return jsonify(code=400, message="已售出。")
    if price <= x.buy_price:
        return jsonify(code=400, message="当前已有更高的价格！请您再提高价格。")
    if y.balance < price:
        return jsonify(code=400,message="钱包余额不足！")
    x.buy_price=price
    x.is_hangon=user_id
    list_gave = y.toke_post
    if list_gave is None:
        list_gave='{"'+str(post_id)+'":'+str(price)+'}'
    else:
        list_gave = eval(list_gave)
        list_gave[str(post_id)]=price
    y.toke_post=str(list_gave)
    db.session.commit()
    confirm(post_id, price, x.title, x.user_id, user_id)
    return jsonify(code=200, message=f"成功叫价！当前价格为{price}")


@buyer_operation.route("/buyer/gave", methods=["POST"])
def gave():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    pid = request.form['pid']
    dict = {"price":0}
    posts_gave = eval(User.query.filter_by(id=user_id).first().toke_post)
    if posts_gave is None:
        return jsonify(code="404", message="开价列表为空。")
    try:
        dict['price']=posts_gave[pid]
    except:
        return jsonify(code="404", message="没找到该贴开价记录")

    else:
        return jsonify(code="200", message="成功", data=dict)


