import socket
import threading
import json
import textwrap # Useful for wrapping long lines
import re # Import regular expressions for more robust whitespace handling
import os # Import the os module to access environment variables
import time # Import time for the spinner animation delay
import sys # Import sys to exit if no AI platform is available

# --- Import libraries for AI platforms ---
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Warning: Google Generative AI library is not found. Install with 'pip install google-generativeai' to enable Gemini support.")

try:
    from openai import OpenAI
except ImportError:
    print("Warning: OpenAI library not found. Install with 'pip install openai' to enable OpenAI support.")
    OpenAI = None # Set to None if import fails

try:
    from anthropic import Anthropic
except ImportError:
    print("Warning: Anthropic library not found. Install with 'pip install anthropic' to enable Anthropic support.")
    Anthropic = None # Set to None if import fails

if (not genai and not OpenAI and not Anthropic):
    print("Error: none of supported AI providers are installed. See warnings above.")
    exit(1)

# --- Configuration ---
# Replace with the IP address of the computer running this script.
# Use '0.0.0.0' to listen on all available interfaces.
SERVER_HOST = '0.0.0.0'
# The port the server will listen on.
SERVER_PORT = 2323
BUFFER_SIZE = 4096 # Buffer size for receiving data

# Your API keys, read from environment variables.
# IMPORTANT: Set these environment variables before running the script.
# Default to an empty string if the environment variable is not set.
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# Optional: Set a custom base URL for the OpenAI API (useful for proxies or local models)
# Read from the OPENAI_BASE_URL environment variable.
OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL')


# Choose the AI platform to use: 'gemini', 'openai', or 'anthropic'.
# Read from the AI_PLATFORM environment variable, default to 'gemini'.
AI_PLATFORM = os.environ.get('AI_PLATFORM', 'gemini').lower()

# Choose the specific AI model to use for the selected platform.
# Read from the AI_MODEL environment variable. Defaults are provided below
# if this variable is not set.
AI_MODEL = os.environ.get('AI_MODEL')


# --- Initialize AI Clients/Models ---
gemini_model = None
openai_client = None
anthropic_client = None
active_platform = None # To store the platform actually being used

print(f"[*] Attempting to initialize AI platform: {AI_PLATFORM}")

if AI_PLATFORM == 'gemini':
    if genai and GEMINI_API_KEY:
        try:
            # Use AI_MODEL if set, otherwise use a default Gemini model
            gemini_model_name = AI_MODEL if AI_MODEL else 'gemini-2.0-flash'
            client = genai.Client(api_key=GEMINI_API_KEY)
            chat = client.chats.create(model=gemini_model_name)
            active_platform = 'gemini'
        except Exception as e:
            print(f"[*] Gemini model '{gemini_model_name}' configured successfully.")
            active_platform = 'gemini'
        except Exception as e:
            print(f"!!! Failed to configure Google Generative AI: {e}")
            print("!!! Please ensure your GEMINI_API_KEY is correct and you have network access.")
    else:
        print("!!! GEMINI_API_KEY environment variable not set.")
        print("!!! Gemini platform not available.")

elif AI_PLATFORM == 'openai':
    if OpenAI and OPENAI_API_KEY:
        try:
            # Use AI_MODEL if set, otherwise use a default OpenAI model
            openai_model_name = AI_MODEL if AI_MODEL else 'gpt-4o-mini' # Default OpenAI model
            # Initialize OpenAI client
            # Pass the base_url if OPENAI_BASE_URL is set
            if OPENAI_BASE_URL:
                openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
                print(f"[*] OpenAI client configured with custom base URL: {OPENAI_BASE_URL}")
            else:
                openai_client = OpenAI(api_key=OPENAI_API_KEY)
                print(f"[*] OpenAI client configured successfully (using default base URL).")

            active_platform = 'openai'
            # Store the model name to use later
            openai_client.model_name = openai_model_name
            print(f"[*] Using OpenAI model: {openai_client.model_name}")
        except Exception as e:
            print(f"!!! Failed to configure OpenAI: {e}")
            print("!!! Please ensure your OPENAI_API_KEY is correct and you have network access.")
            if OPENAI_BASE_URL:
                 print(f"!!! Also check if the custom base URL '{OPENAI_BASE_URL}' is correct and accessible.")
    else:
        if not OpenAI:
            print("!!! OpenAI library not installed.")
        if not OPENAI_API_KEY:
             print("!!! OPENAI_API_KEY environment variable not set.")
        print("!!! OpenAI platform not available.")

