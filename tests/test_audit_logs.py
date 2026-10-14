
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.audit_log import AuditLog
from app.services.audit_logs import (
    list_audit_events,
    record_audit_event,
)


def make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    return engine, session_factory()


def test_record_audit_event():
    engine, db = make_session()
    try:
        event = record_audit_event(
            db,
            actor_id=7,
            action="service_request.created",
            resource_type="service_request",
            resource_id=123,
            new_values={"status": "PENDING"},
            ip_address="127.0.0.1",
        )
        db.commit()

        saved = db.get(AuditLog, event.id)
        assert saved is not None
        assert saved.actor_id == 7
        assert saved.resource_id == 123
        assert saved.new_values == {"status": "PENDING"}
    finally:
        db.close()
        engine.dispose()


def test_list_audit_events_filters_and_paginates():
    engine, db = make_session()
    try:
        record_audit_event(
            db,
            actor_id=7,
            action="service_request.created",
            resource_type="service_request",
            resource_id=123,
            commit=False,
        )
        record_audit_event(
            db,
            actor_id=8,
            action="department.updated",
            resource_type="department",
            resource_id=5,
            commit=False,
        )
        db.commit()

        items, total = list_audit_events(
            db,
            resource_type="service_request",
            limit=10,
            offset=0,
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].resource_id == 123
    finally:
        db.close()
        engine.dispose()


def test_audit_event_rolls_back_with_transaction():
    engine, db = make_session()
    try:
        record_audit_event(
            db,
            actor_id=7,
            action="service_request.created",
            resource_type="service_request",
            resource_id=123,
        )
        db.rollback()

        items, total = list_audit_events(db)
        assert total == 0
        assert items == []
    finally:
        db.close()
        engine.dispose()
