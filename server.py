# # server.py - Flask server with Socket.IO for real-time translation
# from flask import Flask, request
# from flask_socketio import SocketIO, emit
# from flask_cors import CORS
# import speech_recognition as sr
# from deep_translator import GoogleTranslator
# from gtts import gTTS
# import base64
# import tempfile
# import os
# import shutil
# from pydub import AudioSegment

# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
# CORS(app, resources={r"/*": {"origins": "*"}})
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# # Store connected clients with their language preferences
# clients = {}

# def find_ffmpeg():
#     """Check if FFmpeg is available"""
#     ffmpeg_path = shutil.which("ffmpeg")
#     if ffmpeg_path:
#         print(f"✅ FFmpeg found at: {ffmpeg_path}")
#         return True
    
#     print("❌ FFmpeg not found!")
#     print("Please ensure FFmpeg is installed in the Docker container")
#     return False

# # Check FFmpeg on startup
# ffmpeg_available = find_ffmpeg()
# if not ffmpeg_available:
#     print("⚠️ Server starting WITHOUT FFmpeg - audio conversion will fail!")

# def process_audio(audio_base64, source_lang, target_lang):
#     """Process audio: Speech-to-Text -> Translate -> Text-to-Speech"""
#     temp_webm_path = None
#     wav_path = None
#     mp3_path = None
    
#     try:
#         print(f"📥 Processing audio: {len(audio_base64)} chars")
        
#         # Decode base64 audio
#         audio_bytes = base64.b64decode(audio_base64)
#         print(f"📦 Decoded: {len(audio_bytes)} bytes")
        
#         # Save to temporary file
#         with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
#             temp_webm.write(audio_bytes)
#             temp_webm_path = temp_webm.name
        
#         # Convert to WAV
#         print("🔄 Converting WebM to WAV...")
#         sound = AudioSegment.from_file(temp_webm_path, format="webm")
#         wav_path = temp_webm_path.replace('.webm', '.wav')
#         sound.export(wav_path, format="wav")
        
#         # Speech Recognition
#         print(f"🎤 Recognizing speech ({source_lang})...")
#         recognizer = sr.Recognizer()
#         with sr.AudioFile(wav_path) as source:
#             audio_data = recognizer.record(source)
#             text = recognizer.recognize_google(audio_data, language=source_lang)
        
#         print(f"📝 Recognized: {text}")
        
#         # Translate
#         if source_lang != target_lang:
#             print(f"🌍 Translating {source_lang} -> {target_lang}...")
#             translator = GoogleTranslator(source=source_lang, target=target_lang)
#             translated_text = translator.translate(text)
#         else:
#             translated_text = text
        
#         print(f"✅ Translated: {translated_text}")
        
#         # Text-to-Speech
#         print(f"🔊 Generating speech ({target_lang})...")
#         tts = gTTS(translated_text, lang=target_lang, slow=False)
#         mp3_path = wav_path.replace('.wav', '.mp3')
#         tts.save(mp3_path)
        
#         # Encode to base64
#         with open(mp3_path, 'rb') as audio_file:
#             audio_bytes = audio_file.read()
#             translated_audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
#         return {
#             'original_text': text,
#             'translated_text': translated_text,
#             'audio': translated_audio_base64
#         }
    
#     except FileNotFoundError as e:
#         print(f"❌ FFmpeg error: {e}")
#         return None
#     except sr.UnknownValueError:
#         print("❌ Could not understand audio")
#         return None
#     except sr.RequestError as e:
#         print(f"❌ Speech recognition error: {e}")
#         return None
#     except Exception as e:
#         print(f"❌ Error: {e}")
#         import traceback
#         traceback.print_exc()
#         return None
#     finally:
#         # Cleanup temporary files
#         for path in [temp_webm_path, wav_path, mp3_path]:
#             if path and os.path.exists(path):
#                 try:
#                     os.unlink(path)
#                 except:
#                     pass

# @socketio.on('connect')
# def handle_connect():
#     """Handle client connection"""
#     client_id = request.sid
#     print(f"✅ Client connected: {client_id}")

# @socketio.on('disconnect')
# def handle_disconnect():
#     """Handle client disconnection"""
#     client_id = request.sid
#     if client_id in clients:
#         name = clients[client_id]['name']
#         lang = clients[client_id]['lang']
#         del clients[client_id]
#         print(f"❌ {name} disconnected (remaining: {len(clients)})")
        