elif AI_PLATFORM == 'anthropic':
    if Anthropic and ANTHROPIC_API_KEY:
        try:
            # Use AI_MODEL if set, otherwise use a default Anthropic model
            anthropic_model_name = AI_MODEL if AI_MODEL else 'claude-3-5-sonnet-latest' # Default Anthropic model
            # Initialize Anthropic client
            anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
            print(f"[*] Anthropic client configured successfully.")
            active_platform = 'anthropic'
            # Store the model name to use later
            anthropic_client.model_name = anthropic_model_name
            print(f"[*] Using Anthropic model: {anthropic_client.model_name}")
        except Exception as e:
            print(f"!!! Failed to configure Anthropic: {e}")
            print("!!! Please ensure your ANTHROPIC_API_KEY is correct and you have network access.")
    else:
        if not Anthropic:
            print("!!! Anthropic library not installed.")
        if not ANTHROPIC_API_KEY:
            print("!!! ANTHROPIC_API_KEY environment variable not set.")
        print("!!! Anthropic platform not available.")

else:
    print(f"!!! Unknown AI_PLATFORM '{AI_PLATFORM}' specified.")
    print("!!! Please set AI_PLATFORM to 'gemini', 'openai', or 'anthropic'.")


# --- Check if any platform was successfully initialized ---
if active_platform is None:
    print("\n!!! No AI platform was successfully initialized.")
    print("!!! Server cannot start without a configured AI platform.")
    print("!!! Please check your AI_PLATFORM environment variable and corresponding API key.")
    sys.exit(1) # Exit the script if no platform is ready

print(f"[*] Using active AI platform: {active_platform.upper()}")

# --- Spinner Animation ---
spinner_chars = ['|', '/', '-', '\\']
stop_spinner = threading.Event() # Event to signal the spinner thread to stop

def spin_animation(client_socket):
    """Runs a simple spinner animation on the client terminal."""
    i = 0
    # Loop while the stop_spinner event is not set
    while not stop_spinner.is_set():
        try:
            # Send the current spinner character
            client_socket.send(spinner_chars[i % len(spinner_chars)].encode('ascii'))
            # Send a backspace character to move the cursor back
            client_socket.send(b'\b')
            i += 1
            # Wait a short time before the next frame
            time.sleep(0.1)
        except Exception:
            # If there's an error sending (e.g., socket closed), stop the spinner
            break

    # After the loop, clear the last spinner character by sending a space and a backspace
    # This ensures the spinner doesn't remain on the screen after stopping
    try:
        client_socket.send(b' \b')
    except Exception:
        pass # Ignore errors if socket is already closed

# --- Text Formatting for Streaming Chunks ---
def format_chunk(text_chunk):
    """
    Applies basic formatting to a text chunk for display on a vintage terminal.
    This is less sophisticated than full line wrapping but works for streaming.
    Preserves original line breaks within the chunk.
    """
    if not text_chunk:
        return ""

    # 1. Basic Markdown removal/conversion
    # Use regex to remove bold/italic markers, being careful with whitespace
    formatted_chunk = re.sub(r'\*\*(\S[^*]*\S)\*\*', r'\1', text_chunk) # Bold
    formatted_chunk = re.sub(r'\*(\S[^*]*\S)\*', r'\1', formatted_chunk) # Italic
    formatted_chunk = formatted_chunk.replace('`', '') # Remove code block markers
    formatted_chunk = formatted_chunk.replace('>', '') # Remove blockquote markers

    # 2. Replace common HTML entities if they appear (basic example)
    formatted_chunk = formatted_chunk.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

    # 3. Ensure consistent line endings (CRLF for Telnet) within the chunk
    # Replace any mix of newlines with CRLF
    formatted_chunk = formatted_chunk.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')

    return formatted_chunk

