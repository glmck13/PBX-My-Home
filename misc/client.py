#!/usr/bin/env python3

import socket
import struct
import time
import sys
import os
import threading
import io # Used for handling the received audio file data

# --- Configuration ---
SERVER_HOST = 'localhost'
SERVER_PORT = 8123
INITIAL_ID_STRING = "start"
WAV_FILE_PATH = sys.argv[1] if len(sys.argv) > 1 else "input.wav"
RECEIVED_WAV_FILE_PATH = sys.argv[2] if len(sys.argv) > 2 else "output.wav"

# --- Audio Constants ---
WAV_HEADER_SIZE = 44
SLIN_INPUT_RATE = 8000
SLIN_OUTPUT_RATE = 8000
SLIN_FRAME_SIZE_MS = 20
SLIN_SAMPLES_PER_FRAME = int(SLIN_INPUT_RATE * (SLIN_FRAME_SIZE_MS / 1000.0))
SLIN_BYTES_PER_SAMPLE = 2
SLIN_BYTES_PER_FRAME = SLIN_SAMPLES_PER_FRAME * SLIN_BYTES_PER_SAMPLE # 320 bytes

# --- Protocol Constants ---
MSG_TYPE_TERMINATE = 0x00
MSG_TYPE_ID_STRING = 0x01
MSG_TYPE_SLIN      = 0x10
MSG_TYPE_ERROR     = 0xFF 

# --- WAV Header Generation ---
# A helper function to create a valid WAV header for the received SLIN data
def create_wav_header(raw_audio_size):
    """
    Generates a standard 44-byte WAV header for 8kHz, 16-bit, mono audio.
    """
    total_file_size = raw_audio_size + 36
    data_size = raw_audio_size
    
    # '<' means little-endian, 'I' is unsigned integer (4 bytes), 'H' is unsigned short (2 bytes)
    header = struct.pack(
        '<4sI4s' # 'RIFF', ChunkSize, 'WAVE'
        '4sI'    # 'fmt ', Subchunk1Size (16)
        'HHI IHH' # AudioFormat (1), NumChannels, SampleRate, ByteRate, BlockAlign, BitsPerSample
        '4sI',   # 'data', Subchunk2Size (data_size)
        b'RIFF', total_file_size, b'WAVE', b'fmt ', 16, 1, 1, SLIN_OUTPUT_RATE, SLIN_OUTPUT_RATE * 2, 2, 16, b'data', data_size
    )
    return header

def create_message(msg_type, payload):
    payload_len = len(payload)
    header = struct.pack('!BH', msg_type, payload_len)
    return header + payload

def create_id_string_message(id_string):
    id_bytes = id_string.encode('utf-8')
    return create_message(MSG_TYPE_ID_STRING, id_bytes)

def create_slin_audio_message(audio_data):
    return create_message(MSG_TYPE_SLIN, audio_data)

def create_terminate_message():
    return create_message(MSG_TYPE_TERMINATE, b'')

