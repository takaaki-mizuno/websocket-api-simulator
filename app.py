import logging

import asyncio
import json
import os
import uuid
from aiohttp import web, ClientSession, ClientTimeout
from aiohttp import WSMsgType, WSMessage


logging.basicConfig(level=logging.DEBUG)

connections = {}


async def handle_websocket(request):
    logger = logging.getLogger("aiohttp.server")

    logger.info("Websocket connection starting")
    websocket = web.WebSocketResponse()
    await websocket.prepare(request)
    logger.info("Websocket connection ready")

    connection_id = str(uuid.uuid4())
    connections[connection_id] = websocket

    logger.info(f"New connection: {connection_id}")

    try:
        await handle_route('$connect', connection_id)

        message: WSMessage
        async for message in websocket:
            # convert binary message.type to hex
            _type = message.type.to_bytes(1, byteorder='big').hex()
            logger.info(f"Message received ::: {_type}")
            if message.type == WSMsgType.TEXT:
                await handle_route('$default', connection_id, message.data)
            elif message.type == WSMsgType.ERROR:
                logger.error(f"WebSocket connection closed with exception {websocket.exception()}")
                break
            elif message.type == WSMsgType.CLOSE:
                logger.info(f"WebSocket closed by client: {connection_id}")
                break

    except Exception as e:
        logger.error(f"Unexpected error in WebSocket handler: {str(e)}")

    finally:
        logger.info(f"Connection closed: {connection_id}")
        del connections[connection_id]
        await handle_route('$disconnect', connection_id)

    logger.info("loop ended")

    return websocket


async def handle_route(route, connection_id, body=''):
    url = os.environ.get(f'{route.upper().replace("$", "")}_ROUTE')
    if not url:
        print(f"No route defined for {route}")
        return

    headers = {
        'Content-Type': 'application/json',
        'connectionId': connection_id
    }

    try:
        async with ClientSession(timeout=ClientTimeout(total=5)) as session:
            async with session.post(url, data=body, headers=headers) as response:
                if response.status >= 400:
                    print(f"Error calling {route} handler: {response.status}")
                    return

                response_body = await response.text()
                if response_body:
                    try:
                        response_data = json.loads(response_body)
                        if 'body' in response_data:
                            await send_message_to_client(connection_id, response_data['body'])
                    except json.JSONDecodeError:
                        print(f"Invalid JSON response from {route} handler")
    except asyncio.TimeoutError:
        print(f"Timeout calling {route} handler")
    except Exception as e:
        print(f"Error calling {route} handler: {str(e)}")


async def send_message_to_client(connection_id, message):
    if connection_id in connections:
        await connections[connection_id].send_str(json.dumps(message))


async def send_message(request):
    logger = logging.getLogger("aiohttp.server")
    logger.info("Sending message")

    data = await request.json()
    connection_id = data.get('connectionId')
    message = data.get('data')

    if not connection_id or not message:
        return web.Response(status=400, text="Invalid request. Both connectionId and data are required.")

    if connection_id not in connections:
        return web.Response(status=410, text="Invalid connectionId")

    try:
        await send_message_to_client(connection_id, message)
        return web.Response(text="Message sent", status=200)
    except Exception as e:
        return web.Response(status=500, text=f"Failed to send message: {str(e)}")


def main():
    app = web.Application()
    app.router.add_get('/ws', handle_websocket)
    app.router.add_post('/@connections/{connectionId}', send_message)
    port = int(os.environ.get('PORT', 8180))
    print(f"Starting server on port {port}")
    web.run_app(app, port=port)


if __name__ == '__main__':
    main()
