import cv2
import mediapipe as mp
import csv
import os
import numpy as np
import tkinter as tk
from tkinter import simpledialog

mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

csv_path = "final.csv"

# Create CSV if not exists
if not os.path.exists(csv_path):
    with open(csv_path, "w", newline='') as f:
        writer = csv.writer(f)
        header = ['gesture'] + [f'{axis}{i}' for axis in ['x','y','z'] for i in range(21)]
        writer.writerow(header)

print("✅ Data Collector Started!")
print("Press 'n' → Enter gesture label")
print("Press 's' → Save sample")
print("Press 'q' → Quit")

current_label = None

# ✅ Hidden TK root (so it doesn't open a big window)
root = tk.Tk()
root.withdraw()

def ask_label_popup():
    """Open a non-blocking popup to enter label."""
    label = simpledialog.askstring("Gesture Label", "Enter gesture name:")
    return label

def normalize_landmarks(landmarks):
    landmarks = np.array(landmarks).reshape(-1, 3)
    wrist = landmarks[0]
    landmarks -= wrist
    max_val = np.max(np.abs(landmarks))
    if max_val != 0:
        landmarks /= max_val
    return landmarks.flatten().tolist()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    key = cv2.waitKey(1) & 0xFF

    # ✅ Dynamic label input (popup)
    if key == ord('n'):
        new_label = ask_label_popup()
        if new_label:
            current_label = new_label.strip()
            print(f"✅ Label set to: {current_label}")
        else:
            print("⚠️ No label entered")

    # ✅ Quit
    if key == ord('q'):
        break

    # ✅ Save gesture
    if key == ord('s') and current_label:
        if result.multi_hand_landmarks:
            hand = result.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

            landmarks = [[lm.x, lm.y, lm.z] for lm in hand.landmark]
            normalized = normalize_landmarks(landmarks)

            with open(csv_path, "a", newline='') as f:
                writer = csv.writer(f)
                writer.writerow([current_label] + normalized)

            print(f"✅ Saved 1 sample for: {current_label}")

    # ✅ Show active label on screen
    if current_label:
        cv2.putText(frame, f"Label: {current_label}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 3)

    cv2.imshow("Dynamic Gesture Collector", frame)

cap.release()
cv2.destroyAllWindows()

print("✅ Collection Finished")
