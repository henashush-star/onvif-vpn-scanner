# סורק מצלמות רשת ONVIF

פרויקט זה הוא כלי שורת פקודה (CLI) מבוסס Python שנועד לגלות אוטומטית מצלמות תואמות ONVIF ברשתות מקומיות (LAN) וחיבורי VPN, לבדוק את היכולות שלהן, ולספק תוצאות מובנות בטבלה בקונסולה ובפורמט JSON.

## תכונות

- **WS-Discovery**: משתמש ב-multicast (UDP) כדי לגלות התקני ONVIF ברשת המקומית.
- **סריקת טווחי IP**: סורק טווחי CIDR מוגדרים על ידי המשתמש (לדוגמה, `10.8.0.0/24`) כדי למצוא מצלמות, מתאים לסביבות VPN בהן multicast נחסם לעיתים קרובות.
- **בדיקת מצלמה**: מתחבר למצלמות שהתגלו כדי לאחזר:
    - יצרן, דגם, קושחה, מספר סידורי.
    - פרופילי מדיה (RTSP Stream URIs).
    - תמיכה וסטטוס PTZ (מיקומי Pan, Tilt, Zoom ומגבלות).
- **פלט מובנה**: מדפיס טבלה מעוצבת לקונסולה ומייצא נתונים מפורטים לקובץ `cameras.json`.

## התקנה

1.  שכפל את המאגר (Clone).
2.  התקן את התלויות:
    ```bash
    pip install -r requirements.txt
    ```

## שימוש

הפעל את הסורק באמצעות נקודת הכניסה של ה-CLI:

```bash
python3 -m onvif_scanner.cli --user admin --password password123
```

### אפשרויות

- `--mode {ws-discovery,ip-range}`: מצב גילוי (ברירת מחדל: `ws-discovery`).
- `--subnet SUBNET`: רשת CIDR לסריקת טווחי IP (נדרש עבור מצב `ip-range`).
- `--user USER`: שם משתמש למצלמה (חובה).
- `--password PASSWORD`: סיסמה למצלמה (חובה).
- `--output OUTPUT`: נתיב לקובץ JSON לפלט (ברירת מחדל: `cameras.json`).
- `--verbose`: אפשר רישום מפורט (logging).

### דוגמאות

**סריקת רשת מקומית (WS-Discovery):**
```bash
python3 -m onvif_scanner.cli --user admin --password secret
```

**סריקת תת-רשת VPN (טווח IP):**
```bash
python3 -m onvif_scanner.cli --mode ip-range --subnet 10.8.0.0/24 --user admin --password secret
```

## תיאור קבצים

הפרויקט מאורגן כחבילת Python בשם `onvif_scanner`.

- **`onvif_scanner/__init__.py`**:
  מאתחל את חבילת `onvif_scanner`.

- **`onvif_scanner/cli.py`**:
  נקודת הכניסה הראשית לממשק שורת הפקודה. משתמש ב-`argparse` לטיפול בארגומנטים מהמשתמש, מנהל את תהליך הסריקה באמצעות `WSDiscoveryScanner` או `IPRangeScanner`, יוזם בדיקה עם `CameraInspector`, וקורא לפונקציות הפלט.

- **`onvif_scanner/scanner.py`**:
  מכיל את לוגיקת הגילוי.
  - `WSDiscoveryScanner`: מיישם בדיקת multicast UDP מותאמת אישית למציאת התקני ONVIF התואמים ל-WS-Discovery.
  - `IPRangeScanner`: מיישם סורק מרובה תהליכונים (multi-threaded) שבודק כתובות IP בבלוק CIDR עבור נקודות קצה של שירות ONVIF בפורטים 80 ו-8080.

- **`onvif_scanner/inspector.py`**:
  מטפל באינטראקציה עם מצלמות בודדות באמצעות ספריית `onvif-zeep`.
  - `CameraInspector`: מתחבר למצלמה ומאחזר מידע על ההתקן (דגם, קושחה), פרופילי מדיה (RTSP URIs), וסטטוס PTZ.

- **`onvif_scanner/models.py`**:
  מגדיר את מבני הנתונים המשמשים בכל היישום.
  - `CameraInfo`: המיכל הראשי לנתוני המצלמה.
  - `StreamProfile`: מייצג פרופיל מדיה ואת ה-RTSP URI שלו.
  - `PTZInfo`: מיכל ליכולות, סטטוס ומגבלות PTZ.

- **`onvif_scanner/output.py`**:
  מטפל בהצגת התוצאות.
  - `print_summary_table`: משתמש בספריית `rich` להצגת טבלה מעוצבת של המצלמות שהתגלו.
  - `export_to_json`: מסדר (Serialize) את אובייקטי `CameraInfo` לקובץ JSON.

- **`onvif_scanner/utils.py`**:
  מכיל פונקציות עזר, ספציפית `get_network_interfaces`, שמנסה לרשום כתובות IP מקומיות כדי לקשור את שקע גילוי ה-multicast לממשקים ספציפיים.

- **`tests/test_scanner.py`**:
  בדיקות יחידה עבור מודולי הגילוי (`WSDiscoveryScanner`, `IPRangeScanner`), המדמות שקעי רשת ובקשות.

- **`tests/test_inspector.py`**:
  בדיקות יחידה עבור `CameraInspector`, המדמות את אובייקטי המצלמה והשירות של `onvif-zeep`.
