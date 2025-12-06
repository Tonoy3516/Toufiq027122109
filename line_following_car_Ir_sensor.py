#!/usr/bin/env python3
"""
Line Following Car for Raspbot
Using two IR sensors to follow black line on white surface
"""

import RPi.GPIO as GPIO
import time
import YB_Pcb_Car

# ==================== CONFIGURATION ====================
# IR Sensor Pins for line following (BOARD numbering)
LEFT_IR_PIN = 21     # Left IR sensor (GPIO 21)
RIGHT_IR_PIN = 19    # Right IR sensor (GPIO 19)
IR_ENABLE_PIN = 22   # IR sensor enable pin

# Speed settings (0-100)
SPEEDS = {
    'forward': 60,    # Straight line speed
    'turn': 50,       # Turning speed
    'sharp_turn': 40, # Sharp turning speed
    'adjust': 30,     # Small adjustment speed
    'max': 70,        # Maximum speed
    'min': 25,        # Minimum speed
}

# Line following logic (depends on surface color)
# For BLACK line on WHITE surface:
LINE_LOGIC = 0        # 0 = detect line (black), 1 = detect surface (white)
# For WHITE line on BLACK surface, reverse this value

# Line following sensitivity
TURN_THRESHOLD = 0.3  # How sharp to turn (0.1-0.5)
SPEED_ADJUST = True   # Adjust speed based on line straightness

# ==================== INITIALIZATION ====================
print("\n" + "="*60)
print("RASPBOT LINE FOLLOWING CAR")
print("="*60)

# Initialize car
try:
    car = YB_Pcb_Car.YB_Pcb_Car()
    print("✓ Car initialized successfully")
    time.sleep(0.5)
except Exception as e:
    print(f"✗ Error initializing car: {e}")
    exit(1)

# Setup GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# Configure IR sensor pins
GPIO.setup(LEFT_IR_PIN, GPIO.IN)
GPIO.setup(RIGHT_IR_PIN, GPIO.IN)
GPIO.setup(IR_ENABLE_PIN, GPIO.OUT)

# Enable IR sensors
GPIO.output(IR_ENABLE_PIN, GPIO.HIGH)
time.sleep(0.5)

# ==================== SENSOR CALIBRATION ====================
def calibrate_sensors():
    """Calibrate IR sensors for line detection"""
    print("\n🔧 Calibrating IR sensors...")
    print("Place sensors over line and surface to calibrate")
    
    samples = 10
    line_readings = []
    surface_readings = []
    
    print("\nPlace both sensors on the BLACK LINE")
    input("Press Enter when ready...")
    
    for i in range(samples):
        left = GPIO.input(LEFT_IR_PIN)
        right = GPIO.input(RIGHT_IR_PIN)
        line_readings.append((left, right))
        time.sleep(0.1)
    
    print("\nPlace both sensors on the WHITE SURFACE")
    input("Press Enter when ready...")
    
    for i in range(samples):
        left = GPIO.input(LEFT_IR_PIN)
        right = GPIO.input(RIGHT_IR_PIN)
        surface_readings.append((left, right))
        time.sleep(0.1)
    
    # Calculate averages
    avg_line = [sum(x)/len(x) for x in zip(*line_readings)]
    avg_surface = [sum(x)/len(x) for x in zip(*surface_readings)]
    
    print(f"\nCalibration Results:")
    print(f"Line readings: Left={avg_line[0]:.1f}, Right={avg_line[1]:.1f}")
    print(f"Surface readings: Left={avg_surface[0]:.1f}, Right={avg_surface[1]:.1f}")
    
    # Auto-detect logic
    if avg_line[0] < avg_surface[0] and avg_line[1] < avg_surface[1]:
        print("✓ Auto-detected: BLACK line on WHITE surface")
        return 0  # 0 = line detected
    else:
        print("✓ Auto-detected: WHITE line on BLACK surface")
        return 1  # 1 = line detected

# ==================== MOVEMENT FUNCTIONS ====================
def move_forward(speed_left=None, speed_right=None):
    """Move forward with optional different speeds"""
    if speed_left is None:
        speed_left = SPEEDS['forward']
    if speed_right is None:
        speed_right = SPEEDS['forward']
    car.Car_Run(speed_left, speed_right)

def stop():
    """Stop the car"""
    car.Car_Stop()

