# Heartify - Deep Learning Model API

> Flask API backend for heart disease risk prediction using ECG signals and deep learning (ECG Foundation Model)

## 📋 Overview

Heartify provides a REST API for analyzing ECG signals to detect cardiac abnormalities. The system uses a fine-tuned **ECG Foundation Model** to classify ECG signals into **Normal** or **Abnormal** categories.

**Key Features:**
- 🔐 API Key management with email verification
- 🤖 ECG prediction (1-lead, 130Hz signal analysis)
- 📊 Physiological feature extraction (HR, HRV, QRS duration, etc.)
- 🔒 Secure authentication for all prediction requests

## 🚀 API Endpoints

### API Key Management

**POST** `/api/v1/api-keys/generation` - Request new API key  
**POST** `/api/v1/api-keys/deactivation` - Deactivate existing API key  
**GET** `/api/v1/api-keys/verify?token=...` - Verify email

### ECG Prediction

**POST** `/api/v1/predictions/`

Analyze ECG signal and return prediction results.

**Request:**
```json
{
  "ecg_signal": [array of 1300 float values]
}
```

**Response:**
```json
{
  "modelVersion": 1,
  "diagnosis": "Normal Sinus Rhythm",
  "probability": 0.9523,
  "features": {
    "heart_rate": 72.5,
    "hrv_rmssd": 45.3,
    "qrs_duration": 0.082,
    "r_amplitude": 1.234,
    "signal_energy": 15.6789
  }
}
```

## 🛠️ Tech Stack

- **Backend**: Python 3.12.0 or below, Flask 2.3.3, PostgreSQL, SQLAlchemy
- **Deep Learning**: PyTorch 2.6.0
- **Signal Processing**: SciPy 1.15.3

## 📦 Installation
Clone and install dependencies
```bash
# Clone repository
git clone https://github.com/heartify-healthcare/heartify-dl-model.git
cd heartify-dl-model

# Install dependencies
pip install -r requirements.txt

# Configure .env file with your settings
# It should be looked like .env.example
```

Download the `ecg_fm_best.pth` in [link](https://www.kaggle.com/code/minhphuc2544/finetuned-ecgfm-new/output) and put it in `model` folder.

Run server
```bash
# Run server
python wsgi.py
```

## 🐳 Docker

```bash
docker-compose up -d
```

## 🔬 Model Details

**ECG Foundation Model (ECG-FM)**
- Architecture: CNN encoder + Linear classifier
- Input: 1-lead ECG, 1300 samples (130Hz, 10 second)
- Output: Binary classification (Normal/Abnormal)
- Weights: `model/ecg_fm_best.pth`

## 📚 Academic Context

This mobile application was developed as part of a university **graduation thesis**, under the topic:

> **"Heart disease risk prediction using ECG signals with deep learning and large language models."**

## ✍️ Author

- [Vo Tran Phi](https://github.com/votranphi)
- [Le Duong Minh Phuc](https://github.com/minhphuc2544)

## 📄 License

This project is available under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) license.
