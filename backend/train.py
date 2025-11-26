import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

DATA_CSV = "final.csv"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "gesture_model.pkl")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")

os.makedirs(MODEL_DIR, exist_ok=True)

print("📥 Loading dataset:", DATA_CSV)

# Load CSV (your dataset is clean)
df = pd.read_csv(DATA_CSV)

# First column is label
y = df.iloc[:, 0].astype(str)      # convert numeric gesture to string label
X = df.iloc[:, 1:].values.astype(np.float32)  # remaining 63 numeric features

print("✅ Loaded samples:", len(X))
print("✅ Feature dimension:", X.shape[1])
print("✅ Unique gesture labels:", y.unique())

# Encode labels
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

print("📚 Training:", len(X_train))
print("🧪 Testing:", len(X_test))

# Train model
model = RandomForestClassifier(
    n_estimators=500,
    random_state=42,
    n_jobs=-1
)

print("\n🚀 Training model...")
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print("\n✅ TEST ACCURACY:", round(acc * 100, 2), "%\n")
print("📊 Classification Report:")
print(classification_report(y_test, y_pred, target_names=le.classes_))

# Save model + label encoder
with open(MODEL_PATH, "wb") as f:
    pickle.dump(model, f)

with open(ENCODER_PATH, "wb") as f:
    pickle.dump(le, f)

print("\n✅ Model saved:", MODEL_PATH)
print("✅ Encoder saved:", ENCODER_PATH)
print("🎉 DONE!")
