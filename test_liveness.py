"""
Liveness Detection Camera Test
Press B = Blink Test, H = Head Movement Test, P = Photo Attack Test, Q = Quit
"""
import cv2
from users.liveness_detection import LivenessDetector

ld = LivenessDetector()
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print('ERROR: Cannot open camera')
    exit()

print('Camera opened!')
print('Controls:')
print('  B = Test Blink Detection (blink a few times before pressing)')
print('  H = Test Head Movement (move head before pressing)')
print('  P = Test Photo Attack Detection')
print('  Q = Quit')
print()

frames = []

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frames.append(frame.copy())
    if len(frames) > 30:
        frames.pop(0)
    
    # Draw instructions on frame
    cv2.putText(frame, 'B=Blink H=Head P=Photo Q=Quit', (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f'Frames: {len(frames)}', (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    cv2.imshow('Liveness Detection Test', frame)
    
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        break
        
    elif key == ord('b') and len(frames) >= 10:
        try:
            result, details = ld.detect_blink(frames[-15:])
            status = "PASSED" if result else "FAILED"
            print(f'Blink Detection: {status}')
            if 'min_ear' in details:
                print(f'  Min EAR: {details["min_ear"]:.3f}, Max EAR: {details["max_ear"]:.3f}')
            if 'error' in details:
                print(f'  Error: {details["error"]}')
        except Exception as e:
            print(f'Blink test error: {e}')
            
    elif key == ord('h') and len(frames) >= 10:
        try:
            result, details = ld.detect_head_movement(frames[-15:])
            status = "PASSED" if result else "FAILED"
            print(f'Head Movement: {status}')
            print(f'  X Range: {details.get("x_range", 0):.1f}px, Y Range: {details.get("y_range", 0):.1f}px')
        except Exception as e:
            print(f'Head test error: {e}')
            
    elif key == ord('p'):
        try:
            result, details = ld.detect_photo_attack(frame)
            status = "REAL FACE" if result else "POSSIBLE SPOOF"
            print(f'Photo Attack Detection: {status}')
            print(f'  LBP Score: {details.get("lbp_score", 0):.3f}')
            print(f'  Sharpness: {details.get("sharpness", 0):.1f}')
            print(f'  Moire Detected: {details.get("moire_detected", False)}')
            print(f'  Glare Detected: {details.get("glare_detected", False)}')
        except Exception as e:
            print(f'Photo test error: {e}')

cap.release()
cv2.destroyAllWindows()
print('Test ended.')