#         emit('user_left', {
#             'user': name,
#             'lang': lang
#         }, broadcast=True)

# @socketio.on('register')
# def handle_register(data):
#     """Register client with language preference"""
#     client_id = request.sid
#     clients[client_id] = {
#         'lang': data['lang'],
#         'name': data.get('name', f'User_{client_id[:8]}')
#     }
#     print(f"👤 {clients[client_id]['name']} registered (lang: {data['lang']})")
#     print(f"📊 Total clients: {len(clients)}")
    
#     emit('user_joined', {
#         'user': clients[client_id]['name'],
#         'lang': data['lang']
#     }, broadcast=True)

# @socketio.on('audio')
# def handle_audio(data):
#     """Handle audio data and process translation"""
#     client_id = request.sid
    
#     if client_id not in clients:
#         print(f"❌ Unknown client: {client_id}")
#         return
    
#     source_lang = clients[client_id]['lang']
#     audio_base64 = data['audio']
#     speaker_name = clients[client_id]['name']
    
#     print(f"\n{'='*60}")
#     print(f"🎙️ Audio from {speaker_name} ({source_lang})")
#     print(f"{'='*60}")
    
#     # Process and broadcast to all other clients
#     for other_id, other_client in clients.items():
#         if other_id != client_id:
#             target_lang = other_client['lang']
#             print(f"🔄 Translating for {other_client['name']} ({target_lang})...")
            
#             result = process_audio(audio_base64, source_lang, target_lang)
            
#             if result:
#                 socketio.emit('translated_audio', {
#                     'speaker': speaker_name,
#                     'original_text': result['original_text'],
#                     'translated_text': result['translated_text'],
#                     'audio': result['audio']
#                 }, room=other_id)
#                 print(f"✅ Sent to {other_client['name']}")
#             else:
#                 print(f"❌ Failed for {other_client['name']}")
    
#     print(f"{'='*60}\n")

# @app.route('/')
# def index():
#     """Health check endpoint"""
#     return {
#         'status': 'running',
#         'message': 'Real-time Translation Server',
#         'connected_clients': len(clients),
#         'ffmpeg_available': ffmpeg_available,
#         'clients': [{'name': c['name'], 'lang': c['lang']} for c in clients.values()]
#     }

# @app.route('/health')
# def health():
#     """Health check endpoint"""
#     return {
#         'status': 'healthy', 
#         'clients': len(clients),
#         'ffmpeg': ffmpeg_available
#     }

# if __name__ == '__main__':
#     port = int(os.environ.get('PORT', 8000))
#     print("\n" + "="*60)
#     print("🚀 Real-time Translation Server")
#     print("="*60)
#     print(f"📍 Port: {port}")
#     print(f"🎬 FFmpeg: {'✅ Available' if ffmpeg_available else '❌ Missing'}")
#     print("="*60 + "\n")
    
#     socketio.run(app, host='0.0.0.0', port=port, debug=False)


# # server.py - Flask server with Socket.IO for real-time translation
# from flask import Flask, request
# from flask_socketio import SocketIO, emit
# from flask_cors import CORS
# import speech_recognition as sr
# from deep_translator import GoogleTranslator
# from gtts import gTTS
# import base64
# import tempfile
# import os
# import shutil
# from pydub import AudioSegment

# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
# CORS(app, resources={r"/*": {"origins": "*"}})
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# # Store connected clients with their language preferences
# clients = {}

# def find_ffmpeg():
#     """Check if FFmpeg is available"""
#     ffmpeg_path = shutil.which("ffmpeg")
#     ffprobe_path = shutil.which("ffprobe")
    
#     if ffmpeg_path and ffprobe_path:
#         print(f"✅ FFmpeg found at: {ffmpeg_path}")
#         print(f"✅ FFprobe found at: {ffprobe_path}")
#         return True
    
#     print("❌ FFmpeg or FFprobe not found!")
#     print("Please ensure FFmpeg is installed in the Docker container")
#     return False

# # Check FFmpeg on startup
# ffmpeg_available = find_ffmpeg()
# if not ffmpeg_available:
#     print("⚠️ Server starting WITHOUT FFmpeg - audio conversion will fail!")

# def process_audio(audio_base64, source_lang, target_lang):
#     """Process audio: Speech-to-Text -> Translate -> Text-to-Speech"""
#     temp_webm_path = None
#     wav_path = None
#     mp3_path = None
    
