import socket
import threading
import re
import os
import time
import sys
from io import StringIO
from typing import Optional, Dict, Any, List, Tuple

# --- Import libraries for AI platforms ---
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    print("Warning: Google Generative AI library is not found. Install with 'pip install google-generativeai' to enable Gemini support.")
    genai = None
    GENAI_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    print("Warning: OpenAI library not found. Install with 'pip install openai' to enable OpenAI support.")
    OpenAI = None
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    print("Warning: Anthropic library not found. Install with 'pip install anthropic' to enable Anthropic support.")
    Anthropic = None
    ANTHROPIC_AVAILABLE = False

if not (GENAI_AVAILABLE or OPENAI_AVAILABLE or ANTHROPIC_AVAILABLE):
    print("Error: none of supported AI providers are installed. See warnings above.")
    exit(1)

# --- Configuration ---
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 2323
BUFFER_SIZE = 4096
MAX_CHAT_HISTORY = 50  # Limit chat history to prevent memory leaks

# Compile regex patterns once for efficiency
MARKDOWN_PATTERNS = [
    (re.compile(r'\*\*(\S[^*]*\S)\*\*'), r'\1'),  # Bold
    (re.compile(r'\*(\S[^*]*\S)\*'), r'\1'),      # Italic
    (re.compile(r'`([^`]*)`'), r'\1'),            # Code
    (re.compile(r'^>\s*', re.MULTILINE), ''),     # Blockquotes
]

HTML_ENTITIES = {
    '&amp;': '&',
    '&lt;': '<',
    '&gt;': '>',
}


