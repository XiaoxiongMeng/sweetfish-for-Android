from manage import app
from flask_sqlalchemy import SQLAlchemy
import pymysql
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@127.0.0.1/python'
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'exchange_user_table'
    id = db.Column(db.Integer, primary_key=True)  # id，为唯一标识符
    username = db.Column(db.String(10), nullable=False)  # 用户名，最长限制10个字符
    password = db.Column(db.String(300), nullable=False)  # 哈希加密后的密码
    mail = db.Column(db.String(30), nullable=False, unique=True)   # 邮箱，长度为0~30，不允许为空
    avatar = db.Column(db.String(60)) # 头像的url
    permission = db.Column(db.Integer, default=0)  # 0普通用户 1管理员 -1被封 -2被举报暂未被处理 -3讨债
    fav_list = db.Column(db.String(600))  # 收藏列表
    toke_post = db.Column(db.String(600))  # 叫价列表 字典 格式为 {“post_id”：叫价}
    balance = db.Column(db.Integer)  # 余额
    name = db.Column(db.String(10))
    id_number = db.Column(db.String(18))
    reason = db.Column(db.String(100))  # 被举报原因
    followed = db.Column(db.String(1000))  # 关注我的人
    i_followed = db.Column(db.String(1000))  # 我关注的人
    background = db.Column(db.String(100))  # 主页背景图


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)  # id，为唯一标识符
    user_id = db.Column(db.Integer)  #用户id
    title = db.Column(db.String(40), nullable=False)  # 帖子名
    content = db.Column(db.String(6000), nullable=False)  # 帖子内容
    pic_urls = db.Column(db.String(400), nullable=False, unique=True)   # 图床，用于存储帖子中含有的图片
    price = db.Column(db.Float)  # 卖家价格
    buy_price = db.Column(db.Float)  # 买家当前协商价格
    is_approved = db.Column(db.Integer)  # 是否通过审核
    is_hangon = db.Column(db.Integer)  # 最后叫价成功的买家
    is_deleted = db.Column(db.Integer)  # 是否被删除（删除后将出现在垃圾箱中，在垃圾箱中再次删除才会永久删除。已完成交易的要买卖家都支持删除才可永久删除）
    buyer_id = db.Column(db.Integer)  # 买家id
    fav = db.Column(db.Integer)  # 收藏人数
    cover = db.Column(db.String(60), nullable=False)  # 帖子封面
    msg = db.Column(db.String(100), nullable=False)  # 帖子被封禁的原因
    view = db.Column(db.Integer)  # 浏览量 用来参与推送算法


class Chat(db.Model):
    __tablename__ = 'chathistory'
    id = db.Column(db.Integer, primary_key=True)  # id，为唯一标识符
    from_id = db.Column(db.Integer)  #用户id
    to_id = db.Column(db.Integer)  # 用户id
    time = db.Column(db.String(16), nullable=False)  # 帖子名
    message = db.Column(db.String(1000), nullable=False)  # 帖子内容
