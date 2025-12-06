#!/usr/bin/env python3
"""
Advanced Obstacle Avoidance Car with Variable Speeds
For YB_Pcb_Car with ultrasonic and IR sensors
"""

import time
import RPi.GPIO as GPIO
import YB_Pcb_Car

# ==================== CONFIGURATION ====================
# Speed settings (0-100)
SPEEDS = {
    'normal': 70,      # Normal forward speed
    'slow': 40,        # Slow forward (approaching obstacle)
    'fast': 85,        # Fast forward (clear path)
    'turn': 60,        # Turning speed
    'spin': 75,        # Spinning speed
    'back': 50,        # Backward speed
    'creep': 30,       # Very slow (narrow passage)
}

# Distance thresholds (in cm)
DISTANCE_THRESHOLDS = {
    'emergency': 10,   # Emergency stop and reverse
    'close': 20,       # Close obstacle - turn immediately
    'warning': 35,     # Warning - slow down
    'safe': 50,        # Safe distance
}

# Turning angles (in seconds)
TURN_TIMES = {
    'small': 0.3,      # Small adjustment
    'medium': 0.6,     # Medium turn
    'large': 1.0,      # Large turn (180 degree)
}

# ==================== INITIALIZATION ====================
print("Initializing Obstacle Avoidance Car...")

# Initialize car
try:
    car = YB_Pcb_Car.YB_Pcb_Car()
    print("✓ Car initialized successfully")
except Exception as e:
    print(f"✗ Error initializing car: {e}")
    exit(1)

# Setup GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# ==================== PIN DEFINITIONS ====================
# Ultrasonic (HC-SR04)
TRIG_PIN = 16
ECHO_PIN = 18

# IR obstacle sensors
IR_LEFT = 21
IR_RIGHT = 19
IR_ENABLE = 22

# ==================== GPIO SETUP ====================
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.setup(IR_LEFT, GPIO.IN)
GPIO.setup(IR_RIGHT, GPIO.IN)
GPIO.setup(IR_ENABLE, GPIO.OUT)

# Enable IR sensors
GPIO.output(IR_ENABLE, GPIO.HIGH)
GPIO.output(TRIG_PIN, False)
time.sleep(1)

# ==================== ULTRASONIC FUNCTIONS ====================
def get_distance():
    """Get single distance reading in cm"""
    # Send 10us pulse
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)
    
    start_time = time.time()
    stop_time = time.time()
    
    # Wait for echo to go high (with timeout)
    timeout = time.time() + 0.1
    while GPIO.input(ECHO_PIN) == 0:
        start_time = time.time()
        if time.time() > timeout:
            return 100  # Safe default
    
    # Wait for echo to go low (with timeout)
    timeout = time.time() + 0.1
    while GPIO.input(ECHO_PIN) == 1:
        stop_time = time.time()
        if time.time() > timeout:
            return 100  # Safe default
    
    # Calculate distance
    elapsed = stop_time - start_time
    distance = (elapsed * 34300) / 2  # Speed of sound
    
    # Filter unrealistic readings
    if 2 <= distance <= 400:
        return distance
    return 100

