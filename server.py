import socket
import threading
import asyncio
import websockets

clients = {}  # 存储客户端的昵称和socket的映射关系
web_clients = set()  # 存储网页客户端的 WebSocket 连接


# 广播消息给所有普通客户端和网页
def broadcast_message(message, exclude_socket=None):
    # 发送给socket客户端
    for client_socket in clients.values():
        if client_socket != exclude_socket:  # 排除发送消息的客户端
            try:
                client_socket.send(message.encode())
            except:
                client_socket.close()
    # 发送给WebSocket客户端（网页）
    asyncio.run(broadcast_to_web_clients(message))


# 私聊消息发送
def private_message(message, nickname):
    recipient_socket = clients.get(nickname)
    if recipient_socket:
        try:
            recipient_socket.send(message.encode())
        except:
            recipient_socket.close()


# 处理每个客户端的连接
def handle_client(client_socket):
    # 获取客户端昵称
    client_socket.send("请输入你的昵称: ".encode())
    nickname = client_socket.recv(1024).decode()

    # 广播通知其他用户
    welcome_message = f"{nickname} 加入了聊天室！"
    print(welcome_message)
    broadcast_message(welcome_message, exclude_socket=client_socket)

    # 将客户端昵称和socket映射保存
    clients[nickname] = client_socket

    # 接收客户端消息的循环
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break
            if message.startswith('@'):  # 检查是否为私聊消息
                try:
                    target_nickname, private_msg = message[1:].split(' ', 1)  # 提取目标昵称和私聊消息
                    private_message(f"[私聊] {nickname}: {private_msg}", target_nickname)
                except ValueError:
                    client_socket.send("私聊格式错误，请使用 '@昵称 消息内容' 的格式。\n".encode())
            else:
                broadcast_message(f"{nickname}: {message}", exclude_socket=client_socket)
        except:
            break

    # 客户端断开连接
    client_socket.close()
    del clients[nickname]
    broadcast_message(f"{nickname} 离开了聊天室。")


# WebSocket广播
async def broadcast_to_web_clients(message):
    if web_clients:
        await asyncio.wait([client.send(message) for client in web_clients])


# WebSocket 处理器，处理来自网页的连接
async def handle_websocket(websocket, path):
    web_clients.add(websocket)
    try:
        while True:
            await websocket.recv()  # 暂时不处理网页发来的消息
    except:
        pass
    finally:
        web_clients.remove(websocket)


# 创建服务器
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 12345))
    server_socket.listen(5)
    print("服务器已启动，等待客户端连接...")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"客户端 {client_address} 已连接")

        # 为每个客户端启动一个新线程
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()


# 启动 WebSocket 服务器
def start_websocket_server():
    start_server_task = websockets.serve(handle_websocket, "127.0.0.1", 5678)
    asyncio.get_event_loop().run_until_complete(start_server_task)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    # 启动socket聊天服务器
    threading.Thread(target=start_server).start()
    # 启动 WebSocket 服务器以和网页通信
    start_websocket_server()