# --- Client Handling ---
def handle_client(client_socket):
    """Handles a single client connection with chat history."""
    print(f"[*] Accepted connection from {client_socket.getpeername()}")

    # Initialize chat history for this client
    # Gemini uses a list of message objects with 'role' and 'parts'
    # OpenAI and Anthropic use a list of message objects with 'role' and 'content'
    chat_history = []

    try:
        # Send a welcome message indicating the active platform and model
        model_display_name = AI_MODEL if AI_MODEL else 'Default'
        if active_platform == 'gemini' and not AI_MODEL:
            model_display_name = 'gemini-2.0-flash' # Show updated default
        elif active_platform == 'openai' and not AI_MODEL:
            model_display_name = 'gpt-4o-mini'
        elif active_platform == 'anthropic' and not AI_MODEL:
            model_display_name = 'claude-3-5-sonnet-latest'


        welcome_message = f"Vintage AI Gateway ({active_platform.upper()})\r\nModel: {model_display_name}\r\nType your prompt and press Enter twice to send:\r\n\r\n> "
        client_socket.send(welcome_message.encode('ascii'))

        # Accumulate input until the user signals to send (e.g., double Enter)
        input_buffer = ""
        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                break # Connection closed

            # Decode incoming data, assuming ASCII and ignoring errors for robustness
            input_buffer += data.decode('ascii', errors='ignore')

            # --- Corrected Input Signal Handling ---
            prompt = None
            newline_sequence_len = 0

            # Check for CRLF CRLF first
            end_index_crlf = input_buffer.find('\r\n\r\n')

            # If CRLF CRLF not found, look for LF LF
            end_index_lf = input_buffer.find('\n\n')

            if end_index_crlf != -1:
                # Found CRLF CRLF
                end_index = end_index_crlf
                # Extract prompt, removing the "> " from the start
                prompt = input_buffer[:end_index].strip()
                if prompt.startswith('> '):
                    prompt = prompt[2:]
                newline_sequence_len = 4 # Length of '\r\n\r\n'
            elif end_index_lf != -1:
                # Found LF LF
                end_index = end_index_lf
                 # Extract prompt, removing the "> " from the start
                prompt = input_buffer[:end_index].strip()
                if prompt.startswith('> '):
                    prompt = prompt[2:]
                newline_sequence_len = 2 # Length of '\n\n'

            # If a prompt was found (either signal detected)
            if prompt is not None:
                # Keep the rest of the buffer for the next input
                input_buffer = input_buffer[end_index + newline_sequence_len:]

                if prompt:
                    print(f"[*] Received prompt: {prompt}")
                    # Send the "Thinking..." message
                    client_socket.send("\r\nThinking... ".encode('ascii')) # Added CRLF before Thinking and space after

                    # --- Start Spinner Animation ---
                    stop_spinner.clear() # Ensure the event is clear before starting
                    spinner_thread = threading.Thread(target=spin_animation, args=(client_socket,))
                    spinner_thread.start()
                    # --- End Start Spinner Animation ---

                    # --- Get and Stream Response from AI Platform ---
                    first_chunk_received = False
                    full_response_text = "" # To accumulate the full response for history

                    try:
                        if active_platform == 'gemini' and gemini_model_name:
                            # Add user message to history for Gemini
                            # Pass the entire chat history
                            for chunk in chat.send_message_stream(prompt):
                                if not first_chunk_received:
                                    # Stop spinner on first chunk
                                    stop_spinner.set()
                                    spinner_thread.join()
                                    client_socket.send("\r\n".encode('ascii')) # New line after spinner
                                    first_chunk_received = True

                                chunk_text = chunk.text if hasattr(chunk, 'text') and chunk.text else ""
                                if chunk_text:
                                    full_response_text += chunk_text # Accumulate for history
                                    formatted_chunk = format_chunk(chunk_text)
                                    client_socket.send(formatted_chunk.encode('ascii', errors='ignore'))

                            # Add model response to history for Gemini
                            if full_response_text:
                                chat_history.append({'role': 'model', 'parts': [full_response_text]})


                        elif active_platform == 'openai' and openai_client:
                             # Add user message to history for OpenAI
                            chat_history.append({"role": "user", "content": prompt})
                             # Use stream=True for streaming response from OpenAI Chat Completions
                            stream = openai_client.chat.completions.create(
                                model=openai_client.model_name, # Use the configured OpenAI model name
                                messages=chat_history, # Pass the entire chat history
                                stream=True,
                            )
                            for chunk in stream:
                                if not first_chunk_received:
                                    # Stop spinner on first chunk
                                    stop_spinner.set()
                                    spinner_thread.join()
                                    client_socket.send("\r\n".encode('ascii')) # New line after spinner
                                    first_chunk_received = True

                                # OpenAI streaming chunks have text in delta.content
                                chunk_text = chunk.choices[0].delta.content if chunk.choices[0].delta and chunk.choices[0].delta.content else ""
                                if chunk_text:
                                    full_response_text += chunk_text # Accumulate for history
                                    formatted_chunk = format_chunk(chunk_text)
                                    client_socket.send(formatted_chunk.encode('ascii', errors='ignore'))

                            # Add assistant response to history for OpenAI
                            if full_response_text:
                                chat_history.append({"role": "assistant", "content": full_response_text})


                        elif active_platform == 'anthropic' and anthropic_client:
                            # Add user message to history for Anthropic
                            # Anthropic messages API expects alternating user/assistant roles.
                            # We'll build the messages list for the API call.
                            anthropic_messages = []
                            for msg in chat_history:
                                if msg['role'] == 'user':
                                     anthropic_messages.append({"role": "user", "content": msg['content']})
                                elif msg['role'] == 'assistant':
                                     anthropic_messages.append({"role": "assistant", "content": msg['content']})

                            # Add the current user prompt
                            anthropic_messages.append({"role": "user", "content": prompt})

                            # Use stream=True for streaming response from Anthropic Messages API
                            stream = anthropic_client.messages.create(
                                model=anthropic_client.model_name, # Use the configured Anthropic model name
                                max_tokens=4096, # Max tokens to sample (can also make this configurable)
                                messages=anthropic_messages, # Pass the messages list
                                stream=True,
                            )
                            for event in stream:
                                if event.type == "content_block_delta":
                                    if not first_chunk_received:
                                        # Stop spinner on first chunk
                                        stop_spinner.set()
                                        spinner_thread.join()
                                        client_socket.send("\r\n".encode('ascii')) # New line after spinner
                                        first_chunk_received = True

                                    # Anthropic streaming events have text in delta.text
                                    chunk_text = event.delta.text if event.delta and event.delta.text else ""
                                    if chunk_text:
                                        full_response_text += chunk_text # Accumulate for history
                                        formatted_chunk = format_chunk(chunk_text)
                                        client_socket.send(formatted_chunk.encode('ascii', errors='ignore'))
                                elif event.type == "message_stop":
                                    # Stream finished
                                    pass # No extra action needed, loop will end

                            # Add assistant response to history for Anthropic (using the same structure as OpenAI for simplicity)
                            if full_response_text:
                                chat_history.append({"role": "user", "content": prompt}) # Add the user prompt to internal history
                                chat_history.append({"role": "assistant", "content": full_response_text}) # Add the assistant response


                        else:
                             # This case should ideally not be reached if active_platform is set correctly
                             # but included as a fallback.
                             client_socket.send("\r\nError: No active AI platform configured.\r\n".encode('ascii', errors='ignore'))


                    except Exception as e:
                         # If an error occurs during streaming, stop spinner if it's still running
                         if not first_chunk_received:
                             stop_spinner.set()
                             spinner_thread.join()
                             client_socket.send(f"\r\nAI API Streaming Error ({active_platform.upper()}): {e}\r\n".encode('ascii', errors='ignore'))
                         else:
                             # If error after streaming started, just print it to server console
                             print(f"[*] AI API Streaming Error during stream ({active_platform.upper()}): {e}")


                    # --- Ensure spinner is stopped if no chunks were received (e.g., API error) ---
                    if not first_chunk_received:
                         stop_spinner.set()
                         spinner_thread.join()
                         # An error message should have been sent by the exception handler above
                    # --- End Spinner Stop Fallback ---

                    # Send the separator line and the next prompt
                    client_socket.send("\r\n-----\r\n".encode('ascii')) # Added separator
                    client_socket.send(f"Type your next prompt and press Enter twice:\r\n\r\n> ".encode('ascii')) # Added "> " here
                else:
                    # If prompt is empty after double enter, just prompt again
                    client_socket.send("\r\nType your prompt and press Enter twice:\r\n\r\n> ".encode('ascii')) # Added "> " here

            # If no signal was found, continue receiving data (implicit by the loop continuing)
            # --- End Corrected Input Signal Handling ---

    except Exception as e:
        print(f"[*] Error handling client: {e}")
    finally:
        print(f"[*] Client connection closed from {client_socket.getpeername()}")
        client_socket.close()

# --- Main Server Loop ---
def start_server():
    """Starts the TCP server to listen for connections."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow the socket to be reused immediately after closing
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(5) # Max queued connections

    print(f"[*] Listening on {SERVER_HOST}:{SERVER_PORT}")
    print("Press Ctrl+C to stop the server.")

    while True:
        try:
            client_socket, addr = server.accept()
            # Handle client connection in a new thread
            client_handler = threading.Thread(target=handle_client, args=(client_socket,))
            client_handler.start()
        except KeyboardInterrupt:
            print("\n[*] Server shutting down.")
            break
        except Exception as e:
            print(f"[*] Server error: {e}")

    server.close()

# --- Entry Point ---
if __name__ == "__main__":
    # The check for active_platform and sys.exit(1) is done during initialization
    # If we reach here, an active_platform is set.
    start_server()
