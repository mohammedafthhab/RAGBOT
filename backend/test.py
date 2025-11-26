import cv2
import mediapipe as mp
import numpy as np
import pickle
import requests
import time
import platform
import subprocess
import pyttsx3   

MODEL_PATH = "models/gesture_model.pkl"
ENCODER_PATH = "models/label_encoder.pkl"
CHAT_API = "http://127.0.0.1:5000/chat"

START_DELAY = 1
GESTURE_WINDOW = 1
SEND_GESTURE = "Good"
UNDO = "undo"
CLEAR = "clear"

# ---------------------------
# ✅ TEXT TO SPEECH FUNCTION
# ---------------------------
def speak_text(text, lang="en"):
    system = platform.system()

    try:
        # ✅ macOS built-in
        if system == "Darwin":
            subprocess.call(["say", text])

        # ✅ Windows / Linux using pyttsx3
        else:
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            engine.say(text)
            engine.runAndWait()

    except Exception as e:
        print("⚠️ TTS Error:", e)


# Load model
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

with open(ENCODER_PATH, "rb") as f:
    label_encoder = pickle.load(f)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

def normalize_landmarks(landmarks):
    arr = np.array(landmarks).reshape(-1, 3)
    wrist = arr[0]
    arr -= wrist
    max_val = np.max(np.abs(arr))
    if max_val != 0:
        arr /= max_val
    return arr.flatten().tolist()


print("\n✅ ready!")
time.sleep(START_DELAY)

sentence = []
last_pred = None
gesture_start_time = 0
collecting = False

print("\n✅ You can show gestures now.")
print("✋ Show gestures one by one. They will form a sentence.")
print("🤲 Show 'send' gesture to send the final sentence.\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    imgRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(imgRGB)

    h, w, _ = frame.shape
    current_pred = None

    if result.multi_hand_landmarks:
        for handLms in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)
            landmarks = [[lm.x, lm.y, lm.z] for lm in handLms.landmark]
            features = np.array([normalize_landmarks(landmarks)], dtype=np.float32)

            pred_idx = model.predict(features)[0]
            current_pred = label_encoder.inverse_transform([pred_idx])[0]

            cv2.putText(frame, f"Detected: {current_pred}", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    if current_pred is None:
        cv2.imshow("Gesture Sentence Builder", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        continue

    if current_pred != last_pred:
        last_pred = current_pred
        gesture_start_time = time.time()
        collecting = True

    if collecting:
        elapsed = time.time() - gesture_start_time

        cv2.putText(frame, f"Confirming in: {max(0, 3 - int(elapsed))}",
                    (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 255, 0), 2)

        if elapsed >= GESTURE_WINDOW:
            collecting = False

            if current_pred.lower() == SEND_GESTURE.lower():
                query = " ".join(sentence)
                print("\n📨 Sending to chatbot:", query)

                try:
                    response = requests.post(CHAT_API, json={"query": query})
                    bot_reply = response.json().get("answer", "")
                    print("🤖 Chatbot Reply:", bot_reply)

                    # ✅ Speak the chatbot reply
                    speak_text(bot_reply)

                except Exception as e:
                    print("Chatbot error:", e)
                    speak_text("Chatbot error:", e)

                sentence = []

            elif current_pred.lower() == UNDO.lower():
                if sentence:
                    removed = sentence.pop()
                    print(f"↩️ Removed last word: {removed}")
                print("📝 Sentence so far:", " ".join(sentence))

            elif current_pred.lower() == CLEAR.lower():
                sentence = []
                print("🗑️ Cleared the sentence.")

            else:
                sentence.append(current_pred)
                print("📝 Sentence so far:", " ".join(sentence))

    cv2.putText(frame, "Sentence: " + " ".join(sentence),
                (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 255), 2)

    cv2.imshow("Gesture Sentence Builder", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
