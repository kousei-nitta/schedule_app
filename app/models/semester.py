from app.extensions import db


class Semester(db.Model):
    __tablename__ = "semesters"

    id = db.Column(db.Integer, primary_key=True)
    # このデータの持ち主（利用者）。APIは、ログインした利用者の
    # データだけを扱う（app/ownership.py）
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    name = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    subjects = db.relationship("Subject", back_populates="semester")
    closures = db.relationship("Closure", back_populates="semester")
