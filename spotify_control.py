import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv()

# Spotify scopes needed for ATLAS
SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
]

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
    scope=" ".join(SCOPES),  # Fix: Use space-separated scopes
    cache_path=".spotify_cache"
))

def get_current_track():
    """Get currently playing track info"""
    try:
        current = sp.current_playback()
        
        if not current or not current.get('item'):
            return "Nothing is playing"
        
        track = current['item']
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        
        return f"Now playing: {track_name} by {artist_name}"
    
    except Exception as e:
        return f"Error getting current track: {str(e)}"

def search_and_play(query):
    try:
        results = sp.search(q=query, limit=1, type="track")

        # Fix: Correct the key from 'track' to 'tracks'
        if not results['tracks']['items']:
            return f"Couldn't find '{query}'"
        
        track = results['tracks']['items'][0]
        track_name = track['name']
        artist_name = track['artists'][0]['name']

        # Start playback
        sp.start_playback(uris=[track['uri']])

        return f"Playing {track_name} by {artist_name}"
    
    except Exception as e:
        error_msg = str(e) 
        if "NO_ACTIVE_DEVICE" in error_msg:
            return "No active Spotify device found. Please open Spotify on your phone or computer first."
        return f"Error playing music: {error_msg}"

def play_pause():
    """Toggle play/pause"""
    try:
        playback = sp.current_playback()

        if not playback:
            return "No active Spotify device found. Please open Spotify first."
        
        if playback['is_playing']:
            sp.pause_playback()
            return "Paused"
        else:
            sp.start_playback()
            return "Resumed"
        
    except Exception as e:
        return f"Error: {str(e)}"
    
def next_track():
    """Skip to next track"""
    try:
        sp.next_track()
        #Wait a moment for track change

        import time
        time.sleep(0.5)
        return get_current_track()

    except Exception as e:
        return f"Error skipping tracks: {str(e)}"

def previous_track():
    """Go to previous track"""
    try:
        sp.previous_track()
        
        import time
        time.sleep(0.5)

        return get_current_track()
    
    except Exception as e:
        return f"Error going back: {str(e)}"

def set_volume(volume_percent):
    """Set volume (0-100)"""

    try:
        volume = max(0, min(100, volume_percent))
        sp.volume(volume)
        return f"Volume set to {volume}%"
    except Exception as e:
        return f"Error setting volume: {str(e)}"

def play_playlist(playlist_name):
    """Play a playlist by name"""

    try:
        playlists = sp.current_user_playlists(limit=50)

        for playlist in playlists['items']:
            if playlist_name.lower() in playlists['name'].lower():
                sp.start_playback(context_uri=playlist['uri'])
                return f"Playing playlist {playlist['name']}"
        
        return f"Couldn't find playlist '{playlist_name}'"
    except Exception as e:
        return f"Error playing playlist: {str(e)}"


# Test functions
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Spotify Integration")
    print("=" * 60)
    print("\nMake sure Spotify is open and playing on your device!\n")
    
    input("Press Enter to test...")
    
    print("\n1. Getting current track:")
    print(get_current_track())
    
    input("\nPress Enter to search and play 'Floga'...")
    print("\n2. Searching for 'Floga':")
    print(search_and_play("Floga"))
    
    input("\nPress Enter to pause...")
    print("\n3. Pausing:")
    print(play_pause())
    
    input("\nPress Enter to resume...")
    print("\n4. Resuming:")
    print(play_pause())
    
    print("\n✅ Spotify integration test complete!")