def load_audio_data(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found at: {file_path}")
    print(f"[*] Reading audio file: {file_path}")
    with open(file_path, 'rb') as f:
        f.seek(WAV_HEADER_SIZE)
        raw_audio_data = f.read()
    print(f"[+] Successfully loaded {len(raw_audio_data)} bytes of raw SLIN audio.")
    return raw_audio_data

class AudioReceiver(threading.Thread):
    def __init__(self, client_socket, output_file_path):
        super().__init__()
        self.client_socket = client_socket
        self.output_file_path = output_file_path
        self.received_audio_data = io.BytesIO() # Buffer to store raw received audio
        self.running = True
        self.name = "AudioReceiverThread"

    def run(self):
        print(f"[{self.name}] Started listening for server audio...")
        self.client_socket.settimeout(0.5) # Set a small timeout for clean shutdown
        
        while self.running:
            try:
                # Read the 3-byte header: [1-byte Type] [2-byte Length]
                header = self._recv_exactly(3)
                if not header:
                    break # Connection closed or error

                msg_type, payload_len = struct.unpack('!BH', header)

                # Read the payload
                payload = self._recv_exactly(payload_len)

                if msg_type == MSG_TYPE_SLIN:
                    # Received SLIN audio data
                    self.received_audio_data.write(payload)
                    sys.stdout.write(f"\r[{self.name}] Received: {self.received_audio_data.tell()} bytes. ")
                    sys.stdout.flush()

                elif msg_type == MSG_TYPE_TERMINATE:
                    print(f"\n[{self.name}] Received Hangup (0x00). Stopping listener.")
                    break
                
                elif msg_type == MSG_TYPE_ERROR:
                    error_code = payload.decode('ascii', errors='ignore')
                    print(f"\n[{self.name}] Received Error (0xFF): {error_code or '(No Code)'}. Stopping listener.")
                    break
                    
                else:
                    # Handle other potential message types if needed
                    print(f"\n[{self.name}] Received unknown message type {hex(msg_type)} with payload size {payload_len}. Ignoring.")

            except socket.timeout:
                continue

            except struct.error:
                # Happens if we don't read enough bytes for the header/payload (e.g., bad message or connection loss)
                print(f"\n[{self.name}] Protocol framing error (struct unpack failed). Stopping.")
                break

            except Exception as e:
                if self.running: # Only print error if we weren't trying to shut down
                    print(f"\n[{self.name}] An error occurred: {e}")
                break

        self._save_audio()
        print(f"[{self.name}] Listener finished.")
        self.running = False # Ensure we are marked as stopped

    def _recv_exactly(self, size):
        """Helper to ensure we read exactly 'size' bytes."""
        data = b''
        while len(data) < size and self.running:
            try:
                chunk = self.client_socket.recv(size - len(data))
                if not chunk:
                    return b'' # Connection closed
                data += chunk
            except socket.timeout:
                if not self.running: return b''
                continue
            except Exception:
                return b''
        return data

    def stop(self):
        self.running = False

    def _save_audio(self):
        """Saves the buffered raw audio data to a WAV file."""
        raw_data = self.received_audio_data.getvalue()
        if raw_data:
            wav_header = create_wav_header(len(raw_data))
            
            with open(self.output_file_path, 'wb') as f:
                f.write(wav_header)
                f.write(raw_data)
                
            print(f"\n[+] Audio saved to: {self.output_file_path} (Raw size: {len(raw_data)} bytes)")
        else:
            print("\n[!] No audio data received from server to save.")


def run_client():
    client_socket = None
    receiver_thread = None
    
    try:
        raw_audio = load_audio_data(WAV_FILE_PATH)
    except FileNotFoundError as e:
        print(f"[!] ERROR: {e}")
        sys.exit(1)

    print(f"[*] Starting AudioSocket client...")
    print(f"[*] Server: {SERVER_HOST}:{SERVER_PORT}")
    print(f"[*] Initial ID String: {INITIAL_ID_STRING}")

    try:
        # 1. Establish a TCP Connection
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        print("[+] Connection established.")

        # 2. Start the Receiver Thread (Listener)
        # The socket is passed to the thread to handle all incoming data
        receiver_thread = AudioReceiver(client_socket, RECEIVED_WAV_FILE_PATH)
        receiver_thread.start()

        # 3. Send the custom ID Message ("start")
        id_msg = create_id_string_message(INITIAL_ID_STRING)
        client_socket.sendall(id_msg)
        print(f"[>] Sent ID String Message (Payload: '{INITIAL_ID_STRING}').")

        # 4. Send Audio Data in 320-byte chunks (20ms frames)
        print(f"[*] Streaming {len(raw_audio)} bytes of audio data...")
        
        total_audio_bytes = len(raw_audio)
        start_time = time.time()
        
        for i in range(0, total_audio_bytes, SLIN_BYTES_PER_FRAME):
            frame_data = raw_audio[i:i + SLIN_BYTES_PER_FRAME]
            
            # Pad the last frame if necessary
            if len(frame_data) < SLIN_BYTES_PER_FRAME:
                padding_needed = SLIN_BYTES_PER_FRAME - len(frame_data)
                frame_data += b'\x00' * padding_needed

            slin_msg = create_slin_audio_message(frame_data)
            client_socket.sendall(slin_msg)
            print(f"[*] {i}...")

            # Enforce the 20ms timing
            expected_elapsed_time = (i // SLIN_BYTES_PER_FRAME + 1) * (SLIN_FRAME_SIZE_MS / 1000.0)
            actual_elapsed_time = time.time() - start_time
            sleep_duration = expected_elapsed_time - actual_elapsed_time

            if sleep_duration > 0:
                time.sleep(sleep_duration)

        print("[+] Finished sending audio stream.")
        
        # 5. Wait briefly for any final server audio after sending finishes
        print("[*] Waiting for server reply to complete (30 seconds timeout)...")
        time.sleep(30) 

        # 6. Send a Hangup Message
        terminate_msg = create_terminate_message()
        client_socket.sendall(terminate_msg)
        print(f"[>] Sent Terminate/Hangup Message.")

    except ConnectionRefusedError:
        print(f"[!] ERROR: Connection refused. Is the server running on {SERVER_HOST}:{SERVER_PORT}?")
        sys.exit(1)
    except Exception as e:
        print(f"[!] A critical error occurred: {e}")
    finally:
        # Stop the receiver thread cleanly
        if receiver_thread and receiver_thread.is_alive():
            print("[*] Shutting down receiver thread...")
            receiver_thread.stop()
            receiver_thread.join(timeout=1) # Wait for thread to finish
            if receiver_thread.is_alive():
                 print("[!] Receiver thread failed to stop gracefully.")

        # Close the socket connection
        if client_socket:
            client_socket.close()
            print("[*] Connection closed.")

if __name__ == "__main__":
    run_client()
