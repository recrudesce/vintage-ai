# vintage-ai
Telnet to AI bridge

Set the `AI_PLATFORM` environment variable to either `gemini`, `openai`, or `anthropic`.  It will default to `gemini` if not set.

Set the `AI_MODEL` environment variable to be the model name you want to use.  e.g `o4-mini` or `gemini-2.0-flash`
If this is not set, Gemini will default to `gemini-2.0-flash`, OpenAI will default to `gpt-4o-mini`, and Anthropic will default to `claude-3-5-sonnet-latest`

## Gemini
- First set the GEMINI_API_KEY environment variable to be your Google AI Studio API key
- Install the Gemini library `pip install google-generativeai`
- Run the server with `python3 ./start_server.py`

## OpenAI
- First set the OPENAI_API_KEY environment variable to be your OpenAI API key
- Install the OpenAI library `pip install openai`
- Run the server with `python3 ./start_server.py`

## Anthropic Claude
- First set the ANTHROPIC_API_KEY environment variable to be your OpenAI API key
- Install the Anthropic library `pip install anthropic`


Run the server with `python3 ./start_server.py` then connect to it from whatever telnet client you want to use (it runs on port 2323).

Double enter sends the prompt.

See here for a video of it working: https://bsky.app/profile/did:plc:xt3aino56gwrypmn2ovfmg3a/post/3lott7mkcwc2f
