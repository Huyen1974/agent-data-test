# Gemini CLI Usage Guide

## Quick Start

### Single Command (Recommended)
```bash
GOOGLE_GENAI_USE_GCA=true gemini -e none --extensions none -m gemini-2.5-pro
```

### Using Script
```bash
./tools/ai/gemini-start.sh
```

## Smoke Tests

### CLI One-shot Test
```bash
GOOGLE_GENAI_USE_GCA=true gemini -e none --extensions none -m gemini-2.5-pro -p "Reply with just: OK"
```
Expected output: `OK`

### Interactive Test
1. Start Gemini: `./tools/ai/gemini-start.sh`
2. Send message: `Reply with just: OK`
3. Expected response: `OK`

### Model Override Test
```bash
gemini -e none -m gemini-2.5-flash -p "Reply with just: OK"
```
Expected output: `OK`

## Error Handling

- **OAuth Required**: Complete browser login when prompted, then continue.
- **Rate Limits**: Verify `GOOGLE_GENAI_USE_GCA=true`, retry once. If persists, check quota/account.

## Safety Notes

- Only works on feature branches
- Asks approval for file edits and destructive commands
- No sandbox mode by default
