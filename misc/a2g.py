#!/usr/bin/env python3

import io
import asyncio
import socket
import sys
import os
import numpy as np
from scipy import signal
import struct
from google import genai
from google.genai.types import (
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
    LiveConnectConfig,
    Blob,
    Tool
)
from concurrent.futures import ThreadPoolExecutor

AUDIOSOCKET_AUDIO = b'\x10'
AUDIOSOCKET_DTMF = b'\x03'
AUDIOSOCKET_UUID = b'\x01'
AUDIOSOCKET_HANGUP = b'\x00'
AUDIOSOCKET_ERROR = b'\xFF'

# --- CONFIGURATION ---
ASTERISK_HOST = 'localhost'
ASTERISK_PORT = 8123
# Updated to current stable Live API model
GEMINI_MODEL = "gemini-2.5-flash-native-audio-latest"

ASTERISK_RATE = 8000
GEMINI_INPUT_RATE = 16000
GEMINI_OUTPUT_RATE = 24000

TARGET_CHUNK_SIZE = 320 
PLAYBACK_DURATION = 0.020 

def log_message(level, message):
    print(f"[{level}] {message}", file=sys.stderr)

def create_audiosocket_chunk(audio_payload: bytes) -> bytes:
    payload_len = len(audio_payload)
    version_byte = AUDIOSOCKET_AUDIO
    length_bytes = struct.pack('>H', payload_len)
    return version_byte + length_bytes + audio_payload

# --- OPTIMIZED CODEC BRIDGE ---

class AudioConverter:
    @staticmethod
    def asterisk_to_gemini(pcm_8k_bytes: bytes) -> bytes:
        """8kHz -> 16kHz using polyphase resampling."""
        pcm_8k_array = np.frombuffer(pcm_8k_bytes, dtype=np.int16)
        # Ratio 2:1
        pcm_16k_array = signal.resample_poly(pcm_8k_array, 2, 1)
        return pcm_16k_array.astype(np.int16).tobytes()

    @staticmethod
    def gemini_to_asterisk(pcm_24k_bytes: bytes) -> bytes:
        """24kHz -> 8kHz using polyphase resampling."""
        pcm_24k_array = np.frombuffer(pcm_24k_bytes, dtype=np.int16)
        # Ratio 1:3
        pcm_8k_array = signal.resample_poly(pcm_24k_array, 1, 3)
        return pcm_8k_array.astype(np.int16).tobytes()

# --- CORE LOGIC ---

async def gemini_streamer(asterisk_reader, asterisk_writer):
    log_message("INFO", "Initializing Gemini Live Session...")

    asterisk_to_gemini_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="A_to_G")
    gemini_to_asterisk_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="G_to_A")
    
    # Shared buffer for interruption handling
    audio_out_buffer = bytearray()

    def run_in_executor(executor, func, *args):
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(executor, func, *args)

    client = genai.Client(http_options={'api_version': 'v1beta'})
    search_tool = genai.types.Tool(google_search={})
    
    config = LiveConnectConfig(
        response_modalities=["AUDIO"], # Fixes "Cannot extract voices" error
        speech_config=SpeechConfig(
            voice_config=VoiceConfig(
                prebuilt_voice_config=PrebuiltVoiceConfig(voice_name='Puck')
            )
        ),
        tools = [search_tool]
    )

    async with client.aio.live.connect(config=config, model=GEMINI_MODEL) as live_session:
        log_message("INFO", "Gemini Live Session established.")

        async def send_audio_loop():
            try:
                await live_session.send_client_content(
                    turns=genai.types.Content(
                        role="user",
                        parts=[genai.types.Part(text="Hello. I'm ready to talk.")]
                    ),
                    turn_complete=True
                )
                while True:
                    header = await asterisk_reader.readexactly(3)
                    version_byte, payload_len = struct.unpack('>BH', header)
                    if version_byte != int.from_bytes(AUDIOSOCKET_AUDIO): continue
                    
                    pcm_8k_chunk = await asterisk_reader.readexactly(payload_len)
                    pcm_16k_chunk = await run_in_executor(
                        asterisk_to_gemini_executor,
                        AudioConverter.asterisk_to_gemini, 
                        pcm_8k_chunk
                    )
                    await live_session.send_realtime_input(
                        audio=Blob(data=pcm_16k_chunk, mime_type="audio/pcm;rate=16000")
                    )
            except Exception as e:
                log_message("ERROR", f"Sender error: {e}")

        async def playback_task():
            """Drains buffer to Asterisk with 20ms pacing."""
            try:
                while True:
                    if len(audio_out_buffer) >= TARGET_CHUNK_SIZE:
                        chunk = bytes(audio_out_buffer[:TARGET_CHUNK_SIZE])
                        del audio_out_buffer[:TARGET_CHUNK_SIZE]

                        asterisk_writer.write(create_audiosocket_chunk(chunk))
                        await asterisk_writer.drain()
                        await asyncio.sleep(PLAYBACK_DURATION)
                    else:
                        await asyncio.sleep(0.005)
            except asyncio.CancelledError:
                pass

        async def receive_from_gemini_loop():
            try:
                while True: 
                    async for response in live_session.receive():
                        # Handle Barge-in/Interruption
                        if response.server_content and response.server_content.interrupted:
                            log_message("DEBUG", "Interruption detected. Flushing playback buffer.")
                            audio_out_buffer.clear()
                            continue

                        if response.server_content and response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    pcm_8k_chunk = await run_in_executor(
                                        gemini_to_asterisk_executor,
                                        AudioConverter.gemini_to_asterisk, 
                                        part.inline_data.data
                                    )
                                    audio_out_buffer.extend(pcm_8k_chunk)

                        if response.server_content and response.server_content.generation_complete:
                            break
            except Exception as e:
                log_message("ERROR", f"Receiver error: {e}")

        # Start all tasks
        sender_task = asyncio.create_task(send_audio_loop())
        receiver_task = asyncio.create_task(receive_from_gemini_loop())
        play_task = asyncio.create_task(playback_task())

        done, pending = await asyncio.wait(
            [sender_task, receiver_task, play_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending: task.cancel()
        asterisk_to_gemini_executor.shutdown(wait=True)
        gemini_to_asterisk_executor.shutdown(wait=True)

async def handle_call(reader, writer):
    try:
        header = await reader.readexactly(3)
        version_byte, payload_len = struct.unpack('>BH', header)
        await reader.readexactly(payload_len)
        await gemini_streamer(reader, writer)
    except Exception as e:
        log_message("FATAL", f"Call handler failed: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    log_message("START", f"Starting Gateway on {ASTERISK_HOST}:{ASTERISK_PORT}")
    server = await asyncio.start_server(handle_call, ASTERISK_HOST, ASTERISK_PORT)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    if 'GEMINI_API_KEY' not in os.environ:
        log_message("FATAL", "GEMINI_API_KEY not set.")
        sys.exit(1)
    asyncio.run(main())
