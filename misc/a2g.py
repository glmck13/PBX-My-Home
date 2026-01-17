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
# Model optimized for live voice (assumes Native Audio support)
GEMINI_MODEL = "gemini-2.0-flash-exp"

# Audio parameters for the two sides
ASTERISK_RATE = 8000
ASTERISK_CHANNELS = 1
ASTERISK_BITSPERSAMPLE = 16 # PCM

GEMINI_INPUT_RATE = 16000
GEMINI_OUTPUT_RATE = 24000
GEMINI_CHANNELS = 1
GEMINI_BITSPERSAMPLE = 16 # PCM

# --- UTILITIES ---

# Fixed chunk size for 8kHz 16-bit PCM for 20ms of audio
TARGET_CHUNK_SIZE = 320 
# Fixed duration for pacing (20ms)
PLAYBACK_DURATION = 0.020 

GEMINI_DUMPFILE = "gemini.wav"
ASTERISK_DUMPFILE = "asterisk.wav"
gemini_audio_data = io.BytesIO() # Buffer to store raw received audio (converted to 8kHz)
asterisk_audio_data = io.BytesIO() # Buffer to store raw received audio (8kHz)

def create_pcm_hdr(raw_audio_size, rate):
    format = 1
    channels = 1
    bits_per_sample = 16
    chunk_size = 36
    subchunk_size = 16

    byte_rate = rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    chunk_size += raw_audio_size

    wav_header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', chunk_size, b'WAVE', b'fmt ', subchunk_size, format, channels, rate, byte_rate, block_align, bits_per_sample,
        b'data', raw_audio_size
    )
    return wav_header

def dump_asterisk_audio():
    """Dumps the raw 8kHz PCM audio received from Asterisk to a WAV file."""
    raw_data = asterisk_audio_data.getvalue()
    if raw_data:
        # The data in this buffer is 8kHz, 16-bit PCM (from Asterisk)
        wav_header = create_pcm_hdr(len(raw_data), ASTERISK_RATE)
        log_message("INFO", f"Dumping {len(raw_data)} bytes of Asterisk (8k) audio to {ASTERISK_DUMPFILE}")
        with open(ASTERISK_DUMPFILE, 'wb') as f:
            f.write(wav_header)
            f.write(raw_data)

def dump_gemini_audio():
    """Dumps the raw 8kHz PCM audio converted from Gemini to a WAV file."""
    raw_data = gemini_audio_data.getvalue()
    if raw_data:
        # The data in this buffer is 8kHz, 16-bit PCM (converted from Gemini's 24kHz)
        wav_header = create_pcm_hdr(len(raw_data), ASTERISK_RATE)
        log_message("INFO", f"Dumping {len(raw_data)} bytes of Gemini (converted 8k) audio to {GEMINI_DUMPFILE}")
        with open(GEMINI_DUMPFILE, 'wb') as f:
            f.write(wav_header)
            f.write(raw_data)

def log_message(level, message):
    """Helper for clear logging in the console."""
    print(f"[{level}] {message}", file=sys.stderr)

def create_audiosocket_chunk(audio_payload: bytes) -> bytes:
    """
    Prepends the 3-byte AudioSocket header to the audio payload.
    Header: [1 byte version] [2 bytes length (Big Endian)] [Payload]
    """
    payload_len = len(audio_payload)

    version_byte = AUDIOSOCKET_AUDIO

    # 2-byte payload length (Big Endian, unsigned short 'H')
    length_bytes = struct.pack('>H', payload_len)

    # Assemble the full chunk: Header + Payload
    return version_byte + length_bytes + audio_payload

# --- CODEC BRIDGE ---

