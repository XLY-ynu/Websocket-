import asyncio
import websockets
import json
import mysql.connector
from datetime import datetime
import time
import base64

# 存储所有连接的客户端及其昵称
connected_clients = {}

# 为每个客户端维护最后一次收到 pong 的时间
last_pong_times = {}

# 创建 MySQL 连接
db_connection = mysql.connector.connect(
    host="localhost",
    user="root",  # 替换为你的 MySQL 用户名
    password="xlyjiayoua666.",  # 替换为你的 MySQL 密码
    database="chatroom"
)

# 安全发送消息，处理断开连接的客户端
async def safe_send(ws, message):
    try:
        await ws.send(message)
    except websockets.exceptions.ConnectionClosed:
        nickname = connected_clients.get(ws)
        if nickname:
            print(f"{nickname} 已断开连接")
            del connected_clients[ws]
            # 广播更新后的用户列表
            await broadcast_user_list()
    except Exception as e:
        print(f"发送消息时出错: {e}")

# 广播消息给所有连接的客户端
async def broadcast_message(message, sender_ws=None):
    if connected_clients:
        for ws in list(connected_clients):  # 使用列表副本以避免在迭代时修改字典
            if ws != sender_ws:
                await safe_send(ws, message)

# 发送消息给特定的客户端
async def send_private_message(message, recipient_nickname):
    for ws, nickname in connected_clients.items():
        if nickname == recipient_nickname:
            await safe_send(ws, message)
            break

# 保存聊天记录到数据库
def save_message_to_db(sender, message, recipient=None, is_private=False):
    cursor = db_connection.cursor()
    query = """
    INSERT INTO messages (sender, message, recipient, is_private)
    VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (sender, message, recipient, is_private))
    db_connection.commit()
    cursor.close()

# 获取聊天历史记录，分开处理公共和私聊消息
def get_chat_history(nickname=None, include_private=False):
    cursor = db_connection.cursor(dictionary=True)
    
    # 获取公共消息（所有人可见）
    public_query = """
        SELECT sender, message, timestamp FROM messages 
        WHERE is_private = FALSE 
        ORDER BY timestamp ASC
    """
    cursor.execute(public_query)
    public_messages = cursor.fetchall()

    private_messages = []
    if include_private and nickname:
        # 获取与该用户相关的私聊消息
        private_query = """
            SELECT sender, message, recipient, timestamp, is_private FROM messages 
            WHERE is_private = TRUE AND (recipient = %s OR sender = %s)
            ORDER BY timestamp ASC
        """
        cursor.execute(private_query, (nickname, nickname))
        private_messages = cursor.fetchall()

    cursor.close()
    
    # 返回分开的公共和私聊消息
    return public_messages, private_messages

# 广播在线用户列表
async def broadcast_user_list():
    if connected_clients:
        user_list = [nickname for ws, nickname in connected_clients.items()]
        user_list_message = {
            'type': 'user_list',
            'users': user_list
        }
        for ws in list(connected_clients):
            await safe_send(ws, json.dumps(user_list_message))

# 保存文件到数据库
def save_file_to_db(file_name, file_data, sender, recipient=None, is_private=False):
    cursor = db_connection.cursor()
    query = """
    INSERT INTO files (file_name, file_data, sender, recipient, is_private)
    VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (file_name, file_data, sender, recipient, is_private))
    db_connection.commit()
    cursor.close()

def get_file_history(nickname=None, include_private=False):
    cursor = db_connection.cursor(dictionary=True)
    
    # 获取公共文件
    public_files_query = """
        SELECT file_name, file_data, sender, timestamp FROM files 
        WHERE is_private = FALSE 
        ORDER BY timestamp ASC
    """
    cursor.execute(public_files_query)
    public_files = cursor.fetchall()

    private_files = []
    if include_private and nickname:
        # 获取与该用户相关的私聊文件
        private_files_query = """
            SELECT file_name, file_data, sender, recipient, timestamp, is_private FROM files 
            WHERE is_private = TRUE AND (recipient = %s OR sender = %s)
            ORDER BY timestamp ASC
        """
        cursor.execute(private_files_query, (nickname, nickname))
        private_files = cursor.fetchall()

    cursor.close()
    return public_files, private_files


async def send_heartbeat():
    """定期向所有客户端发送心跳包，并检测超时的客户端。"""
    while True:
        current_time = time.time()
        disconnected_clients = []

        for ws in list(connected_clients):
            try:
                # 向客户端发送 ping 消息
                await ws.send(json.dumps({'type': 'ping'}))
            except websockets.exceptions.ConnectionClosed:
                # 如果发送失败，说明客户端已断开连接
                nickname = connected_clients.get(ws)
                if nickname:
                    print(f"{nickname} 已断开连接")
                    disconnected_clients.append(ws)
            else:  # 发送ping成功的情况
                # 检查客户端是否超时（例如，超过10秒未发送 pong）
                last_pong = last_pong_times.get(ws)
                if last_pong is not None and current_time - last_pong > 15:
                    nickname = connected_clients.get(ws)
                    if nickname:
                        print(f"{nickname} 已超时断开")
                        disconnected_clients.append(ws)

        # 移除已断开的客户端
        for ws in disconnected_clients:
            if ws in connected_clients:
                del connected_clients[ws]
            if ws in last_pong_times:
                del last_pong_times[ws]

        # 如果有客户端断开，广播更新后的用户列表
        if disconnected_clients:
            await broadcast_user_list()

        # 等待指定的心跳间隔时间（例如，每5秒发送一次心跳）
        await asyncio.sleep(5)

