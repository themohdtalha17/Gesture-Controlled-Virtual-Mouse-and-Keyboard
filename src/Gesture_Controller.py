# Imports
import cv2
import mediapipe as mp
import pyautogui
import math
from enum import IntEnum
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from google.protobuf.json_format import MessageToDict
import screen_brightness_control as sbcontrol
import time

# --- OPTIMIZATION: Remove PyAutoGUI safety delays ---
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0 

mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Gesture Encodings 
class Gest(IntEnum):
    FIST = 0
    PINKY = 1
    RING = 2
    MID = 4
    LAST3 = 7
    INDEX = 8
    FIRST2 = 12
    LAST4 = 15
    THUMB = 16    
    PALM = 31
    V_GEST = 33
    TWO_FINGER_CLOSED = 34
    PINCH_MAJOR = 35
    PINCH_MINOR = 36
    SHAKA = 37

class HLabel(IntEnum):
    MINOR = 0
    MAJOR = 1

class HandRecog:
    def __init__(self, hand_label):
        self.finger = 0
        self.ori_gesture = Gest.PALM
        self.prev_gesture = Gest.PALM
        self.frame_count = 0
        self.hand_result = None
        self.hand_label = hand_label
    
    def update_hand_result(self, hand_result):
        self.hand_result = hand_result

    def get_signed_dist(self, point):
        sign = -1
        if self.hand_result.landmark[point[0]].y < self.hand_result.landmark[point[1]].y:
            sign = 1
        dist = math.hypot(
            self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x,
            self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y
        )
        return dist * sign
    
    def get_dist(self, point):
        return math.hypot(
            self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x,
            self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y
        )
    
    def get_dz(self,point):
        return abs(self.hand_result.landmark[point[0]].z - self.hand_result.landmark[point[1]].z)
    
    def set_finger_state(self):
        if self.hand_result == None:
            return

        points = [[8,5,0],[12,9,0],[16,13,0],[20,17,0]]
        self.finger = 0
        self.finger = self.finger | 0 
        for idx,point in enumerate(points):
            dist = self.get_signed_dist(point[:2])
            dist2 = self.get_signed_dist(point[1:])
            
            try:
                ratio = round(dist/dist2,1)
            except:
                ratio = round(dist/0.01,1)

            self.finger = self.finger << 1
            if ratio > 0.5 :
                self.finger = self.finger | 1
    
    def get_gesture(self):
        if self.hand_result == None:
            return Gest.PALM

        current_gesture = Gest.PALM
        if self.finger in [Gest.LAST3,Gest.LAST4] and self.get_dist([8,4]) < 0.05:
            if self.hand_label == HLabel.MINOR :
                current_gesture = Gest.PINCH_MINOR
            else:
                current_gesture = Gest.PINCH_MAJOR

        elif Gest.FIRST2 == self.finger :
            point = [[8,12],[5,9]]
            dist1 = self.get_dist(point[0])
            dist2 = self.get_dist(point[1])
            ratio = dist1/dist2
            if ratio > 1.7:
                current_gesture = Gest.V_GEST
            else:
                if self.get_dz([8,12]) < 0.1:
                    current_gesture =  Gest.TWO_FINGER_CLOSED
                else:
                    current_gesture =  Gest.MID
        else:
            current_gesture =  self.finger
        
        # --- THUMB / SHAKA DETECTION ---
        thumb_is_up = False
        if self.hand_result.landmark[4].y < self.hand_result.landmark[3].y:
            thumb_is_up = True

        # 1. Thumbs Up (Fist + Thumb Up) -> Left Click
        if current_gesture == Gest.FIST and thumb_is_up:
            current_gesture = Gest.THUMB

        # 2. Shaka (Pinky + Thumb Up) -> Keyboard Toggle
        elif self.finger == Gest.PINKY and thumb_is_up:
            current_gesture = Gest.SHAKA

        if current_gesture == self.prev_gesture:
            self.frame_count += 1
        else:
            self.frame_count = 0

        self.prev_gesture = current_gesture

        if self.frame_count > 4 :
            self.ori_gesture = current_gesture
        return self.ori_gesture

