#!/usr/bin/env python3.13

import os
import sys
import asyncio
import base64
import json
import uuid
import socket
import struct
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver

AUDIOSOCKET_AUDIO = b'\x10'
AUDIOSOCKET_DTMF = b'\x03'
AUDIOSOCKET_UUID = b'\x01'
AUDIOSOCKET_HANGUP = b'\x00'
AUDIOSOCKET_ERROR = b'\xFF'

# --- CONFIGURATION ---
ASTERISK_HOST = 'localhost'
ASTERISK_PORT = 8123

# Audio parameters for the two sides
ASTERISK_RATE = 8000
ASTERISK_CHANNELS = 1
ASTERISK_BITSPERSAMPLE = 16 # PCM
SONIC_RATE = 8000
SONIC_CHANNELS = 1
SONIC_BITSPERSAMPLE = 16 # PCM

# Fixed chunk size for 8kHz 16-bit PCM for 20ms of audio
TARGET_CHUNK_SIZE = 320 
PLAYBACK_DURATION = 0.020 

AWS_MODEL = 'amazon.nova-sonic-v1:0'
AWS_REGION = 'us-east-1'
AWS_VOICE = 'tiffany'

def create_audiosocket_chunk(audio_payload):
    return AUDIOSOCKET_AUDIO + struct.pack('>H', len(audio_payload)) + audio_payload

def log_message(level, message):
    print(f"[{level}] {message}", file=sys.stderr)

