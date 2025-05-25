# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vintage AI is a Telnet-to-AI bridge server that allows users to interact with various AI models (Gemini, OpenAI, Anthropic) through a vintage terminal interface. The server runs on port 2323 and handles multiple concurrent connections with chat history.

## Running the Server

Start the server with:
```bash
python3 start_server.py
```

Or with Docker:
```bash
docker compose up -d
```

## Required Environment Variables

Set one of these AI platform configurations:

**For Gemini (default):**
```bash
export AI_PLATFORM=gemini
export GEMINI_API_KEY=your_key_here
export AI_MODEL=gemini-2.0-flash  # optional, default is gemini-2.0-flash
```

**For OpenAI:**
```bash
export AI_PLATFORM=openai
export OPENAI_API_KEY=your_key_here
export AI_MODEL=gpt-4o-mini  # optional, default is gpt-4o-mini
export OPENAI_BASE_URL=http://localhost:1234/v1  # optional, for custom endpoints
```

**For Anthropic:**
```bash
export AI_PLATFORM=anthropic
export ANTHROPIC_API_KEY=your_key_here
export AI_MODEL=claude-3-5-sonnet-latest  # optional, default is claude-3-5-sonnet-latest
```

## Architecture

The main application is a single-file server (`start_server.py`) built with a class-based architecture:

**Core Classes:**
- `AIClientManager`: Handles AI platform initialization, configuration, and model switching
- `SpinnerManager`: Manages spinner animation threads with proper cleanup
- `handle_client()`: Per-connection handler with chat history and command processing
- `stream_ai_response()`: Unified streaming function for all AI platforms

**Key Features:**
1. **Platform Detection**: Dynamically imports and configures AI platform libraries based on `AI_PLATFORM` environment variable
2. **Socket Server**: Listens on port 2323 for Telnet connections
3. **Threading**: Handles each client connection in a separate daemon thread with persistent chat history
4. **Streaming**: Implements real-time streaming responses with spinner animation
5. **Protocol**: Uses double Enter (`\r\n\r\n` or `\n\n`) as the send signal for multi-line prompts
6. **Runtime Commands**: Supports `/model`, `/status`, `/help` commands during sessions
7. **Memory Management**: Chat history limited to 50 messages per connection to prevent memory leaks

**Performance Optimizations:**
- Pre-compiled regex patterns for text formatting
- StringIO for efficient buffer management
- Unified streaming logic eliminates code duplication
- Proper thread cleanup with timeouts
- Type hints for better code maintainability

## Dependencies

Install AI platform libraries as needed:
```bash
pip install google-genai     # For Gemini
pip install openai          # For OpenAI/Ollama/vLLM
pip install anthropic       # For Anthropic Claude
```

## Connection Protocol

Clients connect via Telnet on port 2323. The protocol supports:

**Input:**
- Multi-line prompts ending with double Enter
- Runtime commands starting with `/` (e.g., `/model gpt-4o`, `/status`, `/help`)

**Output:**
- Text responses formatted for vintage terminals (CRLF line endings)
- Spinner animation during AI processing
- Command responses and status information

**Session Management:**
- Chat history maintained per connection (max 50 messages)
- Model switching during runtime with `/model` command
- Graceful handling of connection cleanup

## Important Notes for Development

- **Gemini Chat History**: The new Google Gen AI SDK manages history server-side but doesn't expose it client-side, so we track messages locally for status reporting
- **Memory Limits**: Chat history is capped at 50 messages per connection via `limit_chat_history()` function
- **Threading**: All client threads are daemon threads for clean shutdown
- **Error Handling**: All platforms have consistent error handling with fallback behavior