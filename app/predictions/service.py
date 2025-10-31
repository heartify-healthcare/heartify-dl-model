from sqlalchemy.orm import Session
from typing import Dict, List, Tuple, Optional
import numpy as np
from app.predictions.schema import HeartDiseaseInput
from app.predictions.libs.heart_disease_model import HeartDiseaseModel
from app.predictions.libs.ecg_classifier import ECGClassifier
from app.predictions.entity import Prediction
from app.predictions.repository import PredictionRepository
from app.users.repository import UserRepository

class PredictionService:
    def __init__(self, db: Session):
        self.repo = PredictionRepository(db)
        self.user_repo = UserRepository(db)

    def predict_heart_disease(self, input_data: HeartDiseaseInput, user_id: int) -> Tuple[Optional[Prediction], Optional[Dict[str, str]]]:
        # Check if user exists
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return None, {"error": "User not found"}
        
        # Process ECG signal to get restecg value
        try:
            ecg_classifier = ECGClassifier()
            ecg_signal = np.array(input_data.ecg)
            restecg_value, _ = ecg_classifier.classify_ecg(ecg_signal)
        except Exception as e:
            return None, {"error": f"ECG processing error: {str(e)}"}
            
        # Convert pydantic model to list of features in the correct order
        features = [
            input_data.age,
            input_data.sex,
            input_data.cp,
            input_data.trestbps,
            restecg_value,  # Use computed restecg value
            input_data.thalach,
            input_data.exang
        ]
        
        try:
            model = HeartDiseaseModel()
            probability, prediction_result = model.predict(features)
        except Exception as e:
            return None, {"error": f"Prediction model error: {str(e)}"}
        
        # Create prediction record in database
        prediction = Prediction(
            user_id=user_id,  # Use user_id from JWT token
            age=input_data.age,
            sex=input_data.sex,
            cp=input_data.cp,
            trestbps=input_data.trestbps,
            restecg=restecg_value,  # Store computed restecg value
            thalach=input_data.thalach,
            exang=input_data.exang,
            probability=probability,
            prediction=prediction_result
        )
        
        try:
            created_prediction = self.repo.create(prediction)
            return created_prediction, None
        except Exception as e:
            return None, {"error": f"Database error: {str(e)}"}
        
    def get_prediction(self, prediction_id: int) -> Optional[Prediction]:
        return self.repo.get_by_id(prediction_id)
        
    def get_user_predictions(self, user_id: int) -> List[Prediction]:
        return self.repo.get_by_user_id(user_id)
        
    def get_all_predictions(self) -> List[Prediction]:
        return self.repo.get_all()
        
    def delete_prediction(self, prediction_id: int) -> bool:
        prediction = self.repo.get_by_id(prediction_id)
        if prediction:
            try:
                self.repo.delete(prediction)
                return True
            except Exception as e:
                print(f"Error deleting prediction: {str(e)}")
                return False
        return False