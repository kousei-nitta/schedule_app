from app.extensions import db


class Closure(db.Model):
    __tablename__ = "closures"

    id = db.Column(db.Integer, primary_key=True)
    # このデータの持ち主（利用者）。APIは、ログインした利用者の
    # データだけを扱う（app/ownership.py）
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    semester_id = db.Column(
        db.Integer, db.ForeignKey("semesters.id"), nullable=False
    )
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(100), nullable=True)

    semester = db.relationship("Semester", back_populates="closures")
