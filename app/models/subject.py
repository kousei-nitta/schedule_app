from app.extensions import db


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    # このデータの持ち主（利用者）。APIは、ログインした利用者の
    # データだけを扱う（app/ownership.py）
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    semester_id = db.Column(
        db.Integer, db.ForeignKey("semesters.id"), nullable=False
    )
    subject_name = db.Column(db.String(100), nullable=False)
    room = db.Column(db.String(100), nullable=True)
    weekday = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    semester = db.relationship("Semester", back_populates="subjects")
    events = db.relationship("Event", back_populates="subject")
    tasks = db.relationship("Task", back_populates="subject")
