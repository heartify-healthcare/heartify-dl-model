import os
import sys
import torch
import torch.nn as nn
import numpy as np
from typing import Tuple, Dict
from scipy import signal as sps
import math

# --- Constants for Signal Processing ---
ORIGIN_FS = 130   # Original sampling rate (Polar H10)
TARGET_FS = 500   # Target sampling rate for model
TARGET_LEN = 5000 # Expected input length for model (10 seconds @ 500Hz)
SAMPLES_ORIGIN = 1300  # 130Hz * 10 seconds

# Multi-label classes
CLASSES = ["AFIB", "AFL", "Brady", "IAVB", "LBBB", "Normal", "PAC", "PVC", "RBBB", "STD", "STE", "Tachy"]

DIAGNOSIS_MAP = {
    "AFIB":   "Rung nhĩ (Atrial Fibrillation)",
    "AFL":    "Cuồng nhĩ (Atrial Flutter)",
    "Brady":  "Nhịp chậm (<60 BPM)",
    "IAVB":   "Block nhĩ thất độ I",
    "LBBB":   "Block nhánh trái",
    "Normal": "Bình thường (Normal Sinus Rhythm)",
    "PAC":    "Ngoại tâm thu nhĩ",
    "PVC":    "Ngoại tâm thu thất",
    "RBBB":   "Block nhánh phải",
    "STD":    "Chênh xuống đoạn ST (Thiếu máu cơ tim)",
    "STE":    "Chênh lên đoạn ST (Nhồi máu cơ tim)",
    "Tachy":  "Nhịp nhanh (>100 BPM)"
}


def _setup_fairseq_env():
    """Setup fairseq and fairseq-signals paths if available locally."""
    cwd = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    fairseq_path = os.path.join(cwd, "fairseq")
    signals_path = os.path.join(cwd, "fairseq-signals")
    
    if os.path.exists(fairseq_path) and fairseq_path not in sys.path:
        sys.path.insert(0, fairseq_path)
    if os.path.exists(signals_path) and signals_path not in sys.path:
        sys.path.insert(0, signals_path)


# Setup environment before importing fairseq modules
_setup_fairseq_env()

# Import fairseq-signals model components
try:
    from fairseq_signals.models.wav2vec.wav2vec2_cmsc_rlm import Wav2Vec2CMSCRLMModel, Wav2Vec2CMSCRLMConfig
except ImportError:
    # Fallback for alternative package structure
    try:
        from fairseq_signals.models.ecg_transformer import ECGTransformerModel as Wav2Vec2CMSCRLMModel
        from fairseq_signals.models.ecg_transformer import ECGTransformerConfig as Wav2Vec2CMSCRLMConfig
    except ImportError as e:
        raise ImportError(f"Failed to import fairseq-signals components: {e}")


