from app_package import db, login_manager
from datetime import datetime, date
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))
    

class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    timeStamp = db.Column(db.DateTime, default=datetime.now)
    permission = db.Column(db.Text)
    posts = db.relationship('Posts', backref='author', lazy=True)

    def get_reset_token(self, expires_sec=1800):
        s=Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s=Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User(id: {self.id},email: {self.email}, permission: {self.permission})"

class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_title= db.Column(db.Text, nullable=False)
    blog_description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    #timestamp is just record of when post is added to db
    date_published = db.Column(db.DateTime, nullable=False, default=datetime.now)
    #date_published_to_site might be different if updated later on
    edited = db.Column(db.Text)
    link_to_app = db.Column(db.Text)
    word_doc = db.Column(db.Text)
    json_file = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"Posts(id: {self.id},blog_title: {self.blog_title}, " \
            f"date_published: {self.date_published}, timestamp: {self.timestamp})"

# class PostNew(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     dict_key = db.Column(db.Text)
#     row_tag_charaters = db.Column(db.Text)
#     row_tag = db.Column(db.Text)
#     row_going_into_html = db.Column(db.Text)
    
#     def __repr__(self):
#         return f"Posts({self.id},{self.dict_key}, row_tag_characters: {self.row_tag_charaters}, " \
#             f"row_tag: {self.row_tag}, row_going_into_html: {self.row_going_into_html})"