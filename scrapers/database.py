from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String

DATABASE_URL = "sqlite:///./users.db"

database = Database(DATABASE_URL)
metadata = MetaData()

# Users table
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True, index=True),
    Column("password_hash", String),
)

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)