def turn_left(speed=SPEEDS['turn']):
    """Turn left (left wheel slower)"""
    car.Car_Run(speed - 20, speed)

def turn_right(speed=SPEEDS['turn']):
    """Turn right (right wheel slower)"""
    car.Car_Run(speed, speed - 20)

def sharp_left(speed=SPEEDS['sharp_turn']):
    """Sharp left turn"""
    car.Car_Spin_Left(speed, speed)

def sharp_right(speed=SPEEDS['sharp_turn']):
    """Sharp right turn"""
    car.Car_Spin_Right(speed, speed)

# ==================== LINE FOLLOWING LOGIC ====================
def read_line_sensors():
    """Read both IR sensors for line detection"""
    left_val = GPIO.input(LEFT_IR_PIN)
    right_val = GPIO.input(RIGHT_IR_PIN)
    
    # Convert based on LINE_LOGIC
    left_on_line = (left_val == LINE_LOGIC)
    right_on_line = (right_val == LINE_LOGIC)
    
    return left_on_line, right_on_line

def get_line_state():
    """Get current line following state"""
    left_on_line, right_on_line = read_line_sensors()
    
    # Determine state
    if left_on_line and right_on_line:
        return "ON_LINE"        # Both on line
    elif left_on_line and not right_on_line:
        return "RIGHT_OFF"      # Left on line, right off
    elif not left_on_line and right_on_line:
        return "LEFT_OFF"       # Right on line, left off
    else:
        return "BOTH_OFF"       # Both off line

def follow_line():
    """Main line following algorithm"""
    state = get_line_state()
    left_on_line, right_on_line = read_line_sensors()
    
    # Display sensor status
    left_char = "█" if left_on_line else "░"
    right_char = "█" if right_on_line else "░"
    
    print(f"Sensors: [{left_char}] [{right_char}] | State: {state:10}", end=" | ")
    
    # Decision making based on state
    if state == "ON_LINE":
        # Both sensors on line - go straight
        print("STRAIGHT")
        move_forward(SPEEDS['forward'], SPEEDS['forward'])
        
    elif state == "RIGHT_OFF":
        # Left on line, right off - turn right
        print("TURN RIGHT")
        turn_right(SPEEDS['turn'])
        
    elif state == "LEFT_OFF":
        # Right on line, left off - turn left
        print("TURN LEFT")
        turn_left(SPEEDS['turn'])
        
    elif state == "BOTH_OFF":
        # Both sensors off line - lost line
        print("LOST LINE - Searching...")
        search_for_line()
    
    return state

def search_for_line():
    """Search for line when lost"""
    print("  → Searching for line...")
    
    # Try turning left first
    sharp_left(SPEEDS['sharp_turn'])
    time.sleep(0.3)
    stop()
    
    # Check if found line
    for _ in range(5):
        state = get_line_state()
        if state != "BOTH_OFF":
            print(f"  → Found line! State: {state}")
            return
        time.sleep(0.1)
    
    # If not found, try turning right
    sharp_right(SPEEDS['sharp_turn'])
    time.sleep(0.6)  # Turn more
    stop()
    
    # Check again
    for _ in range(5):
        state = get_line_state()
        if state != "BOTH_OFF":
            print(f"  → Found line! State: {state}")
            return
        time.sleep(0.1)
    
    # If still not found, go back
    print("  → Line not found, stopping")
    stop()

# ==================== PROPORTIONAL LINE FOLLOWING ====================
def proportional_follow():
    """Advanced proportional line following (smoother)"""
    left_on_line, right_on_line = read_line_sensors()
    
    # Display
    left_char = "█" if left_on_line else "░"
    right_char = "█" if right_on_line else "░"
    print(f"Sensors: [{left_char}] [{right_char}]", end=" | ")
    
    # Calculate error (for proportional control)
    # 0 = centered, -1 = left off, +1 = right off
    error = 0
    if left_on_line and not right_on_line:
        error = -1  # Need to turn right
    elif not left_on_line and right_on_line:
        error = 1   # Need to turn left
    
    # Proportional control
    base_speed = SPEEDS['forward']
    turn_factor = 20  # How much to adjust speed
    
    left_speed = base_speed - (error * turn_factor)
    right_speed = base_speed + (error * turn_factor)
    
    # Limit speeds
    left_speed = max(SPEEDS['min'], min(SPEEDS['max'], left_speed))
    right_speed = max(SPEEDS['min'], min(SPEEDS['max'], right_speed))
    
    print(f"Error: {error:+.1f} | L:{left_speed:3.0f} R:{right_speed:3.0f}")
    
    # Move with adjusted speeds
    car.Car_Run(int(left_speed), int(right_speed))
    
    return error

