from enum import Enum
import time
import socket
import threading
import random
import pickle

# Global delay variables
INVALIDATION_DELAY = 7  # Invalidation delay in seconds
BROADCAST_DELAY = 2 * INVALIDATION_DELAY + 1  # Broadcast delay in seconds

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
    broadcast = 4,
    empty_broadcast = 5

class Log:
    def __init__(self, type: LogType, timeOfOccurence: int, memId: int = None, clientId: int = None):
        self.type = type
        self.timeOfOccurence = timeOfOccurence
        self.memId = memId
        self.clientId = clientId

    def __str__(self):
        log_info = f"{self.type.name} at {self.timeOfOccurence}s"
        if self.memId is not None:
            log_info += f" [Memory ID: {self.memId}]"
        if self.clientId is not None:
            log_info += f" [Client ID: {self.clientId}]"
        return log_info

startTime = int(time.time())
memory = [Memory(i, int(time.time()) - startTime) for i in range(10)]
subscriptions = []
changelog = []

# Server and Client constants
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 65432

def handle_client(client_socket, client_id):
    client_memory = {i: {'initTime': -1, 'isValid': True} for i in range(10)}  # Initialize client memory

    while True:
        try:
            request = client_socket.recv(1024)
            if not request:
                break

            request_type = request.decode()
            if request_type == 'GET_INVALIDATED':
                invalidated_items = [(m.id, m.initTime) for m in memory if not m.isValid]
                response = {
                    'type': 'INVALIDATED',
                    'items': invalidated_items,
                    'time': int(time.time()) - startTime
                }
                client_socket.send(pickle.dumps(response))
            elif request_type.startswith('SUBSCRIBE'):
                mem_id = int(request.decode().split()[1])
                subscriptions.append(SubscribeRecord(mem_id, int(time.time()) - startTime, client_id))
                changelog.append(Log(LogType.subscribe, int(time.time()) - startTime, memId=mem_id, clientId=client_id))
                response = {'type': 'SUBSCRIBED', 'id': mem_id}
                client_socket.send(pickle.dumps(response))
        except:
            break

    client_socket.close()

def broadcast_invalidations():
    while True:
        time.sleep(BROADCAST_DELAY)  # Broadcast delay based on global variable
        if random.randint(1, 5) == 1:  # Occasionally send an empty broadcast
            empty_message = {'type': 'EMPTY'}
            for subscription in subscriptions:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.connect((SERVER_HOST, SERVER_PORT))
                    sock.send(pickle.dumps(empty_message))
            changelog.append(Log(LogType.empty_broadcast, int(time.time()) - startTime))
            print("[SRV] Empty broadcast sent.")
            continue

        invalidated_items = [(m.id, m.initTime) for m in memory if not m.isValid]
        broadcast_message = {'type': 'BROADCAST', 'items': invalidated_items}
        for subscription in subscriptions:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((SERVER_HOST, SERVER_PORT))
                sock.send(pickle.dumps(broadcast_message))
        changelog.append(Log(LogType.broadcast, int(time.time()) - startTime))
        for mem_id, init_time in invalidated_items:
            print(f"[SRV] Broadcast invalidation - Memory ID: {mem_id}, Time: {init_time}s")

def invalidate_memory():
    while True:
        time.sleep(INVALIDATION_DELAY)  # Invalidation delay based on global variable
        mem_to_invalidate = random.choice(memory)
        mem_to_invalidate.isValid = False
        changelog.append(Log(LogType.invalidate, int(time.time()) - startTime, memId=mem_to_invalidate.id))
        print(f"[SRV] Memory item {mem_to_invalidate.id} invalidated")

def server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    print(f"[SRV] Server listening on {SERVER_HOST}:{SERVER_PORT}")

    # Start invalidate and broadcast threads
    threading.Thread(target=invalidate_memory, daemon=True).start()
    threading.Thread(target=broadcast_invalidations, daemon=True).start()

    while True:
        client_socket, addr = server_socket.accept()
        print(f"[SRV] Accepted connection from {addr}")
        threading.Thread(target=handle_client, args=(client_socket, addr)).start()

def client_behavior(client_id, action_type):
    client_memory = {i: {'initTime': -1, 'isValid': True} for i in range(10)}
    subscribed_mem_ids = random.sample(range(10), 2)  # Subscribe to 2 random Memory objects

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((SERVER_HOST, SERVER_PORT))
        for mem_id in subscribed_mem_ids:
            sock.send(f"SUBSCRIBE {mem_id}".encode())
            response = sock.recv(4096)
            if response:
                print(f"[CL{client_id}] Subscribed to Memory ID {mem_id}")

        while True:
            response = sock.recv(4096)
            if response:
                message = pickle.loads(response)
                if message['type'] == 'BROADCAST':
                    for mem_id, init_time in message['items']:
                        if mem_id in client_memory:
                            client_memory[mem_id]['initTime'] = init_time
                            client_memory[mem_id]['isValid'] = False
                    print(f"[CL{client_id}] Updated memory cache with invalidated items.")
                elif message['type'] == 'EMPTY':
                    if action_type == "request":
                        sock.send("GET_INVALIDATED".encode())
                        response = sock.recv(4096)
                        invalidated_data = pickle.loads(response)
                        for mem_id, init_time in invalidated_data['items']:
                            client_memory[mem_id]['initTime'] = init_time
                            client_memory[mem_id]['isValid'] = False
                        print(f"[CL{client_id}] Requested and updated invalidated items.")
                    elif action_type == "invalidate_all":
                        for mem_id in client_memory:
                            client_memory[mem_id]['isValid'] = False
                        print(f"[CL{client_id}] Invalidated entire cache due to empty broadcast.")

    print(f"\n[CL{client_id}] Full Log of Changes:")
    for log in changelog:
        print(log)

if __name__ == '__main__':
    threading.Thread(target=server, daemon=True).start()
    time.sleep(1)  # Give the server time to start

    # Start two autonomous clients
    threading.Thread(target=client_behavior, args=(1, "request"), daemon=True).start()
    threading.Thread(target=client_behavior, args=(2, "invalidate_all"), daemon=True).start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)  # Sleep to keep the main thread alive
    except KeyboardInterrupt:
        print("Application stopped.")
