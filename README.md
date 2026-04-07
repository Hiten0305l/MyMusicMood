# 🎵 My Music Mood

A responsive, database-driven web application for music discovery and personalized recommendations — built with **Flask**, **MySQL**, and **Bootstrap 5**.

---

## ✨ Features

- 🎯 Personalized song recommendations based on your listening activity
- 🔍 Real-time song search with autocomplete
- 📊 Top songs by language, artist, and mood
- 📈 User activity tracking and history
- 🎨 Modern, responsive UI with Bootstrap 5
- 🌐 TheAudioDB API integration for rich song metadata

---

## 🛠️ Tech Stack

| Layer     | Technology                    |
|-----------|-------------------------------|
| Backend   | Python, Flask                 |
| Database  | MySQL                         |
| Frontend  | HTML, CSS, Bootstrap 5, JS    |
| API       | TheAudioDB (external)         |
| Connector | mysql-connector-python        |

---

## 📁 Project Structure

```
MyMusicMood/
│
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── Procfile                # For deployment (Render/Railway/Heroku)
├── runtime.txt             # Python version pin
├── database_schema.sql     # Database schema
├── sample_data.sql         # Sample data for testing
├── .env.example            # Environment variables template
├── .gitignore
├── README.md
│
├── static/
│   ├── css/
│   │   └── style.css       # Custom styles
│   ├── js/
│   │   └── search.js       # Search functionality
│   └── images/             # Image assets
│
└── templates/
    ├── base.html
    ├── home.html
    ├── profile.html
    ├── songs.html
    ├── song_info.html
    ├── languages.html
    ├── artists.html
    ├── moods.html
    └── history.html
```

---

## 🚀 Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/MyMusicMood.git
cd MyMusicMood
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up MySQL database

- Open MySQL Workbench (or any MySQL client)
- Run `database_schema.sql` to create the database and tables
- *(Optional)* Run `sample_data.sql` to populate with sample data

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=my_music_mood
SECRET_KEY=some-random-secret-string
```

### 5. Run the app

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 🌍 Deployment (Render)

This app is ready to deploy on [Render](https://render.com) (free tier available).

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New Web Service** → connect your repo
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `gunicorn app:app`
5. Add environment variables in Render's dashboard (same as your `.env`):
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `SECRET_KEY`
6. For the database, use [PlanetScale](https://planetscale.com) or [Railway MySQL](https://railway.app) (free hosted MySQL)

---

## 📌 Routes

| Route           | Description                        |
|-----------------|------------------------------------|
| `/`             | Register / Login                   |
| `/songs`        | Discover songs (personalized + top)|
| `/song/<id>`    | Song detail page                   |
| `/languages`    | Browse by language                 |
| `/artists`      | Browse by artist                   |
| `/moods`        | Browse by mood                     |
| `/history`      | Your search history                |
| `/profile`      | View/edit profile                  |
| `/search?q=`    | AJAX search endpoint               |
| `/logout`       | Logout                             |

---

## 🗄️ Database Schema

- `users` — User accounts
- `artists` — Music artists
- `languages` — Song languages
- `moods` — Song moods
- `songs` — Song catalog
- `user_activity` — User search history and activity tracking

---

## 📝 Notes

- `.env` is **gitignored** — never commit your real credentials
- Search count increments only when viewing a song's detail page
- Personalization runs fresh on every page load based on current history

---

## 📄 License

Open source — free for educational use.
