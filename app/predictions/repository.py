from sqlalchemy.orm import Session
from typing import Optional, List
from app.predictions.entity import Prediction

class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, prediction: Prediction) -> Prediction:
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def get_by_id(self, prediction_id: int) -> Optional[Prediction]:
        return self.db.query(Prediction).filter(Prediction.id == prediction_id).first()

    def get_by_user_id(self, user_id: int) -> List[Prediction]:
        return self.db.query(Prediction).filter(Prediction.user_id == user_id).all()

    def get_all(self) -> List[Prediction]:
        return self.db.query(Prediction).all()

    def delete(self, prediction: Prediction) -> None:
        self.db.delete(prediction)
        self.db.commit()