class AudioConverter:
    """
    Handles bidirectional audio format conversion between Asterisk and Gemini.
    These methods are CPU-bound and must be run in a separate thread.
    """

    @staticmethod
    def asterisk_to_gemini(pcm_8k_bytes: bytes) -> bytes:
        """
        Converts: Asterisk (Linear PCM 16-bit @ 8kHz) -> Gemini (Linear PCM 16-bit @ 16kHz)
        """

        pcm_8k_array = np.frombuffer(pcm_8k_bytes, dtype=np.int16)
        num_samples_16k = int(len(pcm_8k_array) * GEMINI_INPUT_RATE / ASTERISK_RATE)
        pcm_16k_array = signal.resample(pcm_8k_array, num_samples_16k)
        pcm_16k_bytes =  pcm_16k_array.astype(np.int16).tobytes()

        return pcm_16k_bytes

    @staticmethod
    def gemini_to_asterisk(pcm_24k_bytes: bytes) -> bytes:
        """
        Converts: Gemini (Linear PCM 16-bit @ 24kHz) -> Asterisk (Linear PCM 16-bit @ 8kHz)
        """

        pcm_24k_array = np.frombuffer(pcm_24k_bytes, dtype=np.int16)
        num_samples_8k = int(len(pcm_24k_array) * ASTERISK_RATE / GEMINI_OUTPUT_RATE)
        pcm_8k_array = signal.resample(pcm_24k_array, num_samples_8k)
        pcm_8k_bytes = pcm_8k_array.astype(np.int16).tobytes()

        return pcm_8k_bytes

# --- CORE LOGIC: THE GEMINI LIVE STREAMER (CONCURRENCY, PACING, & PERSISTENCE FIXES) ---