def get_smoothed_distance(samples=5):
    """Get average distance from multiple samples"""
    distances = []
    for _ in range(samples):
        dist = get_distance()
        if 2 < dist < 300:  # Only valid readings
            distances.append(dist)
        time.sleep(0.01)
    
    if not distances:
        return 50  # Default safe distance
    
    # Return median for stability
    distances.sort()
    return distances[len(distances) // 2]

# ==================== MOVEMENT FUNCTIONS ====================
def move_forward(speed_left=None, speed_right=None):
    """Move forward with optional different speeds for each wheel"""
    if speed_left is None:
        speed_left = SPEEDS['normal']
    if speed_right is None:
        speed_right = SPEEDS['normal']
    
    # Different speeds for turning while moving
    if speed_left != speed_right:
        car.Car_Run(speed_left, speed_right)
    else:
        car.Car_Run(speed_left, speed_right)

def move_backward(speed=SPEEDS['back']):
    """Move backward"""
    car.Car_Back(speed, speed)

def turn_left(speed=SPEEDS['turn'], duration=TURN_TIMES['small']):
    """Turn left (pivot)"""
    car.Car_Spin_Left(speed, speed)
    time.sleep(duration)
    car.Car_Stop()

def turn_right(speed=SPEEDS['turn'], duration=TURN_TIMES['small']):
    """Turn right (pivot)"""
    car.Car_Spin_Right(speed, speed)
    time.sleep(duration)
    car.Car_Stop()

def spin_left(speed=SPEEDS['spin'], duration=TURN_TIMES['medium']):
    """Spin left (sharp turn)"""
    car.Car_Spin_Left(speed, speed)
    time.sleep(duration)
    car.Car_Stop()

def spin_right(speed=SPEEDS['spin'], duration=TURN_TIMES['medium']):
    """Spin right (sharp turn)"""
    car.Car_Spin_Right(speed, speed)
    time.sleep(duration)
    car.Car_Stop()

def stop():
    """Stop the car"""
    car.Car_Stop()

# ==================== OBSTACLE AVOIDANCE LOGIC ====================
def check_and_avoid():
    """Main obstacle avoidance decision function"""
    # Get sensor readings
    distance = get_smoothed_distance(3)
    left_blocked = GPIO.input(IR_LEFT) == 0  # 0 = obstacle detected
    right_blocked = GPIO.input(IR_RIGHT) == 0
    
    # Display sensor status
    print(f"[Sensors] Distance: {distance:5.1f}cm | "
          f"Left IR: {'█' if left_blocked else '░'} | "
          f"Right IR: {'█' if right_blocked else '░'}", end=' | ')
    
    # ===== DECISION TREE =====
    
    # 1. EMERGENCY: Very close obstacle (< 10cm)
    if distance < DISTANCE_THRESHOLDS['emergency']:
        print("EMERGENCY: Too close! Reversing and turning")
        stop()
        time.sleep(0.1)
        move_backward(SPEEDS['back'])
        time.sleep(0.8)
        stop()
        time.sleep(0.2)
        
        # Decide which way to turn based on IR sensors
        if not left_blocked:  # Left is clear
            spin_left(SPEEDS['spin'], TURN_TIMES['medium'])
        else:
            spin_right(SPEEDS['spin'], TURN_TIMES['medium'])
        return
    
    # 2. CLOSE OBSTACLE AHEAD (10-20cm)
    elif distance < DISTANCE_THRESHOLDS['close']:
        print("Close obstacle! Avoiding...")
        stop()
        time.sleep(0.1)
        
        if left_blocked and right_blocked:
            # Obstacle on both sides - back up and turn right
            print("  → Both sides blocked, backing up")
            move_backward(SPEEDS['back'])
            time.sleep(0.5)
            stop()
            time.sleep(0.1)
            spin_right(SPEEDS['spin'], TURN_TIMES['large'])
            
        elif left_blocked and not right_blocked:
            # Obstacle on left only - turn right
            print("  → Obstacle left, turning right")
            turn_right(SPEEDS['turn'], TURN_TIMES['medium'])
            
        elif not left_blocked and right_blocked:
            # Obstacle on right only - turn left
            print("  → Obstacle right, turning left")
            turn_left(SPEEDS['turn'], TURN_TIMES['medium'])
            
        else:
            # Obstacle straight ahead - turn based on last turn or random
            print("  → Obstacle ahead, turning right")
            turn_right(SPEEDS['turn'], TURN_TIMES['medium'])
    
    # 3. WARNING ZONE (20-35cm) - Slow down and prepare to turn
    elif distance < DISTANCE_THRESHOLDS['warning']:
        print("Warning zone: Slowing down")
        
        # Calculate speed based on distance (closer = slower)
        speed_factor = (distance - DISTANCE_THRESHOLDS['close']) / \
                      (DISTANCE_THRESHOLDS['warning'] - DISTANCE_THRESHOLDS['close'])
        speed = SPEEDS['slow'] + int((SPEEDS['normal'] - SPEEDS['slow']) * speed_factor)
        speed = max(SPEEDS['slow'], min(speed, SPEEDS['normal']))
        
        # Gentle steering based on IR sensors
        if left_blocked and not right_blocked:
            # Drift right to avoid left wall
            print(f"  → Drifting right (L:{speed-20}, R:{speed})")
            car.Car_Run(speed-20, speed)
        elif not left_blocked and right_blocked:
            # Drift left to avoid right wall
            print(f"  → Drifting left (L:{speed}, R:{speed-20})")
            car.Car_Run(speed, speed-20)
        else:
            # Go straight, slow speed
            print(f"  → Moving forward slowly ({speed})")
            move_forward(speed, speed)
    
    # 4. SAFE ZONE (35-50cm) - Normal operation
    elif distance < DISTANCE_THRESHOLDS['safe']:
        print("Safe zone: Normal speed")
        
        # Adjust speed based on distance
        base_speed = SPEEDS['normal']
        
        if left_blocked and right_blocked:
            # Narrow passage - go slow and straight
            print(f"  → Narrow passage, creeping ({SPEEDS['creep']})")
            move_forward(SPEEDS['creep'], SPEEDS['creep'])
        elif left_blocked:
            # Keep away from left wall
            print(f"  → Avoiding left wall (L:{base_speed}, R:{base_speed-15})")
            car.Car_Run(base_speed, base_speed-15)
        elif right_blocked:
            # Keep away from right wall
            print(f"  → Avoiding right wall (L:{base_speed-15}, R:{base_speed})")
            car.Car_Run(base_speed-15, base_speed)
        else:
            # Clear path
            print(f"  → Clear path ({base_speed})")
            move_forward(base_speed, base_speed)
    
    # 5. VERY CLEAR (>50cm) - Faster speed
    else:
        print("Very clear: Faster speed")
        
        if left_blocked and right_blocked:
            # Between obstacles but far away - medium speed
            print(f"  → Between obstacles ({SPEEDS['normal']})")
            move_forward(SPEEDS['normal'], SPEEDS['normal'])
        elif left_blocked:
            # Far from left obstacle - slight right bias
            print(f"  → Far left obstacle (L:{SPEEDS['fast']}, R:{SPEEDS['fast']-10})")
            car.Car_Run(SPEEDS['fast'], SPEEDS['fast']-10)
        elif right_blocked:
            # Far from right obstacle - slight left bias
            print(f"  → Far right obstacle (L:{SPEEDS['fast']-10}, R:{SPEEDS['fast']})")
            car.Car_Run(SPEEDS['fast']-10, SPEEDS['fast'])
        else:
            # Completely clear - full speed ahead!
            print(f"  → Full speed ahead! ({SPEEDS['fast']})")
            move_forward(SPEEDS['fast'], SPEEDS['fast'])

# ==================== MAIN PROGRAM ====================
def main():
    print("\n" + "="*60)
    print("           ADVANCED OBSTACLE AVOIDANCE CAR")
    print("="*60)
    print(f"Speed Settings: Normal={SPEEDS['normal']}, Fast={SPEEDS['fast']}, "
          f"Slow={SPEEDS['slow']}, Turn={SPEEDS['turn']}")
    print(f"Distance Zones: Emergency<{DISTANCE_THRESHOLDS['emergency']}cm, "
          f"Close<{DISTANCE_THRESHOLDS['close']}cm, "
          f"Warning<{DISTANCE_THRESHOLDS['warning']}cm")
    print("="*60)
    print("Controls: Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    # Wait for everything to stabilize
    time.sleep(2)
    
    # Initial motor test
    print("Running motor test...")
    move_forward(SPEEDS['normal'], SPEEDS['normal'])
    time.sleep(1)
    stop()
    time.sleep(0.5)
    turn_right(SPEEDS['turn'], 0.3)
    time.sleep(0.5)
    turn_left(SPEEDS['turn'], 0.3)
    time.sleep(1)
    print("Motor test complete!\n")
    
    print("Starting obstacle avoidance in 3 seconds...")
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    print("\n" + "="*60)
    print("BEGINNING OBSTACLE AVOIDANCE")
    print("="*60 + "\n")
    
    loop_count = 0
    try:
        while True:
            check_and_avoid()
            loop_count += 1
            
            # Small delay for CPU and sensor stability
            time.sleep(0.05)
            
            # Display status every 15 loops
            if loop_count % 15 == 0:
                print("\n" + "-"*40)
                print(f"Status: Running... Loop #{loop_count}")
                print("-"*40)
                
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("STOP SIGNAL RECEIVED")
        print("="*60)
    
    finally:
        # Cleanup sequence
        print("\nPerforming cleanup...")
        stop()
        time.sleep(0.5)
        GPIO.output(IR_ENABLE, GPIO.LOW)
        GPIO.cleanup()
        del car
        print("✓ Cleanup complete")
        print("✓ Program ended safely")
        print("="*60)

# ==================== RUN PROGRAM ====================
if __name__ == "__main__":
    main()