class ECGFM_MultiLabel(nn.Module):
    """ECG Foundation Model for Multi-label Classification (12 classes)."""
    
    def __init__(self, num_classes: int = 12):
        super().__init__()
        cfg = Wav2Vec2CMSCRLMConfig()
        if hasattr(cfg, 'model'):
            model_cfg = cfg.model
        else:
            model_cfg = cfg
            
        # Fix Architecture to match training
        model_cfg.encoder_embed_dim = 768
        model_cfg.conv_feature_layers = "[(256, 2, 2)] * 4"
        
        self.enc = Wav2Vec2CMSCRLMModel(model_cfg)
        
        self.head = nn.Sequential(
            nn.Linear(768, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.enc(source=x, padding_mask=None, mask=False)
        return self.head(res['x'].mean(dim=1))


class ECGModel:
    """Singleton wrapper for ECG-FM Multi-label model inference."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ECGModel, cls).__new__(cls)
            cls._instance._model = None
            cls._instance._device = None
        return cls._instance
    
    def load(self, model_path: str) -> None:
        """Load the fine-tuned ECG multi-label model weights."""
        if self._model is None:
            try:
                # Determine device (CPU or CUDA)
                self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                
                # Initialize model with 12 classes
                self._model = ECGFM_MultiLabel(num_classes=len(CLASSES)).to(self._device)
                
                # Load weights
                if os.path.exists(model_path):
                    state = torch.load(model_path, map_location=self._device)
                    self._model.load_state_dict(state)
                    self._model.eval()
                    print(f"✅ ECG Multi-label model loaded from: {model_path}")
                else:
                    raise FileNotFoundError(f"Model file not found: {model_path}")
                    
            except Exception as e:
                raise RuntimeError(f"Failed to load ECG model: {str(e)}")
    
    def preprocess(self, ecg_signal: np.ndarray) -> torch.Tensor:
        """
        Preprocess 130Hz ECG signal to 500Hz format for model input.
        
        Input: 1300 samples (10 seconds @ 130Hz)
        Output: Tensor of shape [1, 12, 5000] (batch, channels, samples)
        
        Processing steps from convert.py:
        1. Detrend - remove baseline wander
        2. Polyphase Resample 130Hz -> 500Hz (up=50, down=13)
        3. Fix length to exactly 5000 samples
        4. Normalize (Z-score)
        5. Tile to 12 leads
        """
        ecg = np.array(ecg_signal, dtype=np.float32)
        ecg = np.nan_to_num(ecg)
        
        # Step 1: Detrend - remove baseline drift
        ecg_detrend = sps.detrend(ecg)
        
        # Step 2: Polyphase Resample from 130Hz to 500Hz
        # GCD(500, 130) = 10 -> up=50, down=13
        g = math.gcd(TARGET_FS, ORIGIN_FS)
        up = TARGET_FS // g   # 50
        down = ORIGIN_FS // g  # 13
        ecg_resampled = sps.resample_poly(ecg_detrend, up, down)
        
        # Step 3: Fix length to exactly TARGET_LEN (5000) samples
        if len(ecg_resampled) != TARGET_LEN:
            ecg_resampled = sps.resample(ecg_resampled, TARGET_LEN)
        
        # Step 4: Normalize (Z-score)
        if np.std(ecg_resampled) > 1e-6:
            ecg_normalized = (ecg_resampled - np.mean(ecg_resampled)) / np.std(ecg_resampled)
        else:
            ecg_normalized = np.zeros_like(ecg_resampled)
        
        # Step 5: Tile to 12 leads and create batch tensor [1, 12, 5000]
        ecg_12lead = np.tile(ecg_normalized, (12, 1))  # Shape: (12, 5000)
        tensor = torch.tensor(ecg_12lead, dtype=torch.float32).unsqueeze(0)  # [1, 12, 5000]
        
        return tensor.to(self._device)
    
    def compute_physiological_features(self, ecg_signal: np.ndarray, fs: int = 130) -> Dict:
        """Compute physiological features from original 130Hz ECG signal."""
        try:
            # Remove DC offset
            ecg = ecg_signal - np.mean(ecg_signal)
            
            # Bandpass filter 0.5-40 Hz
            b, a = sps.butter(3, [0.5/(fs/2), 40/(fs/2)], btype='band')
            ecg_filt = sps.filtfilt(b, a, ecg)
            
            # Simple R-peak detection using local maxima
            min_distance = int(0.4 * fs)
            threshold = 0.3 * np.max(ecg_filt)
            
            peaks = []
            for i in range(min_distance, len(ecg_filt) - min_distance):
                if ecg_filt[i] > threshold:
                    is_peak = True
                    for j in range(i - min_distance, i + min_distance):
                        if j != i and ecg_filt[j] >= ecg_filt[i]:
                            is_peak = False
                            break
                    if is_peak:
                        peaks.append(i)
            
            rpeaks = np.array(peaks)
            
            if len(rpeaks) < 2:
                return {
                    "heart_rate": None,
                    "hrv_rmssd": None,
                    "qrs_duration": None,
                    "r_amplitude": round(float(np.max(ecg_filt)), 3),
                    "signal_energy": round(float(np.sum(ecg_filt**2)), 4),
                    "note": "Insufficient R-peaks detected"
                }
            
            rr_intervals = np.diff(rpeaks) / fs * 1000
            valid_rr = rr_intervals[(rr_intervals > 300) & (rr_intervals < 2000)]
            
            if len(valid_rr) < 2:
                hr = None
                hrv_rmssd = None
            else:
                hr = round(60000 / np.mean(valid_rr), 2)
                hrv_rmssd = round(float(np.sqrt(np.mean(np.square(np.diff(valid_rr))))), 3)
            
            qrs_duration = None
            if len(rpeaks) > 0 and len(valid_rr) > 0:
                qrs_duration = round(np.mean(valid_rr) * 0.1 / 1000, 3)
            
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
    
    def predict(self, ecg_signal: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Predict ECG multi-label classification.
        
        Args:
            ecg_signal: 1D numpy array of 1300 samples (130Hz, 10 seconds)
            
        Returns:
            Tuple of:
                - probabilities: numpy array of 12 class probabilities
                - physio_features: dict of physiological features
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        
        # Preprocess input (130Hz -> 500Hz, tile to 12 leads)
        x = self.preprocess(ecg_signal)
        
        # Inference
        with torch.no_grad():
            logits = self._model(x)
            probs = torch.sigmoid(logits).cpu().numpy()[0]  # Shape: (12,)
        
        # Compute physiological features from original signal
        physio_features = self.compute_physiological_features(ecg_signal)
        
        return probs, physio_features
