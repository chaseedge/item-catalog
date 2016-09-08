from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(300))
    pw_hash = Column(Text)

    @property
    def serialize(self):
        """Returns info in a easily serializable format"""
        return {
            'name': self.name,
            'id': self.id,
            'email': self.email,
            'picture': self.picture
        }


class Genre(Base):
    __tablename__ = 'genre'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name
        }


class Movie(Base):
    __tablename__ = 'movie'

    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False)
    tmdb_id = Column(Integer)
    description = Column(Text)
    year = Column(Integer)
    added_on = Column(DateTime, default=datetime.datetime.utcnow())
    rating = Column(Numeric(2, 1))
    poster = Column(String(500))
    backdrop = Column(String(500))
    trailer = Column(String(500))
    actor_list = Column(String(500))
    genre_id = Column(Integer, ForeignKey('genre.id'))
    genre = relationship(Genre)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Returns info in a easily serializable format"""
        return {
            'title': self.title,
            'id': self.id,
            'added_on': self.added_on,
            'rating': self.rating,
            'tmdb_id': self.tmdb_id,
            'description': self.description,
            'year': self.year,
            'poster': self.poster,
            'backdrop': self.backdrop,
            'actor_list': self.actor_list,
            'trailer': self.trailer,
            'genre_id': self.genre_id,
            'user_id': self.user_id
        }

    @property
    def actors(self):
        """Returns a list of actors"""
        return self.actor_list.split('/')


class Review(Base):
    __tablename__ = 'review'

    id = Column(Integer, primary_key=True)
    created_on = Column(DateTime, default=datetime.datetime.utcnow())
    rating = Column(Integer, nullable=False)
    review = Column(Text)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship(User)
    movie_id = Column(Integer, ForeignKey('movie.id'), nullable=False)
    movie = relationship(Movie)

    @property
    def serialize(self):
        """Returns info in a easily serializable format"""
        return {
            'id': self.id,
            'movie_id': self.movie_id,
            'review': self.review,
            'rating': self.rating,
            'created_on': str(self.created_on),
            'user_id': self.user_id
        }


engine = create_engine('sqlite:///moviecatalog.db')

Base.metadata.create_all(engine)