#     try:
#         print(f"📥 Processing audio: {len(audio_base64)} chars")
        
#         # Decode base64 audio
#         audio_bytes = base64.b64decode(audio_base64)
#         print(f"📦 Decoded: {len(audio_bytes)} bytes")
        
#         # Check if audio is substantial
#         if len(audio_bytes) < 5000:
#             print(f"⚠️ Audio too short ({len(audio_bytes)} bytes), skipping")
#             return None
        
#         # Save to temporary file
#         with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
#             temp_webm.write(audio_bytes)
#             temp_webm_path = temp_webm.name
        
#         # Convert to WAV with better quality settings
#         print("🔄 Converting WebM to WAV...")
#         sound = AudioSegment.from_file(temp_webm_path, format="webm")
#         # Normalize audio and set to mono 16kHz (better for speech recognition)
#         sound = sound.set_channels(1).set_frame_rate(16000)
#         # Normalize volume
#         sound = sound.normalize()
#         wav_path = temp_webm_path.replace('.webm', '.wav')
#         sound.export(wav_path, format="wav")
#         print(f"✅ Converted to WAV: {os.path.getsize(wav_path)} bytes")
        
#         # Speech Recognition
#         print(f"🎤 Recognizing speech ({source_lang})...")
#         recognizer = sr.Recognizer()
#         # Adjust for ambient noise and energy threshold
#         recognizer.energy_threshold = 300
#         recognizer.dynamic_energy_threshold = True
        
#         with sr.AudioFile(wav_path) as source:
#             # Adjust for ambient noise
#             recognizer.adjust_for_ambient_noise(source, duration=0.5)
#             audio_data = recognizer.record(source)
#             text = recognizer.recognize_google(audio_data, language=source_lang)
        
#         print(f"📝 Recognized: {text}")
        
#         # Translate
#         if source_lang != target_lang:
#             print(f"🌍 Translating {source_lang} -> {target_lang}...")
#             translator = GoogleTranslator(source=source_lang, target=target_lang)
#             translated_text = translator.translate(text)
#         else:
#             translated_text = text
        
#         print(f"✅ Translated: {translated_text}")
        
#         # Text-to-Speech
#         print(f"🔊 Generating speech ({target_lang})...")
#         tts = gTTS(translated_text, lang=target_lang, slow=False)
#         mp3_path = wav_path.replace('.wav', '.mp3')
#         tts.save(mp3_path)
#         print(f"✅ Generated audio: {os.path.getsize(mp3_path)} bytes")
        
#         # Encode to base64
#         with open(mp3_path, 'rb') as audio_file:
#             audio_bytes = audio_file.read()
#             translated_audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
#         return {
#             'original_text': text,
#             'translated_text': translated_text,
#             'audio': translated_audio_base64
#         }
    
#     except FileNotFoundError as e:
#         print(f"❌ FFmpeg error: {e}")
#         return None
#     except sr.UnknownValueError:
#         print("❌ Could not understand audio - speech unclear or too quiet")
#         return None
#     except sr.RequestError as e:
#         print(f"❌ Speech recognition service error: {e}")
#         print("Google Speech API might be rate limited or unavailable")
#         return None
#     except Exception as e:
#         print(f"❌ Error: {e}")
#         import traceback
#         traceback.print_exc()
#         return None
#     finally:
#         # Cleanup temporary files
#         for path in [temp_webm_path, wav_path, mp3_path]:
#             if path and os.path.exists(path):
#                 try:
#                     os.unlink(path)
#                 except:
#                     pass

# @socketio.on('connect')
# def handle_connect():
#     """Handle client connection"""
#     client_id = request.sid
#     print(f"✅ Client connected: {client_id}")

# @socketio.on('disconnect')
# def handle_disconnect():
#     """Handle client disconnection"""
#     client_id = request.sid
#     if client_id in clients:
#         name = clients[client_id]['name']
#         lang = clients[client_id]['lang']
#         del clients[client_id]
#         print(f"❌ {name} disconnected (remaining: {len(clients)})")
        
#         emit('user_left', {
#             'user': name,
#             'lang': lang
#         }, broadcast=True)

