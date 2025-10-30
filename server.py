# server.py - Flask server with Socket.IO for real-time translation
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
import base64
import io
from pydub import AudioSegment
import tempfile
import os
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store connected clients with their language preferences
clients = {}

# Try to find FFmpeg automatically
def find_ffmpeg():
    """Try to find FFmpeg in common locations"""
    import shutil
    if shutil.which("ffmpeg"):
        print("✅ FFmpeg found in system PATH")
        return True
    
    # Common Windows locations
    common_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        Path.home() / "ffmpeg" / "bin" / "ffmpeg.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            AudioSegment.converter = str(path)
            print(f"✅ FFmpeg found at: {path}")
            return True
    
    print("❌ FFmpeg not found!")
    print("Please install FFmpeg:")
    print("1. Download from: https://www.gyan.dev/ffmpeg/builds/")
    print("2. Extract to C:\\ffmpeg\\")
    print("3. Or add FFmpeg to your system PATH")
    return False

# Try to configure FFmpeg
if not find_ffmpeg():
    print("\n⚠️ Server starting WITHOUT FFmpeg - audio conversion will fail!")
    print("Press Ctrl+C to stop and install FFmpeg first.\n")

def process_audio(audio_base64, source_lang, target_lang):
    """Process audio: Speech-to-Text -> Translate -> Text-to-Speech"""
    temp_webm_path = None
    wav_path = None
    mp3_path = None
    
    try:
        print(f"📥 Received audio data: {len(audio_base64)} chars")
        
        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_base64)
        print(f"📦 Decoded to {len(audio_bytes)} bytes")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
            temp_webm.write(audio_bytes)
            temp_webm_path = temp_webm.name
        print(f"💾 Saved to temp file: {temp_webm_path}")
        
        # Convert to WAV
        print("🔄 Converting WebM to WAV...")
        sound = AudioSegment.from_file(temp_webm_path, format="webm")
        wav_path = temp_webm_path.replace('.webm', '.wav')
        sound.export(wav_path, format="wav")
        print(f"✅ Converted to WAV: {wav_path}")
        
        # Speech Recognition
        print(f"🎤 Recognizing speech in {source_lang}...")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=source_lang)
        
        print(f"📝 Recognized ({source_lang}): {text}")
        
        # Translate
        if source_lang != target_lang:
            print(f"🌍 Translating {source_lang} -> {target_lang}...")
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated_text = translator.translate(text)
        else:
            translated_text = text
        
        print(f"✅ Translated ({target_lang}): {translated_text}")
        
        # Text-to-Speech - Save to temporary file
        print(f"🔊 Generating speech in {target_lang}...")
        tts = gTTS(translated_text, lang=target_lang, slow=False)
        mp3_path = wav_path.replace('.wav', '.mp3')
        tts.save(mp3_path)
        print(f"✅ Generated audio: {mp3_path}")
        
        # Read the MP3 file and encode to base64
        with open(mp3_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            translated_audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        print(f"📤 Encoded audio: {len(translated_audio_base64)} chars")
        
        return {
            'original_text': text,
            'translated_text': translated_text,
            'audio': translated_audio_base64
        }
    
    except FileNotFoundError as e:
        print(f"❌ File not found error: {e}")
        print("This usually means FFmpeg is not installed or not in PATH")
        return None
    except sr.UnknownValueError:
        print("❌ Speech recognition could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"❌ Speech recognition service error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error processing audio: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Cleanup temporary files
        for path in [temp_webm_path, wav_path, mp3_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                    print(f"🗑️ Cleaned up: {path}")
                except:
                    pass

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    print(f"✅ Client {client_id} connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    if client_id in clients:
        name = clients[client_id]['name']
        lang = clients[client_id]['lang']
        del clients[client_id]
        print(f"❌ {name} disconnected (remaining: {len(clients)})")
        
        # Notify all clients
        emit('user_left', {
            'user': name,
            'lang': lang
        }, broadcast=True)

@socketio.on('register')
def handle_register(data):
    """Register client with language preference"""
    client_id = request.sid
    clients[client_id] = {
        'lang': data['lang'],
        'name': data.get('name', f'User_{client_id[:8]}')
    }
    print(f"👤 {clients[client_id]['name']} registered (lang: {data['lang']})")
    print(f"📊 Total clients: {len(clients)}")
    
    # Notify all clients
    emit('user_joined', {
        'user': clients[client_id]['name'],
        'lang': data['lang']
    }, broadcast=True)

@socketio.on('audio')
def handle_audio(data):
    """Handle audio data and process translation"""
    client_id = request.sid
    
    if client_id not in clients:
        print(f"❌ Unknown client {client_id} sent audio")
        return
    
    source_lang = clients[client_id]['lang']
    audio_base64 = data['audio']
    speaker_name = clients[client_id]['name']
    
    print(f"\n{'='*60}")
    print(f"🎙️ Processing audio from {speaker_name} ({source_lang})")
    print(f"{'='*60}")
    
    # Process and broadcast to all other clients
    for other_id, other_client in clients.items():
        if other_id != client_id:
            target_lang = other_client['lang']
            print(f"\n🔄 Translating for {other_client['name']} ({target_lang})...")
            
            # Process translation
            result = process_audio(audio_base64, source_lang, target_lang)
            
            if result:
                socketio.emit('translated_audio', {
                    'speaker': speaker_name,
                    'original_text': result['original_text'],
                    'translated_text': result['translated_text'],
                    'audio': result['audio']
                }, room=other_id)
                print(f"✅ Sent translation to {other_client['name']}")
            else:
                print(f"❌ Failed to process audio for {other_client['name']}")
    
    print(f"{'='*60}\n")

@app.route('/')
def index():
    """Health check endpoint"""
    return {
        'status': 'running',
        'message': 'Real-time Translation Server',
        'connected_clients': len(clients),
        'clients': [{'name': c['name'], 'lang': c['lang']} for c in clients.values()]
    }

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'clients': len(clients)}

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Starting Real-time Translation Server (Flask + Socket.IO)")
    print("="*60)
    print("📍 HTTP Server: http://localhost:5000")
    print("📍 Socket.IO: http://localhost:5000")
    print("📝 Make sure clients connect to this address")
    print("⚠️  Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)