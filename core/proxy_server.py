import uuid
import time
import json
import sys
from aiohttp import web, ClientSession

from core.redaction import redact_text
from core.security import load_config

COLOR_TEAL = "\033[38;5;38m"
COLOR_BOLD = "\033[1m"
COLOR_GRAY = "\033[38;5;244m"
COLOR_RESET = "\033[0m"


async def ollama_to_openai_sse_stream(response_stream, model, request_id):
    async for line_bytes in response_stream:
        if not line_bytes:
            continue

        line = line_bytes.decode("utf-8").strip()
        if not line:
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        content = data.get("response", "")

        if content:
            timestamp = int(time.time())
            escaped_content = json.dumps(content)
            yield (
                f'data: {{"id":"{request_id}","object":"chat.completion.chunk",'
                f'"created":{timestamp},"model":"{model}",'
                f'"choices":[{{"index":0,"delta":{{"content":{escaped_content}}}}}]}}\n\n'
            )

        if data.get("done"):
            yield "data: [DONE]\n\n"
            break


def _build_context_from_messages(messages):
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


async def handle_chat_completions(request: web.Request):
    ollama_host = request.app["ollama_host"]
    default_model = request.app["default_model"]

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    messages = body.get("messages", [])
    model = body.get("model", default_model)
    stream = body.get("stream", False)

    prompt = _build_context_from_messages(messages)
    prompt = redact_text(prompt)

    request_id = f"chatcmpl-{uuid.uuid4().hex}"

    ollama_payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
    }

    async with ClientSession() as session:
        async with session.post(f"{ollama_host}/api/generate", json=ollama_payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                return web.json_response(
                    {"error": f"Ollama error: {error_text}"}, status=resp.status
                )

            if stream:
                response = web.StreamResponse(
                    status=200,
                    reason="OK",
                    headers={
                        "Content-Type": "text/event-stream",
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    },
                )
                await response.prepare(request)

                async for sse_chunk in ollama_to_openai_sse_stream(
                    resp.content, model, request_id
                ):
                    await response.write(sse_chunk.encode("utf-8"))

                return response

            else:
                full_text = ""
                async for line_bytes in resp.content:
                    if line_bytes:
                        line_data = json.loads(line_bytes.decode("utf-8"))
                        full_text += line_data.get("response", "")

                openai_response = {
                    "id": request_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": full_text},
                            "finish_reason": "stop",
                        }
                    ],
                }
                return web.json_response(openai_response)


async def handle_models(request: web.Request):
    ollama_host = request.app["ollama_host"]

    async with ClientSession() as session:
        async with session.get(f"{ollama_host}/api/tags") as resp:
            if resp.status != 200:
                return web.json_response(
                    {"error": "Failed to fetch Ollama models"}, status=resp.status
                )

            ollama_data = await resp.json()
            openai_models = []

            for model in ollama_data.get("models", []):
                openai_models.append(
                    {
                        "id": model.get("name"),
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "ollama-local",
                    }
                )

            return web.json_response({"object": "list", "data": openai_models})


def create_app():
    config = load_config()
    app = web.Application()
    app["ollama_host"] = config.get("ollama_url", "http://localhost:11434")
    app["default_model"] = config.get("models", {}).get("coder", "qwen3.5:9b")
    app.add_routes(
        [
            web.post("/v1/chat/completions", handle_chat_completions),
            web.get("/v1/models", handle_models),
        ]
    )
    return app


def run_server(host="127.0.0.1", port=11435):
    print(
        f"{COLOR_TEAL}{COLOR_BOLD}TaigaAI Secure Proxy Server{COLOR_RESET}",
        file=sys.stderr,
    )
    print(
        f"{COLOR_GRAY}Listening on http://{host}:{port}{COLOR_RESET}", file=sys.stderr
    )
    print(
        f"{COLOR_GRAY}OpenAI-compatible endpoint: http://{host}:{port}/v1{COLOR_RESET}",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    app = create_app()
    web.run_app(app, host=host, port=port)