# @socketio.on('register')
# def handle_register(data):
#     """Register client with language preference"""
#     client_id = request.sid
#     clients[client_id] = {
#         'lang': data['lang'],
#         'name': data.get('name', f'User_{client_id[:8]}')
#     }
#     print(f"👤 {clients[client_id]['name']} registered (lang: {data['lang']})")
#     print(f"📊 Total clients: {len(clients)}")
    
#     emit('user_joined', {
#         'user': clients[client_id]['name'],
#         'lang': data['lang']
#     }, broadcast=True)

# @socketio.on('audio')
# def handle_audio(data):
#     """Handle audio data and process translation"""
#     client_id = request.sid
    
#     if client_id not in clients:
#         print(f"❌ Unknown client: {client_id}")
#         return
    
#     source_lang = clients[client_id]['lang']
#     audio_base64 = data['audio']
#     speaker_name = clients[client_id]['name']
    
#     print(f"\n{'='*60}")
#     print(f"🎙️ Audio from {speaker_name} ({source_lang})")
#     print(f"{'='*60}")
    
#     # Process and broadcast to all other clients
#     for other_id, other_client in clients.items():
#         if other_id != client_id:
#             target_lang = other_client['lang']
#             print(f"🔄 Translating for {other_client['name']} ({target_lang})...")
            
#             result = process_audio(audio_base64, source_lang, target_lang)
            
#             if result:
#                 socketio.emit('translated_audio', {
#                     'speaker': speaker_name,
#                     'original_text': result['original_text'],
#                     'translated_text': result['translated_text'],
#                     'audio': result['audio']
#                 }, room=other_id)
#                 print(f"✅ Sent to {other_client['name']}")
#             else:
#                 print(f"❌ Failed for {other_client['name']}")
    
#     print(f"{'='*60}\n")

# @app.route('/')
# def index():
#     """Health check endpoint"""
#     return {
#         'status': 'running',
#         'message': 'Real-time Translation Server',
#         'connected_clients': len(clients),
#         'ffmpeg_available': ffmpeg_available,
#         'clients': [{'name': c['name'], 'lang': c['lang']} for c in clients.values()]
#     }

# @app.route('/health')
# def health():
#     """Health check endpoint"""
#     return {
#         'status': 'healthy', 
#         'clients': len(clients),
#         'ffmpeg': ffmpeg_available
#     }

# if __name__ == '__main__':
#     port = int(os.environ.get('PORT', 8000))
#     print("\n" + "="*60)
#     print("🚀 Real-time Translation Server")
#     print("="*60)
#     print(f"📍 Port: {port}")
#     print(f"🎬 FFmpeg: {'✅ Available' if ffmpeg_available else '❌ Missing'}")
#     print("="*60 + "\n")
    
#     socketio.run(app, host='0.0.0.0', port=port, debug=False)



# server.py - Flask server with Socket.IO for real-time translation
from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
import base64
import tempfile
import os
import shutil
from pydub import AudioSegment
from threading import Lock
from copy import copy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Store connected clients with their language preferences
clients = {}
clients_lock = Lock()  # Thread-safe access to clients dictionary

def find_ffmpeg():
    """Check if FFmpeg is available"""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"✅ FFmpeg found at: {ffmpeg_path}")
        return True
    
    print("❌ FFmpeg not found!")
    print("Please ensure FFmpeg is installed in the Docker container")
    return False

# Check FFmpeg on startup
ffmpeg_available = find_ffmpeg()
if not ffmpeg_available:
    print("⚠️ Server starting WITHOUT FFmpeg - audio conversion will fail!")

