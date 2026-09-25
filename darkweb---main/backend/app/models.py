from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from .database import Base


class Actor(Base):
    __tablename__ = "actors"

    actor_id = Column(String(20), primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Identifiers and posts relationships
    identifiers = relationship("Identifier", back_populates="actor", lazy="joined")
    posts = relationship("Post", back_populates="actor", lazy="select")

    @property
    def id(self):
        return self.actor_id

    @property
    def primary_handle(self):
        # Return first handle identifier or actor_id
        if self.identifiers:
            for i in self.identifiers:
                if i.identifier_type == "handle" and i.identifier_value:
                    return i.identifier_value
        return self.actor_id

    @property
    def confidence(self):
        return 0.85

    @property
    def last_seen(self):
        if self.identifiers:
            dates = [i.last_seen for i in self.identifiers if i.last_seen]
            if dates:
                return max(dates)
        return self.created_at


class Identifier(Base):
    __tablename__ = "identifiers"

    identifier_id = Column(String(20), primary_key=True, index=True)
    actor_id = Column(String(20), ForeignKey("actors.actor_id"), nullable=False)
    identifier_type = Column(String(50), nullable=False)
    identifier_value = Column(Text, nullable=False)
    source_id = Column(String(20), nullable=False)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    confidence = Column(Float, default=1.0)
    status = Column(String(50), nullable=True)
    observation_id = Column(String(20), nullable=True)

    # Relationship
    actor = relationship("Actor", back_populates="identifiers")

    @property
    def id(self):
        return self.identifier_id

    @property
    def type(self):
        return self.identifier_type

    @property
    def value(self):
        return self.identifier_value


class Post(Base):
    __tablename__ = "posts"

    post_id = Column(String(20), primary_key=True, index=True)
    actor_id = Column(String(20), ForeignKey("actors.actor_id"), nullable=False)
    handle = Column(Text, nullable=True)
    source_id = Column(String(20), nullable=False)
    content = Column(Text, nullable=True)
    event_timestamp = Column(DateTime, nullable=False)
    language = Column(String(20), nullable=True)
    category = Column(String(50), nullable=True)
    reply_count = Column(Integer, default=0)
    sentiment_score = Column(Float, nullable=True)
    word_count = Column(Integer, nullable=True)
    avg_sentence_length = Column(Float, nullable=True)
    punctuation_ratio = Column(Float, nullable=True)
    technical_term_ratio = Column(Float, nullable=True)

    # Relationship
    actor = relationship("Actor", back_populates="posts")

    @property
    def id(self):
        return self.post_id

    @property
    def text(self):
        return self.content

    @property
    def source(self):
        return self.source_id

    @property
    def timestamp(self):
        return self.event_timestamp

    @property
    def pgp_key(self):
        return None

    @property
    def wallet(self):
        return None