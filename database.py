from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/img_vid_db_migr"
engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    with Session(engine) as session:
        yield session