class Controller:
    tx_old = 0
    ty_old = 0
    trial = True
    flag = False
    grabflag = False
    pinchmajorflag = False
    pinchminorflag = False
    pinchstartxcoord = None
    pinchstartycoord = None
    pinchdirectionflag = None
    prevpinchlv = 0
    pinchlv = 0
    framecount = 0
    prev_hand = None
    pinch_threshold = 0.3
    
    def getpinchylv(hand_result):
        dist = round((Controller.pinchstartycoord - hand_result.landmark[8].y)*10,1)
        return dist

    def getpinchxlv(hand_result):
        dist = round((hand_result.landmark[8].x - Controller.pinchstartxcoord)*10,1)
        return dist
    
    def changesystembrightness():
        currentBrightnessLv = sbcontrol.get_brightness(display=0)/100.0
        currentBrightnessLv += Controller.pinchlv/50.0
        if currentBrightnessLv > 1.0:
            currentBrightnessLv = 1.0
        elif currentBrightnessLv < 0.0:
            currentBrightnessLv = 0.0       
        sbcontrol.fade_brightness(int(100*currentBrightnessLv) , start = sbcontrol.get_brightness(display=0))
    
    def changesystemvolume():
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        currentVolumeLv = volume.GetMasterVolumeLevelScalar()
        currentVolumeLv += Controller.pinchlv/50.0
        if currentVolumeLv > 1.0:
            currentVolumeLv = 1.0
        elif currentVolumeLv < 0.0:
            currentVolumeLv = 0.0
        volume.SetMasterVolumeLevelScalar(currentVolumeLv, None)
    
    def scrollVertical():
        pyautogui.scroll(120 if Controller.pinchlv>0.0 else -120)
        
    def scrollHorizontal():
        pyautogui.keyDown('shift')
        pyautogui.keyDown('ctrl')
        pyautogui.scroll(-120 if Controller.pinchlv>0.0 else 120)
        pyautogui.keyUp('ctrl')
        pyautogui.keyUp('shift')

    def get_position(hand_result):
        point = 9
        position = [hand_result.landmark[point].x ,hand_result.landmark[point].y]
        sx,sy = pyautogui.size()
        x_old,y_old = pyautogui.position()
        x = int(position[0]*sx)
        y = int(position[1]*sy)
        if Controller.prev_hand is None:
            Controller.prev_hand = x,y
        delta_x = x - Controller.prev_hand[0]
        delta_y = y - Controller.prev_hand[1]

        distsq = delta_x**2 + delta_y**2
        ratio = 1
        Controller.prev_hand = [x,y]

        if distsq <= 25:
            ratio = 0
        elif distsq <= 900:
            ratio = 0.07 * (distsq ** (1/2))
        else:
            ratio = 2.1
        x , y = x_old + delta_x*ratio , y_old + delta_y*ratio
        return (x,y)

    def pinch_control_init(hand_result):
        Controller.pinchstartxcoord = hand_result.landmark[8].x
        Controller.pinchstartycoord = hand_result.landmark[8].y
        Controller.pinchlv = 0
        Controller.prevpinchlv = 0
        Controller.framecount = 0

    def pinch_control(hand_result, controlHorizontal, controlVertical):
        if Controller.framecount == 5:
            Controller.framecount = 0
            Controller.pinchlv = Controller.prevpinchlv

            if Controller.pinchdirectionflag == True:
                controlHorizontal()

            elif Controller.pinchdirectionflag == False:
                controlVertical()

        lvx =  Controller.getpinchxlv(hand_result)
        lvy =  Controller.getpinchylv(hand_result)
            
        if abs(lvy) > abs(lvx) and abs(lvy) > Controller.pinch_threshold:
            Controller.pinchdirectionflag = False
            if abs(Controller.prevpinchlv - lvy) < Controller.pinch_threshold:
                Controller.framecount += 1
            else:
                Controller.prevpinchlv = lvy
                Controller.framecount = 0

        elif abs(lvx) > Controller.pinch_threshold:
            Controller.pinchdirectionflag = True
            if abs(Controller.prevpinchlv - lvx) < Controller.pinch_threshold:
                Controller.framecount += 1
            else:
                Controller.prevpinchlv = lvx
                Controller.framecount = 0

    def handle_controls(gesture, hand_result):  
        x,y = None,None
        if gesture != Gest.PALM :
            x,y = Controller.get_position(hand_result)
        
        # --- DRAG AND DROP: DROP (Release) ---
        # If the gesture is NOT Fist, but we are currently holding (grabflag=True),
        # release the mouse button.
        if gesture != Gest.FIST and Controller.grabflag:
            Controller.grabflag = False
            pyautogui.mouseUp(button = "left")

        if gesture != Gest.PINCH_MAJOR and Controller.pinchmajorflag:
            Controller.pinchmajorflag = False

        if gesture != Gest.PINCH_MINOR and Controller.pinchminorflag:
            Controller.pinchminorflag = False

        if gesture == Gest.V_GEST:
            Controller.flag = True
            pyautogui.moveTo(x, y, duration = 0)

        # --- DRAG AND DROP: DRAG (Hold & Move) ---
        # If gesture IS Fist, hold down the mouse button and move.
        elif gesture == Gest.FIST:
            if not Controller.grabflag : 
                Controller.grabflag = True
                pyautogui.mouseDown(button = "left")
            pyautogui.moveTo(x, y, duration = 0)

        elif gesture == Gest.THUMB and Controller.flag:
            pyautogui.click()
            Controller.flag = False

        elif gesture == Gest.INDEX and Controller.flag:
            pyautogui.click(button='right')
            Controller.flag = False

        elif gesture == Gest.TWO_FINGER_CLOSED and Controller.flag:
            pyautogui.doubleClick()
            Controller.flag = False

        elif gesture == Gest.PINCH_MINOR:
            if Controller.pinchminorflag == False:
                Controller.pinch_control_init(hand_result)
                Controller.pinchminorflag = True
            Controller.pinch_control(hand_result,Controller.scrollHorizontal, Controller.scrollVertical)
        
        elif gesture == Gest.PINCH_MAJOR:
            if Controller.pinchmajorflag == False:
                Controller.pinch_control_init(hand_result)
                Controller.pinchmajorflag = True
            Controller.pinch_control(hand_result,Controller.changesystembrightness, Controller.changesystemvolume)