class AIClientManager:
    """Manages AI client initialization and configuration."""
    
    def __init__(self):
        self.active_platform: Optional[str] = None
        self.gemini_client = None
        self.gemini_chat = None
        self.openai_client = None
        self.anthropic_client = None
        self.model_name: Optional[str] = None
        
        # Environment variables
        self.ai_platform = os.environ.get('AI_PLATFORM', 'gemini').lower()
        self.ai_model = os.environ.get('AI_MODEL')
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY', '')
        self.openai_api_key = os.environ.get('OPENAI_API_KEY', '')
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        self.openai_base_url = os.environ.get('OPENAI_BASE_URL')
        
    def initialize(self) -> bool:
        """Initialize the AI client based on platform selection."""
        print(f"[*] Attempting to initialize AI platform: {self.ai_platform}")
        
        if self.ai_platform == 'gemini':
            return self._init_gemini()
        elif self.ai_platform == 'openai':
            return self._init_openai()
        elif self.ai_platform == 'anthropic':
            return self._init_anthropic()
        else:
            print(f"!!! Unknown AI_PLATFORM '{self.ai_platform}' specified.")
            print("!!! Please set AI_PLATFORM to 'gemini', 'openai', or 'anthropic'.")
            return False
    
    def _init_gemini(self) -> bool:
        """Initialize Gemini client."""
        if not GENAI_AVAILABLE or not self.gemini_api_key:
            if not GENAI_AVAILABLE:
                print("!!! Google Generative AI library not installed.")
            if not self.gemini_api_key:
                print("!!! GEMINI_API_KEY environment variable not set.")
            print("!!! Gemini platform not available.")
            return False
        
        try:
            self.model_name = self.ai_model if self.ai_model else 'gemini-2.0-flash'
            self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            self.gemini_chat = self.gemini_client.chats.create(model=self.model_name)
            self.active_platform = 'gemini'
            print(f"[*] Gemini model '{self.model_name}' configured successfully.")
            return True
        except Exception as e:
            print(f"!!! Failed to configure Google Generative AI: {e}")
            print("!!! Please ensure your GEMINI_API_KEY is correct and you have network access.")
            return False
    
    def _init_openai(self) -> bool:
        """Initialize OpenAI client."""
        if not OPENAI_AVAILABLE or not self.openai_api_key:
            if not OPENAI_AVAILABLE:
                print("!!! OpenAI library not installed.")
            if not self.openai_api_key:
                print("!!! OPENAI_API_KEY environment variable not set.")
            print("!!! OpenAI platform not available.")
            return False
        
        try:
            self.model_name = self.ai_model if self.ai_model else 'gpt-4o-mini'
            
            if self.openai_base_url:
                self.openai_client = OpenAI(api_key=self.openai_api_key, base_url=self.openai_base_url)
                print(f"[*] OpenAI client configured with custom base URL: {self.openai_base_url}")
            else:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                print(f"[*] OpenAI client configured successfully (using default base URL).")
            
            self.active_platform = 'openai'
            print(f"[*] Using OpenAI model: {self.model_name}")
            return True
        except Exception as e:
            print(f"!!! Failed to configure OpenAI: {e}")
            print("!!! Please ensure your OPENAI_API_KEY is correct and you have network access.")
            if self.openai_base_url:
                print(f"!!! Also check if the custom base URL '{self.openai_base_url}' is correct and accessible.")
            return False
    
    def _init_anthropic(self) -> bool:
        """Initialize Anthropic client."""
        if not ANTHROPIC_AVAILABLE or not self.anthropic_api_key:
            if not ANTHROPIC_AVAILABLE:
                print("!!! Anthropic library not installed.")
            if not self.anthropic_api_key:
                print("!!! ANTHROPIC_API_KEY environment variable not set.")
            print("!!! Anthropic platform not available.")
            return False
        
        try:
            self.model_name = self.ai_model if self.ai_model else 'claude-3-5-sonnet-latest'
            self.anthropic_client = Anthropic(api_key=self.anthropic_api_key)
            self.active_platform = 'anthropic'
            print(f"[*] Anthropic client configured successfully.")
            print(f"[*] Using Anthropic model: {self.model_name}")
            return True
        except Exception as e:
            print(f"!!! Failed to configure Anthropic: {e}")
            print("!!! Please ensure your ANTHROPIC_API_KEY is correct and you have network access.")
            return False
    
    def change_model(self, new_model: str) -> bool:
        """Change the AI model for the current platform."""
        if not self.active_platform:
            return False
        
        old_model = self.model_name
        self.model_name = new_model
        
        try:
            if self.active_platform == 'gemini':
                # Create new Gemini chat with new model
                self.gemini_chat = self.gemini_client.chats.create(model=new_model)
                print(f"[*] Gemini model changed from '{old_model}' to '{new_model}'")
                return True
            
            elif self.active_platform == 'openai':
                # OpenAI model change is just updating the name (validated on next request)
                print(f"[*] OpenAI model changed from '{old_model}' to '{new_model}'")
                return True
            
            elif self.active_platform == 'anthropic':
                # Anthropic model change is just updating the name (validated on next request)
                print(f"[*] Anthropic model changed from '{old_model}' to '{new_model}'")
                return True
                
        except Exception as e:
            # Revert model name on failure
            self.model_name = old_model
            print(f"[*] Failed to change model to '{new_model}': {e}")
            return False
        
        return False


class SpinnerManager:
    """Manages spinner animation threads."""
    
    def __init__(self):
        self.spinner_chars = ['|', '/', '-', '\\']
        self.active_spinners: Dict[threading.Thread, threading.Event] = {}
    
    def start_spinner(self, client_socket) -> Tuple[threading.Thread, threading.Event]:
        """Start a spinner animation for a client."""
        stop_event = threading.Event()
        spinner_thread = threading.Thread(target=self._spin_animation, args=(client_socket, stop_event))
        self.active_spinners[spinner_thread] = stop_event
        spinner_thread.start()
        return spinner_thread, stop_event
    
    def stop_spinner(self, spinner_thread: threading.Thread, stop_event: threading.Event):
        """Stop a specific spinner animation."""
        stop_event.set()
        spinner_thread.join(timeout=1.0)  # Timeout to prevent blocking
        if spinner_thread in self.active_spinners:
            del self.active_spinners[spinner_thread]
    
    def _spin_animation(self, client_socket, stop_event: threading.Event):
        """Runs a spinner animation on the client terminal."""
        i = 0
        while not stop_event.is_set():
            try:
                client_socket.send(self.spinner_chars[i % len(self.spinner_chars)].encode('ascii'))
                client_socket.send(b'\b')
                i += 1
                time.sleep(0.1)
            except Exception:
                break
        
        try:
            client_socket.send(b' \b')
        except Exception:
            pass
    
    def cleanup_all(self):
        """Clean up all active spinners."""
        for spinner_thread, stop_event in list(self.active_spinners.items()):
            self.stop_spinner(spinner_thread, stop_event)


