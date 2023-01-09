'''A module to provide the mongo DB connection'''
import os

from pymongo import MongoClient
from pymongo.collection import Collection

from app.dtos import db

connection_string = os.environ.get('MongoDb', 'mongodb://root:rootpassword@localhost:27017')
database_name = os.environ.get('DatabaseName', 'test')

mongo_client = MongoClient(connection_string)

game_client: Collection[db.Game] = mongo_client[database_name]['game']
user_client: Collection[db.User] = mongo_client[database_name]['user']
