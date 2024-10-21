import asyncio
import websockets
import json

# 存储所有连接的客户端及其昵称
connected_clients = {}

# 广播消息给所有连接的客户端
async def broadcast_message(message, sender_ws=None):
    if connected_clients:
        coroutines = [ws.send(message) for ws in connected_clients if ws != sender_ws]
        if coroutines:
            await asyncio.wait(coroutines)

# 发送消息给特定的客户端
async def send_private_message(message, recipient_nickname):
    for ws, nickname in connected_clients.items():
        if nickname == recipient_nickname:
            await ws.send(message)
            break

# 定期发送心跳包
async def send_heartbeat():
    while True:
        if connected_clients:
            # 向所有连接的客户端发送心跳包
            coroutines = [ws.send(json.dumps({'type': 'ping'})) for ws in connected_clients]
            await asyncio.wait(coroutines)
        await asyncio.sleep(30)  # 每30秒发送一次心跳

# 处理每个WebSocket客户端连接的逻辑
async def handle_client(websocket, path):
    try:
        async for message in websocket:
            data = json.loads(message)

            if data['type'] == 'login':
                nickname = data['nickname']
                connected_clients[websocket] = nickname
                welcome_message = f"{nickname} 进入聊天室"
                print(welcome_message)
            elif data['type'] == 'message':
                sender_nickname = connected_clients[websocket]
                content = data['content']

                if data.get('private'):
                    recipient_nickname = data['recipient']
                    formatted_message = {
                        'type': 'message',
                        'content': f"[私聊]{sender_nickname} 对你说: {content}",
                        'sender': sender_nickname,
                        'private': True
                    }
                    await send_private_message(json.dumps(formatted_message), recipient_nickname)
                else:
                    formatted_message = {
                        'type': 'message',
                        'content': content,
                        'sender': sender_nickname
                    }
                    await broadcast_message(json.dumps(formatted_message), sender_ws=websocket)
            elif data['type'] == 'file':
                sender_nickname = connected_clients[websocket]
                file_name = data['fileName']
                file_data = data['fileData']

                if data.get('private'):
                    recipient_nickname = data['recipient']
                    formatted_message = {
                        'type': 'file',
                        'fileName': file_name,
                        'fileData': file_data,
                        'sender': sender_nickname,
                        'private': True
                    }
                    await send_private_message(json.dumps(formatted_message), recipient_nickname)
                else:
                    formatted_message = {
                        'type': 'file',
                        'fileName': file_name,
                        'fileData': file_data,
                        'sender': sender_nickname
                    }
                    await broadcast_message(json.dumps(formatted_message), sender_ws=websocket)
            elif data['type'] == 'pong':
                # 客户端回应心跳，表示连接正常
                pass
    except websockets.exceptions.ConnectionClosed as e:
        if websocket in connected_clients:
            print(f"{connected_clients[websocket]} 已断开连接")
    finally:
        # 客户端断开连接，移除客户端
        if websocket in connected_clients:
            del connected_clients[websocket]

# 启动WebSocket服务器
start_server = websockets.serve(handle_client, "0.0.0.0", 5678)

# 运行服务器并启动心跳任务
loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)
loop.create_task(send_heartbeat())  # 启动心跳发送任务
print("服务器已启动...")
loop.run_forever()
