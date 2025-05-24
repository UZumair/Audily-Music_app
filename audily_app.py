import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from dotenv import load_dotenv
import time
from typing import Union, List, Dict, Any

# Load environment variables
load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
        
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="umair1122",
                database="MUSIC_APP",
                auth_plugin='mysql_native_password'
            )
            if self.connection.is_connected():
                print("✅ Successfully connected to MySQL database")
        except Error as e:
            st.error(f"❌ Error connecting to MySQL: {e}")
            if "Unknown database" in str(e):
                self.create_database()
            else:
                st.stop()

    def create_database(self):
        try:
            # Connect without specifying database
            temp_conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="umair1122",
                auth_plugin='mysql_native_password'
            )
            cursor = temp_conn.cursor()
            
            # Create database
            cursor.execute("CREATE DATABASE IF NOT EXISTS MUSIC_APP")
            cursor.execute("USE MUSIC_APP")
            
            # Create tables with all required columns
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS USERS (
                    User_ID INT AUTO_INCREMENT PRIMARY KEY,
                    Username VARCHAR(50) NOT NULL UNIQUE,
                    Email VARCHAR(100) NOT NULL,
                    Password VARCHAR(100) NOT NULL,
                    Profile_Picture VARCHAR(255),
                    Subscription_Type VARCHAR(20) DEFAULT 'Free',
                    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ARTISTS (
                    Artist_ID INT AUTO_INCREMENT PRIMARY KEY,
                    Name VARCHAR(100) NOT NULL,
                    Bio TEXT,
                    Profile_Picture VARCHAR(255)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SONGS (
                    Song_ID INT AUTO_INCREMENT PRIMARY KEY,
                    Title VARCHAR(100) NOT NULL,
                    Duration INT NOT NULL,
                    Genre VARCHAR(50),
                    File_Path VARCHAR(255) NOT NULL,
                    Cover_Image VARCHAR(255),
                    User_ID INT NOT NULL,
                    Upload_Date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    Play_Count INT DEFAULT 0,
                    FOREIGN KEY (User_ID) REFERENCES USERS(User_ID)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SONG_ARTISTS (
                    Song_ID INT,
                    Artist_ID INT,
                    PRIMARY KEY (Song_ID, Artist_ID),
                    FOREIGN KEY (Song_ID) REFERENCES SONGS(Song_ID),
                    FOREIGN KEY (Artist_ID) REFERENCES ARTISTS(Artist_ID)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS PLAYLISTS (
                    Playlist_ID INT AUTO_INCREMENT PRIMARY KEY,
                    Name VARCHAR(100) NOT NULL,
                    User_ID INT NOT NULL,
                    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (User_ID) REFERENCES USERS(User_ID)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS PLAYLIST_SONGS (
                    Playlist_ID INT,
                    Song_ID INT,
                    PRIMARY KEY (Playlist_ID, Song_ID),
                    FOREIGN KEY (Playlist_ID) REFERENCES PLAYLISTS(Playlist_ID),
                    FOREIGN KEY (Song_ID) REFERENCES SONGS(Song_ID)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS TRENDING (
                    Trend_ID INT AUTO_INCREMENT PRIMARY KEY,
                    Song_ID INT NOT NULL,
                    Trend_Date DATE NOT NULL,
                    Play_Count INT DEFAULT 0,
                    FOREIGN KEY (Song_ID) REFERENCES SONGS(Song_ID),
                    UNIQUE KEY (Song_ID, Trend_Date)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS COMMENTS (
                    Comment_ID INT AUTO_INCREMENT PRIMARY KEY,
                    Comment_Text TEXT NOT NULL,
                    User_ID INT NOT NULL,
                    Song_ID INT NOT NULL,
                    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (User_ID) REFERENCES USERS(User_ID),
                    FOREIGN KEY (Song_ID) REFERENCES SONGS(Song_ID)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS RATINGS (
                    Rating_ID INT AUTO_INCREMENT PRIMARY KEY,
                    Rating_Value FLOAT NOT NULL,
                    User_ID INT NOT NULL,
                    Song_ID INT NOT NULL,
                    FOREIGN KEY (User_ID) REFERENCES USERS(User_ID),
                    FOREIGN KEY (Song_ID) REFERENCES SONGS(Song_ID),
                    UNIQUE KEY (User_ID, Song_ID)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS USER_ACTIVITY (
                    Activity_ID INT AUTO_INCREMENT PRIMARY KEY,
                    User_ID INT NOT NULL,
                    Activity_Type VARCHAR(50) NOT NULL,
                    Activity_Details TEXT,
                    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (User_ID) REFERENCES USERS(User_ID)
                )
            """)
            
            temp_conn.commit()
            cursor.close()
            temp_conn.close()
            st.success("Database and all tables created successfully! Please restart the app.")
            st.stop()
        except Exception as e:
            st.error(f"Failed to create database: {e}")
            st.stop()

    def execute_query(self, query: str, params=None, fetch: bool = True) -> Union[List[Dict], bool]:
        """Execute a database query with proper error handling"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
            
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            
            if fetch and query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE')):
                result = cursor.fetchall()
                return result if result else []
            
            self.connection.commit()
            return True
        except Error as e:
            st.error(f"Database error: {e}")
            return False
        finally:
            cursor.close()

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

class AudilyApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.setup_page_styles()
        self.setup_authentication()
        
    def setup_page_styles(self):
        st.markdown("""
        <style>
            .main {
                background-color: #0E1117;
                color: #FAFAFA;
            }
            .sidebar .sidebar-content {
                background-color: #1A1C20;
            }
            .stButton>button {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 0.5rem 1rem;
            }
            .stTextInput>div>div>input {
                color: #4CAF50;
            }
            .css-1aumxhk {
                background-color: #1A1C20;
            }
        </style>
        """, unsafe_allow_html=True)

    def setup_authentication(self):
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
            st.session_state.current_user = None

        if not st.session_state.authenticated:
            self.show_login()
        else:
            self.show_main_app()

    def show_login(self):
        st.title("🎵 Audily - Music Streaming Platform")
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Login"):
                    user = self.db.execute_query(
                        "SELECT * FROM USERS WHERE Username = %s AND Password = %s",
                        (username, password)
                    )
                    
                    if isinstance(user, list) and len(user) > 0:
                        st.session_state.authenticated = True
                        st.session_state.current_user = user[0]
                        st.success("Login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
        
        with tab2:
            with st.form("register_form"):
                st.subheader("Create New Account")
                new_username = st.text_input("Choose Username")
                new_email = st.text_input("Email Address")
                new_password = st.text_input("Create Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                profile_pic = st.file_uploader("Profile Picture (optional)", type=["jpg", "png"])
                
                if st.form_submit_button("Register"):
                    if new_password != confirm_password:
                        st.error("Passwords don't match!")
                    else:
                        # Save profile picture if uploaded
                        profile_path = None
                        if profile_pic:
                            os.makedirs("user_uploads/profile_pics", exist_ok=True)
                            profile_path = f"user_uploads/profile_pics/{new_username}_{profile_pic.name}"
                            with open(profile_path, "wb") as f:
                                f.write(profile_pic.getbuffer())
                        
                        try:
                            success = self.db.execute_query(
                                "INSERT INTO USERS (Username, Email, Password, Profile_Picture) "
                                "VALUES (%s, %s, %s, %s)",
                                (new_username, new_email, new_password, profile_path),
                                fetch=False
                            )
                            if success:
                                st.success("Account created successfully! Please login.")
                        except Error as e:
                            st.error(f"Registration failed: {e}")

    def show_main_app(self):
        st.sidebar.title(f"Welcome, {st.session_state.current_user['Username']}")
        
        # Handle profile picture safely
        profile_pic = st.session_state.current_user.get("Profile_Picture", "https://via.placeholder.com/150")
        if not isinstance(profile_pic, str) or not profile_pic.startswith(('http', '/')):
            profile_pic = "https://via.placeholder.com/150"
        st.sidebar.image(profile_pic, width=150)

        menu = ["Dashboard", "Browse Music", "My Playlists", "Upload Music", "Trending", "Admin"]
        choice = st.sidebar.selectbox("Menu", menu)
        
        if choice == "Dashboard":
            self.show_dashboard()
        elif choice == "Browse Music":
            self.browse_music()
        elif choice == "My Playlists":
            self.show_playlists()
        elif choice == "Upload Music":
            self.upload_music()
        elif choice == "Trending":
            self.show_trending()
        elif choice == "Admin":
            self.admin_panel()
        
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()

    def show_dashboard(self):
        st.title("🎧 Your Music Dashboard")
        st.markdown("---")
        
        # User stats with safe data access
        col1, col2, col3 = st.columns(3)
        with col1:
            playlist_count = self.db.execute_query(
                "SELECT COUNT(*) as count FROM PLAYLISTS WHERE User_ID = %s",
                (st.session_state.current_user['User_ID'],)
            )
            st.metric("Your Playlists", playlist_count[0]['count'] if isinstance(playlist_count, list) and playlist_count else 0)

        with col2:
            songs_uploaded = self.db.execute_query(
                "SELECT COUNT(*) as count FROM SONGS WHERE User_ID = %s",
                (st.session_state.current_user['User_ID'],)
            )
            st.metric("Songs Uploaded", songs_uploaded[0]['count'] if isinstance(songs_uploaded, list) and songs_uploaded else 0)

        with col3:
            total_plays = self.db.execute_query(
                "SELECT SUM(Play_Count) as total FROM SONGS WHERE User_ID = %s",
                (st.session_state.current_user['User_ID'],)
            )
            display_plays = total_plays[0]['total'] if isinstance(total_plays, list) and total_plays and total_plays[0]['total'] is not None else 0
            st.metric("Total Plays", display_plays)
        
        # Recently played with safe data access
        st.subheader("Recently Played")
        recent_songs = self.db.execute_query(
            "SELECT s.Song_ID, s.Title, a.Name as Artist, s.Play_Count "
            "FROM SONGS s "
            "JOIN SONG_ARTISTS sa ON s.Song_ID = sa.Song_ID "
            "JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID "
            "WHERE s.User_ID = %s "
            "ORDER BY s.Upload_Date DESC LIMIT 5",
            (st.session_state.current_user['User_ID'],)
        )
        
        if isinstance(recent_songs, list) and recent_songs:
            for song in recent_songs:
                with st.expander(f"{song['Title']} - {song['Artist']}"):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        song_image = song.get('Cover_Image', 'https://via.placeholder.com/150')
                        if not isinstance(song_image, str) or not song_image.startswith(('http', '/')):
                            song_image = 'https://via.placeholder.com/150'
                        st.image(song_image, width=150)
                    with col2:
                        st.write(f"Plays: {song['Play_Count']}")
                        if st.button("Play", key=f"play_{song['Song_ID']}"):
                            self.play_song(song['Song_ID'])
        else:
            st.warning("No recently played songs")
        
        # Recommended for you with safe data access
        st.subheader("Recommended For You")
        recommended = self.db.execute_query(
            "SELECT s.Song_ID, s.Title, a.Name as Artist "
            "FROM SONGS s "
            "JOIN SONG_ARTISTS sa ON s.Song_ID = sa.Song_ID "
            "JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID "
            "ORDER BY RAND() LIMIT 5"
        )
        
        if isinstance(recommended, list) and recommended:
            st.write(pd.DataFrame(recommended))
        else:
            st.info("No recommendations yet. Start listening to get recommendations!")

    def browse_music(self):
        st.title("🎶 Browse Music")
        st.markdown("---")
        
        tab1, tab2, tab3 = st.tabs(["All Songs", "Artists", "Genres"])
        
        with tab1:
            st.subheader("All Songs")
            search_query = st.text_input("Search songs")
            
            base_query = """
                SELECT s.Song_ID, s.Title, GROUP_CONCAT(a.Name SEPARATOR ', ') as Artists, 
                s.Genre, s.Duration, s.Play_Count 
                FROM SONGS s 
                JOIN SONG_ARTISTS sa ON s.Song_ID = sa.Song_ID 
                JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID 
                {}
                GROUP BY s.Song_ID 
                ORDER BY s.Play_Count DESC
            """
            
            if search_query:
                songs = self.db.execute_query(
                    base_query.format("WHERE s.Title LIKE %s OR a.Name LIKE %s"),
                    (f"%{search_query}%", f"%{search_query}%")
                )
            else:
                songs = self.db.execute_query(base_query.format(""))
            
            if isinstance(songs, list) and songs:
                df = pd.DataFrame(songs)
                df['Duration'] = pd.to_datetime(df['Duration'], unit='s').dt.strftime('%M:%S')
                st.dataframe(df)
                
                selected_song = st.selectbox(
                    "Select a song to play",
                    options=[f"{s['Title']} - {s['Artists']}" for s in songs]
                )
                
                if st.button("Play Selected Song"):
                    song_id = next(s['Song_ID'] for s in songs if f"{s['Title']} - {s['Artists']}" == selected_song)
                    self.play_song(song_id)
            else:
                st.warning("No songs found")
        
        with tab2:
            st.subheader("Artists")
            artists = self.db.execute_query("SELECT * FROM ARTISTS ORDER BY Name")
            
            if isinstance(artists, list) and artists:
                cols = st.columns(4)
                for idx, artist in enumerate(artists):
                    with cols[idx % 4]:
                        artist_image = artist.get('Profile_Picture', 'https://via.placeholder.com/150')
                        if not isinstance(artist_image, str) or not artist_image.startswith(('http', '/')):
                            artist_image = 'https://via.placeholder.com/150'
                        st.image(artist_image, width=150)
                        st.subheader(artist['Name'])
                        if st.button(f"View songs", key=f"artist_{artist['Artist_ID']}"):
                            self.show_artist_songs(artist['Artist_ID'])
            else:
                st.warning("No artists found")
        
        with tab3:
            st.subheader("Genres")
            genres = self.db.execute_query(
                "SELECT DISTINCT Genre FROM SONGS WHERE Genre IS NOT NULL"
            )
            
            if isinstance(genres, list) and genres:
                selected_genre = st.selectbox(
                    "Select a genre",
                    options=[g['Genre'] for g in genres]
                )
                
                genre_songs = self.db.execute_query(
                    "SELECT s.Song_ID, s.Title, GROUP_CONCAT(a.Name SEPARATOR ', ') as Artists "
                    "FROM SONGS s "
                    "JOIN SONG_ARTISTS sa ON s.Song_ID = sa.Song_ID "
                    "JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID "
                    "WHERE s.Genre = %s "
                    "GROUP BY s.Song_ID",
                    (selected_genre,)
                )
                
                if isinstance(genre_songs, list) and genre_songs:
                    st.write(pd.DataFrame(genre_songs))
                else:
                    st.warning(f"No songs found in genre: {selected_genre}")
            else:
                st.warning("No genres found")

    def show_artist_songs(self, artist_id):
        artist = self.db.execute_query(
            "SELECT * FROM ARTISTS WHERE Artist_ID = %s",
            (artist_id,)
        )
        
        if not isinstance(artist, list) or not artist:
            st.error("Artist not found")
            return
            
        artist = artist[0]
        st.title(f"Songs by {artist['Name']}")
        st.markdown("---")
        
        songs = self.db.execute_query(
            "SELECT s.Song_ID, s.Title, s.Genre, s.Duration, s.Play_Count "
            "FROM SONGS s "
            "JOIN SONG_ARTISTS sa ON s.Song_ID = sa.Song_ID "
            "WHERE sa.Artist_ID = %s",
            (artist_id,)
        )
        
        if isinstance(songs, list) and songs:
            df = pd.DataFrame(songs)
            df['Duration'] = pd.to_datetime(df['Duration'], unit='s').dt.strftime('%M:%S')
            st.dataframe(df)
            
            selected_song = st.selectbox(
                "Select a song to play",
                options=[f"{s['Title']}" for s in songs]
            )
            
            if st.button("Play Selected Song"):
                song_id = next(s['Song_ID'] for s in songs if s['Title'] == selected_song)
                self.play_song(song_id)
        else:
            st.warning("No songs found for this artist")
        
        if st.button("Back to Artists"):
            self.browse_music()

    def show_playlists(self):
        st.title("🎼 Your Playlists")
        st.markdown("---")
        
        # Create new playlist
        with st.expander("Create New Playlist"):
            with st.form("new_playlist"):
                playlist_name = st.text_input("Playlist Name")
                
                if st.form_submit_button("Create"):
                    if playlist_name:
                        success = self.db.execute_query(
                            "INSERT INTO PLAYLISTS (Name, User_ID) VALUES (%s, %s)",
                            (playlist_name, st.session_state.current_user['User_ID']),
                            fetch=False
                        )
                        if success:
                            st.success("Playlist created successfully!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("Please enter a playlist name")
        
        # Display user's playlists
        playlists = self.db.execute_query(
            "SELECT * FROM PLAYLISTS WHERE User_ID = %s",
            (st.session_state.current_user['User_ID'],)
        )
        
        if isinstance(playlists, list) and playlists:
            for playlist in playlists:
                with st.expander(playlist['Name']):
                    # Show songs in playlist
                    songs = self.db.execute_query(
                        "SELECT s.Song_ID, s.Title, a.Name as Artist "
                        "FROM PLAYLIST_SONGS ps "
                        "JOIN SONGS s ON ps.Song_ID = s.Song_ID "
                        "JOIN SONG_ARTISTS sa ON s.Song_ID = sa.Song_ID "
                        "JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID "
                        "WHERE ps.Playlist_ID = %s",
                        (playlist['Playlist_ID'],)
                    )
                    
                    if isinstance(songs, list) and songs:
                        st.write(pd.DataFrame(songs))
                        
                        # Add song to playlist
                        all_songs = self.db.execute_query(
                            "SELECT s.Song_ID, s.Title, a.Name as Artist "
                            "FROM SONGS s "
                            "JOIN SONG_ARTISTS sa ON s.Song_ID = sa.Song_ID "
                            "JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID"
                        )
                        
                        if isinstance(all_songs, list) and all_songs:
                            song_to_add = st.selectbox(
                                "Add song to playlist",
                                options=[f"{s['Title']} - {s['Artist']}" for s in all_songs],
                                key=f"add_{playlist['Playlist_ID']}"
                            )
                            
                            if st.button("Add Song", key=f"add_btn_{playlist['Playlist_ID']}"):
                                song_id = next(s['Song_ID'] for s in all_songs if f"{s['Title']} - {s['Artist']}" == song_to_add)
                                success = self.db.execute_query(
                                    "INSERT INTO PLAYLIST_SONGS (Playlist_ID, Song_ID) VALUES (%s, %s)",
                                    (playlist['Playlist_ID'], song_id),
                                    fetch=False
                                )
                                if success:
                                    st.success("Song added to playlist!")
                                    time.sleep(1)
                                    st.rerun()
                    else:
                        st.info("This playlist is empty")
                    
                    if st.button(f"Delete Playlist", key=f"del_{playlist['Playlist_ID']}"):
                        success = self.db.execute_query(
                            "DELETE FROM PLAYLISTS WHERE Playlist_ID = %s",
                            (playlist['Playlist_ID'],),
                            fetch=False
                        )
                        if success:
                            st.success("Playlist deleted!")
                            time.sleep(1)
                            st.rerun()
        else:
            st.info("You haven't created any playlists yet")

    def upload_music(self):
        st.title("🎤 Upload Music")
        st.markdown("---")
        
        with st.form("upload_form"):
            st.subheader("Upload New Song")
            
            song_title = st.text_input("Song Title*", placeholder="Required")
            song_file = st.file_uploader("Audio File*", type=["mp3", "wav"], accept_multiple_files=False)
            genre = st.text_input("Genre", placeholder="Optional")
            duration = st.number_input("Duration (seconds)*", min_value=1)
            
            # Artist selection
            existing_artists = self.db.execute_query("SELECT * FROM ARTISTS")
            artist_option = st.radio("Artist", ["Existing Artist", "New Artist"])
            
            if artist_option == "Existing Artist" and isinstance(existing_artists, list) and existing_artists:
                artist_id = st.selectbox(
                    "Select Artist",
                    options=[a['Artist_ID'] for a in existing_artists],
                    format_func=lambda x: next(a['Name'] for a in existing_artists if a['Artist_ID'] == x)
                )
            else:
                new_artist = st.text_input("New Artist Name*", placeholder="Required if creating new artist")
            
            if st.form_submit_button("Upload Song"):
                if not song_title:
                    st.error("Please enter a song title")
                elif not song_file:
                    st.error("Please upload an audio file")
                elif artist_option == "New Artist" and not new_artist:
                    st.error("Please enter an artist name")
                else:
                    try:
                        # Save audio file
                        os.makedirs("user_uploads/songs", exist_ok=True)
                        song_path = f"user_uploads/songs/{st.session_state.current_user['User_ID']}_{song_file.name}"
                        with open(song_path, "wb") as f:
                            f.write(song_file.getbuffer())
                        
                        # Add new artist if needed
                        if artist_option == "New Artist" and new_artist:
                            success = self.db.execute_query(
                                "INSERT INTO ARTISTS (Name) VALUES (%s)",
                                (new_artist,),
                                fetch=False
                            )
                            if success:
                                artist_id = self.db.execute_query("SELECT LAST_INSERT_ID() as id")[0]['id']
                        
                        # Add song to database
                        success = self.db.execute_query(
                            "INSERT INTO SONGS (Title, Genre, Duration, File_Path, User_ID) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (song_title, genre, duration, song_path, st.session_state.current_user['User_ID']),
                            fetch=False
                        )
                        
                        if success:
                            song_id = self.db.execute_query("SELECT LAST_INSERT_ID() as id")[0]['id']
                            
                            # Link song to artist
                            self.db.execute_query(
                                "INSERT INTO SONG_ARTISTS (Song_ID, Artist_ID) VALUES (%s, %s)",
                                (song_id, artist_id),
                                fetch=False
                            )
                            
                            st.success("Song uploaded successfully!")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to upload song: {e}")

    def show_trending(self):
        st.title("📈 Trending Now")
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["Songs", "Artists"])
        
        with tab1:
            st.subheader("Trending Songs")
            trending_songs = self.db.execute_query(
                "SELECT s.Song_ID, s.Title, a.Name as Artist, t.Play_Count "
                "FROM TRENDING t "
                "JOIN SONGS s ON t.Song_ID = s.Song_ID "
                "JOIN SONG_ARTISTS sa ON s.Song_ID = sa.Song_ID "
                "JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID "
                "WHERE t.Trend_Date = CURDATE() "
                "ORDER BY t.Play_Count DESC LIMIT 10"
            )
            
            if isinstance(trending_songs, list) and trending_songs:
                df = pd.DataFrame(trending_songs)
                fig = px.bar(df, x='Title', y='Play_Count', color='Artist',
                             title="Today's Top Songs")
                st.plotly_chart(fig)
                
                st.write("Top Songs List:")
                st.dataframe(df)
            else:
                st.warning("No trending data available")
        
        with tab2:
            st.subheader("Trending Artists")
            trending_artists = self.db.execute_query(
                "SELECT a.Artist_ID, a.Name, COUNT(t.Song_ID) as Song_Count, SUM(t.Play_Count) as Total_Plays "
                "FROM TRENDING t "
                "JOIN SONG_ARTISTS sa ON t.Song_ID = sa.Song_ID "
                "JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID "
                "WHERE t.Trend_Date = CURDATE() "
                "GROUP BY a.Artist_ID "
                "ORDER BY Total_Plays DESC LIMIT 5"
            )
            
            if isinstance(trending_artists, list) and trending_artists:
                df = pd.DataFrame(trending_artists)
                fig = px.pie(df, values='Total_Plays', names='Name',
                            title="Artist Popularity Today")
                st.plotly_chart(fig)
                
                st.write("Top Artists List:")
                st.dataframe(df)
            else:
                st.warning("No trending data available")

    def admin_panel(self):
        if st.session_state.current_user['Username'] != 'admin':
            st.warning("You don't have admin privileges")
            return
        
        st.title("🛠 Admin Panel")
        st.markdown("---")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Users", "Songs", "Artists", "Reports"])
        
        with tab1:
            st.subheader("User Management")
            users = self.db.execute_query("SELECT * FROM USERS")
            
            if isinstance(users, list) and users:
                st.dataframe(pd.DataFrame(users))
                
                with st.expander("Add New User"):
                    with st.form("add_user"):
                        username = st.text_input("Username")
                        email = st.text_input("Email")
                        password = st.text_input("Password", type="password")
                        subscription = st.selectbox(
                            "Subscription",
                            options=["Free", "Premium", "Family"]
                        )
                        
                        if st.form_submit_button("Add User"):
                            success = self.db.execute_query(
                                "INSERT INTO USERS (Username, Email, Password, Subscription_Type) "
                                "VALUES (%s, %s, %s, %s)",
                                (username, email, password, subscription),
                                fetch=False
                            )
                            if success:
                                st.success("User added successfully!")
            else:
                st.warning("No users found")
        
        with tab2:
            st.subheader("Song Management")
            songs = self.db.execute_query(
                "SELECT s.*, GROUP_CONCAT(a.Name SEPARATOR ', ') as Artists "
                "FROM SONGS s "
                "JOIN SONG_ARTISTS sa ON s.Song_ID = sa.Song_ID "
                "JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID "
                "GROUP BY s.Song_ID"
            )
            
            if isinstance(songs, list) and songs:
                st.dataframe(pd.DataFrame(songs))
                
                with st.expander("Delete Song"):
                    song_to_delete = st.selectbox(
                        "Select song to delete",
                        options=[f"{s['Title']} - {s['Artists']}" for s in songs]
                    )
                    
                    if st.button("Delete Song"):
                        song_id = next(s['Song_ID'] for s in songs if f"{s['Title']} - {s['Artists']}" == song_to_delete)
                        success = self.db.execute_query(
                            "DELETE FROM SONGS WHERE Song_ID = %s",
                            (song_id,),
                            fetch=False
                        )
                        if success:
                            st.success("Song deleted successfully!")
                            time.sleep(1)
                            st.rerun()
            else:
                st.warning("No songs found")
        
        with tab3:
            st.subheader("Artist Management")
            artists = self.db.execute_query("SELECT * FROM ARTISTS")
            
            if isinstance(artists, list) and artists:
                st.dataframe(pd.DataFrame(artists))
                
                with st.expander("Add New Artist"):
                    with st.form("add_artist"):
                        name = st.text_input("Name")
                        
                        if st.form_submit_button("Add Artist"):
                            success = self.db.execute_query(
                                "INSERT INTO ARTISTS (Name) VALUES (%s)",
                                (name,),
                                fetch=False
                            )
                            if success:
                                st.success("Artist added successfully!")
            else:
                st.warning("No artists found")
        
        with tab4:
            st.subheader("System Reports")
            
            # User activity report
            st.write("### User Activity")
            user_activity = self.db.execute_query(
                "SELECT u.Username, COUNT(ua.Activity_ID) as Activity_Count "
                "FROM USERS u LEFT JOIN USER_ACTIVITY ua ON u.User_ID = ua.User_ID "
                "GROUP BY u.User_ID"
            )
            if isinstance(user_activity, list) and user_activity:
                fig = px.bar(pd.DataFrame(user_activity), x='Username', y='Activity_Count',
                            title="User Activity Count")
                st.plotly_chart(fig)
            else:
                st.warning("No user activity data")
            
            # Song popularity report
            st.write("### Song Popularity")
            song_popularity = self.db.execute_query(
                "SELECT s.Title, a.Name as Artist, s.Play_Count "
                "FROM SONGS s "
                "JOIN SONG_ARTISTS sa ON s.Song_ID = sa.Song_ID "
                "JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID "
                "ORDER BY s.Play_Count DESC LIMIT 10"
            )
            if isinstance(song_popularity, list) and song_popularity:
                fig = px.pie(pd.DataFrame(song_popularity), values='Play_Count', names='Title',
                            title="Top Songs by Plays")
                st.plotly_chart(fig)
            else:
                st.warning("No song popularity data")

    def play_song(self, song_id):
        song = self.db.execute_query(
            "SELECT * FROM SONGS WHERE Song_ID = %s",
            (song_id,)
        )
        
        if not isinstance(song, list) or not song:
            st.error("Song not found")
            return
            
        song = song[0]
        
        # Increment play count
        self.db.execute_query(
            "UPDATE SONGS SET Play_Count = Play_Count + 1 WHERE Song_ID = %s",
            (song_id,),
            fetch=False
        )
        
        # Update trending data
        self.db.execute_query(
            "INSERT INTO TRENDING (Song_ID, Trend_Date, Play_Count) "
            "VALUES (%s, CURDATE(), 1) "
            "ON DUPLICATE KEY UPDATE Play_Count = Play_Count + 1",
            (song_id,),
            fetch=False
        )
        
        # Log user activity
        self.db.execute_query(
            "INSERT INTO USER_ACTIVITY (User_ID, Activity_Type, Activity_Details) "
            "VALUES (%s, %s, %s)",
            (st.session_state.current_user['User_ID'], "play", f"Played song: {song['Title']}"),
            fetch=False
        )
        
        st.title(f"🎵 Now Playing: {song['Title']}")
        st.markdown("---")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            song_image = song.get('Cover_Image', 'https://via.placeholder.com/300')
            if not isinstance(song_image, str) or not song_image.startswith(('http', '/')):
                song_image = 'https://via.placeholder.com/300'
            st.image(song_image, width=300)
        with col2:
            st.write(f"Plays: {song['Play_Count'] + 1}")  # +1 because we already incremented
            st.write(f"Duration: {datetime.utcfromtimestamp(song['Duration']).strftime('%M:%S')}")
            
            # Get artists
            artists = self.db.execute_query(
                "SELECT a.Name FROM SONG_ARTISTS sa "
                "JOIN ARTISTS a ON sa.Artist_ID = a.Artist_ID "
                "WHERE sa.Song_ID = %s",
                (song_id,)
            )
            if isinstance(artists, list) and artists:
                st.write("Artists:", ", ".join([a['Name'] for a in artists]))
        
        # Audio player
        st.audio(song['File_Path'])
        
        # Comments section
        st.subheader("Comments")
        comments = self.db.execute_query(
            "SELECT c.Comment_Text, u.Username, c.Timestamp "
            "FROM COMMENTS c JOIN USERS u ON c.User_ID = u.User_ID "
            "WHERE c.Song_ID = %s ORDER BY c.Timestamp DESC",
            (song_id,)
        )
        
        if comments and isinstance(comments, list):
            for comment in comments:
                st.write(f"**{comment['Username']}** ({comment['Timestamp'].strftime('%Y-%m-%d %H:%M')})")
                st.write(comment['Comment_Text'])
                st.markdown("---")
        else:
            st.info("No comments yet")
        
        # Add comment
        with st.form("add_comment"):
            comment_text = st.text_area("Add your comment")
            if st.form_submit_button("Post Comment"):
                if comment_text:
                    success = self.db.execute_query(
                        "INSERT INTO COMMENTS (Comment_Text, User_ID, Song_ID) "
                        "VALUES (%s, %s, %s)",
                        (comment_text, st.session_state.current_user['User_ID'], song_id),
                        fetch=False
                    )
                    if success:
                        st.success("Comment added!")
                        time.sleep(1)
                        st.rerun()

        
        # Rating
        current_rating = self.db.execute_query(
            "SELECT Rating_Value FROM RATINGS "
            "WHERE User_ID = %s AND Song_ID = %s",
            (st.session_state.current_user['User_ID'], song_id)
        )
        
        with st.form("add_rating"):
            rating = st.slider("Rate this song", 0.0, 5.0, 0.0, 0.5,
                              value=current_rating[0]['Rating_Value'] if current_rating and isinstance(current_rating, list) and len(current_rating) > 0 else 0.0)
            if st.form_submit_button("Submit Rating"):
                if current_rating and isinstance(current_rating, list) and len(current_rating) > 0:
                    success = self.db.execute_query(
                        "UPDATE RATINGS SET Rating_Value = %s "
                        "WHERE User_ID = %s AND Song_ID = %s",
                        (rating, st.session_state.current_user['User_ID'], song_id),
                        fetch=False
                    )
                else:
                    success = self.db.execute_query(
                        "INSERT INTO RATINGS (Rating_Value, User_ID, Song_ID) "
                        "VALUES (%s, %s, %s)",
                        (rating, st.session_state.current_user['User_ID'], song_id),
                        fetch=False
                    )
                if success:
                    st.success("Rating submitted!")
                    time.sleep(1)
                    st.rerun()


# Run the application
if __name__ == "__main__":
    app = AudilyApp()