def format_chunk(text_chunk: str) -> str:
    """
    Applies basic formatting to a text chunk for display on a vintage terminal.
    Optimized with pre-compiled regex patterns.
    """
    if not text_chunk:
        return ""
    
    # Apply markdown removal using pre-compiled patterns
    formatted_chunk = text_chunk
    for pattern, replacement in MARKDOWN_PATTERNS:
        formatted_chunk = pattern.sub(replacement, formatted_chunk)
    
    # Replace HTML entities
    for entity, replacement in HTML_ENTITIES.items():
        formatted_chunk = formatted_chunk.replace(entity, replacement)
    
    # Ensure consistent line endings (CRLF for Telnet)
    formatted_chunk = formatted_chunk.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
    
    return formatted_chunk


def limit_chat_history(chat_history: List[Dict[str, Any]], max_size: int = MAX_CHAT_HISTORY) -> List[Dict[str, Any]]:
    """Limit chat history size to prevent memory leaks."""
    if len(chat_history) > max_size:
        # Keep the most recent messages, but maintain conversation structure
        return chat_history[-max_size:]
    return chat_history


def stream_ai_response(ai_manager: AIClientManager, prompt: str, chat_history: List[Dict[str, Any]], 
                      client_socket, spinner_manager: SpinnerManager) -> str:
    """
    Unified streaming function for all AI platforms.
    Returns the full response text for history tracking.
    """
    first_chunk_received = False
    full_response_text = ""
    spinner_thread, stop_event = spinner_manager.start_spinner(client_socket)
    
    try:
        if ai_manager.active_platform == 'gemini':
            for chunk in ai_manager.gemini_chat.send_message_stream(prompt):
                if not first_chunk_received:
                    spinner_manager.stop_spinner(spinner_thread, stop_event)
                    client_socket.send("\r\n".encode('ascii'))
                    first_chunk_received = True
                
                chunk_text = chunk.text if hasattr(chunk, 'text') and chunk.text else ""
                if chunk_text:
                    full_response_text += chunk_text
                    formatted_chunk = format_chunk(chunk_text)
                    client_socket.send(formatted_chunk.encode('ascii', errors='ignore'))
        
        elif ai_manager.active_platform == 'openai':
            # Add user message to history for OpenAI
            current_history = chat_history + [{"role": "user", "content": prompt}]
            
            stream = ai_manager.openai_client.chat.completions.create(
                model=ai_manager.model_name,
                messages=current_history,
                stream=True,
            )
            for chunk in stream:
                if not first_chunk_received:
                    spinner_manager.stop_spinner(spinner_thread, stop_event)
                    client_socket.send("\r\n".encode('ascii'))
                    first_chunk_received = True
                
                chunk_text = chunk.choices[0].delta.content if chunk.choices[0].delta and chunk.choices[0].delta.content else ""
                if chunk_text:
                    full_response_text += chunk_text
                    formatted_chunk = format_chunk(chunk_text)
                    client_socket.send(formatted_chunk.encode('ascii', errors='ignore'))
        
        elif ai_manager.active_platform == 'anthropic':
            # Build Anthropic messages format
            anthropic_messages = []
            for msg in chat_history:
                if msg['role'] in ['user', 'assistant']:
                    anthropic_messages.append({"role": msg['role'], "content": msg['content']})
            
            anthropic_messages.append({"role": "user", "content": prompt})
            
            stream = ai_manager.anthropic_client.messages.create(
                model=ai_manager.model_name,
                max_tokens=4096,
                messages=anthropic_messages,
                stream=True,
            )
            for event in stream:
                if event.type == "content_block_delta":
                    if not first_chunk_received:
                        spinner_manager.stop_spinner(spinner_thread, stop_event)
                        client_socket.send("\r\n".encode('ascii'))
                        first_chunk_received = True
                    
                    chunk_text = event.delta.text if event.delta and event.delta.text else ""
                    if chunk_text:
                        full_response_text += chunk_text
                        formatted_chunk = format_chunk(chunk_text)
                        client_socket.send(formatted_chunk.encode('ascii', errors='ignore'))
    
    except Exception as e:
        if not first_chunk_received:
            spinner_manager.stop_spinner(spinner_thread, stop_event)
            client_socket.send(f"\r\nAI API Streaming Error ({ai_manager.active_platform.upper()}): {e}\r\n".encode('ascii', errors='ignore'))
        else:
            print(f"[*] AI API Streaming Error during stream ({ai_manager.active_platform.upper()}): {e}")
    
    finally:
        # Ensure spinner is always stopped
        if not first_chunk_received:
            spinner_manager.stop_spinner(spinner_thread, stop_event)
    
    return full_response_text


