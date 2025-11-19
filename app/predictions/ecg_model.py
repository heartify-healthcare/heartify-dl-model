"""
ECG-FM Fine-tuned Model for ECG Classification
Based on the PyTorch implementation from ecg-fm-finetuned.ipynb
"""
import torch
import torch.nn as nn
import numpy as np
import os
from typing import Tuple, Dict
import scipy.signal as sps


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
            ecg_signal: 1D numpy array of ECG signal (length=1300 for 130Hz, 10-second, 1-lead ECG)
        
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
    
    def compute_physiological_features(self, ecg_signal: np.ndarray, fs: int = 130) -> Dict:
        """
        Compute physiological features from ECG signal

        Based on simplified feature extraction (without neurokit2 dependency)
        
        Args:
            ecg_signal: 1D numpy array of ECG signal
            fs: Sampling frequency (default 130Hz)
        
        Returns:
            Dictionary of physiological features
        """
        try:
            # Remove DC offset
            ecg = ecg_signal - np.mean(ecg_signal)
            
            # Bandpass filter 0.5-40 Hz
            b, a = sps.butter(3, [0.5/(fs/2), 40/(fs/2)], btype='band')
            ecg_filt = sps.filtfilt(b, a, ecg)
            
            # Simple R-peak detection using local maxima
            # Find peaks with minimum distance of 0.4s (min 150 bpm)
            min_distance = int(0.4 * fs)
            threshold = 0.3 * np.max(ecg_filt)
            
            peaks = []
            for i in range(min_distance, len(ecg_filt) - min_distance):
                if ecg_filt[i] > threshold:
                    # Check if it's a local maximum
                    is_peak = True
                    for j in range(i - min_distance, i + min_distance):
                        if j != i and ecg_filt[j] >= ecg_filt[i]:
                            is_peak = False
                            break
                    if is_peak:
                        peaks.append(i)
            
            rpeaks = np.array(peaks)
            
            # Check if we have enough R peaks
            if len(rpeaks) < 2:
                return {
                    "heart_rate": None,
                    "hrv_rmssd": None,
                    "qrs_duration": None,
                    "r_amplitude": round(float(np.max(ecg_filt)), 3),
                    "signal_energy": round(float(np.sum(ecg_filt**2)), 4),
                    "note": "Insufficient R-peaks detected"
                }
            
            # RR intervals in milliseconds
            rr_intervals = np.diff(rpeaks) / fs * 1000
            
            # Filter outliers (300-2000 ms range = 30-200 bpm)
            valid_rr = rr_intervals[(rr_intervals > 300) & (rr_intervals < 2000)]
            
            if len(valid_rr) < 2:
                hr = None
                hrv_rmssd = None
            else:
                # Calculate heart rate
                hr = round(60000 / np.mean(valid_rr), 2)
                
                # Calculate HRV (RMSSD)
                if len(valid_rr) >= 2:
                    hrv_rmssd = round(float(np.sqrt(np.mean(np.square(np.diff(valid_rr))))), 3)
                else:
                    hrv_rmssd = None
            
            # Estimate QRS duration (average width at 50% amplitude)
            qrs_duration = None
            if len(rpeaks) > 0:
                # Simplified QRS estimation: ~10% of average RR interval
                if len(valid_rr) > 0:
                    qrs_duration = round(np.mean(valid_rr) * 0.1 / 1000, 3)  # in seconds
            
            features = {
                "heart_rate": hr,
                "hrv_rmssd": hrv_rmssd,
                "qrs_duration": qrs_duration,
                "r_amplitude": round(float(np.max(ecg_filt)), 3),
                "signal_energy": round(float(np.sum(ecg_filt**2)), 4),
                "r_peaks_count": int(len(rpeaks))
            }
            
        except Exception as e:
            features = {
                "error": f"Feature extraction failed: {str(e)}"
            }
        
        return features
    
    def predict(self, ecg_signal: np.ndarray) -> Tuple[str, Dict[str, float], Dict, np.ndarray]:
        """
        Predict ECG classification with physiological features
        
        Args:
            ecg_signal: 1D numpy array of ECG signal
        
        Returns:
            Tuple of (prediction_label, probabilities_dict, features_dict, embedding)
            - prediction_label: "Normal" or "Abnormal"
            - probabilities_dict: {"Normal": 0.xx, "Abnormal": 0.xx}
            - features_dict: Physiological features (HR, HRV, QRS, etc.)
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
        
        # Compute physiological features
        physio_features = self.compute_physiological_features(ecg_signal)
        
        embedding = features.cpu().numpy().flatten()
        
        return label, probabilities, physio_features, embedding
