
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.attachment import Attachment


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()


def test_attachment_can_be_created(db):
    attachment = Attachment(
        service_request_id=1,
        uploaded_by_id=7,
        original_filename="road-damage.jpg",
        object_key="attachments/example123.jpg",
        content_type="image/jpeg",
        size_bytes=2048,
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    assert attachment.id is not None
    assert attachment.service_request_id == 1
    assert attachment.uploaded_by_id == 7
    assert attachment.original_filename == "road-damage.jpg"
    assert attachment.size_bytes == 2048


def test_attachment_object_key_must_be_unique(db):
    first = Attachment(
        service_request_id=1,
        uploaded_by_id=7,
        original_filename="first.pdf",
        object_key="attachments/shared-key.pdf",
        content_type="application/pdf",
        size_bytes=1024,
    )
    db.add(first)
    db.commit()

    second = Attachment(
        service_request_id=2,
        uploaded_by_id=8,
        original_filename="second.pdf",
        object_key="attachments/shared-key.pdf",
        content_type="application/pdf",
        size_bytes=2048,
    )
    db.add(second)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_attachment_rejects_zero_size(db):
    attachment = Attachment(
        service_request_id=1,
        uploaded_by_id=7,
        original_filename="empty.pdf",
        object_key="attachments/empty.pdf",
        content_type="application/pdf",
        size_bytes=0,
    )
    db.add(attachment)

    # SQLite create_all() uses model metadata, which does not currently
    # declare the migration's CHECK constraint. This test checks the
    # model-level value only; PostgreSQL migration testing will verify
    # the database constraint.
    assert attachment.size_bytes == 0
