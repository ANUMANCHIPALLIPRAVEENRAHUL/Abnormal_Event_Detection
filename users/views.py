from django.http import JsonResponse, StreamingHttpResponse
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, HttpResponse
from .models import UserRegistrationModel
from .forms import UserRegistrationForm
from email.message import EmailMessage
from django.contrib import messages
from twilio.rest import Client
from ultralytics import YOLO
import numpy as np
import subprocess
import threading
import smtplib
import pygame
import torch
import cv2
import os

def UserHome(request):
    id=request.GET['id']
    return render(request, 'users/UserHome.html',{'id':id})

def UserRegisterActions(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            print('Data is Valid')
            form.save()
            messages.success(request, 'You have been successfully registered')
            form = UserRegistrationForm()
            return render(request, 'UserRegistrations.html', {'form': form})
        else:
            messages.success(request, 'Email or Mobile Already Existed')
            print("Invalid form")
    else:
        form = UserRegistrationForm()
    return render(request, 'UserRegistrations.html', {'form': form})

def UserLoginCheck(request):
    if request.method == "POST":
        loginid = request.POST.get('loginname')
        pswd = request.POST.get('pswd')
        print("Login ID = ", loginid, ' Password = ', pswd)
        try:
            check = UserRegistrationModel.objects.get(loginid=loginid, password=pswd)
            status = check.status
            print('Status is = ', status)
            if status == "activated":
                request.session['id'] = check.id
                request.session['loggeduser'] = check.name
                request.session['loginid'] = loginid
                request.session['email'] = check.email
                print("User id At", check.id, status)
                return render(request, 'users/UserHome.html',{'id':check.id})
            else:
                messages.success(request, 'Your Account Not at activated')
                return render(request, 'UserLogin.html')
        except Exception as e:
            print('Exception is ', str(e))
            pass
        messages.success(request, 'Invalid Login id and password')
    return render(request, 'UserLogin.html', {})

def otp(id):
    from_mail='abhyudayacse2k24@gmail.com'
    server =smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()

    server.login(from_mail,'ssus rgfl diqh vnju')

    ch=UserRegistrationModel.objects.get(id=id)
    to_mail=ch.email

    msg=EmailMessage()
    msg['subject']='Alert message'
    msg['from']=from_mail
    msg['to']=to_mail
    msg.set_content("Abnormal event detected")

    server.send_message(msg)

def play_sound_alret():
    pygame.mixer.init()
    Sound_path=r'media/alert.mp3'
    pygame.mixer.music.load(Sound_path)
    pygame.mixer.music.play()

def mobile(to_number, message_body):
    account_sid = 'USE_YOUR_TWILIO_ACCOUNT_SID'
    auth_token = 'e7055536beb7c1b464d4bdf82c9d375a'
    
    from_number = '+14352413636'
    
    client = Client(account_sid, auth_token)
    
    try:
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=to_number
        )
        print(f"Message sent successfully! Message SID: {message.sid}")
    except Exception as e:
        print(f"Failed to send message: {e}")

# Add necessary imports
import queue
import threading
import time

