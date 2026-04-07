-- My Music Mood Database Schema

CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS artists (
    artist_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    artist_coverphoto VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS languages (
    language_id INT PRIMARY KEY AUTO_INCREMENT,
    language_name VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS moods (
    mood_id INT PRIMARY KEY AUTO_INCREMENT,
    mood_name VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS songs (
    song_id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    artist_id INT,
    language_id INT,
    mood_id INT,
    song_coverphoto VARCHAR(500),
    rating DECIMAL(3,2) DEFAULT 0.0,
    FOREIGN KEY (artist_id) REFERENCES artists(artist_id),
    FOREIGN KEY (language_id) REFERENCES languages(language_id),
    FOREIGN KEY (mood_id) REFERENCES moods(mood_id)
);

CREATE TABLE IF NOT EXISTS user_activity (
    user_id INT,
    song_id INT,
    search_count INT DEFAULT 0,
    last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, song_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

