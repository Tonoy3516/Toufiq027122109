#!/usr/bin/env python3
"""
Ultrasonic-Only Obstacle Avoidance Car
Uses only HC-SR04 ultrasonic sensor for obstacle detection
"""

import time
import RPi.GPIO as GPIO
import YB_Pcb_Car

# ==================== CONFIGURATION ====================
# Speed settings (0-100)
SPEEDS = {
    'normal': 70,      # Normal forward speed
    'slow': 45,        # Slow forward (approaching obstacle)
    'fast': 85,        # Fast forward (clear path)
    'turn': 65,        # Turning speed
    'spin': 80,        # Spinning speed (sharp turns)
    'back': 55,        # Backward speed
    'creep': 35,       # Very slow (close to obstacle)
}

# Distance zones (in centimeters)
ZONES = {
    'emergency': 12,   # Emergency stop and reverse
    'very_close': 18,  # Very close - turn immediately
    'close': 25,       # Close - prepare to turn
    'warning': 35,     # Warning - slow down
    'safe': 50,        # Safe distance
    'clear': 100,      # Clear path
}

# Turning times (in seconds)
TURN_DURATIONS = {
    'small': 0.25,     # Small adjustment
    'medium': 0.5,     # Medium turn (45-90 degrees)
    'large': 0.8,      # Large turn (90-135 degrees)
    'full': 1.2,       # Full 180-degree turn
}

# Ultrasonic sensor pins (BOARD numbering)
TRIG_PIN = 16   # GPIO 23
ECHO_PIN = 18   # GPIO 24

# ==================== INITIALIZATION ====================
print("\n" + "="*60)
print("ULTRASONIC-ONLY OBSTACLE AVOIDANCE CAR")
print("="*60)

# Initialize car
try:
    car = YB_Pcb_Car.YB_Pcb_Car()
    print("✓ Car initialized successfully")
    time.sleep(0.5)
except Exception as e:
    print(f"✗ Error initializing car: {e}")
    exit(1)

# Setup GPIO for ultrasonic only
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# Configure ultrasonic pins
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# Initialize trigger pin to LOW
GPIO.output(TRIG_PIN, False)
time.sleep(1)  # Let sensor settle

# ==================== ULTRASONIC FUNCTIONS ====================
def measure_distance():
    """
    Measure single distance reading in cm
    Returns -1 if measurement fails
    """
    # Send 10us pulse to trigger
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)  # 10 microseconds
    GPIO.output(TRIG_PIN, False)
    
    pulse_start = time.time()
    pulse_end = time.time()
    
    # Wait for echo to go HIGH (with timeout)
    timeout = time.time() + 0.1  # 100ms timeout
    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()
        if time.time() > timeout:
            return -1
    
    # Wait for echo to go LOW (with timeout)
    timeout = time.time() + 0.1  # 100ms timeout
    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()
        if time.time() > timeout:
            return -1
    
    # Calculate distance (speed of sound = 34300 cm/s)
    pulse_duration = pulse_end - pulse_start
    distance = (pulse_duration * 34300) / 2
    
    # Validate reading
    if 2 <= distance <= 400:  # Reasonable range for HC-SR04
        return round(distance, 1)
    return -1

