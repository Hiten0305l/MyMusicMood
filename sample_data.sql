-- Sample data for testing My Music Mood

USE my_music_mood;

-- Insert sample languages
INSERT INTO languages (language_name) VALUES
('English'),
('Spanish'),
('Hindi'),
('French'),
('Korean');

-- Insert sample moods
INSERT INTO moods (mood_name) VALUES
('Happy'),
('Sad'),
('Energetic'),
('Relaxed'),
('Romantic'),
('Motivational');

-- Insert sample artists
INSERT INTO artists (name, artist_coverphoto) VALUES
('The Weeknd', 'https://via.placeholder.com/300x300?text=The+Weeknd'),
('Taylor Swift', 'https://via.placeholder.com/300x300?text=Taylor+Swift'),
('Ed Sheeran', 'https://via.placeholder.com/300x300?text=Ed+Sheeran'),
('Arijit Singh', 'https://via.placeholder.com/300x300?text=Arijit+Singh'),
('Bad Bunny', 'https://via.placeholder.com/300x300?text=Bad+Bunny'),
('BTS', 'https://via.placeholder.com/300x300?text=BTS'),
('Billie Eilish', 'https://via.placeholder.com/300x300?text=Billie+Eilish'),
('Drake', 'https://via.placeholder.com/300x300?text=Drake');

-- Insert sample songs
INSERT INTO songs (title, artist_id, language_id, mood_id, song_coverphoto, rating) VALUES
('Blinding Lights', 1, 1, 3, 'https://via.placeholder.com/300x300?text=Blinding+Lights', 4.8),
('Save Your Tears', 1, 1, 2, 'https://via.placeholder.com/300x300?text=Save+Your+Tears', 4.6),
('Anti-Hero', 2, 1, 2, 'https://via.placeholder.com/300x300?text=Anti-Hero', 4.7),
('Shake It Off', 2, 1, 1, 'https://via.placeholder.com/300x300?text=Shake+It+Off', 4.5),
('Shape of You', 3, 1, 1, 'https://via.placeholder.com/300x300?text=Shape+of+You', 4.9),
('Perfect', 3, 1, 5, 'https://via.placeholder.com/300x300?text=Perfect', 4.8),
('Tum Hi Ho', 4, 3, 5, 'https://via.placeholder.com/300x300?text=Tum+Hi+Ho', 4.7),
('Channa Mereya', 4, 3, 2, 'https://via.placeholder.com/300x300?text=Channa+Mereya', 4.6),
('Me Porto Bonito', 5, 2, 1, 'https://via.placeholder.com/300x300?text=Me+Porto+Bonito', 4.5),
('Dynamite', 6, 5, 1, 'https://via.placeholder.com/300x300?text=Dynamite', 4.8),
('Butter', 6, 5, 1, 'https://via.placeholder.com/300x300?text=Butter', 4.7),
('Bad Guy', 7, 1, 3, 'https://via.placeholder.com/300x300?text=Bad+Guy', 4.6),
('Gods Plan', 8, 1, 6, 'https://via.placeholder.com/300x300?text=Gods+Plan', 4.9),
('One Dance', 8, 1, 1, 'https://via.placeholder.com/300x300?text=One+Dance', 4.7);

