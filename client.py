import socket
import threading

def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode()  # 接收服务器的消息
            if not message:
                break  # 如果消息为空，说明连接关闭
            # 检查消息是否为昵称提示
            if "请输入你的昵称" not in message:
                print(message)  # 只有当消息不是昵称提示时才打印
        except:
            break  # 出现错误时断开连接


# 创建客户端 socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP连接
client_socket.connect(('10.103.195.45', 12345))  # 连接到服务器

# 接收服务器请求输入昵称
nickname = input("请输入你的昵称: ")
client_socket.send(nickname.encode())  # 发送昵称给服务器

# 创建线程处理接收服务器消息
receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
receive_thread.start()  # 启动线程

# 主线程处理发送消息
while True:
    message = input()  # 输入要发送的消息
    if message.lower() == 'exit':  # 用户输入 'exit' 退出
        break
    client_socket.send(message.encode())  # 发送消息给服务器

client_socket.close()  # 关闭客户端 socket