async def gemini_streamer(asterisk_reader, asterisk_writer):
    log_message("INFO", "Initializing Gemini Live Session...")

    # --- CONCURRENCY FIX: Dedicated Executors for Audio Conversion ---
    asterisk_to_gemini_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="A_to_G")
    gemini_to_asterisk_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="G_to_A")
    # -----------------------------------------------------------------

    # Helper function to run a function in a specific executor's thread
    def run_in_executor(executor, func, *args):
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(executor, func, *args)

    client = genai.Client()
    search_tool = genai.types.Tool(google_search={})

    config = LiveConnectConfig(
        speech_config=SpeechConfig(
            voice_config=VoiceConfig(
                prebuilt_voice_config=PrebuiltVoiceConfig(
                    voice_name='Kore'
                )
            )
        ),
        tools=[search_tool]
    )

    async with client.aio.live.connect(config=config, model=GEMINI_MODEL) as live_session:
        log_message("INFO", "Gemini Live Session established. Starting streams.")

        # --- Sub-Task 1: Send Audio to Gemini ---
        async def send_audio_loop():
            try:

                # Initial prompt (sent once at the beginning of the call)
                await live_session.send_client_content(
                    turns = genai.types.Content(
                        role="user",
                        parts=[genai.types.Part(text="Hello. I'd like to chat, but try to keep your replies short. Are you ready?")]
                    ),
                    turn_complete=True # Tells the model to generate the response NOW
                )

                while True:
                    # 1. Read the 3-byte AudioSocket header
                    header = await asterisk_reader.readexactly(3)

                    if not header:
                        log_message("INFO", "Asterisk stream closed (client hung up or EOF on header). Sender exiting.")
                        break

                    version_byte, payload_len = struct.unpack('>BH', header)

                    if version_byte != int.from_bytes(AUDIOSOCKET_AUDIO):
                        log_message("DEBUG", f"Received non-audio packet: {version_byte}, (skip).")
                        continue

                    if payload_len == 0:
                        log_message("DEBUG", "Received 0-length audio chunk (skip).")
                        continue

                    # 3. Read the audio payload (8kHz PCM)
                    pcm_8k_chunk = await asterisk_reader.readexactly(payload_len)

                    if len(pcm_8k_chunk) != payload_len:
                        log_message("ERROR", f"Read partial chunk! Expected {payload_len} bytes, got {len(pcm_8k_chunk)}. Breaking.")
                        break

                    #asterisk_audio_data.write(pcm_8k_chunk)

                    # 4. Convert 8kHz to 16kHz in the dedicated thread pool
                    pcm_16k_chunk = await run_in_executor(
                        asterisk_to_gemini_executor,
                        AudioConverter.asterisk_to_gemini, 
                        pcm_8k_chunk
                    )

                    # 5. Send the 16kHz chunk to Gemini
                    await live_session.send_realtime_input(
                        audio=Blob(
                            data=pcm_16k_chunk,
                            mime_type="audio/pcm;rate=16000"
                        )
                    )

            except asyncio.IncompleteReadError as e:
                log_message("INFO", f"Incomplete read (Asterisk hung up mid-chunk): {e}")

            except Exception as e:
                log_message("ERROR", f"Error in send_audio_loop: {e}")
                raise

            finally:
                log_message("INFO", "Audio sender task cleanly finished.")
                #dump_asterisk_audio()

        # --- Sub-Task 2: Receive Audio/Messages from Gemini (CORRECTED) ---
        async def receive_from_gemini_loop():
            # Buffer to collect 8kHz audio before sending (Local variable)
            audio_send_buffer = b'' 

            try:
                # Outer while True loop keeps the receiver active for multiple turns
                while True: 
                    # 1. Get the stream generator for the current (or next) turn
                    response_stream = live_session.receive()

                    # 2. Process responses for this turn
                    async for response in response_stream:

                        if response.server_content and response.server_content.model_turn:
                            model_turn = response.server_content.model_turn

                            for part in model_turn.parts:

                                # a. Check for Text Output
                                if hasattr(part, 'text') and part.text:
                                    log_message("GEMINI", f"Text/Status: {part.text}")

                                # b. Check for Audio Output (The raw 24kHz PCM data)
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    inline_data = part.inline_data

                                    if inline_data.mime_type == "audio/pcm;rate=24000":
                                        gemini_pcm_chunk = inline_data.data

                                        # Convert 24kHz to 8kHz in the dedicated thread pool
                                        pcm_8k_chunk = await run_in_executor(
                                            gemini_to_asterisk_executor,
                                            AudioConverter.gemini_to_asterisk, 
                                            gemini_pcm_chunk
                                        )

                                        #gemini_audio_data.write(pcm_8k_chunk) # For debugging/dumping

                                        # 1. Add the converted audio to the persistent buffer
                                        # CORRECTED: Removed 'nonlocal' as the variable is local to this function.
                                        audio_send_buffer += pcm_8k_chunk

                                        # 2. Buffer Splitting Loop: Send in fixed 320-byte chunks
                                        while len(audio_send_buffer) >= TARGET_CHUNK_SIZE:
                                            # i. Extract exactly 320 bytes
                                            chunk_to_send = audio_send_buffer[:TARGET_CHUNK_SIZE]
                                            audio_send_buffer = audio_send_buffer[TARGET_CHUNK_SIZE:] # Keep the remainder

                                            # ii. Add the required 3-byte AudioSocket header
                                            audiosocket_chunk = create_audiosocket_chunk(chunk_to_send)

                                            # iii. Write the headered chunk to Asterisk
                                            asterisk_writer.write(audiosocket_chunk)
                                            await asterisk_writer.drain()

                                            # iv. Throttle for exactly 20ms
                                            await asyncio.sleep(PLAYBACK_DURATION)

                                    else:
                                        log_message("DEBUG", f"Received non-audio inline data: {inline_data.mime_type}")

                        # Check for the model's signal that its turn is complete
                        if hasattr(response, 'server_content') and response.server_content.generation_complete:
                            log_message("DEBUG", "Gemini turn completed. Processing remaining buffer.")

                            # CRITICAL: Send any remaining audio in the buffer
                            # This loop handles the final few bytes (< 320)
                            while len(audio_send_buffer) > 0:
                                # Determine the size of the final chunk
                                chunk_size = min(len(audio_send_buffer), TARGET_CHUNK_SIZE)
                                chunk_to_send = audio_send_buffer[:chunk_size]
                                audio_send_buffer = audio_send_buffer[chunk_size:]

                                # Send the chunk (even if it's less than 320 bytes)
                                audiosocket_chunk = create_audiosocket_chunk(chunk_to_send)
                                asterisk_writer.write(audiosocket_chunk)
                                await asterisk_writer.drain()

                                # Throttle based on the size of this specific chunk
                                # bytes_per_sample is 2 (16-bit PCM)
                                final_chunk_duration = chunk_size / (ASTERISK_RATE * 2) 
                                await asyncio.sleep(final_chunk_duration)

                            log_message("DEBUG", "Remaining buffer flushed. Restarting receiver for next turn...")
                            break # Exit the async for and let while True restart the turn

            except asyncio.CancelledError:
                log_message("INFO", "Receive task cancelled gracefully.")
                # Allow the cancellation to propagate

            except Exception as e:
                log_message("ERROR", f"Error in receive_from_gemini_loop: {e}")

            finally:
                log_message("INFO", "Audio receiver task cleanly finished.")
                #dump_gemini_audio()

        # Start the two main stream tasks
        sender_task = asyncio.create_task(send_audio_loop())
        receiver_task = asyncio.create_task(receive_from_gemini_loop())

        # Wait for either the sender (Asterisk hangup) or receiver (Gemini error/close) to finish
        done, pending = await asyncio.wait(
            [sender_task, receiver_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        await asyncio.gather(*pending, return_exceptions=True)

        # Clean up the custom thread pool executors
        log_message("INFO", "Shutting down custom thread pool executors.")
        asterisk_to_gemini_executor.shutdown(wait=True)
        gemini_to_asterisk_executor.shutdown(wait=True)

        log_message("INFO", "All stream tasks and executors have been cleaned up.")


# --- CALL HANDLER & MAIN SERVER ---

async def handle_call(reader, writer):
    """ The main handler for an incoming Asterisk AudioSocket connection. """
    addr = writer.get_extra_info('peername')
    log_message("CALL", f"Connection accepted from Asterisk: {addr}")

    try:
        # Read the initial metadata/payload from AudioSocket
        header = await reader.readexactly(3)
        version_byte, payload_len = struct.unpack('>BH', header)
        payload = await reader.readexactly(payload_len)
        log_message("CALL", f"Initial AudioSocket Message: {version_byte}:{payload_len}:{payload.hex(' ', 1)}")

        # Hand off control to the Gemini streaming logic
        await gemini_streamer(reader, writer)

    except Exception as e:
        log_message("FATAL", f"Call handler failed: {e}")
    finally:
        # Clean up the Asterisk connection
        log_message("CALL", f"Closing connection from {addr}")
        writer.close()
        await writer.wait_closed()


async def main():
    """ Sets up the asynchronous TCP listener for Asterisk AudioSocket. """
    log_message("START", f"Starting Gemini Voice Gateway on {ASTERISK_HOST}:{ASTERISK_PORT}")

    server = await asyncio.start_server(
        handle_call, ASTERISK_HOST, ASTERISK_PORT, family=socket.AF_INET
    )

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    # Check for TARGET_CHUNK_SIZE consistency
    bytes_per_sample = ASTERISK_BITSPERSAMPLE // 8
    expected_duration = TARGET_CHUNK_SIZE / (ASTERISK_RATE * bytes_per_sample)
    if expected_duration != PLAYBACK_DURATION:
        log_message("ERROR", "TARGET_CHUNK_SIZE and PLAYBACK_DURATION are inconsistent!")
        sys.exit(1)

    try:
        # This line assumes GEMINI_API_KEY is set in the environment
        if 'GEMINI_API_KEY' in os.environ:
             log_message("DEBUG", f"GEMINI_API_KEY found.")
        else:
             log_message("FATAL", "GEMINI_API_KEY environment variable not set. Exiting.")
             sys.exit(1)

        asyncio.run(main())
    except KeyboardInterrupt:
        log_message("EXIT", "Server stopped by user.")
    except Exception as e:
        log_message("EXIT", f"An unexpected error occurred: {e}")
