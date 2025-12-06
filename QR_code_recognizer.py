#!/usr/bin/env python3
"""
QR Code Reader for Putty/SSH (No GUI)
For Raspbot using Putty connection
"""

import cv2
import time
import sys

print("\n" + "="*60)
print("RASPBOT QR CODE READER - PUTTY VERSION")
print("="*60)
print("This version works via SSH/Putty (no display needed)")
print("="*60)

# Check for required packages
try:
    from pyzbar import pyzbar
    print("✓ pyzbar is installed")
except ImportError:
    print("✗ pyzbar not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyzbar"])
    from pyzbar import pyzbar

try:
    import cv2
    print("✓ OpenCV is installed")
except ImportError:
    print("✗ OpenCV not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python"])
    import cv2

def setup_camera():
    """Setup camera for Raspbot"""
    print("\nSetting up camera...")
    
    # Try different camera indices
    for i in range(2):
        camera = cv2.VideoCapture(i)
        if camera.isOpened():
            print(f"✓ Camera found at /dev/video{i}")
            
            # Set camera properties for QR scanning
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            camera.set(cv2.CAP_PROP_FPS, 15)
            
            # Optimize for QR codes
            try:
                camera.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)
                camera.set(cv2.CAP_PROP_CONTRAST, 0.5)
                camera.set(cv2.CAP_PROP_EXPOSURE, -1)  # Auto exposure
            except:
                pass  # Ignore if not supported
            
            # Test camera
            ret, frame = camera.read()
            if ret:
                print(f"✓ Camera test passed: {frame.shape[1]}x{frame.shape[0]}")
                return camera
            else:
                camera.release()
    
    print("✗ Could not initialize camera")
    return None

def scan_qr_code():
    """Main QR scanning function"""
    camera = setup_camera()
    if not camera:
        print("\nTroubleshooting steps:")
        print("1. Check camera is connected to Raspbot")
        print("2. Run: ls /dev/video*")
        print("3. Enable camera: sudo raspi-config")
        print("   → Interface Options → Camera → Enable")
        print("4. Reboot and try again")
        return
    
    print("\n" + "="*60)
    print("QR CODE SCANNING ACTIVE")
    print("="*60)
    print("INSTRUCTIONS:")
    print("1. Hold QR code in front of Raspbot camera")
    print("2. Keep QR code steady for 1-2 seconds")
    print("3. Data will appear below when detected")
    print("4. Press Ctrl+C to stop scanning")
    print("="*60 + "\n")
    
    scan_count = 0
    qr_history = []
    
    try:
        while True:
            # Read frame
            ret, frame = camera.read()
            if not ret:
                print("Error reading frame")
                time.sleep(0.1)
                continue
            
            scan_count += 1
            
            # Convert to grayscale (better for QR detection)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Find QR codes
            qrcodes = pyzbar.decode(gray)
            
            # Process detected QR codes
            if qrcodes:
                print("\n" + "═" * 50)
                print(f"📱 QR CODE DETECTED - Scan #{len(qr_history)+1}")
                print("═" * 50)
                
                for qr in qrcodes:
                    # Get QR code data
                    qr_data = qr.data.decode("utf-8")
                    qr_type = qr.type
                    
                    # Get position
                    x, y, w, h = qr.rect
                    
                    # Display information
                    print(f"  Type: {qr_type}")
                    print(f"  Data: {qr_data}")
                    print(f"  Position: X={x}, Y={y}, Width={w}, Height={h}")
                    print(f"  Time: {time.strftime('%H:%M:%S')}")
                    
                    # Save to history
                    qr_entry = {
                        'data': qr_data,
                        'type': qr_type,
                        'time': time.time(),
                        'position': (x, y, w, h)
                    }
                    qr_history.append(qr_entry)
                    
                    # Save to file
                    save_qr_result(qr_entry)
                
                print("═" * 50)
                
                # Pause briefly to avoid multiple detections
                time.sleep(1)
            
            # Show progress every 50 scans
            if scan_count % 50 == 0:
                print(f"\n⏳ Still scanning... Total scans: {scan_count}")
                if qr_history:
                    print(f"   QR codes found: {len(qr_history)}")
            
            # Small delay to reduce CPU usage
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("SCANNING STOPPED")
        print("="*60)
        
    finally:
        # Cleanup
        camera.release()
        print("✓ Camera released")
        
        # Show summary
        print_summary(qr_history, scan_count)

