import json
import re
import smtplib
import random
import time
from operator import itemgetter
import jwt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from qiniu import Auth,put_file
from models import Post, User, db


def send_code(target_mail,type):  # type： 0  注册 1 修改密码
    code = str(random.randint(100000, 999999))  # 生成六位数随机验证码
    sender_email = 'tianyuzhendebuxian@outlook.com'  # 发送人的邮箱地址
    sender_password = 'tyzdbx666'  # 发送人的邮箱密码
    receiver_email = target_mail  # 收件人的邮箱
    msg = MIMEMultipart()  # 创建一个MIMEMultipart对象用来发送邮件
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = '您的平台的验证码'
    if type == 0:
        message = f'您的平台注册验证码为{code}，请妥善保管，不要泄露.有效期为五分钟，请尽快验证.'
    else:
        message = f'您即将在平台执行修改密码操作，验证码为{code}，请妥善保管，不要泄露.有效期为五分钟.'
    msg.attach(MIMEText(message, 'plain'))
    server = smtplib.SMTP('smtp.office365.com', 587)
    server.ehlo()  # 与发信服务器建立连接
    server.starttls()  # 加密链接
    server.login(sender_email, sender_password)  # 登陆发信服务器
    server.sendmail(sender_email, receiver_email, msg.as_string())  # 发信
    server.quit()  # 断开与服务器的链接
    return code


def creat_picture_url(file):
    ak = '9WtJTijVY5XC9FnLpv0dvVoWfSv4xKF9-J3ITb1b'
    sk = 'QRgzexYdbhuASYoj6F8tEqIPPj2-e3U1p_GMfihm'
    q = Auth(access_key=ak, secret_key=sk)
    bucket_name = 'west-two'
    key = file
    token = q.upload_token(bucket_name, key)
    # 要上传文件的路径
    localfile = file
    ret, info = put_file(token, key, localfile)
    # 拼接路径   qj5s0uqce.hb-bkt.clouddn.com这个是创建空间分配的测试域名
    image_file = 'http://rwa0i3rsm.hn-bkt.clouddn.com/' + ret.get('key')
    print(image_file)  # http://qj5s0uqce.hb-bkt.clouddn.com/1.jpg
    return image_file


def generate_token(user_id, username, permission):
    secret_key = 'westtwohouduansecond'  # token加密密钥
    payload = {  # token的荷载信息
        'id': user_id,  # 用户id
        'username': username,  # 用户名
        'permission': permission  # 用户权限
    }
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token


def fetch_posts_info(id):
    print(id)
    addview(id)
    pic_urls = []
    posts = Post.query.filter_by(id=id).first()
    post_id= posts.id
    users_id = posts.user_id
    title = posts.title
    content = posts.content
    price = posts.price
    buy_price = posts.buy_price
    fav = posts.fav
    now_buyer=posts.is_hangon
    if posts.pic_urls:
        pic_url_temp = re.findall("<.*?>", posts.pic_urls)
        for u in range(len(pic_url_temp)):
            pic_url_temp[u] = pic_url_temp[u].strip("<")
            pic_urls.append(pic_url_temp[u].strip(">"))
    else:
        pic_urls = []
    username = User.query.filter_by(id=users_id).all()[0].username
    avatar = User.query.filter_by(id=users_id).all()[0].avatar
    return {"post_id": post_id, "user_id": users_id, "title": title, "content": content, "price": price,
            "pic_urls" :pic_urls, "buy_price": buy_price, "fav": fav, "cover": posts.cover, "username": username,
            "avatar": avatar, "now_buyer": now_buyer}


def addview(post_id):
    post = Post.query.filter_by(id=post_id).first()
    post.view = post.view + 1
    db.session.commit()


def check_token(header):
    try:
        token = header.get("Authorization")
        user_id = jwt.decode(token, 'westtwohouduansecond', algorithms=['HS256'])['id']
        return user_id
    except:
        return {"message":"身份信息验证失效，请重新登陆."}


def show_posts():
    random.seed(time.time())
    view_per = random.randint(0, 20)
    fav_per = random.randint(0,30)
    rand_per = 100-view_per-fav_per
    posts = Post.query.filter_by(is_approved=1,buyer_id=0).all()
    nums = len(posts)
    weight = []
    for i in range(min(nums, 8)):
        view = posts[i].view
        fav = posts[i].fav
        sc = random.randint(1, 100)
        score = (view*view_per+fav*fav_per+rand_per*sc)/100
        weight.append([score,posts[i].id])
    res = sorted(weight,key=itemgetter(0))
    return res


