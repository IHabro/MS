from enum import Enum
import time
import socket
import threading
import random
import pickle


class Memory:
    def __init__(self, id: int, initTime: int):
        self.id = id
        self.initTime = initTime
        self.isValid = True


class SubscribeRecord:
    def __init__(self, memId: int, registerTime: int, clientId: int):
        self.id = memId
        self.registerTime = registerTime
        self.clientId = clientId


class LogType(Enum):
    invalidate = 0,
    validate = 1,
    subscribe = 2,
    unsubscribe = 3,


class Log:
    def __init__(self, type: LogType, timeOfOccurence: int):
        self.type = type
        self.timeOfOccurence = timeOfOccurence


startTime = int(time.time())
memory = [Memory(i, int(time.time()) - startTime) for i in range(10)]
subscriptions = []
changelog = []

# Constants for server
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 65432


def handle_client(client_socket, client_id):
    global changelog
    while True:
        request = client_socket.recv(1024)
        if not request:
            break

        request_type = request.decode()
        if request_type == 'GET_INVALIDATED':
            invalidated_items = [m.id for m in memory if not m.isValid]
            response = {
                'type': 'INVALIDATED',
                'items': invalidated_items,
                'time': int(time.time()) - startTime
            }
            client_socket.send(pickle.dumps(response))
        elif request_type.startswith('SUBSCRIBE'):
            mem_id = int(request.decode().split()[1])
            subscriptions.append(SubscribeRecord(mem_id, int(time.time()) - startTime, client_id))
            changelog.append(Log(LogType.subscribe, int(time.time()) - startTime))
            response = {'type': 'SUBSCRIBED', 'id': mem_id}
            client_socket.send(pickle.dumps(response))
        elif request_type == 'UNSUBSCRIBE':
            mem_id = int(request.decode().split()[1])
            subscriptions[:] = [sub for sub in subscriptions if sub.memId != mem_id or sub.clientId != client_id]
            changelog.append(Log(LogType.unsubscribe, int(time.time()) - startTime))
            response = {'type': 'UNSUBSCRIBED', 'id': mem_id}
            client_socket.send(pickle.dumps(response))

    client_socket.close()


def server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")

    def invalidate_memory():
        while True:
            time.sleep(7)  # Invalidate memory every 7 seconds
            mem_to_invalidate = random.choice(memory)
            mem_to_invalidate.isValid = False
            changelog.append(Log(LogType.invalidate, int(time.time()) - startTime))
            print(f"Memory item {mem_to_invalidate.id} invalidated")

    # Start invalidation thread
    threading.Thread(target=invalidate_memory, daemon=True).start()

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Accepted connection from {addr}")
        threading.Thread(target=handle_client, args=(client_socket, addr)).start()


def client(client_id):
    while True:
        action = input("Enter action (GET_INVALIDATED, SUBSCRIBE <id>, UNSUBSCRIBE <id>, EXIT): ").strip()
        if action.upper() == 'EXIT':
            break

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((SERVER_HOST, SERVER_PORT))
            sock.send(action.encode())
            response = sock.recv(4096)
            print(pickle.loads(response))


if __name__ == '__main__':
    threading.Thread(target=server, daemon=True).start()
    time.sleep(1)  # Give the server some time to start
    client_id = random.randint(1, 1000)  # Unique client ID
    client(client_id)
