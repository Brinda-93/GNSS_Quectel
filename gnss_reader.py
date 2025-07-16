import serial
import time
import threading
import pynmea2  # pip install pynmea2

# ========= USER SETTINGS =========
SERIAL_PORT = '/dev/ttyUSB0'    # Change to your port (e.g., '/dev/ttyUSB0')
BAUD_RATE = 115200
UPDATE_INTERVAL_MS = 1000   # e.g., 200ms = 5Hz
USE_GPS = True
USE_GLONASS = True
USE_GALILEO = True
USE_BEIDOU = True
# =================================

def calculate_checksum(nmea_str):
    checksum = 0
    for char in nmea_str:
        checksum ^= ord(char)
    return f"{checksum:02X}"

def send_command(serial_port, base_command):
    nmea_body = base_command.strip().lstrip('$')
    checksum = calculate_checksum(nmea_body)
    full_command = f"${nmea_body}*{checksum}\r\n"
    serial_port.write(full_command.encode('ascii'))
    print(f">> {full_command.strip()}")

def configure_gnss_systems(ser):
    mode = 1  # enable/disable each individually
    gps = int(USE_GPS)
    glonass = int(USE_GLONASS)
    galileo = int(USE_GALILEO)
    beidou = int(USE_BEIDOU)
    # Format: $PQGNSS,<mode>,<gps>,<glonass>,<galileo>,<beidou>,<reserved>
    base_cmd = f"PQGNSS,{mode},{gps},{glonass},{galileo},{beidou},0"
    send_command(ser, base_cmd)


def configure_update_rate(ser, interval_ms):
    interval_ms = max(200, interval_ms)  # minimum allowed by many modules
    rate_hz = int(1000 / interval_ms)
    base_cmd = f"PQTMCFGPMODE,{interval_ms}"
    send_command(ser, base_cmd)

    # Also try standard MTK-style command if your module supports it
    gga_rate = 1
    gsv_rate = 0
    gsa_rate = 0
    rmc_rate = 1
    vtg_rate = 0
    zda_rate = 0

    # Example: Set all sentence rates to 1 (1 Hz)
    send_command(ser, "PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    send_command(ser, f"PMTK220,{interval_ms}")  # Output interval in ms

def configure_nmea_output(ser):
    send_command(ser, "PQTMCFGMSG,RMC,1")  # Enable RMC every fix
    send_command(ser, "PQTMCFGMSG,GGA,1")  # Enable GGA every fix

def save_configuration(ser):
    send_command(ser, "PQTMSAVEPAR")


def read_nmea_loop(ser):
    print(">>> Listening for NMEA data...\n")
    last_fix_time = None

    while True:
        try:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if not line.startswith("$"):
                continue

            try:
                msg = pynmea2.parse(line)

                if isinstance(msg, pynmea2.types.talker.GGA):
                    fix_status = int(msg.gps_qual)
                    if fix_status > 0:  # Only show if there's a fix
                        current_time = time.time()
                        interval = (current_time - last_fix_time) if last_fix_time else 0
                        last_fix_time = current_time
                        print(f"[GGA] Fix: {fix_status} | Interval: {interval:.2f}s | Time: {msg.timestamp} | Lat: {msg.latitude} {msg.lat_dir} | Lon: {msg.longitude} {msg.lon_dir} | Alt: {msg.altitude} {msg.altitude_units}")

                elif isinstance(msg, pynmea2.types.talker.RMC):
                    if msg.status == 'A':  # A = Valid fix
                        current_time = time.time()
                        interval = (current_time - last_fix_time) if last_fix_time else 0
                        last_fix_time = current_time
                        print(f"[RMC] Interval: {interval:.2f}s | Time: {msg.timestamp} | Lat: {msg.latitude} | Lon: {msg.longitude} | Speed: {msg.spd_over_grnd} knots | Heading: {msg.true_course}°")

            except pynmea2.ParseError:
                continue

        except KeyboardInterrupt:
            print("Stopped.")
            break

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for module to initialize

        print(">>> Configuring GNSS systems...")
        configure_gnss_systems(ser)

        print(">>> Setting output interval...")
        configure_update_rate(ser, UPDATE_INTERVAL_MS)

        print(">>> Enabling NMEA messages...")
        configure_nmea_output(ser)

        print(">>> Saving configuration...")
        save_configuration(ser)

        print(">>> Configuration done. Starting data read...\n")
        read_thread = threading.Thread(target=read_nmea_loop, args=(ser,))
        read_thread.start()

    except serial.SerialException as e:
        print(f"Serial error: {e}")

if __name__ == "__main__":
    main()
