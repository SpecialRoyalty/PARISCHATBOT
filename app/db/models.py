from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__='users'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str|None] = mapped_column(String(255))
    first_name: Mapped[str|None] = mapped_column(String(255))
    last_name: Mapped[str|None] = mapped_column(String(255))
    category_pref: Mapped[str|None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    invite_count: Mapped[int] = mapped_column(Integer, default=0)
    good_predictions: Mapped[int] = mapped_column(Integer, default=0)
    total_predictions: Mapped[int] = mapped_column(Integer, default=0)
    exact_scores: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)

class Role(Base):
    __tablename__='roles'
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[str] = mapped_column(String(32), primary_key=True) # super_admin/admin/trusted
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__='settings'
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str|None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Match(Base):
    __tablename__='matches'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    team_a: Mapped[str] = mapped_column(String(120))
    team_b: Mapped[str] = mapped_column(String(120))
    photo_file_id: Mapped[str|None] = mapped_column(String(255))
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime|None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default='active') # draft/pending/active/locked/closed/cancelled
    created_by: Mapped[int|None] = mapped_column(BigInteger)
    proposed_by: Mapped[int|None] = mapped_column(BigInteger)
    group_message_id: Mapped[int|None] = mapped_column(Integer)
    result_winner: Mapped[str|None] = mapped_column(String(32))
    result_score: Mapped[str|None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Prediction(Base):
    __tablename__='predictions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey('matches.id'))
    user_id: Mapped[int] = mapped_column(BigInteger)
    winner: Mapped[str] = mapped_column(String(32)) # a/b/draw
    exact_score: Mapped[str|None] = mapped_column(String(32))
    is_good: Mapped[bool|None] = mapped_column(Boolean)
    is_exact: Mapped[bool|None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__=(UniqueConstraint('match_id','user_id',name='uix_prediction_match_user'),)

class ForbiddenWord(Base):
    __tablename__='forbidden_words'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(255), unique=True)
    added_by: Mapped[int|None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MediaHash(Base):
    __tablename__='media_hashes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hash: Mapped[str] = mapped_column(String(128), unique=True)
    media_type: Mapped[str] = mapped_column(String(32))
    added_by: Mapped[int|None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SecurityLog(Base):
    __tablename__='security_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int|None] = mapped_column(BigInteger)
    details: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class InviteLink(Base):
    __tablename__='invite_links'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    link: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Suggestion(Base):
    __tablename__='suggestions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    category: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    proposed_date: Mapped[str|None] = mapped_column(String(100))
    photo_file_id: Mapped[str|None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Badge(Base):
    __tablename__='badges'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    code: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__=(UniqueConstraint('user_id','code',name='uix_badge_user_code'),)

class UsernameHistory(Base):
    __tablename__='username_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    old_value: Mapped[str|None] = mapped_column(String(255))
    new_value: Mapped[str|None] = mapped_column(String(255))
    field: Mapped[str] = mapped_column(String(32))
    public_announced_at: Mapped[datetime|None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ResultPrompt(Base):
    __tablename__='result_prompts'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey('matches.id'))
    user_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__=(UniqueConstraint('match_id','user_id',name='uix_result_prompt_match_user'),)