class Button:
    def __init__(self, pos, text, size=[40, 40]):
        self.pos = pos
        self.size = size
        self.text = text

class GestureController:
    gc_mode = 0
    cap = None
    CAM_HEIGHT = None
    CAM_WIDTH = None
    hr_major = None
    hr_minor = None
    dom_hand = True

    keyboard_keys = [
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";"],
        ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"],
        ["Space", "BS", "Ent"]
    ]
    
    buttonList = []
    keyboard_active = False
    last_toggle_time = 0
    last_click_time = 0

    def __init__(self):
        GestureController.gc_mode = 1
        GestureController.cap = cv2.VideoCapture(0)
        GestureController.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        GestureController.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        GestureController.CAM_HEIGHT = GestureController.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        GestureController.CAM_WIDTH = GestureController.cap.get(cv2.CAP_PROP_FRAME_WIDTH)

        start_x = 30
        start_y = 60 
        for i, row in enumerate(self.keyboard_keys):
            for j, key in enumerate(row):
                if i == 4: 
                    if key == "Space":
                        self.buttonList.append(Button([start_x + 60, start_y + i * 55], key, size=[150, 40]))
                    elif key == "BS":
                        self.buttonList.append(Button([start_x + 230, start_y + i * 55], key, size=[80, 40]))
                    elif key == "Ent":
                        self.buttonList.append(Button([start_x + 330, start_y + i * 55], key, size=[80, 40]))
                else:
                    self.buttonList.append(Button([start_x + j * 55, start_y + i * 55], key))

    def draw_keyboard(self, img):
        for button in self.buttonList:
            x, y = button.pos
            w, h = button.size
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 255), cv2.FILLED)
            font_scale = 2 if len(button.text) == 1 else 1
            text_x = x + 10
            text_y = y + 30
            if button.text == "Space": text_x += 20
            cv2.putText(img, button.text, (text_x, text_y),
                        cv2.FONT_HERSHEY_PLAIN, font_scale, (255, 255, 255), 2)
        return img

    def classify_hands(results):
        left , right = None,None
        try:
            handedness_dict = MessageToDict(results.multi_handedness[0])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[0]
            else :
                left = results.multi_hand_landmarks[0]
        except:
            pass
        try:
            handedness_dict = MessageToDict(results.multi_handedness[1])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[1]
            else :
                left = results.multi_hand_landmarks[1]
        except:
            pass
        
        if GestureController.dom_hand == True:
            GestureController.hr_major = right
            GestureController.hr_minor = left
        else :
            GestureController.hr_major = left
            GestureController.hr_minor = right

    def start(self):
        handmajor = HandRecog(HLabel.MAJOR)
        handminor = HandRecog(HLabel.MINOR)

        with mp_hands.Hands(max_num_hands = 2,
                            model_complexity=0, 
                            min_detection_confidence=0.5, 
                            min_tracking_confidence=0.5) as hands:
            while GestureController.cap.isOpened() and GestureController.gc_mode:
                success, image = GestureController.cap.read()
                if not success:
                    continue
                
                image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = hands.process(image)
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                if results.multi_hand_landmarks:                   
                    GestureController.classify_hands(results)
                    handmajor.update_hand_result(GestureController.hr_major)
                    handminor.update_hand_result(GestureController.hr_minor)

                    handmajor.set_finger_state()
                    handminor.set_finger_state()
                    gest_name = handminor.get_gesture()

                    if gest_name == Gest.PINCH_MINOR:
                        Controller.handle_controls(gest_name, handminor.hand_result)
                    else:
                        gest_name = handmajor.get_gesture()
                        
                        # Prevent mouse clicks while typing (INDEX gesture) in keyboard mode
                        if self.keyboard_active and gest_name == Gest.INDEX:
                            Controller.handle_controls(Gest.PALM, handmajor.hand_result)
                        else:
                            Controller.handle_controls(gest_name, handmajor.hand_result)
                        
                        if gest_name == Gest.SHAKA and (time.time() - self.last_toggle_time) > 2.0:
                            self.keyboard_active = not self.keyboard_active
                            self.last_toggle_time = time.time()
                            print(f"Keyboard Active: {self.keyboard_active}")

                        if self.keyboard_active and handmajor.hand_result:
                            image = self.draw_keyboard(image)
                            
                            idx_x = int(handmajor.hand_result.landmark[8].x * self.CAM_WIDTH)
                            idx_y = int(handmajor.hand_result.landmark[8].y * self.CAM_HEIGHT)
                            
                            for button in self.buttonList:
                                x, y = button.pos
                                w, h = button.size
                                
                                if x < idx_x < x + w and y < idx_y < y + h:
                                    cv2.rectangle(image, (x, y), (x + w, y + h), (175, 0, 175), cv2.FILLED)
                                    font_scale = 2 if len(button.text) == 1 else 1
                                    cv2.putText(image, button.text, (x + 10, y + 30),
                                                cv2.FONT_HERSHEY_PLAIN, font_scale, (255, 255, 255), 2)
                                    
                                    if gest_name == Gest.INDEX and (time.time() - self.last_click_time) > 0.5:
                                        if button.text == "Space":
                                            pyautogui.press('space')
                                        elif button.text == "BS":
                                            pyautogui.press('backspace')
                                        elif button.text == "Ent":
                                            pyautogui.press('enter')
                                        else:
                                            pyautogui.press(button.text)
                                            
                                        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), cv2.FILLED)
                                        self.last_click_time = time.time()

                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                else:
                    Controller.prev_hand = None
                
                cv2.imshow('Gesture Controller', image)
                if cv2.waitKey(1) & 0xFF == 13:
                    break
        GestureController.cap.release()
        cv2.destroyAllWindows()