class SimpleNovaSonic:
    def __init__(self, reader, writer, model_id=AWS_MODEL, region=AWS_REGION):
        self.model_id = model_id
        self.region = region
        self.client = None
        self.stream = None
        self.response = None
        self.is_active = False
        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())
        self.audio_queue = asyncio.Queue()
        self.role = None
        self.display_assistant_text = False
        self.reader = reader
        self.writer = writer

    def initialize_client(self):
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        self.client = BedrockRuntimeClient(config=config)

    async def send_event(self, event_json):
        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
        )
        await self.stream.input_stream.send(event)

    async def start_session(self):
        if not self.client:
            self.initialize_client()

        self.stream = await self.client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
        )
        self.is_active = True

        session_start = '''
        {
          "event": {
            "sessionStart": {
              "inferenceConfiguration": {
                "maxTokens": 1024,
                "topP": 0.9,
                "temperature": 0.7
              }
            }
          }
        }
        '''
        await self.send_event(session_start)

        prompt_start = f'''
        {{
          "event": {{
            "promptStart": {{
              "promptName": "{self.prompt_name}",
              "textOutputConfiguration": {{
                "mediaType": "text/plain"
              }},
              "audioOutputConfiguration": {{
                "mediaType": "audio/lpcm",
                "sampleRateHertz": {SONIC_RATE},
                "sampleSizeBits": {SONIC_BITSPERSAMPLE},
                "channelCount": {SONIC_CHANNELS},
                "voiceId": "{AWS_VOICE}",
                "encoding": "base64",
                "audioType": "SPEECH"
              }}
            }}
          }}
        }}
        '''
        await self.send_event(prompt_start)

        text_content_start = f'''
        {{
            "event": {{
                "contentStart": {{
                    "promptName": "{self.prompt_name}",
                    "contentName": "{self.content_name}",
                    "type": "TEXT",
                    "interactive": false,
                    "role": "SYSTEM",
                    "textInputConfiguration": {{
                        "mediaType": "text/plain"
                    }}
                }}
            }}
        }}
        '''
        await self.send_event(text_content_start)

        system_prompt = "You are a friendly assistant. The user and you will engage in a spoken dialog " \
            "exchanging the transcripts of a natural real-time conversation. Keep your responses short, " \
            "generally two or three sentences for chatty scenarios."

        text_input = f'''
        {{
            "event": {{
                "textInput": {{
                    "promptName": "{self.prompt_name}",
                    "contentName": "{self.content_name}",
                    "content": "{system_prompt}"
                }}
            }}
        }}
        '''
        await self.send_event(text_input)

        text_content_end = f'''
        {{
            "event": {{
                "contentEnd": {{
                    "promptName": "{self.prompt_name}",
                    "contentName": "{self.content_name}"
                }}
            }}
        }}
        '''
        await self.send_event(text_content_end)

        self.response = asyncio.create_task(self.process_responses())

    async def start_audio_input(self):
        audio_content_start = f'''
        {{
            "event": {{
                "contentStart": {{
                    "promptName": "{self.prompt_name}",
                    "contentName": "{self.audio_content_name}",
                    "type": "AUDIO",
                    "interactive": true,
                    "role": "USER",
                    "audioInputConfiguration": {{
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": {SONIC_RATE},
                        "sampleSizeBits": {SONIC_BITSPERSAMPLE},
                        "channelCount": {SONIC_CHANNELS},
                        "audioType": "SPEECH",
                        "encoding": "base64"
                    }}
                }}
            }}
        }}
        '''
        await self.send_event(audio_content_start)

    async def send_audio_chunk(self, audio_bytes):
        blob = base64.b64encode(audio_bytes)
        audio_event = f'''
        {{
            "event": {{
                "audioInput": {{
                    "promptName": "{self.prompt_name}",
                    "contentName": "{self.audio_content_name}",
                    "content": "{blob.decode('utf-8')}"
                }}
            }}
        }}
        '''
        await self.send_event(audio_event)

    async def end_audio_input(self):
        audio_content_end = f'''
        {{
            "event": {{
                "contentEnd": {{
                    "promptName": "{self.prompt_name}",
                    "contentName": "{self.audio_content_name}"
                }}
            }}
        }}
        '''
        await self.send_event(audio_content_end)

    async def end_session(self):
        prompt_end = f'''
        {{
            "event": {{
                "promptEnd": {{
                    "promptName": "{self.prompt_name}"
                }}
            }}
        }}
        '''
        await self.send_event(prompt_end)

        session_end = '''
        {
            "event": {
                "sessionEnd": {}
            }
        }
        '''
        await self.send_event(session_end)

    async def process_responses(self):
        try:
            while self.is_active:
                output = await self.stream.await_output()
                result = await output[1].receive()

                if result and result.value and result.value.bytes_:
                    response_data = result.value.bytes_.decode('utf-8')
                    json_data = json.loads(response_data)
                    #log_message("INFO", f"Received {json_data.get("event", {}).keys()} from Nova Sonic...")

                    if 'event' in json_data:
                        # Handle content start event
                        if 'contentStart' in json_data['event']:
                            content_start = json_data['event']['contentStart']
                            # set role
                            self.role = content_start['role']
                            # Check for speculative content
                            if 'additionalModelFields' in content_start:
                                additional_fields = json.loads(content_start['additionalModelFields'])
                                if additional_fields.get('generationStage') == 'SPECULATIVE':
                                    self.display_assistant_text = True
                                else:
                                    self.display_assistant_text = False

                        # Handle text output event
                        elif 'textOutput' in json_data['event']:
                            text = json_data['event']['textOutput']['content']

                            if (self.role == "ASSISTANT" and self.display_assistant_text):
                                print(f"Assistant: {text}")
                            elif self.role == "USER":
                                print(f"User: {text}")

                        # Handle audio output
                        elif 'audioOutput' in json_data['event']:
                            audio_content = json_data['event']['audioOutput']['content']
                            audio_bytes = base64.b64decode(audio_content)
                            await self.audio_queue.put(audio_bytes)

                        # Handle hangup
                        elif 'completionEnd' in json_data['event']:
                            self.is_active = False
                            await self.stream.input_stream.close()

        except Exception as e:
            print(f"Error processing responses: {e}")

        finally:
            log_message("INFO", "Nova Sonic response task cleanly finished.")

    async def play_audio(self):
        try:
            while self.is_active:
                audio_send_buffer = await self.audio_queue.get()

                while len(audio_send_buffer) >= TARGET_CHUNK_SIZE:
                    chunk_to_send = audio_send_buffer[:TARGET_CHUNK_SIZE]
                    audio_send_buffer = audio_send_buffer[TARGET_CHUNK_SIZE:] # Keep the remainder
                    self.writer.write(create_audiosocket_chunk(chunk_to_send))
                    await self.writer.drain()
                    await asyncio.sleep(PLAYBACK_DURATION)

                else:
                    if len(audio_send_buffer) > 0:
                        chunk_to_send = audio_send_buffer
                        self.writer.write(create_audiosocket_chunk(chunk_to_send))
                        await self.writer.drain()
                        await asyncio.sleep(len(chunk_to_send) / (ASTERISK_RATE * 2) )

        except Exception as e:
            log_message("ERROR", f"Error in play_audio: {e}")

        finally:
            log_message("INFO", "Audio receiver task cleanly finished.")

    async def capture_audio(self):
        await self.start_audio_input()
        try:
            while self.is_active:
                header = await self.reader.readexactly(3)

                if not header:
                    log_message("INFO", "Asterisk stream closed (client hung up or EOF on header). Sender exiting.")
                    break

                version_byte, payload_len = struct.unpack('>BH', header)
                #log_message("INFO", f"Received {payload_len} bytes from Asterisk...")

                if version_byte != int.from_bytes(AUDIOSOCKET_AUDIO):
                    log_message("DEBUG", f"Received non-audio packet: {version_byte}, (skip).")
                    continue

                if payload_len == 0:
                    log_message("DEBUG", "Received 0-length audio chunk (skip).")
                    continue

                pcm_8k_chunk = await self.reader.readexactly(payload_len)

                if len(pcm_8k_chunk) != payload_len:
                    log_message("ERROR", f"Read partial chunk! Expected {payload_len} bytes, got {len(pcm_8k_chunk)}. Breaking.")
                    break

                await self.send_audio_chunk(pcm_8k_chunk)

        except asyncio.IncompleteReadError as e:
            log_message("INFO", f"Incomplete read (Asterisk hung up mid-chunk): {e}")

        except Exception as e:
            log_message("ERROR", f"Error in capture_audio: {e}")

        finally:
            log_message("INFO", "Audio sender task cleanly finished.")