# 获取聊天历史记录并添加时间戳字段
def get_combined_chat_history(nickname=None, include_private=False):
    public_chat_history, private_chat_history = get_chat_history(nickname=nickname, include_private=include_private)
    public_files, private_files = get_file_history(nickname=nickname, include_private=include_private)

    combined_history = []

    # 添加公共消息
    for msg in public_chat_history:
        combined_history.append({
            'type': 'message',
            'content': msg['message'],
            'sender': msg['sender'],
            'timestamp': msg['timestamp'],
            'is_private': False
        })

    # 添加私聊消息
    for msg in private_chat_history:
        if msg['recipient'] == nickname or msg['sender'] == nickname:
            combined_history.append({
                'type': 'message',
                'content': msg['message'],
                'sender': msg['sender'],
                'timestamp': msg['timestamp'],
                'is_private': True,
                'recipient': msg['recipient']
            })

    # 添加公共文件
    for file in public_files:
        file_data_uri = 'data:;base64,' + base64.b64encode(file['file_data']).decode()
        combined_history.append({
            'type': 'file',
            'fileName': file['file_name'],
            'fileData': file_data_uri,
            'sender': file['sender'],
            'timestamp': file['timestamp'],
            'is_private': False
        })

    # 添加私聊文件
    for file in private_files:
        file_data_uri = 'data:;base64,' + base64.b64encode(file['file_data']).decode()
        if file['recipient'] == nickname or file['sender'] == nickname:
            combined_history.append({
                'type': 'file',
                'fileName': file['file_name'],
                'fileData': file_data_uri,
                'sender': file['sender'],
                'timestamp': file['timestamp'],
                'is_private': True,
                'recipient': file['recipient']
            })

    # 根据 timestamp 排序
    combined_history.sort(key=lambda x: x['timestamp'])

    return combined_history


# 处理每个WebSocket客户端连接的逻辑
async def handle_client(websocket, path):
    try:
        last_pong_times[websocket] = time.time()

        async for message in websocket:  # for循环——服务器持续监听客户端发送的消息
            data = json.loads(message)  # 将json格式的message转换为字典形式的data

            if data['type'] == 'login':  # 登录时服务器反应
                nickname = data['nickname']
                connected_clients[websocket] = nickname  # websocket表示当前正在连接的客户端
                welcome_message = f"{nickname} 进入聊天室"
                print(welcome_message)   # 输出至终端

                # 广播新的在线用户列表（用于显示在聊天室中）？？？
                await broadcast_user_list()  

                # 获取公共和私聊聊天记录 ？？？
                combined_history = get_combined_chat_history(nickname=nickname, include_private=True)

                 # 发送历史记录
                for record in combined_history:
                    record['timestamp'] = record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    await safe_send(websocket, json.dumps(record))

            elif data['type'] == 'message':
                sender_nickname = connected_clients[websocket]
                content = data['content']

                if data.get('private'):
                    # 私聊信息格式化！！！
                    recipient_nickname = data['recipient']
                    formatted_message = {
                        'type': 'message',
                        'content': f"{content}",
                        'sender': sender_nickname,
                        'private': True
                    }
                    # 单独转发给接收方
                    await send_private_message(json.dumps(formatted_message), recipient_nickname)

                    # 保存私聊消息到数据库
                    save_message_to_db(sender_nickname, content, recipient=recipient_nickname, is_private=True)
                    
                else:
                    formatted_message = {
                        'type': 'message',
                        'content': content,
                        'sender': sender_nickname,
                        'is_private': False
                    }
                    # 广播转发除了自己的用户端
                    await broadcast_message(json.dumps(formatted_message), sender_ws=websocket)

                    # 保存公开消息到数据库
                    save_message_to_db(sender_nickname, content)
            
            elif data['type'] == 'file':
                sender_nickname = connected_clients[websocket]
                file_name = data['fileName']
                file_data = data['fileData']

                # 将文件数据从 base64 解码为二进制数据
                binary_file_data = base64.b64decode(file_data.split(',')[1])  # 假设 dataURI 格式的数据

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

                    # 保存私聊文件到数据库
                    save_file_to_db(file_name, binary_file_data, sender_nickname, recipient=recipient_nickname, is_private=True)
                else:
                    formatted_message = {
                        'type': 'file',
                        'fileName': file_name,
                        'fileData': file_data,
                        'sender': sender_nickname
                    }
                    await broadcast_message(json.dumps(formatted_message), sender_ws=websocket)
                    
                    # 保存公开文件到数据库
                    save_file_to_db(file_name, binary_file_data, sender_nickname)


            elif data['type'] == 'pong':
                last_pong_times[websocket] = time.time()

    except websockets.exceptions.ConnectionClosed as e:
        if websocket in connected_clients:
            print(f"{connected_clients[websocket]} 已断开连接")
            del connected_clients[websocket]
            del last_pong_times[websocket]
            await broadcast_user_list()

# 创建并启动一个WebSocket服务器
# 任何客户端通过5678端口访问WebSocket服务都会被监听到
# 每当一个客户端连接到服务器时，handle_client函数会接管该连接
start_server = websockets.serve(
    handle_client, "0.0.0.0", 5678,
)

# 运行服务器并启动心跳任务
loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)
loop.create_task(send_heartbeat())  # 启动心跳发送任务
print("服务器已启动...")
loop.run_forever()