def save_qr_result(qr_entry):
    """Save QR code detection to file"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"qr_result_{timestamp}.txt"
    
    with open(filename, 'w') as f:
        f.write("="*50 + "\n")
        f.write("RASPBOT QR CODE DETECTION\n")
        f.write("="*50 + "\n\n")
        f.write(f"Detection Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"QR Code Type: {qr_entry['type']}\n")
        f.write(f"QR Code Data: {qr_entry['data']}\n")
        f.write(f"Position: X={qr_entry['position'][0]}, Y={qr_entry['position'][1]}\n")
        f.write(f"Size: {qr_entry['position'][2]}x{qr_entry['position'][3]}\n")
        f.write("\n" + "="*50 + "\n")
    
    print(f"✓ Results saved to: {filename}")

def print_summary(qr_history, scan_count):
    """Print scanning summary"""
    print(f"\n📊 SCANNING SUMMARY:")
    print(f"   Total frames scanned: {scan_count}")
    print(f"   QR codes detected: {len(qr_history)}")
    
    if qr_history:
        print(f"\n📝 DETECTED QR CODES:")
        for i, qr in enumerate(qr_history, 1):
            print(f"   {i}. [{qr['type']}] {qr['data']}")
        
        # Save complete history
        save_complete_history(qr_history)
    else:
        print(f"\nℹ️  No QR codes were detected")
        print("   Make sure:")
        print("   - QR code is well lit")
        print("   - QR code fills about 1/4 of camera view")
        print("   - Hold QR code steady for 1-2 seconds")
    
    print("\n" + "="*60)
    print("PROGRAM COMPLETED")
    print("="*60)

def save_complete_history(qr_history):
    """Save complete scanning history"""
    if not qr_history:
        return
    
    filename = "qr_scanning_history.txt"
    
    with open(filename, 'w') as f:
        f.write("="*60 + "\n")
        f.write("RASPBOT QR CODE SCANNING HISTORY\n")
        f.write("="*60 + "\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total detections: {len(qr_history)}\n")
        f.write("\n" + "="*60 + "\n\n")
        
        for i, qr in enumerate(qr_history, 1):
            f.write(f"Detection #{i}\n")
            f.write(f"  Time: {time.strftime('%H:%M:%S', time.localtime(qr['time']))}\n")
            f.write(f"  Type: {qr['type']}\n")
            f.write(f"  Data: {qr['data']}\n")
            f.write(f"  Position: X={qr['position'][0]}, Y={qr['position'][1]}\n")
            f.write("-" * 40 + "\n")
    
    print(f"✓ Complete history saved to: {filename}")

def check_system():
    """Check system requirements"""
    print("\n🔍 Checking system requirements...")
    
    # Check camera
    import subprocess
    result = subprocess.run(['vcgencmd', 'get_camera'], 
                          capture_output=True, text=True)
    if 'detected=1' in result.stdout:
        print("✓ Camera is detected")
    else:
        print("⚠ Camera not detected. Check connection.")
    
    # Check video devices
    result = subprocess.run(['ls', '/dev/video*'], 
                          capture_output=True, text=True)
    if result.stdout:
        print(f"✓ Video devices: {result.stdout.strip()}")
    else:
        print("⚠ No video devices found")
    
    return True

# Main execution
if __name__ == "__main__":
    # Check system first
    check_system()
    
    # Start QR scanning
    scan_qr_code()