# ==================== MAIN PROGRAM ====================
def main():
    """Main line following program"""
    print("\n" + "="*60)
    print("LINE FOLLOWING SYSTEM READY")
    print("="*60)
    
    # Auto-calibrate or use preset
    print("\nChoose calibration method:")
    print("1. Auto-calibrate (recommended)")
    print("2. Use preset values")
    print("3. Test sensors only")
    
    try:
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == "1":
            global LINE_LOGIC
            LINE_LOGIC = calibrate_sensors()
        elif choice == "2":
            print(f"\nUsing preset: LINE_LOGIC = {LINE_LOGIC}")
            print("(0 = Black line, 1 = White line)")
        elif choice == "3":
            test_sensors_only()
            return
    except:
        print("\nUsing default calibration")
    
    # Show configuration
    print("\n" + "="*60)
    print("CONFIGURATION:")
    print(f"Line Logic: {LINE_LOGIC} ({'Black' if LINE_LOGIC==0 else 'White'} line detection)")
    print(f"Left IR Pin: {LEFT_IR_PIN}")
    print(f"Right IR Pin: {RIGHT_IR_PIN}")
    print("="*60)
    
    # Test line detection
    print("\nTesting line detection...")
    print("Place car on line and press Enter")
    input()
    
    for i in range(5):
        left_on_line, right_on_line = read_line_sensors()
        print(f"Test {i+1}: Left={'ON LINE' if left_on_line else 'OFF'}, "
              f"Right={'ON LINE' if right_on_line else 'OFF'}")
        time.sleep(0.5)
    
    # Select following algorithm
    print("\n" + "="*60)
    print("SELECT FOLLOWING ALGORITHM:")
    print("1. Basic (Stop-and-turn)")
    print("2. Proportional (Smooth)")
    print("="*60)
    
    algorithm = input("Enter choice (1-2): ").strip()
    
    print("\n" + "="*60)
    print("STARTING LINE FOLLOWING")
    print("Place car on line to begin")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    # Wait for start
    time.sleep(2)
    
    # Counters
    loop_count = 0
    lost_count = 0
    
    try:
        while True:
            loop_count += 1
            
            if algorithm == "1":
                state = follow_line()
                if state == "BOTH_OFF":
                    lost_count += 1
            else:
                proportional_follow()
            
            # Display status every 50 loops
            if loop_count % 50 == 0:
                print(f"\n📊 Status: Loops={loop_count}, Lost={lost_count}")
                print("-" * 40)
            
            time.sleep(0.05)  # Control loop speed
            
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("LINE FOLLOWING STOPPED")
        print("="*60)
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        stop()
        time.sleep(0.5)
        GPIO.output(IR_ENABLE_PIN, GPIO.LOW)
        GPIO.cleanup()
        del car
        
        print(f"\n📊 FINAL STATISTICS:")
        print(f"  Total loops: {loop_count}")
        print(f"  Times lost line: {lost_count}")
        print(f"  Success rate: {(1 - lost_count/loop_count)*100:.1f}%")
        print("\n" + "="*60)
        print("PROGRAM COMPLETED")
        print("="*60)

def test_sensors_only():
    """Test sensors without moving"""
    print("\n" + "="*60)
    print("SENSOR TEST MODE")
    print("Move sensors over line/surface to test")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    try:
        while True:
            left_val = GPIO.input(LEFT_IR_PIN)
            right_val = GPIO.input(RIGHT_IR_PIN)
            
            left_on_line = (left_val == LINE_LOGIC)
            right_on_line = (right_val == LINE_LOGIC)
            
            left_char = "█" if left_on_line else "░"
            right_char = "█" if right_on_line else "░"
            
            print(f"Raw: L={left_val}, R={right_val} | "
                  f"Line: [{left_char}] [{right_char}] | "
                  f"State: {get_line_state()}")
            
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print("\nSensor test stopped")
    finally:
        GPIO.cleanup()

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    main()