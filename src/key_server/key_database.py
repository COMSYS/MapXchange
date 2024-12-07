"""
Database models for key server

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

from datetime import datetime

from src.lib.user_database import db, SecurityInteger


class StoredKey(db.Model):
    """SQLAlchemy class representing one key"""

    __tablename__ = "keys"

    map_id = db.Column(db.Integer, primary_key=True)
    machine = db.Column(db.Text, nullable=False)
    material = db.Column(db.Text, nullable=False)
    tool_id = db.Column(db.Integer,
                        db.ForeignKey("tools.id"),
                        nullable=False)
    tool = db.relationship("StoredTool", back_populates="maps")
    public_key_n = db.Column(SecurityInteger, nullable=False)
    private_key_p = db.Column(SecurityInteger, nullable=False)
    private_key_q = db.Column(SecurityInteger, nullable=False)
    __table_args__ = (db.UniqueConstraint("material", "machine", "tool_id",
                                          name='_map_name_uc'),)


class StoredTool(db.Model):
    """SQLAlchemy class representing one milling tool"""

    __tablename__ = "tools"

    id = db.Column(db.Integer, primary_key=True)
    tool = db.Column(db.Text, nullable=False, unique=True)
    maps = db.relationship("StoredKey",
                           uselist=True,
                           back_populates="tool")
    tool_type = db.Column(db.Text, nullable=False)
    tool_diameter = db.Column(db.Integer, nullable=False)
    # First provider tracked for verification
    first_provider_id = db.Column(db.Integer,
                                  db.ForeignKey("producers.id"),
                                  nullable=False)
    first_provider = db.relationship("Producer",
                                     uselist=False,
                                     foreign_keys=[first_provider_id])


class KeyRetrievalClient(db.Model):
    """SQLAlchemy class representing one client key retrieval operation"""

    __tablename__ = 'key_retrievals_client'

    id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer,
                            db.ForeignKey("producers.id"))
    producer = db.relationship("Producer",
                               uselist=False,
                               foreign_keys=[producer_id])
    key_id = db.Column(db.Integer,
                       db.ForeignKey("keys.map_id"),
                       nullable=False)
    key = db.relationship("StoredKey",
                          uselist=False,
                          foreign_keys=[key_id])
    timestamp = db.Column(db.DateTime, default=datetime.now(), nullable=False)


class KeyRetrievalProvider(db.Model):
    """SQLAlchemy class representing one provider key retrieval operation"""

    __tablename__ = 'key_retrievals_provider'

    id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer,
                            db.ForeignKey("producers.id"),
                            nullable=False)
    producer = db.relationship("Producer",
                               uselist=False,
                               foreign_keys=[producer_id])
    key_id = db.Column(db.Integer,
                       db.ForeignKey("keys.map_id"),
                       nullable=False)
    key = db.relationship("StoredKey",
                          uselist=False,
                          foreign_keys=[key_id])
    timestamp = db.Column(db.DateTime, default=datetime.now(), nullable=False)


class IDRetrieval(db.Model):
    """
    SQLAlchemy class representing one map ID retrieval operation
    by a producer
    """

    __tablename__ = 'id_retrievals'

    id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer,
                            db.ForeignKey("producers.id"),
                            nullable=False)
    producer = db.relationship("Producer",
                               uselist=False,
                               foreign_keys=[producer_id])
    count = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(), nullable=False)
