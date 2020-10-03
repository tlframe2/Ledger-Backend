from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_jwt_simple import JWTManager, jwt_required, create_jwt, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import os

#from config import ProductionConfig, DevelopmentConfig

# Init app
app = Flask(__name__)

# ENV = 'dev'

# CORS_HEADERS = 'Content-Type'
# SQLALCHEMY_TRACK_MODIFICATIONS = False
# JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']


# if ENV == 'dev':
#     app.config.from_object(DevelopmentConfig())
# else:
#     app.config.from_object(ProductionConfig())


# app.debug = os.environ['DEBUG']
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['JWT_SECRET_KEY'] = os.environ['JWT_SECRET_KEY']
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

cors = CORS(app)

jwt = JWTManager(app)

# Init db
db = SQLAlchemy(app)

# Init ma
ma = Marshmallow(app)

# User class
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = password

    @classmethod
    def find_by_username(cls, username):
        return cls.query.filter_by(username=username).first()

    @classmethod
    def save_user(cls, username, password):
        new_user = cls(username, password)
        db.session.add(new_user)
        db.session.commit()
        return new_user

# Transaction class
class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.String(50), primary_key=True, autoincrement=False)
    type = db.Column(db.String(3))
    description = db.Column(db.String(100))
    amount = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

    def __init__(self, id, type, description, amount, user_id):
        self.id = id
        self.type = type
        self.description = description
        self.amount = amount
        self.user_id = user_id

    @classmethod
    def get_all_transactions_for_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def add_transaction(cls, id, type, description, amount, user_id):
        new_transaction = cls(id, type, description, amount, user_id)
        db.session.add(new_transaction)
        db.session.commit()
        return new_transaction

    @classmethod
    def update_transaction(cls, id, type, description, amount, user_id):
        transaction = cls.query.get(id)

        transaction.id = id
        transaction.type = type
        transaction.description = description
        transaction.amount = amount
        transaction.user_id = user_id

        db.session.commit()

        return transaction

    @classmethod
    def delete_transaction(cls, id):
        transaction = cls.query.get(id)

        db.session.delete(transaction)
        db.session.commit()

        return transaction

# Transaction schema
class TransactionSchema(ma.Schema):
    class Meta:
        fields = ('id', 'type', 'description', 'amount', 'user_id')

# Init schema
transaction_schema = TransactionSchema()
transactions_schema = TransactionSchema(many=True)

@app.route('/register', methods=['POST'])
@cross_origin()
def register():
    username = request.json['username']
    password = request.json['password']

    new_user = User.save_user(username, generate_password_hash(password))

    return { 'token': create_jwt(identity=new_user.id) }, 201

@app.route('/login', methods=['POST'])
def login():
    username = request.json['username']
    password = request.json['password']

    requested_user = User.find_by_username(username)

    if requested_user and check_password_hash(requested_user.password, password):
        return { 'token': create_jwt(identity=requested_user.id) }
    else:
        return { 'error': 'Username or password is incorrect!' }, 404

# Create a transaction
@app.route('/transaction', methods=['POST'])
@cross_origin()
@jwt_required
def add_transaction():
    id = request.json['id']
    type = request.json['type']
    description = request.json['description']
    amount = request.json['amount']

    new_transaction = Transaction.add_transaction(id, type, description, amount, get_jwt_identity())

    return transaction_schema.jsonify(new_transaction)

# Get all transactions for user
@app.route('/transaction/byUser', methods=['GET'])
@cross_origin()
@jwt_required
def get_transactions_for_user():
    user_id = get_jwt_identity()
    return transactions_schema.jsonify(Transaction.get_all_transactions_for_user(user_id))

# Update a transaction
@app.route('/transaction/<id>', methods=['PUT'])
@cross_origin()
@jwt_required
def update_transaction(id):
    id = request.json['id']
    type = request.json['type']
    description = request.json['description']
    amount = request.json['amount']
    user_id = get_jwt_identity()

    updated_transaction = Transaction.update_transaction(id, type, description, amount, user_id)

    return transaction_schema.jsonify(updated_transaction)

# Delete a transaction
@app.route('/transaction/<id>', methods=['DELETE'])
@cross_origin()
@jwt_required
def delete_transaction(id):
    transaction = Transaction.delete_transaction(id);
    return transaction_schema.jsonify(transaction)

# Run server
if __name__ == '__main__':
    app.run()