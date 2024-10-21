import socket
import threading

clients = {}  # 存储客户端的昵称和socket的映射关系


# 广播消息给所有客户端
def broadcast_message(message, exclude_socket=None):
    for client_socket in clients.values():
        if client_socket != exclude_socket:  # 排除发送消息的客户端
            try:
                client_socket.send(message.encode())
            except:
                client_socket.close()


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


start_server()
