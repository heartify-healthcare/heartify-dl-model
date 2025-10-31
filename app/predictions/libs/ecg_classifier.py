import numpy as np
from scipy.signal import butter, filtfilt, lfilter, iirnotch, firwin, medfilt
from scipy.stats import zscore
import warnings
import time
from typing import Tuple, Dict

warnings.filterwarnings('ignore')

class ECGClassifier:
    def __init__(self, sampling_rate: int = 250, adc_gain: float = 1.0):
        """
        ECG Classifier để phân loại ECG thành 3 nhóm:
        0: Normal
        1: ST-T wave abnormality
        2: Left ventricular hypertrophy (LVH)
        
        Args:
            sampling_rate (int): Tần số lấy mẫu (Hz)
            adc_gain (float): Hệ số khuếch đại ADC (mV/unit)
        """
        self.sampling_rate = sampling_rate
        self.adc_gain = adc_gain
        
        # Adaptive thresholds based on ADC gain
        self.st_threshold = 0.1 * adc_gain  # mV
        self.lvh_threshold_male = 3.5 * adc_gain
        self.lvh_threshold_female = 2.5 * adc_gain

    def _moving_average_filter(self, signal: np.ndarray, window_size: int) -> np.ndarray:
        """
        Efficient moving average using scipy.signal.lfilter
        Thay thế pd.Series.rolling để tăng tốc độ
        """
        if window_size <= 1:
            return signal
        
        # Create filter coefficients
        b = np.ones(window_size) / window_size
        a = 1
        
        # Apply filter
        filtered = lfilter(b, a, signal)
        
        # Handle edge effects (similar to center=True in rolling)
        delay = window_size // 2
        if delay > 0:
            filtered = np.concatenate([filtered[delay:], filtered[-delay:]])
        
        return filtered

    def preprocess_ecg(self, ecg_signal: np.ndarray, powerline: float = 50) -> np.ndarray:
        """
        Tiền xử lý tín hiệu ECG với tối ưu hóa tốc độ
        """
        fs = self.sampling_rate
        
        # Validation đầu vào
        if len(ecg_signal) < fs:
            raise ValueError(f"ECG signal too short: {len(ecg_signal)} samples (minimum {fs} required)")
        
        # Convert to float and handle any non-numeric values
        cleaned = np.array(ecg_signal, dtype=float)
        
        # 1. Notch filter 50/60 Hz
        try:
            b_notch, a_notch = iirnotch(powerline/(fs/2), Q=30)
            cleaned = filtfilt(b_notch, a_notch, cleaned)
        except Exception as e:
            print(f"Warning: Notch filter failed: {e}")
            pass

        # 2. Reduced FIR filter (201 taps thay vì 401 để giảm latency)
        try:
            bp = firwin(numtaps=201, cutoff=[0.5, 40], fs=fs, pass_zero=False)
            cleaned = filtfilt(bp, [1], cleaned)
        except Exception as e:
            print(f"Warning: FIR filter failed, using Butterworth: {e}")
            # Fallback to Butterworth filter
            nyquist = fs / 2
            low_cutoff = 0.5 / nyquist
            high_cutoff = 40 / nyquist
            b, a = butter(4, [low_cutoff, high_cutoff], btype='band')
            cleaned = filtfilt(b, a, cleaned)

        # 3. Baseline wander removal (optimized)
        kernel_size = int(0.2*fs)
        if kernel_size % 2 == 0:
            kernel_size += 1
        baseline = medfilt(cleaned, kernel_size=kernel_size)
        cleaned -= baseline

        # 4. Motion-artifact detection (using optimized moving average)
        win = int(0.25*fs)
        if win > 0:
            rms = np.sqrt(self._moving_average_filter(cleaned**2, win))
            threshold = 8 * np.nanstd(cleaned)
            artifact_mask = rms > threshold
            cleaned[artifact_mask] = np.nan

        # 5. Z-score normalization
        valid = ~np.isnan(cleaned)
        if np.sum(valid) > 0:
            cleaned[valid] = zscore(cleaned[valid])

        return cleaned

    def detect_qrs_peaks(self, ecg_signal: np.ndarray) -> np.ndarray:
        """
        Phát hiện QRS peaks bằng thuật toán Pan-Tompkins tối ưu
        """
        fs = self.sampling_rate
        sig = ecg_signal.copy()
        
        # Xử lý NaN
        sig[np.isnan(sig)] = 0

        # 1. Derivative
        diff = np.diff(sig, prepend=sig[0])
        
        # 2. Square
        diff2 = diff**2
        
        # 3. Moving average 150 ms (optimized)
        window_size = int(0.15*fs)
        if window_size < 1:
            window_size = 1
        ma = self._moving_average_filter(diff2, window_size)

        # 4. Adaptive thresholding Pan-Tompkins
        SPKI, NPKI = 0.0, 0.0
        threshold_I1 = 0.0
        peaks = []
        warmup_samples = int(0.25*fs)

        for i, val in enumerate(ma):
            if val > threshold_I1 and i > warmup_samples:
                peaks.append(i)
                SPKI = 0.125*val + 0.875*SPKI
            else:
                NPKI = 0.125*val + 0.875*NPKI
            threshold_I1 = NPKI + 0.25*(SPKI - NPKI)

        # 5. Minimum distance constraint
        peaks = np.array(peaks)
        if len(peaks) > 1:
            rr = np.diff(peaks)
            min_rr = int(0.2*fs)
            invalid = np.where(rr < min_rr)[0] + 1
            peaks = np.delete(peaks, invalid)

        return peaks

    def extract_beats(self, ecg_signal: np.ndarray, qrs_peaks: np.ndarray) -> np.ndarray:
        """
        Trích xuất từng nhịp tim từ tín hiệu ECG
        """
        beats = []
        beat_length = int(0.8 * self.sampling_rate)
        
        for peak in qrs_peaks:
            start = max(0, peak - beat_length // 3)
            end = min(len(ecg_signal), peak + 2 * beat_length // 3)
            
            if end - start >= beat_length // 2:
                beat = ecg_signal[start:end]
                if len(beat) > beat_length:
                    beat = beat[:beat_length]
                elif len(beat) < beat_length:
                    beat = np.pad(beat, (0, beat_length - len(beat)), 'constant')
                beats.append(beat)
        
        return np.array(beats)

    def _calculate_st_slope(self, beat: np.ndarray, j_idx: int) -> Tuple[float, str]:
        """
        Tính toán ST slope để giảm false alarm trong tachycardia
        """
        fs = self.sampling_rate
        
        # ST segment: J point đến J+80ms
        st_start = j_idx
        st_end = min(j_idx + int(0.08*fs), len(beat))
        
        if st_end <= st_start + 1:
            return 0.0, "insufficient_data"
        
        st_segment = beat[st_start:st_end]
        time_points = np.arange(len(st_segment)) / fs
        
        # Linear regression for slope
        if len(time_points) > 1:
            slope = np.polyfit(time_points, st_segment, 1)[0]
            
            # Classify slope
            if slope > 0.5:
                slope_type = "upslope"
            elif slope < -0.5:
                slope_type = "downslope"
            else:
                slope_type = "flat"
                
            return slope, slope_type
        
        return 0.0, "insufficient_data"

    def analyze_st_segment(self, beat: np.ndarray, heart_rate: float = 60) -> Tuple[bool, float, str]:
        """
        Phân tích ST segment với ST-slope analysis để giảm false alarm
        """
        fs = self.sampling_rate
        
        # Validation
        if np.any(np.isnan(beat)) or len(beat) < 0.6*fs:
            return False, 0.0, "artifact"

        # Tìm R peak
        r_idx = np.argmax(beat)
        
        # 1. Tìm J point
        search_window = int(0.12*fs)
        end_idx = min(r_idx + search_window, len(beat))
        window = beat[r_idx:end_idx]
        
        if len(window) < 2:
            return False, 0.0, "short_beat"
        
        # Gradient để tìm J point
        der = np.gradient(window)
        j_candidates = np.where(np.abs(der) < 0.05)[0]
        
        if len(j_candidates) == 0:
            return False, 0.0, "no_J"
        
        j_offset = j_candidates[0]
        j_idx = r_idx + j_offset
        
        # 2. ST measurement point (J + 60ms)
        st_idx = j_idx + int(0.06*fs)
        
        if st_idx >= len(beat):
            return False, 0.0, "short_beat"

        # 3. Baseline estimation
        baseline_window = int(0.2*fs)
        base_start = max(0, j_idx - baseline_window)
        baseline_segment = beat[base_start:j_idx]
        
        if len(baseline_segment) == 0:
            baseline = 0.0
        else:
            baseline = np.median(baseline_segment)

        # 4. ST amplitude calculation
        st_amp = beat[st_idx] - baseline

        # 5. ST slope analysis
        slope, slope_type = self._calculate_st_slope(beat, j_idx)

        # 6. Advanced abnormality detection
        # Adaptive threshold based on heart rate and slope
        base_threshold = self.st_threshold
        
        # Tachycardia adjustment (giảm false alarm trong nhịp nhanh)
        if heart_rate > 100:
            # Trong tachycardia, cần threshold cao hơn
            base_threshold *= 1.3
            
            # Nếu là upslope trong tachycardia, có thể là normal
            if slope_type == "upslope" and abs(st_amp) < base_threshold * 1.5:
                return False, st_amp, f"tachycardia_upslope_{slope:.3f}"
        
        # Primary abnormality detection
        abnormal = abs(st_amp) >= base_threshold
        
        # Secondary criteria: slope analysis
        if slope_type == "downslope" and st_amp < -base_threshold * 0.7:
            abnormal = True
        elif slope_type == "upslope" and st_amp > base_threshold * 0.7:
            abnormal = True
        
        status = f"st_amp_{st_amp:.3f}_{slope_type}_slope_{slope:.3f}"
        
        return abnormal, st_amp, status

    def _estimate_qrs_width(self, beat: np.ndarray, r_peak_idx: int) -> int:
        """
        Ước tính độ rộng QRS complex (improved)
        """
        fs = self.sampling_rate
        
        # Tìm Q wave start
        q_search_start = max(0, r_peak_idx - int(0.08 * fs))
        q_start = q_search_start
        
        # Tìm điểm bắt đầu QRS (derivative approach)
        if q_search_start < r_peak_idx:
            pre_qrs = beat[q_search_start:r_peak_idx]
            der = np.gradient(pre_qrs)
            significant_change = np.where(np.abs(der) > 0.1)[0]
            if len(significant_change) > 0:
                q_start = q_search_start + significant_change[0]
        
        # Tìm S wave end
        s_search_end = min(r_peak_idx + int(0.12 * fs), len(beat))
        s_end = s_search_end
        
        if r_peak_idx < s_search_end:
            post_qrs = beat[r_peak_idx:s_search_end]
            der = np.gradient(post_qrs)
            return_to_baseline = np.where(np.abs(der) < 0.05)[0]
            if len(return_to_baseline) > 0:
                s_end = r_peak_idx + return_to_baseline[0]
        
        return s_end - q_start

    def analyze_lvh_criteria(self, beats: np.ndarray, sex: str = "M") -> Tuple[bool, float, str]:
        """
        Phân tích LVH với disclaimer rõ ràng về giới hạn single-lead
        """
        if len(beats) == 0:
            return False, 0.0, "no_beats"
        
        # Sử dụng beat trung bình
        avg_beat = np.mean(beats, axis=0)
        
        if len(avg_beat) < 100:
            return False, 0.0, "short_beat"
        
        # Tìm R peak amplitude
        r_peak_idx = np.argmax(avg_beat)
        r_amplitude = avg_beat[r_peak_idx]
        
        # Tìm S wave amplitude (improved detection)
        s_search_start = r_peak_idx
        s_search_end = min(r_peak_idx + int(0.12 * self.sampling_rate), len(avg_beat))
        
        s_amplitude = 0.0
        if s_search_end > s_search_start:
            s_region = avg_beat[s_search_start:s_search_end]
            s_idx = np.argmin(s_region)
            s_amplitude = abs(s_region[s_idx])
        
        # Enhanced voltage criteria
        voltage_sum = r_amplitude + s_amplitude
        
        # QRS width analysis (additional criterion)
        qrs_width = self._estimate_qrs_width(avg_beat, r_peak_idx)
        qrs_wide = qrs_width > 0.10 * self.sampling_rate  # >100ms
        
        # Threshold based on sex and enhanced criteria
        if sex.upper() == "M":
            voltage_threshold = self.lvh_threshold_male
        else:
            voltage_threshold = self.lvh_threshold_female
        
        # Multi-criteria LVH detection
        voltage_criteria = voltage_sum >= voltage_threshold
        
        # Bonus points for QRS width
        if qrs_wide:
            voltage_sum += 0.5  # Bonus for wide QRS
        
        lvh_detected = voltage_criteria
        
        # Enhanced status
        status = f"single_lead_voltage_{voltage_sum:.2f}mV_qrs_{qrs_width/self.sampling_rate*1000:.0f}ms"
        
        return lvh_detected, voltage_sum, status

    def classify_ecg(self, ecg_signal: np.ndarray) -> Tuple[int, Dict]:
        """
        Phân loại tín hiệu ECG với enhanced analysis
        """
        start_time = time.time()
        
        try:
            # Tiền xử lý
            processed_signal = self.preprocess_ecg(ecg_signal)
            
            # Phát hiện QRS peaks
            qrs_peaks = self.detect_qrs_peaks(processed_signal)
            
            if len(qrs_peaks) < 3:
                return 0, {
                    "error": "Insufficient QRS complexes detected", 
                    "qrs_count": len(qrs_peaks),
                    "processing_time": time.time() - start_time
                }
            
            # Tính heart rate
            duration = len(ecg_signal) / self.sampling_rate
            heart_rate = len(qrs_peaks) * 60 / duration
            
            # Trích xuất beats
            beats = self.extract_beats(processed_signal, qrs_peaks)
            
            if len(beats) == 0:
                return 0, {"error": "No valid beats extracted"}
            
            # Phân tích ST-T abnormalities với heart rate context
            st_abnormal_count = 0
            st_elevations = []
            st_statuses = []
            
            for beat in beats:
                st_abnormal, st_elevation, status = self.analyze_st_segment(beat, heart_rate)
                if st_abnormal:
                    st_abnormal_count += 1
                st_elevations.append(st_elevation)
                st_statuses.append(status)
            
            # Phân tích LVH
            lvh_detected, voltage_score, lvh_status = self.analyze_lvh_criteria(beats)
            
            # Classification logic
            st_abnormal_ratio = st_abnormal_count / len(beats)
            
            analysis_details = {
                "num_beats": len(beats),
                "qrs_peaks": len(qrs_peaks),
                "st_abnormal_count": st_abnormal_count,
                "st_abnormal_ratio": st_abnormal_ratio,
                "avg_st_elevation": np.mean([x for x in st_elevations if not np.isnan(x)]) if st_elevations else 0,
                "st_elevation_range": [np.min(st_elevations), np.max(st_elevations)] if st_elevations else [0, 0],
                "st_statuses": st_statuses[:5],  # First 5 for brevity
                "lvh_detected": lvh_detected,
                "voltage_score": voltage_score,
                "lvh_status": lvh_status,
                "lvh_disclaimer": "⚠️ Single-lead LVH detection has limited accuracy. Multi-lead ECG recommended for definitive diagnosis.",
                "heart_rate": heart_rate,
                "signal_quality": {
                    "duration": duration,
                    "valid_beats_ratio": len(beats) / len(qrs_peaks) if qrs_peaks.size > 0 else 0,
                    "adc_gain": self.adc_gain
                },
                "processing_time": time.time() - start_time
            }
            
            # Enhanced classification logic
            if lvh_detected:
                return 2, analysis_details  # LVH
            elif st_abnormal_ratio > 0.5:  # >50% beats have ST-T abnormality
                return 1, analysis_details  # ST-T abnormality
            else:
                return 0, analysis_details  # Normal
                
        except Exception as e:
            return 0, {
                "error": f"Classification failed: {str(e)}", 
                "processing_time": time.time() - start_time
            }