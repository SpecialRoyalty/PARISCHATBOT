from sqlalchemy import BigInteger, String, DateTime, Boolean, Integer, Text, ForeignKey, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.session import Base

class User(Base):
    __tablename__='users'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str|None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str|None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str|None] = mapped_column(String(255), nullable=True)
    started: Mapped[bool] = mapped_column(Boolean, default=False)
    welcome_seen: Mapped[bool] = mapped_column(Boolean, default=False)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    exact_scores: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    suggestions_accepted: Mapped[int] = mapped_column(Integer, default=0)
    invites: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Match(Base):
    __tablename__='matches'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    option_a: Mapped[str] = mapped_column(String(100))
    option_b: Mapped[str] = mapped_column(String(100))
    photo_file_id: Mapped[str|None] = mapped_column(String(255), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime)
    vote_close_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='active')
    group_message_id: Mapped[int|None] = mapped_column(Integer, nullable=True)
    trend_message_id: Mapped[int|None] = mapped_column(Integer, nullable=True)
    result_winner: Mapped[str|None] = mapped_column(String(20), nullable=True)
    result_score: Mapped[str|None] = mapped_column(String(20), nullable=True)
    created_by: Mapped[int|None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Prediction(Base):
    __tablename__='predictions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey('matches.id'))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'))
    winner: Mapped[str] = mapped_column(String(20))
    score: Mapped[str|None] = mapped_column(String(20), nullable=True)
    is_correct: Mapped[bool|None] = mapped_column(Boolean, nullable=True)
    exact: Mapped[bool|None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__=(UniqueConstraint('match_id','user_id',name='uq_prediction_match_user'),)

class Setting(Base):
    __tablename__='settings'
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str|None] = mapped_column(Text, nullable=True)

class ForbiddenWord(Base):
    __tablename__='forbidden_words'
    word: Mapped[str] = mapped_column(String(120), primary_key=True)

class Sanction(Base):
    __tablename__='sanctions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(50))
    count: Mapped[int] = mapped_column(Integer, default=1)

class MediaHash(Base):
    __tablename__='media_hashes'
    hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    media_type: Mapped[str] = mapped_column(String(50))
    added_by: Mapped[int|None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class InviteLink(Base):
    __tablename__='invite_links'
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    link: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Suggestion(Base):
    __tablename__='suggestions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    proposed_date: Mapped[str|None] = mapped_column(String(100), nullable=True)
    photo_file_id: Mapped[str|None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class IdentityHistory(Base):
    __tablename__='identity_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    old_name: Mapped[str|None] = mapped_column(String(255), nullable=True)
    new_name: Mapped[str|None] = mapped_column(String(255), nullable=True)
    old_username: Mapped[str|None] = mapped_column(String(255), nullable=True)
    new_username: Mapped[str|None] = mapped_column(String(255), nullable=True)
    announced_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SecurityLog(Base):
    __tablename__='security_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[int|None] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[str|None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
