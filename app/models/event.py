from app.extensions import db


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(
        db.Integer, db.ForeignKey("subjects.id"), nullable=True
    )
    category = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    room = db.Column(db.String(100), nullable=True)
    employer = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_generated = db.Column(db.Boolean, nullable=False, default=False)

    subject = db.relationship("Subject", back_populates="events")
