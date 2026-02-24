#!/usr/bin/env python3

import os
import asyncio
import base64
import json
import uuid
import warnings
import struct
import sys
import datetime
import httpx
import math
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver

# --- Configuration ---
warnings.filterwarnings("ignore")

SAMPLE_RATE = 8000 
AUDIOSOCKET_AUDIO = b'\x10'
ASTERISK_HOST = '0.0.0.0'
ASTERISK_PORT = 8456

# --- Logging Utility ---

def log_msg(level, message):
    """Standardized logging for the gateway."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"[{timestamp}] [{level}] {message}", file=sys.stderr)

def create_audiosocket_chunk(audio_payload):
    """Wraps raw PCM in AudioSocket header."""
    return AUDIOSOCKET_AUDIO + struct.pack('>H', len(audio_payload)) + audio_payload

# --- Bedrock Event Factory ---

class BedrockEventFactory:
    @staticmethod
    def session_start(max_tokens=1024):
        return json.dumps({
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": {
                        "maxTokens": max_tokens, "topP": 0.9, "temperature": 0.7
                    }
                }
            }
        })

    @staticmethod
    def prompt_start(prompt_name, tools_schema):
        return json.dumps({
            "event": {
                "promptStart": {
                    "promptName": prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm", "sampleRateHertz": SAMPLE_RATE, "sampleSizeBits": 16,
                        "channelCount": 1, "voiceId": "tiffany", "encoding": "base64", "audioType": "SPEECH"
                    },
                    "toolUseOutputConfiguration": {"mediaType": "application/json"},
                    "toolConfiguration": {"tools": tools_schema}
                }
            }
        })

    @staticmethod
    def content_start(prompt_name, content_name, role="USER", content_type="AUDIO", tool_id=None):
        event_data = {
            "promptName": prompt_name, "contentName": content_name,
            "type": content_type, "role": role, "interactive": (content_type == "AUDIO")
        }
        if content_type == "AUDIO":
            event_data["audioInputConfiguration"] = {
                "mediaType": "audio/lpcm", "sampleRateHertz": SAMPLE_RATE, 
                "sampleSizeBits": 16, "channelCount": 1, "audioType": "SPEECH", "encoding": "base64"
            }
        elif content_type == "TEXT":
            event_data["textInputConfiguration"] = {"mediaType": "text/plain"}
        elif content_type == "TOOL":
            event_data["toolResultInputConfiguration"] = {
                "toolUseId": tool_id, "type": "TEXT", "textInputConfiguration": {"mediaType": "text/plain"}
            }
        return json.dumps({"event": {"contentStart": event_data}})

    @staticmethod
    def audio_input(prompt_name, content_name, b64_chunk):
        return json.dumps({
            "event": {
                "audioInput": {
                    "promptName": prompt_name, "contentName": content_name, "content": b64_chunk
                }
            }
        })

# --- Tool Processing ---

class ToolProcessor:
    def __init__(self):
        self.serper_api_key = os.getenv("SERPER_API_KEY")
    
    async def process_tool_async(self, tool_name, tool_content):
        log_msg("TOOL", f"Executing: {tool_name}")
        if tool_name.lower() == "serpersearchtool":
            return await self._execute_serper(tool_content)
        return {"error": f"Unsupported tool: {tool_name}"}

    async def _execute_serper(self, tool_content):
        content = tool_content.get("content", {})
        query = json.loads(content).get("query") if isinstance(content, str) else content.get("query")
        if not self.serper_api_key or not query: 
            log_msg("ERROR", "Serper API key or query missing")
            return {"error": "Missing Key/Query"}

        log_msg("SEARCH", f"Query: {query}")
        async with httpx.AsyncClient() as client:
            resp = await client.post("https://google.serper.dev/search", 
                                     headers={'X-API-KEY': self.serper_api_key}, 
                                     json={"q": query})
            return {"query": query, "result": resp.json().get("organic", [{}])[0].get("snippet", "")[:500]}

# --- Bedrock & AudioSocket Manager ---

class BedrockAudioSocketManager:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.model_id = os.getenv("AWS_MODEL_NAME", "amazon.nova-sonic-v1:0")
        self.region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.audio_output_queue = asyncio.Queue()
        self.is_active = True
        self.tool_processor = ToolProcessor()
        self.prompt_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())

        # --- Interruption & VAD Logic ---
        self.interrupt_event = asyncio.Event()
        self.is_playing = False
        self.VAD_THRESHOLD = 500      # RMS volume threshold
        self.SPEECH_WINDOW = 3        # Chunks needed to confirm speech (60ms)
        self.SILENCE_WINDOW = 15      # Chunks needed to confirm silence (~300ms)
        self.speech_counter = 0
        self.silence_counter = 0
        self.user_is_speaking = False

    async def run(self):
        addr = self.writer.get_extra_info('peername')
        log_msg("CONN", f"New connection from Asterisk: {addr}")
        
        try:
            config = Config(region=self.region, aws_credentials_identity_resolver=EnvironmentCredentialsResolver())
            self.bedrock_client = BedrockRuntimeClient(config=config)
            self.stream_response = await self.bedrock_client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
            )
            log_msg("AWS", "Bedrock stream established")

            await self.send_raw_event(BedrockEventFactory.session_start())
            await self.send_raw_event(self._get_tool_config())
            await self._send_system_prompt()
            await self.send_raw_event(BedrockEventFactory.content_start(self.prompt_name, self.audio_content_name))

            await asyncio.gather(
                self._process_responses(),
                self._capture_asterisk_audio(),
                self._play_to_asterisk()
            )
        except Exception as e:
            log_msg("FATAL", f"Session crash: {e}")
        finally:
            log_msg("CONN", f"Closing connection for {addr}")

    def _get_tool_config(self):
        schema = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        tools = [{"toolSpec": {"name": "serperSearchTool", "description": "Search Google", "inputSchema": {"json": json.dumps(schema)}}}]
        return BedrockEventFactory.prompt_start(self.prompt_name, tools)

    async def _send_system_prompt(self):
        c_name = str(uuid.uuid4())
        await self.send_raw_event(BedrockEventFactory.content_start(self.prompt_name, c_name, "SYSTEM", "TEXT"))
        await self.send_raw_event(json.dumps({"event": {"textInput": {"promptName": self.prompt_name, "contentName": c_name, "content": "You are a friendly phone assistant. Keep your answers short."}}}))
        await self.send_raw_event(json.dumps({"event": {"contentEnd": {"promptName": self.prompt_name, "contentName": c_name}}}))

    async def send_raw_event(self, event_json):
        event = InvokeModelWithBidirectionalStreamInputChunk(value=BidirectionalInputPayloadPart(bytes_=event_json.encode()))
        await self.stream_response.input_stream.send(event)

    def _calculate_rms(self, audio_data):
        """Calculates volume of the PCM chunk."""
        if len(audio_data) < 2: return 0
        shorts = struct.unpack(f"{len(audio_data)//2}h", audio_data)
        sum_squares = sum(s**2 for s in shorts)
        return math.sqrt(sum_squares / len(shorts))

    async def _capture_asterisk_audio(self):
        try:
            while self.is_active:
                header = await self.reader.readexactly(3) 
                v_byte, p_len = struct.unpack('>BH', header)
                payload = await self.reader.readexactly(p_len)
                
                if v_byte == AUDIOSOCKET_AUDIO[0]:
                    rms = self._calculate_rms(payload)

                    if rms > self.VAD_THRESHOLD:
                        self.speech_counter += 1
                        self.silence_counter = 0
                        if self.speech_counter >= self.SPEECH_WINDOW:
                            if not self.user_is_speaking:
                                log_msg("VAD", "User speaking...")
                                self.user_is_speaking = True
                            await self._handle_interrupt()
                    else:
                        self.speech_counter = 0
                        if self.user_is_speaking:
                            self.silence_counter += 1
                            if self.silence_counter >= self.SILENCE_WINDOW:
                                log_msg("VAD", "Silence detected. End of turn.")
                                self.user_is_speaking = False
                                self.silence_counter = 0
                                await self._signal_end_of_turn()

                    # Send audio data to Bedrock
                    b64 = base64.b64encode(payload).decode()
                    await self.send_raw_event(BedrockEventFactory.audio_input(self.prompt_name, self.audio_content_name, b64))
        except Exception as e:
            log_msg("INFO", f"Input stream stopped: {e}")
            self.is_active = False

    async def _handle_interrupt(self):
        """Clears AI response queue if user interrupts."""
        if not self.audio_output_queue.empty() or self.is_playing:
            log_msg("VOICE", "Barge-in: Interrupting AI response.")
            # CORRECTED: get_nowait() instead of get_now_nowait()
            while not self.audio_output_queue.empty():
                try: 
                    self.audio_output_queue.get_nowait()
                except asyncio.QueueEmpty: 
                    break
            self.interrupt_event.set()

    async def _signal_end_of_turn(self):
        """Ends user turn and opens a new content block for the next one."""
        await self.send_raw_event(json.dumps({"event": {"contentEnd": {"promptName": self.prompt_name, "contentName": self.audio_content_name}}}))
        self.audio_content_name = str(uuid.uuid4())
        await self.send_raw_event(BedrockEventFactory.content_start(self.prompt_name, self.audio_content_name))

    async def _play_to_asterisk(self):
        CHUNK_BYTES = 320 
        INTERVAL = 0.020
        buffer = b""
        try:
            while self.is_active:
                chunk = await self.audio_output_queue.get()
                self.is_playing = True
                self.interrupt_event.clear()
                
                buffer += chunk
                while len(buffer) >= CHUNK_BYTES:
                    if self.interrupt_event.is_set():
                        buffer = b""
                        break

                    to_send = buffer[:CHUNK_BYTES]
                    buffer = buffer[CHUNK_BYTES:]
                    self.writer.write(create_audiosocket_chunk(to_send))
                    await self.writer.drain()
                    await asyncio.sleep(INTERVAL)
                
                self.is_playing = False
        except Exception as e:
            log_msg("INFO", f"Output stream stopped: {e}")
            self.is_active = False

    async def _process_responses(self):
        try:
            while self.is_active:
                output = await self.stream_response.await_output()
                result = await output[1].receive()
                if not result.value or not result.value.bytes_: continue
                
                data = json.loads(result.value.bytes_.decode())
                event = data.get("event", {})

                if "audioOutput" in event:
                    await self.audio_output_queue.put(base64.b64decode(event["audioOutput"]["content"]))
                elif "textOutput" in event:
                    log_msg("AI", f"Transcript: {event['textOutput']['content']}")
                elif "toolUse" in event:
                    asyncio.create_task(self._handle_tool_call(event["toolUse"]))
        except Exception: 
            self.is_active = False

    async def _handle_tool_call(self, tool_use):
        t_id, t_name = tool_use["toolUseId"], tool_use["toolName"]
        res = await self.tool_processor.process_tool_async(t_name, tool_use)
        c_name = str(uuid.uuid4())
        await self.send_raw_event(BedrockEventFactory.content_start(self.prompt_name, c_name, "TOOL", "TOOL", t_id))
        await self.send_raw_event(json.dumps({"event": {"toolResult": {"promptName": self.prompt_name, "contentName": c_name, "content": json.dumps(res)}}}))
        await self.send_raw_event(json.dumps({"event": {"contentEnd": {"promptName": self.prompt_name, "contentName": c_name}}}))

async def main():
    log_msg("START", f"Gateway listening on {ASTERISK_HOST}:{ASTERISK_PORT}")
    server = await asyncio.start_server(lambda r, w: BedrockAudioSocketManager(r, w).run(), ASTERISK_HOST, ASTERISK_PORT)
    async with server: await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        log_msg("EXIT", "Server stopped!")
