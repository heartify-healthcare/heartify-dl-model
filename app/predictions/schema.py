from pydantic import BaseModel, Field, validator
from typing import List
from datetime import datetime

class HeartDiseaseInput(BaseModel):
    age: int = Field(..., ge=0, le=120, description="Age in years")
    sex: int = Field(..., ge=0, le=1, description="Sex (0 = female, 1 = male)")
    cp: int = Field(..., ge=1, le=4, description="Chest pain type (1-4)")
    trestbps: int = Field(..., ge=0, description="Resting blood pressure (in mm Hg)")
    ecg: List[int] = Field(..., description="ECG signal data as array of integers")
    thalach: int = Field(..., ge=0, description="Maximum heart rate achieved")
    exang: int = Field(..., ge=0, le=1, description="Exercise induced angina (1 = yes, 0 = no)")
    
    @validator('age')
    def age_must_be_reasonable(cls, v):
        if v < 18 or v > 100:
            raise ValueError("Age should be between 18 and 100")
        return v
    
    @validator('trestbps')
    def trestbps_must_be_reasonable(cls, v):
        if v < 50 or v > 300:
            raise ValueError("Resting blood pressure should be between 50 and 300")
        return v
    
    @validator('thalach')
    def thalach_must_be_reasonable(cls, v):
        if v < 50 or v > 300:
            raise ValueError("Maximum heart rate should be between 50 and 300")
        return v
    
    @validator('ecg')
    def ecg_must_not_be_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError("ECG signal data cannot be empty")
        return v


class PredictionResponse(BaseModel):
    id: int
    user_id: int
    
    # Health metrics
    age: int
    sex: int
    cp: int
    trestbps: int
    restecg: int
    thalach: int
    exang: int
    
    # Prediction results
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability of having heart disease")
    prediction: str = Field(..., description="Prediction result (POSITIVE or NEGATIVE)")
    created_at: datetime = Field(..., description="Timestamp when the prediction was created")
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "user_id": 2,
                "age": 45,
                "sex": 1,
                "cp": 3,
                "trestbps": 120,
                "restecg": 0,
                "thalach": 145,
                "exang": 0,
                "probability": 0.75,
                "prediction": "POSITIVE",
                "created_at": "2024-01-15T10:30:00"
            }
        }