def handle_command(command: str, client_socket, ai_manager: AIClientManager, chat_history: List[Dict[str, Any]]):
    """Handle special commands like /model, /help, etc."""
    parts = command.strip().split()
    cmd = parts[0].lower()
    
    if cmd == '/model':
        if len(parts) < 2:
            client_socket.send(f"\r\nUsage: /model <model_name>\r\nCurrent model: {ai_manager.model_name}\r\n".encode('ascii'))
        else:
            new_model = parts[1]
            if ai_manager.change_model(new_model):
                client_socket.send(f"\r\nModel changed to: {new_model}\r\n".encode('ascii'))
                # For Gemini, changing model creates new chat, so clear history for consistency
                if ai_manager.active_platform == 'gemini':
                    chat_history.clear()
                    client_socket.send("Chat history cleared due to model change.\r\n".encode('ascii'))
            else:
                client_socket.send(f"\r\nFailed to change model to: {new_model}\r\n".encode('ascii'))
    
    elif cmd == '/help':
        help_text = (
            "\r\nAvailable commands:\r\n"
            "/model <name>  - Change AI model\r\n"
            "/help          - Show this help\r\n"
            "/status        - Show current settings\r\n"
            "\r\n"
        )
        client_socket.send(help_text.encode('ascii'))
    
    elif cmd == '/status':
        # Use local chat_history for all platforms since new Google Gen AI SDK doesn't expose history
        message_count = len(chat_history)
        
        status_text = (
            f"\r\nCurrent Status:\r\n"
            f"Platform: {ai_manager.active_platform.upper()}\r\n"
            f"Model: {ai_manager.model_name}\r\n"
            f"Chat history: {message_count} messages\r\n"
            "\r\n"
        )
        client_socket.send(status_text.encode('ascii'))
    
    else:
        client_socket.send(f"\r\nUnknown command: {cmd}\r\nType /help for available commands.\r\n".encode('ascii'))


