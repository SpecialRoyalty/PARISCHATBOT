from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    public_identity_alert_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    muted_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    banned: Mapped[bool] = mapped_column(Boolean, default=False)
    link_violations: Mapped[int] = mapped_column(Integer, default=0)
    word_violations: Mapped[int] = mapped_column(Integer, default=0)
    command_violations: Mapped[int] = mapped_column(Integer, default=0)
    good_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    accepted_suggestions: Mapped[int] = mapped_column(Integer, default=0)

class Role(Base):
    __tablename__ = 'roles'
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[str] = mapped_column(String(32), primary_key=True)  # super_admin/admin/trusted
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Match(Base):
    __tablename__ = 'matches'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(512))
    side_a: Mapped[str] = mapped_column(String(255))
    side_b: Mapped[str] = mapped_column(String(255))
    image_file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    votes_close_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default='active')  # draft/active/locked/pending_result/closed/cancelled
    winner: Mapped[str | None] = mapped_column(String(16), nullable=True) # A/B/DRAW/CANCEL
    final_score: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_prono_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_trend_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    predictions = relationship('Prediction', back_populates='match')

class Prediction(Base):
    __tablename__ = 'predictions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey('matches.id'))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'))
    choice: Mapped[str] = mapped_column(String(16)) # A/B/DRAW
    exact_score: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score_exact_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    match = relationship('Match', back_populates='predictions')
    __table_args__ = (UniqueConstraint('match_id', 'user_id', name='uq_prediction_once'),)

class UserStats(Base):
    __tablename__ = 'user_stats'
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    participations: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    exact_scores: Mapped[int] = mapped_column(Integer, default=0)

class Badge(Base):
    __tablename__ = 'badges'
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    badge: Mapped[str] = mapped_column(String(64), primary_key=True)
    awarded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class InviteLink(Base):
    __tablename__ = 'invite_links'
    code: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    link: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Invitation(Base):
    __tablename__ = 'invitations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inviter_id: Mapped[int] = mapped_column(BigInteger)
    invited_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('invited_id', name='uq_invited_once'),)

class Suggestion(Base):
    __tablename__ = 'suggestions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    category: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(512))
    proposed_date: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ForbiddenWord(Base):
    __tablename__ = 'forbidden_words'
    word: Mapped[str] = mapped_column(String(255), primary_key=True)
    created_by: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MediaHash(Base):
    __tablename__ = 'media_hashes'
    hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_by: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default='')

class ScheduledMessage(Base):
    __tablename__ = 'scheduled_messages'
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class IdentityHistory(Base):
    __tablename__ = 'identity_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    old_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    new_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SecurityLog(Base):
    __tablename__ = 'security_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String(128))
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    details: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
