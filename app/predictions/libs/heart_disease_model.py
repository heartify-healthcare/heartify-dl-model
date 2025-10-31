import numpy as np
from typing import List, Tuple, Union
import tensorflow as tf
import joblib
from app.config import Config

class HeartDiseaseModel:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HeartDiseaseModel, cls).__new__(cls)
            cls._instance._model = None
            cls._instance._scaler = None
        return cls._instance
    
    def load(self) -> None:
        if self._model is None:
            try:
                self._model = tf.keras.models.load_model(Config.MODEL_PATH)
            except Exception as e:
                raise RuntimeError(f"Failed to load model: {str(e)}")
                
        if self._scaler is None:
            try:
                self._scaler = joblib.load(Config.SCALER_PATH)
            except Exception as e:
                raise RuntimeError(f"Failed to load scaler: {str(e)}")
    
    def preprocess(self, features: List[Union[int, float]]) -> np.ndarray:
        if self._scaler is None:
            self.load()
            
        # Convert to numpy array and reshape
        X = np.array([features])
        
        # Apply scaling
        X_scaled = self._scaler.transform(X)
        
        # Reshape for CNN-LSTM model (samples, timesteps, features)
        X_reshaped = X_scaled.reshape((1, X_scaled.shape[1], 1))
        
        return X_reshaped
    
    def predict(self, features: List[Union[int, float]]) -> Tuple[float, str]:
        if self._model is None:
            self.load()
        
        # Preprocess the features
        X_processed = self.preprocess(features)
        
        # Make prediction
        prediction = self._model.predict(X_processed)
        probability = float(prediction[0][0])
        
        # Convert to human-readable prediction
        prediction_label = "POSITIVE" if probability > 0.5 else "NEGATIVE"
        
        return probability, prediction_label