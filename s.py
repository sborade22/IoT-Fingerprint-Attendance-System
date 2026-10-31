import RPi.GPIO as GPIO
from RPLCD.gpio import CharLCD
from pyfingerprint.pyfingerprint import PyFingerprint
from telegram import Bot
import datetime
import time

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Hardware initialization
lcd = CharLCD(
    pin_rs=25,
    pin_rw=None,
    pin_e=24,
    pins_data=[23, 17, 18, 22],
    numbering_mode=GPIO.BCM,
    cols=16,
    rows=2
)

# Telegram configuration
# Add your own private bot token and chat ID locally.
# Never upload real credentials to a public GitHub repository.
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"
bot = Bot(token=TELEGRAM_TOKEN)

# Fingerprint sensor initialization
try:
    sensor = PyFingerprint(
        '/dev/ttyUSB0',
        57600,
        0xFFFFFFFF,
        0x00000000
    )

    if not sensor.verifyPassword():
        raise ValueError("Sensor authentication failed!")

    print(">>> Sensor Connected Successfully >>>")

except Exception as e:
    lcd.clear()
    lcd.write_string("Sensor Error!")
    print(f"Error: {e}")
    raise SystemExit(1)

# Student database: fingerprint template ID -> (roll number, name)
# Replace these sample entries with authorized test data.
STUDENT_DATABASE = {
    20: ("12", "Student 1"),
    21: ("02", "Student 2"),
    2: ("11", "Student 3"),
    3: ("06", "Student 4"),
    4: ("47", "Student 5")
}

present_students = set()

# Main attendance loop
lcd.clear()
lcd.write_string("System Ready")
lcd.cursor_pos = (1, 0)
lcd.write_string("Scan Finger...")
print(">> System Ready. Place finger on sensor...")
time.sleep(2)

try:
    while True:
        lcd.clear()
        lcd.write_string("Place Finger...")

        # Wait until a fingerprint is detected
        while not sensor.readImage():
            time.sleep(0.1)

        # Convert and search the fingerprint
        sensor.convertImage(0x01)
        result = sensor.searchTemplate()
        position_number = result[0]

        if position_number >= 0 and position_number in STUDENT_DATABASE:
            roll_no, name = STUDENT_DATABASE[position_number]

            if position_number in present_students:
                lcd.clear()
                lcd.write_string(name[:16])
                lcd.cursor_pos = (1, 0)
                lcd.write_string("Already Marked!")
                print(f"[ALREADY MARKED] Roll: {roll_no} - {name}")
            else:
                present_students.add(position_number)
                lcd.clear()
                lcd.write_string(name[:16])
                lcd.cursor_pos = (1, 0)
                lcd.write_string("Status: Present")
                print(f"[PRESENT] Roll: {roll_no} - {name}")
        else:
            lcd.clear()
            lcd.write_string("Fingerprint")
            lcd.cursor_pos = (1, 0)
            lcd.write_string("Not Found / Unreg")
            print("[UNKNOWN] Fingerprint not registered!")

        time.sleep(3)

except KeyboardInterrupt:
    print("\\nSession Terminated. Generating Report...")

finally:
    lcd.clear()
    lcd.write_string("Generating Report")

    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Absentees = all registered students - present students
    all_ids = set(STUDENT_DATABASE.keys())
    absent_ids = all_ids - present_students

    # Generate attendance report
    report = [
        "=== ATTENDANCE REPORT ===",
        f"Date/Time: {current_date}",
        f"Total Students : {len(STUDENT_DATABASE)}",
        f"Present : {len(present_students)}",
        f"Absent : {len(absent_ids)}",
        "",
        "--- PRESENT STUDENTS ---"
    ]

    for fingerprint_id in sorted(present_students):
        roll, name = STUDENT_DATABASE[fingerprint_id]
        report.append(f"- [{roll}] {name}")

    report.append("")
    report.append("--- ABSENTEE LIST ---")

    for fingerprint_id in sorted(absent_ids):
        roll, name = STUDENT_DATABASE[fingerprint_id]
        report.append(f"- [{roll}] {name}")

    report_text = "\\n".join(report)

    # Save report to a local text file
    with open("attendance.txt", "w", encoding="utf-8") as file:
        file.write(report_text)

    # Send report through Telegram
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=report_text
        )

        lcd.clear()
        lcd.write_string("Report Sent!")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("Saved to File")
        print("\\n>> Report Sent via Telegram & Saved to attendance.txt!")

    except Exception as e:
        lcd.clear()
        lcd.write_string("Telegram Error!")
        print(f"\\n>> Telegram Error: {e}")

    time.sleep(2)
    lcd.clear()
    GPIO.cleanup()
