"""
Database models for map server

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

from datetime import datetime

from src.lib.user_database import db, SecurityInteger


class ReverseQuerist(db.Model):
    """
    SQLAlchemy class representing one producer who has
    reverse-queried a map (association object)
    """

    __tablename__ = "reverse_querists"

    id = db.Column(db.Integer, primary_key=True)
    producer_id = db.Column(db.Integer, db.ForeignKey("producers.id"))
    map_id = db.Column(db.Integer, db.ForeignKey("map_keys.map_id"))
    producer = db.relationship("Producer")
    point_count = db.Column(db.Integer, nullable=False)
    offset = db.Column(db.Integer, nullable=False)
    tool = db.Column(db.Text, nullable=False)


past_requests = db.Table(
    "past_requests",
    db.Model.metadata,
    db.Column("producer_id", db.ForeignKey("producers.id")),
    db.Column("map_id", db.ForeignKey("map_keys.map_id")),
)

open_requests = db.Table(
    "open_requests",
    db.Model.metadata,
    db.Column("producer_id", db.ForeignKey("producers.id")),
    db.Column("point_id", db.ForeignKey("points.id")),
)

current_comparators = db.Table(
    "current_comparators",
    db.Model.metadata,
    db.Column("producer_id", db.ForeignKey("producers.id")),
    db.Column("point_id", db.ForeignKey("points.id")),
)

point_vendees = db.Table(
    "point_vendees",
    db.Model.metadata,
    db.Column("producer_id", db.ForeignKey("producers.id")),
    db.Column("point_id", db.ForeignKey("points.id")),
)


class MapKey(db.Model):
    """SQLAlchemy class representing key stored for one map"""

    __tablename__ = "map_keys"

    id = db.Column(db.Integer, primary_key=True)
    map_id = db.Column(db.Integer, nullable=False, unique=True)
    machine = db.Column(db.Text, nullable=False)
    material = db.Column(db.Text, nullable=False)
    tool = db.Column(db.Text, nullable=False)
    public_key_n = db.Column(SecurityInteger, nullable=False)
    # First provider tracked for verification
    first_provider_id = db.Column(db.Integer,
                                  db.ForeignKey("producers.id"),
                                  nullable=False)
    first_provider = db.relationship("Producer",
                                     uselist=False,
                                     foreign_keys=[first_provider_id])
    # Exclude map vendees from reverse queries
    past_requests = db.relationship("Producer",
                                    uselist=True,
                                    secondary=past_requests)
    # Ensure entire map is retrieved after reverse query
    reverse_querists = db.relationship("ReverseQuerist",
                                       uselist=True)
    __table_args__ = (db.UniqueConstraint("material", "machine", "tool",
                                          name='_map_name_uc'),)


class StoredPoint(db.Model):
    """SQLAlchemy class representing one stored point"""

    __tablename__ = "points"

    id = db.Column(db.Integer, primary_key=True)
    map_id = db.Column(db.Integer,
                       db.ForeignKey("map_keys.map_id"),
                       nullable=False)
    map = db.relationship("MapKey",
                          uselist=False,
                          foreign_keys=[map_id])
    ap = db.Column(db.Integer, nullable=False)
    ae = db.Column(db.Integer, nullable=False)
    usage_total = db.Column(SecurityInteger)
    fz_optimal = db.Column(SecurityInteger)
    provider_optimal_id = db.Column(db.Integer,
                                    db.ForeignKey("producers.id"))
    provider_optimal = db.relationship("Producer",
                                       uselist=False,
                                       foreign_keys=[provider_optimal_id])
    fz_pending = db.Column(SecurityInteger)
    provider_pending_id = db.Column(db.Integer,
                                    db.ForeignKey("producers.id"))
    provider_pending = db.relationship("Producer",
                                       uselist=False,
                                       foreign_keys=[provider_pending_id])
    fz_unknown = db.Column(SecurityInteger)
    provider_unknown_id = db.Column(db.Integer,
                                    db.ForeignKey("producers.id"))
    provider_unknown = db.relationship("Producer",
                                       uselist=False,
                                       foreign_keys=[provider_unknown_id])
    open_requests = db.relationship("Producer",
                                    uselist=True,
                                    secondary=open_requests)
    current_offset = db.Column(db.Integer) # replace when comparison results are stored
    current_comparators = db.relationship("Producer",
                                          uselist=True,
                                          secondary=current_comparators) # reset for new last_comparator
    last_comparator_id = db.Column(db.Integer,
                                   db.ForeignKey("producers.id"))
    last_comparator = db.relationship("Producer",
                                      uselist=False,
                                      foreign_keys=[last_comparator_id])
    point_vendees = db.relationship("Producer",
                                    uselist=True,
                                    secondary=point_vendees) # reset for new fz_optimal
    __table_args__ = (db.UniqueConstraint("map_id", "ap", "ae",
                                          name='_point_name_uc'),)


class MapUsage(db.Model):
    """
    SQLAlchemy class representing point usage of one map
    by one producer
    """

    __tablename__ = "map_usage"

    id = db.Column(db.Integer, primary_key=True)
    map_id = db.Column(db.Integer,
                       db.ForeignKey("map_keys.map_id"),
                       nullable=False)
    map = db.relationship("MapKey",
                          uselist=False,
                          foreign_keys=[map_id])
    provider_id = db.Column(db.Integer,
                            db.ForeignKey("producers.id"),
                            nullable=False)
    provider = db.relationship("Producer",
                               uselist=False,
                               foreign_keys=[provider_id])
    usage_provider = db.Column(SecurityInteger)
    __table_args__ = (db.UniqueConstraint("map_id", "provider_id",
                                          name='_map_provider_uc'),)


class RetrievalProducer(db.Model):
    """
    SQLAlchemy class representing one regular query
    by a producer
    """

    __tablename__ = 'retrievals_producer'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer,
                          db.ForeignKey("producers.id"),
                          nullable=False)
    client = db.relationship("Producer",
                             uselist=False,
                             foreign_keys=[client_id])
    billing = db.relationship("BillingProducer",
                              uselist=False,
                              back_populates="retrieval")
    point_count = db.Column(db.Integer, nullable=False) # Number of retrieved points
    timestamp = db.Column(db.DateTime, default=datetime.now(), nullable=False)


class BillingProducer(db.Model):
    """
    SQLAlchemy class representing map server billing information
    of producer for one provider
    """

    __tablename__ = 'billing_information_producer'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer,
                          db.ForeignKey("producers.id"),
                          nullable=False)
    client = db.relationship("Producer",
                             uselist=False,
                             foreign_keys=[client_id])
    provider_id = db.Column(db.Integer,
                            db.ForeignKey("producers.id"),
                            nullable=False)
    provider = db.relationship("Producer",
                               uselist=False,
                               foreign_keys=[provider_id])
    count_provider = db.Column(db.Integer, nullable=False) # Number of retrieved points per provider
    retrieval_id = db.Column(db.Integer,
                             db.ForeignKey("retrievals_producer.id"),
                             nullable=False)
    retrieval = db.relationship("RetrievalProducer",
                                back_populates="billing")
    timestamp = db.Column(db.DateTime, default=datetime.now(), nullable=False)


class PreviewBilling(db.Model):
    """
    SQLAlchemy class representing map server billing information
    for one reverse query by a producer
    """

    __tablename__ = 'preview_billing'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer,
                          db.ForeignKey("producers.id"),
                          nullable=False)
    client = db.relationship("Producer",
                             uselist=False,
                             foreign_keys=[client_id])
    map_id = db.Column(db.Integer,
                       db.ForeignKey("map_keys.map_id"),
                       nullable=False)
    map = db.relationship("MapKey",
                          uselist=False,
                          foreign_keys=[map_id])
    timestamp = db.Column(db.DateTime, default=datetime.now(), nullable=False)


class OffsetBilling(db.Model):
    """
    SQLAlchemy class representing map server billing information
    for one offset query by a producer
    """

    __tablename__ = 'offset_billing'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer,
                          db.ForeignKey("producers.id"),
                          nullable=False)
    client = db.relationship("Producer",
                             uselist=False,
                             foreign_keys=[client_id])
    point_count = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(), nullable=False)
