# vintage-ai
Telnet to AI bridge

![vintage-ai](https://github.com/user-attachments/assets/2947a16a-ef78-4bdb-9b89-c363086c0264)

## Running Locally
Ensure that any of these AI providers are installed:

- `google-genai` for Google Gemini models
- `openai` for OpenAI models
- `anthropic` for Anthropic Claude models

Set the `AI_PLATFORM` environment variable to either `gemini`, `openai`, or `anthropic`.  It will default to `gemini` if not set.

Set the `AI_MODEL` environment variable to be the model name you want to use.  e.g `o4-mini` or `gemini-2.0-flash`. 

If this is not set, Gemini will default to `gemini-2.0-flash`, OpenAI will default to `gpt-4o-mini`, and Anthropic will default to `claude-3-5-sonnet-latest`

### Gemini
- First set the `GEMINI_API_KEY` environment variable to be your Google AI Studio API key
- Install the Gemini library `pip install google-genai`

### OpenAI Compatible API's (OpenAI, Ollama, vLLM etc)
- First set the `OPENAI_API_KEY` environment variable to be your OpenAI/Ollama/whatever API key
- IF you want to use Ollama/vLLM/any other OpenAI compatible API, set the `OPENAI_BASE_URL` environment variable to the relevant base URL for your provider. You WILL need to set the `AI_MODEL` environment variable if you do this, else it can't default to an OpenAI model.
- Install the OpenAI library `pip install openai`

### Anthropic Claude
- First set the `ANTHROPIC_API_KEY` environment variable to be your Anthropic API key
- Install the Anthropic library `pip install anthropic`

Run the server with `python3 ./start_server.py` then connect to it from whatever telnet client you want to use (it runs on port 2323).

## Performance & Memory Management

The server has been optimized for efficiency and includes:

- **Memory management**: Chat history is automatically limited to 50 messages per connection to prevent memory leaks
- **Improved threading**: Proper cleanup of spinner animation threads with timeout handling
- **Optimized text processing**: Pre-compiled regex patterns for better performance
- **Unified streaming**: Single codebase handles all AI platforms efficiently
- **Clean shutdown**: Daemon threads allow graceful server termination

## Docker
This can be run via docker, if you so wanted.  Edit the `docker-compose.yml` as per the instructions within, setting the relevant API keys and AI platform to use etc.
Then run `docker compose up -d` to start the container.
Connect to it on port 2323 from your telnet/bbs client.

## Commands

The server now supports runtime commands:

- `/model <name>` - Change AI model during your session (e.g. `/model gpt-4o`, `/model claude-3-5-sonnet-20241022`)
- `/status` - Show current platform, model, and chat history count
- `/help` - Display available commands

## Other Things to Know
Double enter sends what you've typed.  This allows you to send multi-line prompts.

See here for a video of it working: https://bsky.app/profile/did:plc:xt3aino56gwrypmn2ovfmg3a/post/3lott7mkcwc2f

