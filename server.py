import asyncio
import websockets

# 存储所有连接的客户端
connected_clients = set()

# 广播消息给所有连接的客户端
async def broadcast_message(message):
    if connected_clients:  # 如果有连接的客户端
        await asyncio.wait([client.send(message) for client in connected_clients])

# 处理每个WebSocket客户端连接的逻辑
async def handle_client(websocket, path):
    # 添加新连接的客户端
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            # 广播消息给其他客户端
            await broadcast_message(message)
    except websockets.exceptions.ConnectionClosed as e:
        print(f"客户端断开连接: {e}")
    finally:
        # 客户端断开连接，移除客户端
        connected_clients.remove(websocket)

# 启动WebSocket服务器
start_server = websockets.serve(handle_client, "0.0.0.0", 5678)  # 监听所有网络接口

# 运行服务器
asyncio.get_event_loop().run_until_complete(start_server)
print("服务器已启动...")
asyncio.get_event_loop().run_forever()