# Add threaded video capture class
class VideoCaptureDaemon:
    def __init__(self, video_path):
        self.cap = cv2.VideoCapture(video_path)
        self.fps = max(self.cap.get(cv2.CAP_PROP_FPS), 1)
        self.frame_times = queue.Queue()
        self.start_time = time.perf_counter()
        self.queue = queue.Queue(maxsize=10)  # Limit queue to avoid memory issues
        self.running = True
        self.thread = threading.Thread(target=self._reader)
        self.thread.daemon = True
        self.thread.start()

    def _reader(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break
            if not self.queue.full():
                self.queue.put(frame)
            else:
                # Discard the oldest frame to maintain queue size
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    pass
                self.queue.put(frame)

    def read(self):
        try:
            return self.queue.get(timeout=1)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
        self.cap.release()


# Modify the VideoProcessor class
class VideoProcessor:
    def __init__(self, video_path, id):
        self.video_path = video_path
        self.yolo_model = YOLO("yolov8n.pt").to('cuda' if torch.cuda.is_available() else 'cpu')
  # Use half-precision on GPU
        self.vehicle_classes = [1, 2, 3, 5, 7]
        self.pedestrian_pathway = np.array([[200, 400], [600, 400], [700, 700], [100, 700]])
        self.prev_gray = None
        self.movement_threshold = 10
        self.fight_threshold = 0.5
        self.angle_variance_threshold = 0.1
        self.cap = VideoCaptureDaemon(video_path)
        self.fps = self.cap.fps if (self.cap.fps and self.cap.fps > 0) else 30 # Default to 30 FPS if invalid
        self.frame_delay = 1 / self.fps
        self.abnormal_detected = False
        self.frame = None
        self.status_text = "Status: NORMAL"
        self.lock = threading.Lock()
        self.id = id

    def process_frame(self):
        frame = self.cap.read()
        if frame is None:
            return None

        # Resize frame for faster processing
        frame = cv2.resize(frame, (640, 480))  # Adjust dimensions as needed

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        overlay = frame.copy()
        cv2.polylines(overlay, [self.pedestrian_pathway], isClosed=True, color=(255, 255, 255), thickness=2)
        cv2.fillPoly(overlay, [self.pedestrian_pathway], color=(255, 255, 255))
        gray_overlay = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray_overlay, 1, 255, cv2.THRESH_BINARY)

        # Run YOLO inference with half-precision if available
        results = self.yolo_model(frame, half=torch.cuda.is_available())
        people_boxes = []
        abnormal_detected_frame = False

        for result in results:
            for box, cls in zip(result.boxes.xyxy, result.boxes.cls):
                x1, y1, x2, y2 = map(int, box)
                class_id = int(cls)

                if class_id in self.vehicle_classes:
                    center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
                    if mask[center_y, center_x] == 255:
                        label = result.names[class_id]
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(frame, f"Abnormal: {label}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        abnormal_detected_frame = True

                if class_id == 0:
                    people_boxes.append((x1, y1, x2, y2))

        # Check for fights only if people detected
        if self.prev_gray is not None and len(people_boxes) > 1:
            fight_detected = False
            for (x1, y1, x2, y2) in people_boxes:
                # Extract regions for optical flow
                prev_region = self.prev_gray[y1:y2, x1:x2]
                current_region = gray[y1:y2, x1:x2]
                
                if prev_region.size == 0 or current_region.size == 0:
                    continue
                
                # Compute optical flow with optimized parameters
                flow = cv2.calcOpticalFlowFarneback(prev_region, current_region, None, 0.5, 2, 5, 3, 5, 1.2, 0)
                if flow is None:
                    continue
                mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                
                motion_ratio = np.sum(mag > self.movement_threshold) / mag.size
                angle_variance = np.var(ang)
                
                if motion_ratio > self.fight_threshold and angle_variance > self.angle_variance_threshold:
                    fight_detected = True
                    break

            if fight_detected:
                cv2.putText(frame, "FIGHT DETECTED", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                abnormal_detected_frame = True

        self.prev_gray = gray

        # Trigger alerts if any abnormal detected
        if abnormal_detected_frame and not self.abnormal_detected:
                self.abnormal_detected = True  # Prevent multiple alerts
                threading.Thread(target=play_sound_alret).start()
                threading.Thread(target=otp, args=(self.id,)).start()
                threading.Thread(target=mobile, args=('+917036144357', 'Abnormal Event Detected')).start()
                self.abnormal_detected = True

        status_text = "Status: ABNORMAL" if abnormal_detected_frame else "Status: NORMAL"
        cv2.putText(frame, status_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 
                    (0, 0, 255) if abnormal_detected_frame else (0, 255, 0), 3)

        with self.lock:
            self.frame = frame
            self.status_text = status_text

        return frame

    def generate_frames(self):
        try:
            # Get accurate video FPS (add fallback for invalid values)
            actual_fps = self.cap.fps if self.cap.fps > 0 else 30
            frame_interval = 1 / actual_fps
            
            # Initialize timing control
            last_frame_time = time.perf_counter()
            
            while True:
                # Calculate exact time for next frame
                next_frame_time = last_frame_time + frame_interval
                
                # Process and yield frame
                frame = self.process_frame()
                if frame is None:
                    break

                _, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

                # Maintain precise timing using perf_counter()
                sleep_duration = next_frame_time - time.perf_counter()
                if sleep_duration > 0:
                    time.sleep(sleep_duration)
                
                # Update last frame time for next iteration
                last_frame_time = next_frame_time

        finally:
            self.cap.stop()


    def get_status(self):
        with self.lock:
            return self.status_text

# Update video_feed to use the new VideoProcessor
def video_feed(request):
    video_path = request.session.get('video_path')
    id=request.session.get('id')
    if not video_path:
        default_video_path = r"C:\MAJOR PROJECT\Deep Learning based Abnormal Event Detection\media"
        if os.path.exists(default_video_path):
            video_path = default_video_path
            request.session['video_path'] = video_path
            request.session['id']=id

        else:
            return HttpResponse("No video uploaded and default video not found.", status=400)

    processor = VideoProcessor(video_path,id)
    return StreamingHttpResponse(processor.generate_frames(), content_type='multipart/x-mixed-replace; boundary=frame')

video_processors = {}

def get_abnormal_status(request):
    global video_processors
    
    video_path = request.session.get('video_path')
    id=request.session.get('id')
    if not video_path:
        return JsonResponse({"status": "No video uploaded"})

    processor = VideoProcessor(video_path,id)
    status = processor.get_status()

    return JsonResponse({"status": status})

def predict_image(request):
    if request.method == 'POST' and 'media' in request.FILES:
        media_file = request.FILES['media']
        sid=request.POST['id']
        fs = FileSystemStorage()
        file_path = fs.save(media_file.name, media_file)
        media_path = os.path.join(fs.location, file_path)
        request.session['video_path'] = media_path
        request.session['id']=sid
        return render(request, 'users/predict.html',{'id':sid})
    
    id=request.GET['id']
    return render(request, 'users/predict.html',{'id':id})

def logout_views(request):
    request.session.flush()
    return render(request,'UserLogin.html')