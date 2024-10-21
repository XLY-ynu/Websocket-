import asyncio
import websockets

# 存储所有连接的客户端及其昵称
connected_clients = {}

# 广播消息给所有连接的客户端
async def broadcast_message(message, sender_ws=None):
    if connected_clients:
        # 构建要发送消息的协程列表，排除发送者自身
        coroutines = [ws.send(message) for ws in connected_clients if ws != sender_ws]
        if coroutines:
            await asyncio.wait(coroutines)

# 发送消息给特定的客户端
async def send_private_message(message, recipient_nickname):
    for ws, nickname in connected_clients.items():
        if nickname == recipient_nickname:
            await ws.send(message)
            break

# 处理每个WebSocket客户端连接的逻辑
async def handle_client(websocket, path):
    try:
        # 接收客户端发送的昵称作为首次消息
        nickname = await websocket.recv()
        connected_clients[websocket] = nickname
        welcome_message = f"{nickname} 进入聊天室"
        print(welcome_message)
        
        # 启动心跳机制
        asyncio.ensure_future(heartbeat(websocket))

        async for message in websocket:
            # 判断是否为私聊消息
            if message.startswith("@"):
                # 提取目标昵称和实际消息
                split_message = message.split(" ", 1)
                if len(split_message) > 1:
                    target_nickname = split_message[0][1:]  # 去掉 '@'
                    actual_message = split_message[1]
                    formatted_message = f"[私聊]{connected_clients[websocket]} 对你说: {actual_message}"
                    # 发送私聊消息
                    await send_private_message(formatted_message, target_nickname)
            else:
                # 广播消息给其他客户端
                formatted_message = f"{connected_clients[websocket]}: {message}"
                await broadcast_message(formatted_message, sender_ws=websocket)
    except websockets.exceptions.ConnectionClosed as e:
        print(f"{connected_clients[websocket]} 已断开连接")
    finally:
        # 客户端断开连接，移除客户端
        if websocket in connected_clients:
            del connected_clients[websocket]

# 定期发送ping消息以维持连接
async def heartbeat(websocket, interval=30):
    while True:
        try:
            await websocket.ping()  # 发送ping消息，间隔时间可以调整
            await asyncio.sleep(interval)  # 休眠一定时间，保持心跳频率
        except websockets.exceptions.ConnectionClosed:
            break  # 如果连接关闭，退出心跳循环

# 启动WebSocket服务器
start_server = websockets.serve(handle_client, "0.0.0.0", 5678)  # 监听所有网络接口

# 运行服务器
asyncio.get_event_loop().run_until_complete(start_server)
print("服务器已启动...")
asyncio.get_event_loop().run_forever()
