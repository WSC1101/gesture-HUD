# -*- coding: utf-8 -*-
import math
import cv2
import mediapipe as mp
import json
import websocket
import time
from mediapipe.tasks.python.components.containers.landmark import Landmark

def connect_websocket():
    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect("ws://localhost:8884")
            print("✓ WebSocket Connected")
            return ws
        except ConnectionRefusedError:
            print("✗ Connection refused. Retrying in 2 seconds...")
            time.sleep(2)
        except Exception as e:
            print(f"✗ Connection error: {e}. Retrying in 2 seconds...")
            time.sleep(2)

ws = connect_websocket()


mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(1)


# --- Gesture recognization function ---
def get_distance(p1, p2):
    if p1 is None or p2 is None: return None
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def get_dict_distance(p1_dict, p2_dict):
    if p1_dict is None or p2_dict is None: return None
    return math.sqrt((p1_dict["x"] - p2_dict["x"]) ** 2 + (p1_dict["y"] - p2_dict["y"]) ** 2)


def extract_landmarks(hand_landmarks, ids_to_extract):
    landmarks_of_interest = {}
    for tip_id in ids_to_extract:
        landmarks = hand_landmarks.landmark[tip_id]
        landmarks_of_interest[str(tip_id)] = {
            'x': round(landmarks.x, 5),
            'y': round(landmarks.y, 5),
            'z': round(landmarks.z, 5)
        }
    return landmarks_of_interest


def recognize_single_hand_gesture(landmarks_of_interest, pinch_thresh, zoom_thresh, thresh):
    pos4 = landmarks_of_interest.get("4")
    pos8 = landmarks_of_interest.get("8")
    pos12 = landmarks_of_interest.get("12")
    pos16 = landmarks_of_interest.get("16")
    pos20 = landmarks_of_interest.get("20")

    dist_4_8 = get_dict_distance(pos4, pos8)
    dist_8_12 = get_dict_distance(pos8, pos12)
    dist_12_16 = get_dict_distance(pos12, pos16)
    dist_16_20 = get_dict_distance(pos16, pos20)

    dist = [dist_4_8, dist_8_12, dist_12_16, dist_16_20]

    if any(d is None for d in dist):
        return "none"

    if (dist_4_8 < pinch_thresh) and (dist_8_12 > thresh):
        return "pinch"

    if (dist_16_20 < zoom_thresh) and (dist_8_12 < thresh) and (dist_12_16 > thresh):
        return "pinch_zoom"

    return "pointer"

# --- function End ---

# websocket connection function(Continuous connectivity)
def safe_send(ws_connection, data):
    try:
        ws_connection.send(data)
        return True
    except (BrokenPipeError, ConnectionResetError, websocket.WebSocketConnectionClosedException) as e:
        print(f"\n✗ WebSocket connect refused: {e}")
        print("→ reconnection trying")
        return False
    except Exception as e:
        print(f"\n✗ send err: {e}")
        return False




with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
) as hands:
    THRESHOLD = 0.1
    pinch_THRESHOLD = 0.06
    ZOOM_THRESHOLD = 0.1

    last_send_time = 0
    THROTTLE_INTERVAL = 0.05

    current_gesture_state = "none"
    gesturekey = ""


    while cap.isOpened():
        current_time = time.time()

        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        current_global_action = "none"

        action_payload = {
            "action": "none", "x": 0.0, "y": 0.0, "current_dist": 0.0
        }

        if result.multi_hand_landmarks:
            all_hands_data = []
            tip_ids = [4, 8, 12, 16, 20]



            for hand_landmarks, handedness in zip(result.multi_hand_landmarks, result.multi_handedness):
                hand_label = handedness.classification[0].label
                landmarks_of_interest = extract_landmarks(hand_landmarks, tip_ids)

                gesture = "none"

                if hand_label == "Right":


                    gesture = recognize_single_hand_gesture(landmarks_of_interest, pinch_THRESHOLD, ZOOM_THRESHOLD,
                                                            THRESHOLD)
                    action_payload["action"] = gesture

                    if gesture == "pinch_zoom":
                        current_dist = get_dict_distance(landmarks_of_interest.get("4"),
                                                         landmarks_of_interest.get("8"))
                        zoom_center = landmarks_of_interest.get("4")

                        action_payload["current_dist"] = current_dist if current_dist is not None else 0.0
                        action_payload["x"] = zoom_center["x"] if zoom_center else 0.0
                        action_payload["y"] = zoom_center["y"] if zoom_center else 0.0

                    elif gesture == "pinch":
                        current_pinch_pos = landmarks_of_interest.get("4")
                        if current_pinch_pos:
                            action_payload["x"] = current_pinch_pos["x"]
                            action_payload["y"] = current_pinch_pos["y"]

                    elif gesture == "pointer":
                        pointer_pos = landmarks_of_interest.get("8")
                        if pointer_pos:
                            action_payload["x"] = pointer_pos["x"]
                            action_payload["y"] = pointer_pos["y"]

                    else:
                        gesture = "none"
                        action_payload["action"] = "none"

                    current_gesture_state = gesture
                    current_global_action = gesture

                elif hand_label == "Left" and current_global_action == "none":
                    gesture = recognize_single_hand_gesture(landmarks_of_interest, pinch_THRESHOLD, ZOOM_THRESHOLD, THRESHOLD)

                    if gesture == "pinch":

                        gesturekey = "left_pinch"
                        action_payload["action"] = "left_pinch"

                        current_pinch_pos = landmarks_of_interest.get("4")
                        if current_pinch_pos:
                            action_payload["x"] = current_pinch_pos["x"]
                            action_payload["y"] = current_pinch_pos["y"]

                        current_gesture_state = gesturekey




                all_hands_data.append({"landmarks": landmarks_of_interest})
                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

            if current_global_action != "none":
                action_payload["action"] = current_global_action
                gesturekey = current_global_action

            action_payload["hands"] = all_hands_data
            if current_global_action == "none":
                action_payload["action"] = current_gesture_state

            gesturekey = action_payload["action"]

            if gesturekey != "pinch_zoom":
                if "current_dist" in action_payload:
                    del action_payload["current_dist"]


            is_none_message = (gesturekey == "none")

            if is_none_message or (current_time - last_send_time) >= THROTTLE_INTERVAL:
                if is_none_message and current_gesture_state == "none":
                    pass
                else:
                    json_data = json.dumps({gesturekey: action_payload})

                    if not safe_send(ws, json_data):
                        ws.close()
                        ws = connect_websocket()
                        safe_send(ws, json_data)

                    print(json_data)
                    last_send_time = current_time
                    current_gesture_state = gesturekey


        else:
            if current_gesture_state != "none":
                print("---All gestures done! (No hands)---")

            current_global_action = "none"
            current_gesture_state = "none"

            json_data = json.dumps({"none": {"action": "none"}})
            if not safe_send(ws, json_data):
                ws.close()
                ws = connect_websocket()
                safe_send(ws, json_data)

        cv2.imshow('Hand Tracking', frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()
ws.close()