def handle_client(client_socket, ai_manager: AIClientManager):
    """Handles a single client connection with chat history."""
    print(f"[*] Accepted connection from {client_socket.getpeername()}")
    
    chat_history = []
    spinner_manager = SpinnerManager()
    
    try:
        # Send welcome message
        model_display_name = ai_manager.model_name if ai_manager.model_name else 'Default'
        welcome_message = f"Vintage AI Gateway ({ai_manager.active_platform.upper()})\r\nModel: {model_display_name}\r\nType your prompt and press Enter twice to send (or use /help for commands):\r\n\r\n> "
        client_socket.send(welcome_message.encode('ascii'))
        
        # Use StringIO for efficient buffer management
        input_buffer = StringIO()
        
        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                break
            
            # Decode incoming data
            decoded_data = data.decode('ascii', errors='ignore')
            input_buffer.write(decoded_data)
            
            # Get current buffer content
            buffer_content = input_buffer.getvalue()
            
            # Check for send signals
            prompt = None
            newline_sequence_len = 0
            
            end_index_crlf = buffer_content.find('\r\n\r\n')
            end_index_lf = buffer_content.find('\n\n')
            
            if end_index_crlf != -1:
                end_index = end_index_crlf
                prompt = buffer_content[:end_index].strip()
                if prompt.startswith('> '):
                    prompt = prompt[2:]
                newline_sequence_len = 4
            elif end_index_lf != -1:
                end_index = end_index_lf
                prompt = buffer_content[:end_index].strip()
                if prompt.startswith('> '):
                    prompt = prompt[2:]
                newline_sequence_len = 2
            
            if prompt is not None:
                # Reset buffer with remaining content
                remaining_content = buffer_content[end_index + newline_sequence_len:]
                input_buffer = StringIO()
                input_buffer.write(remaining_content)
                
                if prompt:
                    # Check for commands
                    if prompt.startswith('/'):
                        handle_command(prompt, client_socket, ai_manager, chat_history)
                    else:
                        print(f"[*] Received prompt: {prompt}")
                        client_socket.send("\r\nThinking... ".encode('ascii'))
                        
                        # Stream AI response
                        full_response_text = stream_ai_response(ai_manager, prompt, chat_history, client_socket, spinner_manager)
                        
                        # Update chat history with size limits for all platforms
                        # Note: New Google Gen AI SDK manages history server-side but doesn't expose it client-side
                        chat_history.append({"role": "user", "content": prompt})
                        if full_response_text:
                            chat_history.append({"role": "assistant", "content": full_response_text})
                        chat_history = limit_chat_history(chat_history)
                        
                        # Send prompt for next input
                        client_socket.send("\r\n-----\r\n".encode('ascii'))
                    client_socket.send("Type your next prompt and press Enter twice:\r\n\r\n> ".encode('ascii'))
                else:
                    client_socket.send("\r\nType your prompt and press Enter twice:\r\n\r\n> ".encode('ascii'))
    
    except Exception as e:
        print(f"[*] Error handling client: {e}")
    finally:
        spinner_manager.cleanup_all()
        print(f"[*] Client connection closed from {client_socket.getpeername()}")
        client_socket.close()


def start_server(ai_manager: AIClientManager):
    """Starts the TCP server to listen for connections."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(5)
    
    print(f"[*] Listening on {SERVER_HOST}:{SERVER_PORT}")
    print("Press Ctrl+C to stop the server.")
    
    while True:
        try:
            client_socket, addr = server.accept()
            client_handler = threading.Thread(target=handle_client, args=(client_socket, ai_manager))
            client_handler.daemon = True  # Allow clean shutdown
            client_handler.start()
        except KeyboardInterrupt:
            print("\n[*] Server shutting down.")
            break
        except Exception as e:
            print(f"[*] Server error: {e}")
    
    server.close()


if __name__ == "__main__":
    # Initialize AI client manager
    ai_manager = AIClientManager()
    
    if not ai_manager.initialize():
        print("\n!!! No AI platform was successfully initialized.")
        print("!!! Server cannot start without a configured AI platform.")
        print("!!! Please check your AI_PLATFORM environment variable and corresponding API key.")
        sys.exit(1)
    
    print(f"[*] Using active AI platform: {ai_manager.active_platform.upper()}")
    
    # Start the server
    start_server(ai_manager)