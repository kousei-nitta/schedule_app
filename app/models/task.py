from app.extensions import db


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(
        db.Integer, db.ForeignKey("subjects.id"), nullable=True
    )
    category = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    due_datetime = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    is_completed = db.Column(db.Boolean, nullable=False, default=False)

    subject = db.relationship("Subject", back_populates="tasks")
