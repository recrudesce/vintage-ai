# vintage-ai
Telnet to AI bridge

## Gemini
- First set the GEMINI_API_KEY to be your Google AI Studio API key
- Install the Gemini library `pip install google-generativeai`
- Run the server with `python3 ./start_server.py gemini`

## OpenAI
- First set the OPENAI_API_KEY to be your OpenAI API key
- Install the OpenAI library `pip install openai`
- Run the server with `python3 ./start_server.py openai`

## Anthropic Claude
- First set the ANTHROPIC_API_KEY to be your OpenAI API key
- Install the Anthropic library `pip install anthropic`
- Run the server with `python3 ./start_server.py anthropic`


Then connect to it from whatever telnet client you want to use (it runs on port 2323).

Double enter sends the prompt.

See here for a video of it working: https://bsky.app/profile/did:plc:xt3aino56gwrypmn2ovfmg3a/post/3lott7mkcwc2f