async def sonic_streamer(asterisk_reader, asterisk_writer):

    # Create Nova Sonic client
    nova_client = SimpleNovaSonic(asterisk_reader, asterisk_writer)
    log_message("INFO", f"Nova Sonic client created successfully...")

    # Start session
    await nova_client.start_session()
    log_message("INFO", f"Nova Sonic session started successfully...")

    # Start audio playback task
    playback_task = asyncio.create_task(nova_client.play_audio())

    # Start audio capture task
    capture_task = asyncio.create_task(nova_client.capture_audio())

    # Wait for either task to finish
    done, pending = await asyncio.wait(
        [playback_task, capture_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    # End session
    await nova_client.end_audio_input()
    await nova_client.end_session()
    await asyncio.sleep(2)
    nova_client.is_active = False
    await nova_client.stream.input_stream.close()
    
    print("Session ended")

# --- CALL HANDLER & MAIN SERVER ---

async def handle_call(reader, writer):
    addr = writer.get_extra_info('peername')
    log_message("CALL", f"Connection accepted from Asterisk: {addr}")

    try:
        # Read the initial metadata/payload from AudioSocket
        header = await reader.readexactly(3)
        version_byte, payload_len = struct.unpack('>BH', header)
        payload = await reader.readexactly(payload_len)
        log_message("CALL", f"Initial AudioSocket Message: {version_byte}:{payload_len}:{payload.hex(' ', 1)}")

        # Hand off control to the Nova Sonic streaming logic
        await sonic_streamer(reader, writer)

    except Exception as e:
        log_message("FATAL", f"Call handler failed: {e}")

    finally:
        # Clean up the Asterisk connection
        log_message("CALL", f"Closing connection from {addr}")
        writer.close()
        await writer.wait_closed()

async def main():
    log_message("START", f"Starting Nova Sonic Voice Gateway on {ASTERISK_HOST}:{ASTERISK_PORT}")

    server = await asyncio.start_server(
        handle_call, ASTERISK_HOST, ASTERISK_PORT, family=socket.AF_INET
    )

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_message("EXIT", "Server stopped by user.")
    except Exception as e:
        log_message("EXIT", f"An unexpected error occurred: {e}")
