# 🎮 SuperBall Game Backend

Backend API למשחק SuperBall - משחק פאזל מרובה משתתפים בזמן אמת.

## ✨ תכונות עיקריות

- 👥 **ניהול משתמשים** - רישום, התחברות, מעקב אחר טרופיים ומטבעות
- 🎮 **מערכת משחק מלאה** - משחקים בין 2 שחקנים, 5 סיבובים, חישוב ניקוד אוטומטי
- 🔄 **Matchmaking** - חיפוש יריבים אוטומטי
- 💰 **מערכת תגמולים** - טרופיים, מטבעות, כוכבים + היסטוריה מלאה
- 🎡 **גלגל מזל** - סיבוב יומי לפרסים
- 🌐 **WebSocket** - עדכונים בזמן אמת
- 🗄️ **MongoDB** - שמירת כל הנתונים (משתמשים, משחקים, תוצאות)
- 📊 **API מלא** - תיעוד אינטראקטיבי עם Swagger
- 🚀 **FastAPI** - ביצועים גבוהים ו-async

## 🚀 התקנה מהירה

### דרישות מוקדמות
- Python 3.9+
- MongoDB 4.4+

### צעדי התקנה

1. **צור סביבה וירטואלית:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

2. **התקן תלויות:**
```bash
pip install -r requirements.txt
```

3. **הרץ את השרת:**
```bash
python run.py
```

4. **בדוק שהכל עובד:**
- פתח דפדפן: http://localhost:8000/docs
- אמור לראות את תיעוד ה-API

### 📖 התקנה מפורטת
לתיעוד התקנה מפורט (כולל התקנת MongoDB), ראה: **[INSTALLATION.md](INSTALLATION.md)**

## 📚 API Endpoints

### Authentication (`/auth`)
- `POST /auth/register` - רישום משתמש חדש
- `GET /auth/user/{uniqId}` - קבלת נתוני משתמש

### Game (`/game`)
- `POST /game/create` - יצירת משחק חדש
- `POST /game/{game_id}/move` - ביצוע מהלך
- `GET /game/{game_id}/state` - קבלת מצב משחק
- `WebSocket /game/{game_id}/ws/{uniqId}` - עדכונים בזמן אמת

### Matchmaking (`/matchmaking`)
- `POST /matchmaking/join` - הצטרפות לתור חיפוש יריב
- `POST /matchmaking/cancel` - ביטול חיפוש

### Rewards (`/rewards`)
- `GET /rewards/player/{player_id}/history` - היסטוריית משחקים
- `GET /rewards/player/{player_id}/stats` - סטטיסטיקות (wins, losses, win rate)
- `GET /rewards/player/{player_id}/rewards` - תגמולים נוכחיים

### Wheel (`/wheel`)
- `POST /wheel/spin` - סיבוב גלגל מזל
- `POST /wheel/reset-timer` - איפוס טיימר (מנהל)

### 📖 תיעוד מלא
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 📁 מבנה הפרויקט

```
SuperBall-Backend/
├── app/
│   ├── main.py                      # אפליקציית FastAPI
│   ├── config.py                    # הגדרות
│   ├── database/                    # Repositories
│   │   ├── connection.py
│   │   ├── user_repository.py
│   │   ├── game_repository.py
│   │   └── game_result_repository.py
│   ├── models/                      # מודלים
│   │   ├── user.py
│   │   ├── game.py
│   │   └── game_result.py
│   ├── routes/                      # API endpoints
│   │   ├── auth.py
│   │   ├── game.py
│   │   ├── matchmaking.py
│   │   ├── rewards.py
│   │   └── wheel.py
│   ├── services/                    # לוגיקה עסקית
│   │   ├── game_service.py
│   │   ├── matchmaking.py
│   │   └── reward_service.py
│   └── core/
│       └── websocket.py             # WebSocket manager
├── requirements.txt
├── run.py
├── README.md                        # הקובץ הזה
├── README_HE.md                     # README בעברית
└── INSTALLATION.md                  # הוראות התקנה מפורטות
```

## 🎮 כללי המשחק

### מבנה המשחק:
- **5 סיבובים** בכל משחק
- **2 מהלכים** לכל שחקן בכל תור
- **לוח 7×8** עם 6 צבעים שונים
- **ניקוד**: 3 בלוקים = 30, 4 = 60, 5 = 100, 6+ = בונוס

### תגמולים:
- **ניצחון**: +50 טרופיים
- **הפסד**: -50 טרופיים
- **מטבעות**: 10% מהניקוד
- **כוכבים**: 1-3 לפי ביצועים

## 🗄️ Database

המערכת משתמשת ב-MongoDB עם 3 collections:
- **`users`** - משתמשים (trophies, coins)
- **`game_sessions`** - משחקים פעילים וגמורים
- **`game_results`** - היסטוריית משחקים ותוצאות

## 🛠️ טכנולוגיות

- **FastAPI** - Web framework
- **Motor** - MongoDB async driver
- **Pydantic** - Data validation
- **WebSockets** - Real-time communication
- **Uvicorn** - ASGI server

## 📖 תיעוד נוסף

- **[INSTALLATION.md](INSTALLATION.md)** - הוראות התקנה מפורטות (באנגלית)
- **[README_HE.md](README_HE.md)** - README מלא בעברית
- **API Docs** - http://localhost:8000/docs (אחרי הרצת השרת)

## 🎓 למרצה

המערכת מוכנה להרצה ומלאה בתכונות. לתיעוד התקנה מפורט, ראה **[INSTALLATION.md](INSTALLATION.md)**

---

**בהצלחה! 🚀**