def process_audio(audio_base64, source_lang, target_lang):
    """Process audio: Speech-to-Text -> Translate -> Text-to-Speech"""
    temp_webm_path = None
    wav_path = None
    mp3_path = None
    
    try:
        print(f"📥 Processing audio: {len(audio_base64)} chars")
        
        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_base64)
        print(f"📦 Decoded: {len(audio_bytes)} bytes")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
            temp_webm.write(audio_bytes)
            temp_webm_path = temp_webm.name
        
        # Convert to WAV
        print("🔄 Converting WebM to WAV...")
        sound = AudioSegment.from_file(temp_webm_path, format="webm")
        wav_path = temp_webm_path.replace('.webm', '.wav')
        sound.export(wav_path, format="wav")
        
        # Speech Recognition
        print(f"🎤 Recognizing speech ({source_lang})...")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=source_lang)
        
        print(f"📝 Recognized: {text}")
        
        # Translate
        if source_lang != target_lang:
            print(f"🌍 Translating {source_lang} -> {target_lang}...")
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated_text = translator.translate(text)
        else:
            translated_text = text
        
        print(f"✅ Translated: {translated_text}")
        
        # Text-to-Speech
        print(f"🔊 Generating speech ({target_lang})...")
        tts = gTTS(translated_text, lang=target_lang, slow=False)
        mp3_path = wav_path.replace('.wav', '.mp3')
        tts.save(mp3_path)
        
        # Encode to base64
        with open(mp3_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            translated_audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        return {
            'original_text': text,
            'translated_text': translated_text,
            'audio': translated_audio_base64
        }
    
    except FileNotFoundError as e:
        print(f"❌ FFmpeg error: {e}")
        return None
    except sr.UnknownValueError:
        print("❌ Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"❌ Speech recognition error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Cleanup temporary files
        for path in [temp_webm_path, wav_path, mp3_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except:
                    pass

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    print(f"✅ Client connected: {client_id}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    
    with clients_lock:
        if client_id in clients:
            name = clients[client_id]['name']
            lang = clients[client_id]['lang']
            del clients[client_id]
            print(f"❌ {name} disconnected (remaining: {len(clients)})")
            
            # Emit outside the lock to avoid potential deadlocks
            emit('user_left', {
                'user': name,
                'lang': lang
            }, broadcast=True)

@socketio.on('register')
def handle_register(data):
    """Register client with language preference"""
    client_id = request.sid
    
    with clients_lock:
        clients[client_id] = {
            'lang': data['lang'],
            'name': data.get('name', f'User_{client_id[:8]}')
        }
        name = clients[client_id]['name']
        lang = data['lang']
        total = len(clients)
    
    print(f"👤 {name} registered (lang: {lang})")
    print(f"📊 Total clients: {total}")
    
    emit('user_joined', {
        'user': name,
        'lang': lang
    }, broadcast=True)

@socketio.on('audio')
def handle_audio(data):
    """Handle audio data and process translation"""
    client_id = request.sid
    
    # Get speaker info and create snapshot of other clients
    with clients_lock:
        if client_id not in clients:
            print(f"❌ Unknown client: {client_id}")
            return
        
        source_lang = clients[client_id]['lang']
        speaker_name = clients[client_id]['name']
        
        # Create a snapshot of other clients to iterate safely
        other_clients = {
            other_id: {'lang': other_client['lang'], 'name': other_client['name']}
            for other_id, other_client in clients.items()
            if other_id != client_id
        }
    
    audio_base64 = data['audio']
    
    print(f"\n{'='*60}")
    print(f"🎙️ Audio from {speaker_name} ({source_lang})")
    print(f"{'='*60}")
    
    # Process and broadcast to all other clients (now safe from dictionary changes)
    for other_id, other_client in other_clients.items():
        target_lang = other_client['lang']
        print(f"🔄 Translating for {other_client['name']} ({target_lang})...")
        
        result = process_audio(audio_base64, source_lang, target_lang)
        
        if result:
            try:
                socketio.emit('translated_audio', {
                    'speaker': speaker_name,
                    'original_text': result['original_text'],
                    'translated_text': result['translated_text'],
                    'audio': result['audio']
                }, room=other_id)
                print(f"✅ Sent to {other_client['name']}")
            except Exception as e:
                print(f"❌ Failed to send to {other_client['name']}: {e}")
        else:
            print(f"❌ Processing failed for {other_client['name']}")
    
    print(f"{'='*60}\n")

@app.route('/')
def index():
    """Health check endpoint"""
    with clients_lock:
        client_list = [{'name': c['name'], 'lang': c['lang']} for c in clients.values()]
        client_count = len(clients)
    
    return {
        'status': 'running',
        'message': 'Real-time Translation Server',
        'connected_clients': client_count,
        'ffmpeg_available': ffmpeg_available,
        'clients': client_list
    }

@app.route('/health')
def health():
    """Health check endpoint"""
    with clients_lock:
        client_count = len(clients)
    
    return {
        'status': 'healthy', 
        'clients': client_count,
        'ffmpeg': ffmpeg_available
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print("\n" + "="*60)
    print("🚀 Real-time Translation Server")
    print("="*60)
    print(f"📍 Port: {port}")
    print(f"🎬 FFmpeg: {'✅ Available' if ffmpeg_available else '❌ Missing'}")
    print("="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False)