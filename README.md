# SuperBall Game Backend

Backend API למשחק SuperBall בסגנון Candy Crush, כולל מערכת הרשמה והתחברות אוטומטית.

## תכונות

- 🔐 מערכת הרשמה והתחברות אוטומטית
- 🗄️ אחסון נתונים ב-MongoDB
- 🎮 ניהול נתוני משחק (רמה, ניקוד, מטבעות, חיים)
- 📊 API מלא עם תיעוד אוטומטי
- 🚀 FastAPI עם ביצועים גבוהים

## התקנה

### דרישות מוקדמות

1. Python 3.8+
2. MongoDB (מקומי או cloud)

### שלבי התקנה

1. **התקנת dependencies:**
```bash
pip install -r requirements.txt
```

2. **הגדרת משתני סביבה:**
   - העתק את `env_example.txt` ל-`.env`
   - ערוך את הקובץ `.env` עם הנתונים שלך:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=superball_game

# JWT Configuration
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

3. **הפעלת השרת:**
```bash
python run.py
```

או:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## שימוש

### נקודות API עיקריות

#### 1. התחברות/הרשמה אוטומטית
```http
POST /auth/login-or-register
Content-Type: application/json

{
    "unique_id": "player_12345",
    "username": "שם_משתמש_אופציונלי",
    "email": "email@example.com"
}
```

**תגובה עבור משתמש חדש:**
```json
{
    "message": "הרשמה בוצעה בהצלחה",
    "action": "register",
    "is_new_user": true,
    "user": {
        "id": "...",
        "unique_id": "player_12345",
        "username": "שם_משתמש_אופציונלי",
        "level": 1,
        "score": 0,
        "coins": 0,
        "lives": 5,
        "created_at": "2024-01-01T12:00:00",
        "is_active": true
    }
}
```

**תגובה עבור משתמש קיים:**
```json
{
    "message": "התחברות בוצעה בהצלחה",
    "action": "login",
    "is_new_user": false,
    "user": {
        // נתוני המשתמש הקיים
    }
}
```

#### 2. קבלת נתוני משתמש
```http
GET /auth/user/{unique_id}
```

#### 3. עדכון נתוני משתמש
```http
PUT /auth/user/{unique_id}
Content-Type: application/json

{
    "level": 5,
    "score": 1500,
    "coins": 100,
    "lives": 3
}
```

#### 4. קבלת סטטיסטיקות משתמש
```http
GET /auth/user/{unique_id}/stats
```

### תיעוד API

לאחר הפעלת השרת, ניתן לגשת לתיעוד האינטראקטיבי:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## מבנה הפרויקט

```
SuperBall-Backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # קובץ ראשי של האפליקציה
│   ├── config.py            # הגדרות ומשתני סביבה
│   ├── models/              # מודלים של הנתונים
│   │   ├── __init__.py
│   │   └── user.py
│   ├── database/            # חיבור ומניפולציה של מסד הנתונים
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── user_repository.py
│   └── routes/              # נתיבי API
│       ├── __init__.py
│       └── auth.py
├── requirements.txt         # dependencies
├── env_example.txt         # דוגמה למשתני סביבה
├── run.py                  # קובץ הפעלה
└── README.md
```

## לוגיקת ההרשמה/התחברות

1. **המשחק שולח unique_id** של השחקן לשרת
2. **השרת בודק** האם המשתמש קיים במסד הנתונים
3. **אם קיים:** מתחבר ומעדכן last_login
4. **אם לא קיים:** יוצר משתמש חדש אוטומטית
5. **מחזיר** את נתוני המשתמש למשחק

## פיתוח נוסף

הבקאנד מוכן להרחבה עם:
- 🎯 מערכת משימות ואתגרים
- 🏆 לוח תוצאות
- 💰 חנות פריטים
- 👥 מערכת חברים
- 📈 אנליטיקס ומעקב

## תמיכה

לשאלות או בעיות, פנה למפתח הפרויקט.
