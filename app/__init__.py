from sqlalchemy import create_engine


DATABASE_URL = "sqlite:///ecommerce.db"


engine = create_engine(DATABASE_URL, echo=True)