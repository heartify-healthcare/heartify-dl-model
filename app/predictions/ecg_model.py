"""
ECG-FM Fine-tuned Model for ECG Classification
Based on the PyTorch implementation from ecg-fm-finetuned.ipynb
"""
import torch
import torch.nn as nn
import numpy as np
import os
from typing import Tuple, Dict


class ECGFMClassifier(nn.Module):
    """
    ECG Foundation Model Classifier
    Fine-tuned for binary classification (Normal vs Abnormal)
    """
    
    def __init__(self, input_dim=130, hidden_dim=256, num_classes=2):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv1d(1, 16, 7, padding=3),
            nn.ReLU(),
            nn.Conv1d(16, 32, 5, padding=2),
            nn.ReLU(),
            nn.Conv1d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1)
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x, return_features=False):
        feats = self.encoder(x)
        logits = self.classifier(feats)
        if return_features:
            return logits, feats.squeeze(-1)
        return logits


class ECGModel:
    """
    Singleton wrapper for ECG-FM model inference
    Handles model loading and prediction
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ECGModel, cls).__new__(cls)
            cls._instance._model = None
            cls._instance._device = None
        return cls._instance
    
    def load(self, model_path: str) -> None:
        """
        Load the fine-tuned ECG model weights
        
        Args:
            model_path: Path to the .pt model weights file
        """
        if self._model is None:
            try:
                # Determine device (CPU or CUDA)
                self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                
                # Initialize model
                self._model = ECGFMClassifier().to(self._device)
                
                # Load weights
                if os.path.exists(model_path):
                    self._model.load_state_dict(
                        torch.load(model_path, map_location=self._device)
                    )
                    self._model.eval()
                    print(f"✅ ECG model loaded from: {model_path}")
                else:
                    raise FileNotFoundError(f"Model file not found: {model_path}")
                    
            except Exception as e:
                raise RuntimeError(f"Failed to load ECG model: {str(e)}")
    
    def preprocess(self, ecg_signal: np.ndarray) -> torch.Tensor:
        """
        Preprocess ECG signal for model input
        
        Args:
            ecg_signal: 1D numpy array of ECG signal (length=130 for 130Hz, 1-lead)
            
        Returns:
            Preprocessed tensor ready for model input [1, 1, length]
        """
        # Normalize signal (z-score normalization)
        signal_mean = np.mean(ecg_signal)
        signal_std = np.std(ecg_signal) + 1e-6
        normalized = (ecg_signal - signal_mean) / signal_std
        
        # Convert to tensor and add batch/channel dimensions
        tensor = torch.tensor(normalized, dtype=torch.float32)
        tensor = tensor.unsqueeze(0).unsqueeze(0)  # [1, 1, length]
        
        return tensor.to(self._device)
    
    def predict(self, ecg_signal: np.ndarray) -> Tuple[str, Dict[str, float], np.ndarray]:
        """
        Predict ECG classification
        
        Args:
            ecg_signal: 1D numpy array of ECG signal
            
        Returns:
            Tuple of (prediction_label, probabilities_dict, embedding)
            - prediction_label: "Normal" or "Abnormal"
            - probabilities_dict: {"Normal": 0.xx, "Abnormal": 0.xx}
            - embedding: Feature embedding from encoder (for advanced analysis)
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        
        # Preprocess input
        x = self.preprocess(ecg_signal)
        
        # Inference
        with torch.no_grad():
            output, features = self._model(x, return_features=True)
            probs = torch.softmax(output, dim=1).cpu().numpy().flatten()
            pred_label_idx = np.argmax(probs)
        
        # Map to labels
        label = "Normal" if pred_label_idx == 0 else "Abnormal"
        
        probabilities = {
            "Normal": round(float(probs[0]), 4),
            "Abnormal": round(float(probs[1]), 4)
        }
        
        embedding = features.cpu().numpy().flatten()
        
        return label, probabilities, embedding
    
    def predict_from_file(self, file_path: str) -> Tuple[str, Dict[str, float]]:
        """
        Predict from a .npy file containing ECG signal
        
        Args:
            file_path: Path to .npy file
            
        Returns:
            Tuple of (prediction_label, probabilities_dict)
        """
        ecg_signal = np.load(file_path).astype(np.float32)
        label, probs, _ = self.predict(ecg_signal)
        return label, probs
