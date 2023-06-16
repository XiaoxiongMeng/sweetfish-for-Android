import os
from flask import request, jsonify
from models import Post, db, User
from . import seller_operation
from utils.functions import creat_picture_url, fetch_posts_info, check_token


@seller_operation.route('/createposts', methods=['POST'])  # 发帖
def create_post():
    lists = request.files  # 从传来的数据中取出图片
    query = request.form  # 从传来的数据中取出表单
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    title = query['title']  # 帖子标题
    content = query['content']  # 帖子内容
    price = query['price']  # 卖家设置的价格
    if not os.path.exists('temp'):  # 创建一个缓存文件夹
        os.makedirs('temp')
    pic_url = ""
    try:
        last_record = Post.query.order_by(Post.id.desc()).first()  # 获得最后一条记录的id
        pid = int(last_record.id) + 1  # 给本条帖子设置id
    except:  # 如果还没有帖子，那么本帖子的id就是1
        pid = 1
    times = 0
    for i in lists:
        if times == 0:
            file = request.files[i]  # 取出第i个文件
            file.save('temp/{}_{}_{}.jpg'.format(user_id, pid, i))  # 缓存到本地缓存文件夹中
            tempu = creat_picture_url('temp/{}_{}_{}.jpg'.format(user_id, pid, i))
            pic_url = pic_url + "<" + (tempu) + ">"  # 上传到图床
            times = tempu
            os.remove('temp/{}_{}_{}.jpg'.format(user_id, pid, i))  # 删除本地图片释放内存

    new_user = Post(title=title, content=content, id=pid, user_id=user_id, pic_urls=pic_url,
                    price=price, is_approved=0, is_deleted=0, buyer_id=0, fav=0,
                    cover=times, view=0, buy_price=0, is_hangon=0)
    db.session.add(new_user)
    db.session.commit()
    return jsonify(code=200, message='帖子已成功发布，等待买家吧！')


@seller_operation.route("/seller/posted_posts", methods=["GET"])
def posted_post():
    lists = []
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    posts = Post.query.filter_by(user_id=user_id).all()
    for i in range(len(posts)):
        avatar = User.query.filter_by(id=posts[i].user_id).all()[0].avatar
        username = User.query.filter_by(id=posts[i].user_id).all()[0].username
        lists.append({"id": posts[i].id, "title": posts[i].title,
                      "content": posts[i].content, "buy_price": posts[i].buy_price, "price": posts[i].price,
                      "cover": posts[i].cover, "username": username, "avatar": avatar, "now_buyer":posts[i].is_hangon})
    return jsonify(code=200, message="以下是你发布的交易贴.", data={"posts_lists": lists})


@seller_operation.route("/seller/sold_posts", methods=["GET"])
def sold_post():
    lists = []
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    posts = Post.query.filter_by(user_id=user_id).all()
    for i in range(len(posts)):
        if posts[i].buyer_id != 0:
            avatar = User.query.filter_by(id=posts[i].user_id).all()[0].avatar
            username = User.query.filter_by(id=posts[i].user_id).all()[0].username
            lists.append({"id": posts[i].id, "title": posts[i].title,
                          "content": posts[i].content, "buy_price": posts[i].buy_price, "price": posts[i].price,
                          "cover": posts[i].cover, "username": username, "avatar": avatar})
    return jsonify(code=200, message="以下是你已经卖出的商品.", data={"posts_lists": lists})


@seller_operation.route("/detail", methods=["POST"])
def detail():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    info = fetch_posts_info(request.form["post_id"])
    return jsonify(code=200, message="success", data={"detail": info})


@seller_operation.route("/change_cover", methods=["POST"])
def change_cover():
    user_id = check_token(request.headers)
    if type(user_id) != type(1):  # 检验token
        return jsonify(code=400, message="身份信息验证失效，请重新登陆.")
    x=Post.query.filter_by(id=request.form['postid']).first()
    if x.user_id != user_id:
        return jsonify(code=400, message="这不是您的帖子，您不能修改封面！")
    for i in request.files:
        file = request.files[i]  # 取出第i个文件
        file.save('temp/{}_{}_{}.jpg'.format(user_id, x.id, i))  # 缓存到本地缓存文件夹中
        cover = creat_picture_url('temp/{}_{}_{}.jpg'.format(user_id, x.id, i))
        x.cover = cover
        db.session.commit()
        return jsonify(code=200, message="修改完成！",data={"cover":cover})