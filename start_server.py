import socket
import threading
import json
import textwrap # Useful for wrapping long lines
import google.generativeai as genai # Import the Google Generative AI library
import re # Import regular expressions for more robust whitespace handling
import os # Import the os module to access environment variables
import time # Import time for the spinner animation delay

# --- Configuration ---
# Replace with the IP address of the computer running this script.
# Use '0.0.0.0' to listen on all available interfaces.
SERVER_HOST = '0.0.0.0'
# The port the server will listen on.
SERVER_PORT = 2323
BUFFER_SIZE = 4096 # Buffer size for receiving data

# Your Google AI API key (for Gemini)
# IMPORTANT: This is read from the GEMINI_API_KEY environment variable.
# Make sure to set this environment variable before running the script.
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- Initialize Gemini ---
model = None # Initialize model to None
if GEMINI_API_KEY is None:
    print("!!! IMPORTANT: GEMINI_API_KEY environment variable not set.")
    print("!!! Please set the GEMINI_API_KEY environment variable before running the script.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Choose the specified model
        model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
        print(f"[*] Gemini model 'gemini-2.5-flash-preview-04-17' configured successfully.")
    except Exception as e:
        print(f"!!! Failed to configure Google Generative AI: {e}")
        print("!!! Please ensure your API key is correct and you have network access.")
        model = None # Ensure model is None if configuration fails

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
    formatted_chunk = text_chunk.replace('**', '').replace('*', '') # Remove bold/italic markers
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
    """Handles a single client connection."""
    print(f"[*] Accepted connection from {client_socket.getpeername()}")

    try:
        # Send a welcome message
        welcome_message = "Vintage Mac Gemini Gateway\r\nType your prompt and press Enter twice to send:\r\n\r\n> "
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
                # Remove the "> " from the start of the actual prompt
                prompt = input_buffer[:end_index].strip()
                if prompt.startswith('> '):
                    prompt = prompt[2:]
                newline_sequence_len = 4 # Length of '\r\n\r\n'
            elif end_index_lf != -1:
                # Found LF LF
                end_index = end_index_lf
                 # Remove the "> " from the start of the actual prompt
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

                    # --- Get and Stream Response from Gemini ---
                    first_chunk_received = False
                    try:
                        # Use stream=True to get a streaming response
                        streamed_response = model.generate_content(prompt, stream=True)
                      
                        for chunk in streamed_response:
                            if not first_chunk_received:
                                # --- Stop Spinner Animation on First Chunk ---
                                stop_spinner.set() # Signal the spinner thread to stop
                                spinner_thread.join() # Wait for the spinner thread to finish
                                # The spin_animation function will send ' \b' to clear the last spinner char
                                # --- End Stop Spinner Animation ---
                                first_chunk_received = True
                                # Send a newline after clearing the spinner to start the response on a new line
                                client_socket.send("\r\n".encode('ascii'))

                            # Get the text from the chunk
                            chunk_text = chunk.text if hasattr(chunk, 'text') and chunk.text else ""

                            if chunk_text:
                                # Format the chunk and send it
                                formatted_chunk = format_chunk(chunk_text)
                                client_socket.send(formatted_chunk.encode('ascii', errors='ignore'))

                    except Exception as e:
                         # If an error occurs during streaming, stop spinner if it's still running
                         if not first_chunk_received:
                             stop_spinner.set()
                             spinner_thread.join()
                             client_socket.send(f"\r\nGemini API Streaming Error: {e}\r\n".encode('ascii', errors='ignore'))
                         else:
                             # If error after streaming started, just print it to server console
                             print(f"[*] Gemini API Streaming Error during stream: {e}")


                    # --- Ensure spinner is stopped if no chunks were received (e.g., API error) ---
                    if not first_chunk_received:
                         stop_spinner.set()
                         spinner_thread.join()
                         # An error message should have been sent by the exception handler above
                    # --- End Spinner Stop Fallback ---

                    # Send the separator line and the next prompt
                    client_socket.send("\r\n-----\r\n".encode('ascii')) # Added separator
                    client_socket.send("Type your next prompt and press Enter twice:\r\n\r\n> ".encode('ascii')) # Added "> " here
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
    # Check if the model was initialized successfully before starting the server
    if model is not None:
        start_server()
    else:
        print("Server not started due to Gemini API configuration error (API key not set or configuration failed).")