def get_smooth_distance(samples=5):
    """
    Get smoothed distance by taking multiple samples
    Returns median of valid readings
    """
    readings = []
    
    for i in range(samples):
        dist = measure_distance()
        if dist != -1 and 2 <= dist <= 300:  # Valid range
            readings.append(dist)
        time.sleep(0.02)  # 20ms between readings
    
    if not readings:  # No valid readings
        return ZONES['safe'] + 20  # Return safe distance
    
    # Return median for stability
    readings.sort()
    return readings[len(readings) // 2]

# ==================== MOVEMENT FUNCTIONS ====================
def move_forward(speed_left=None, speed_right=None):
    """Move forward with optional wheel speed difference"""
    if speed_left is None:
        speed_left = SPEEDS['normal']
    if speed_right is None:
        speed_right = SPEEDS['normal']
    car.Car_Run(speed_left, speed_right)

def move_backward(speed=SPEEDS['back']):
    """Move backward"""
    car.Car_Back(speed, speed)

def stop():
    """Stop the car"""
    car.Car_Stop()

def turn_left(speed=SPEEDS['turn'], duration=TURN_DURATIONS['medium']):
    """Turn left (spin in place)"""
    car.Car_Spin_Left(speed, speed)
    time.sleep(duration)
    stop()

def turn_right(speed=SPEEDS['turn'], duration=TURN_DURATIONS['medium']):
    """Turn right (spin in place)"""
    car.Car_Spin_Right(speed, speed)
    time.sleep(duration)
    stop()

def pivot_left(speed=SPEEDS['turn'], duration=TURN_DURATIONS['small']):
    """Pivot left (one wheel moves)"""
    car.Car_Left(speed, speed)
    time.sleep(duration)
    stop()

def pivot_right(speed=SPEEDS['turn'], duration=TURN_DURATIONS['small']):
    """Pivot right (one wheel moves)"""
    car.Car_Right(speed, speed)
    time.sleep(duration)
    stop()

# ==================== OBSTACLE AVOIDANCE LOGIC ====================
def avoid_obstacle(distance):
    """
    Main obstacle avoidance logic based on distance only
    Returns True if car should continue, False if emergency stop
    """
    # Display current distance with visual indicator
    visual_bar = "█" * int(distance / 5) + "░" * (20 - int(distance / 5))
    print(f"Distance: {distance:5.1f} cm [{visual_bar:20}]", end=" | ")
    
    # ===== DECISION TREE (Distance-based only) =====
    
    # 1. EMERGENCY: Too close (< 12cm)
    if distance < ZONES['emergency']:
        print("EMERGENCY! Too close - Reversing and turning")
        stop()
        time.sleep(0.1)
        
        # Reverse for safety
        move_backward(SPEEDS['back'])
        time.sleep(0.6)
        stop()
        time.sleep(0.2)
        
        # Turn 90-120 degrees (random-ish based on time)
        turn_time = time.time()
        if int(turn_time * 10) % 2 == 0:  # Simple "random" decision
            spin_right(SPEEDS['spin'], TURN_DURATIONS['large'])
            print("  → Turned RIGHT")
        else:
            spin_left(SPEEDS['spin'], TURN_DURATIONS['large'])
            print("  → Turned LEFT")
        return True
    
    # 2. VERY CLOSE: 12-18cm
    elif distance < ZONES['very_close']:
        print("Too close! Turning immediately")
        stop()
        time.sleep(0.1)
        
        # Decide turn direction (alternate to avoid getting stuck)
        turn_time = time.time()
        if int(turn_time) % 2 == 0:
            turn_right(SPEEDS['spin'], TURN_DURATIONS['medium'])
            print("  → Turned RIGHT (medium)")
        else:
            turn_left(SPEEDS['spin'], TURN_DURATIONS['medium'])
            print("  → Turned LEFT (medium)")
        return True
    
    # 3. CLOSE: 18-25cm
    elif distance < ZONES['close']:
        print("Obstacle close - Turning")
        stop()
        time.sleep(0.1)
        
        # Small turn to avoid
        turn_right(SPEEDS['turn'], TURN_DURATIONS['small'])
        print("  → Turned RIGHT (small)")
        return True
    
    # 4. WARNING: 25-35cm
    elif distance < ZONES['warning']:
        # Slow down and make slight turn
        speed = SPEEDS['slow']
        print(f"Warning zone - Slowing down ({speed})")
        
        # Gentle turn while moving (right wheel slower)
        car.Car_Run(speed + 10, speed)
        return True
    
    # 5. SAFE: 35-50cm
    elif distance < ZONES['safe']:
        # Normal speed, straight ahead
        speed = SPEEDS['normal']
        print(f"Safe zone - Normal speed ({speed})")
        move_forward(speed, speed)
        return True
    
    # 6. CLEAR: 50-100cm
    elif distance < ZONES['clear']:
        # Faster speed
        speed = SPEEDS['fast']
        print(f"Clear zone - Faster speed ({speed})")
        move_forward(speed, speed)
        return True
    
    # 7. VERY CLEAR: >100cm
    else:
        # Maximum speed
        speed = min(SPEEDS['fast'] + 10, 100)  # Cap at 100
        print(f"Very clear - Maximum speed ({speed})")
        move_forward(speed, speed)
        return True

# ==================== WANDER MODE ====================
def wander_mode():
    """
    Wander mode: Move forward until obstacle detected,
    then turn and continue
    """
    print("\n" + "="*60)
    print("STARTING WANDER MODE")
    print("Car will wander freely, avoiding obstacles")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    # Variables for wander behavior
    last_turn_direction = "right"  # Start with right turns
    consecutive_turns = 0
    
    try:
        while True:
            # Get distance measurement
            distance = get_smooth_distance(3)
            
            # Avoid obstacle based on distance
            continue_moving = avoid_obstacle(distance)
            
            # If we just turned, move forward a bit
            if consecutive_turns > 0:
                move_forward(SPEEDS['normal'], SPEEDS['normal'])
                time.sleep(0.3)  # Move forward for 0.3s after turn
                consecutive_turns = 0
            
            # Small delay to prevent sensor interference
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\nWander mode interrupted by user")

# ==================== EXPLORE MODE ====================
def explore_mode():
    """
    Explore mode: More aggressive exploration with varied turns
    """
    print("\n" + "="*60)
    print("STARTING EXPLORE MODE")
    print("Car will explore more aggressively")
    print("="*60)
    
    explore_counter = 0
    
    try:
        while True:
            distance = get_smooth_distance(3)
            
            # Display exploration status
            explore_counter += 1
            if explore_counter % 10 == 0:
                print(f"\n[Explore #{explore_counter}] Still exploring...")
            
            # Decision based on distance
            if distance < ZONES['very_close']:
                print(f"\nExplore: Obstacle at {distance}cm - Changing direction")
                stop()
                time.sleep(0.1)
                
                # Vary turn direction and duration based on counter
                if explore_counter % 3 == 0:
                    # Big turn left
                    turn_left(SPEEDS['spin'], TURN_DURATIONS['large'])
                    print("  → Big left turn")
                elif explore_counter % 3 == 1:
                    # Big turn right
                    turn_right(SPEEDS['spin'], TURN_DURATIONS['large'])
                    print("  → Big right turn")
                else:
                    # 180-degree turn
                    turn_right(SPEEDS['spin'], TURN_DURATIONS['full'])
                    print("  → 180-degree turn")
                
                # Move forward after turn
                move_forward(SPEEDS['normal'], SPEEDS['normal'])
                time.sleep(0.5)
                
            elif distance < ZONES['warning']:
                # Slow and slight turn
                speed = max(SPEEDS['creep'], 
                          int(SPEEDS['slow'] * (distance / ZONES['warning'])))
                print(f"Explore: Approaching ({distance}cm) - Speed: {speed}")
                
                # Gentle curve away from obstacle
                car.Car_Run(speed + 5, speed)
                
            else:
                # Full speed ahead
                speed = SPEEDS['fast']
                print(f"Explore: Clear ({distance}cm) - Speed: {speed}")
                move_forward(speed, speed)
            
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\nExplore mode interrupted")

# ==================== MAIN PROGRAM ====================
def main():
    """Main program with mode selection"""
    print("\n" + "="*60)
    print("ULTRASONIC OBSTACLE AVOIDANCE CAR - READY")
    print("="*60)
    print(f"Distance Zones:")
    print(f"  Emergency: <{ZONES['emergency']}cm  (Stop & Reverse)")
    print(f"  Very Close: {ZONES['emergency']}-{ZONES['very_close']}cm  (Immediate Turn)")
    print(f"  Close: {ZONES['very_close']}-{ZONES['close']}cm  (Turn)")
    print(f"  Warning: {ZONES['close']}-{ZONES['warning']}cm  (Slow Down)")
    print(f"  Safe: {ZONES['warning']}-{ZONES['safe']}cm  (Normal Speed)")
    print(f"  Clear: {ZONES['safe']}-{ZONES['clear']}cm  (Fast Speed)")
    print(f"  Very Clear: >{ZONES['clear']}cm  (Maximum Speed)")
    print("="*60)
    print(f"Speeds: Slow={SPEEDS['slow']}, Normal={SPEEDS['normal']}, Fast={SPEEDS['fast']}")
    print("="*60)
    
    # Wait for startup
    time.sleep(2)
    
    # Quick sensor test
    print("\nTesting ultrasonic sensor...")
    test_distance = get_smooth_distance()
    print(f"Initial distance reading: {test_distance} cm")
    
    if test_distance < 0 or test_distance > 500:
        print("⚠ Warning: Ultrasonic reading may be inaccurate")
    else:
        print("✓ Ultrasonic sensor working")
    
    time.sleep(1)
    
    # Quick motor test
    print("\nQuick motor test...")
    move_forward(SPEEDS['normal'], SPEEDS['normal'])
    time.sleep(0.8)
    stop()
    time.sleep(0.3)
    turn_right(SPEEDS['turn'], 0.2)
    time.sleep(0.3)
    turn_left(SPEEDS['turn'], 0.2)
    time.sleep(0.5)
    print("✓ Motor test complete")
    
    # Mode selection
    print("\n" + "="*60)
    print("SELECT MODE:")
    print("1. Wander Mode (Simple obstacle avoidance)")
    print("2. Explore Mode (Aggressive exploration)")
    print("3. Manual Control Test")
    print("="*60)
    
    try:
        mode = input("Enter choice (1, 2, or 3): ").strip()
        
        if mode == "1":
            wander_mode()
        elif mode == "2":
            explore_mode()
        elif mode == "3":
            # Manual test mode
            print("\nManual Test Mode - Running for 10 seconds")
            for i in range(10, 0, -1):
                distance = get_smooth_distance()
                print(f"Time: {i}s | Distance: {distance}cm")
                avoid_obstacle(distance)
                time.sleep(1)
        else:
            print("Invalid choice, defaulting to Wander Mode")
            wander_mode()
            
    except KeyboardInterrupt:
        print("\nMode selection interrupted")
    
    except EOFError:
        print("\nNo input detected, defaulting to Wander Mode")
        wander_mode()
    
    finally:
        # Cleanup
        print("\n" + "="*60)
        print("CLEANUP SEQUENCE")
        print("="*60)
        stop()
        time.sleep(0.5)
        GPIO.cleanup()
        del car
        print("✓ GPIO cleanup complete")
        print("✓ Car object deleted")
        print("✓ Program ended safely")
        print("="*60)

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        # Emergency cleanup
        try:
            car.Car_Stop()
            GPIO.cleanup()
        except:
            pass
        print("Emergency cleanup performed")