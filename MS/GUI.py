import logging
import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
from datetime import datetime


def on_log(mqttc, obj, level, string):
    print(string)


class MQTTClientGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MQTT Client")

        # Create the GUI layout
        self.create_layout()
        self.fillDefaults()

        self.client = None

    def start(self):
        self.root.mainloop()

    def fillDefaults(self):
        self.entries_top["Host"].insert(0, "pcfeib425t.vsb.cz")
        self.entries_top["Port"].insert(0, "1883")
        self.entries_top["Username"].insert(0, "mobilni")
        self.entries_top["Password"].insert(0, "Systemy")

        self.entries_middle["Client ID"].insert(0, "hab0065")
        self.entries_middle["Keepalive"].insert(0, "60")
        self.entries_middle["Timeout"].insert(0, "3")

        self.sub_topic_entry.insert(0, "/mschat/all/#")

        self.will_topic_entry.insert(0, "/mschat/status/hab0065")
        self.will_message_text.insert("1.0", "Jak se pripojil, tak se odpojil, nahodou")

    def create_layout(self):
        # Left side frame for all sections except chat window
        left_frame = tk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Chat window on the right side
        chat_frame = tk.Frame(self.root, bd=2, relief=tk.SUNKEN)
        chat_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        chat_label = tk.Label(chat_frame, text="Chat")
        chat_label.pack(anchor='w', padx=5, pady=5)

        self.chat_text = tk.Text(chat_frame, height=20, width=40)
        self.chat_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Main Section - "Login info"
        login_info = tk.LabelFrame(left_frame, text="Login Info", padx=10, pady=10)
        login_info.pack(fill=tk.BOTH, expand=True)

        # Subsection: General Information
        general_info = tk.LabelFrame(login_info, text="General Information", padx=10, pady=10)
        general_info.pack(fill=tk.BOTH, expand=True)

        # 1st Row: Host, Port, Path, Username, Password
        labels_top = ["Host", "Port", "Username", "Password"]
        self.entries_top = {}

        for i, label_text in enumerate(labels_top):
            label = tk.Label(general_info, text=label_text)
            label.grid(row=0, column=i, padx=5, pady=5)

            entry = tk.Entry(general_info)
            entry.grid(row=1, column=i, padx=5, pady=5)
            self.entries_top[label_text] = entry

        # 2nd Row: Client ID, Keepalive, Timeout, Checkboxes
        labels_middle = ["Client ID", "Keepalive", "Timeout"]
        self.entries_middle = {}

        for i, label_text in enumerate(labels_middle):
            label = tk.Label(general_info, text=label_text)
            label.grid(row=2, column=i, padx=5, pady=5)

            entry = tk.Entry(general_info)
            entry.grid(row=3, column=i, padx=5, pady=5)
            self.entries_middle[label_text] = entry

        # Checkboxes for TLS, Clean session, Automatic reconnect
        self.tls_var = tk.BooleanVar()
        self.clean_session_var = tk.BooleanVar()
        self.auto_reconnect_var = tk.BooleanVar()

        tls_checkbox = tk.Checkbutton(general_info, text="TLS", variable=self.tls_var)
        tls_checkbox.grid(row=3, column=3, padx=5, pady=5, sticky='w')

        clean_session_checkbox = tk.Checkbutton(general_info, text="Clean session", variable=self.clean_session_var)
        clean_session_checkbox.grid(row=3, column=4, padx=5, pady=5, sticky='w')

        auto_reconnect_checkbox = tk.Checkbutton(general_info, text="Automatic reconnect",
                                                 variable=self.auto_reconnect_var)
        auto_reconnect_checkbox.grid(row=3, column=5, padx=5, pady=5, sticky='w')

        # Subsection: Last Will
        last_will_info = tk.LabelFrame(login_info, text="Last Will", padx=10, pady=10)
        last_will_info.pack(fill=tk.BOTH, expand=True)

        # Add Login and Disconnect buttons
        disconnect_button = tk.Button(login_info, text="Disconnect", command=self.disconnect_click)
        disconnect_button.pack(side=tk.RIGHT, padx=10, pady=10)

        connect_button = tk.Button(login_info, text="Connect", command=self.connect_click)
        connect_button.pack(side=tk.RIGHT, padx=10, pady=10)

        will_topic_label = tk.Label(last_will_info, text="Last Will Topic")
        will_topic_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')

        self.will_topic_entry = tk.Entry(last_will_info)
        self.will_topic_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        qos_label = tk.Label(last_will_info, text="QoS")
        qos_label.grid(row=0, column=2, padx=5, pady=5, sticky='e')

        qos_options = ["0", "1", "2"]
        self.qos_dropdown = ttk.Combobox(last_will_info, values=qos_options)
        self.qos_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky='w')
        self.qos_dropdown.current(0)

        self.retain_var = tk.BooleanVar()
        retain_checkbox = tk.Checkbutton(last_will_info, text="Retain", variable=self.retain_var)
        retain_checkbox.grid(row=0, column=4, padx=5, pady=5, sticky='w')

        will_message_label = tk.Label(last_will_info, text="Last Will Message")
        will_message_label.grid(row=1, column=0, padx=5, pady=5, sticky='e')

        self.will_message_text = tk.Text(last_will_info, height=5, width=40)
        self.will_message_text.grid(row=2, column=0, columnspan=5, padx=5, pady=5, sticky='w')

        # New Section: Client behaviour
        client_behaviour = tk.LabelFrame(left_frame, text="Client Behaviour", padx=10, pady=10)
        client_behaviour.pack(fill=tk.BOTH, expand=True)

        # Subsection: Subscribe
        subscribe_frame = tk.LabelFrame(client_behaviour, text="Subscribe", padx=10, pady=10)
        subscribe_frame.pack(fill=tk.BOTH, expand=True)

        sub_topic_label = tk.Label(subscribe_frame, text="Topic")
        sub_topic_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')

        self.sub_topic_entry = tk.Entry(subscribe_frame)
        self.sub_topic_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        sub_qos_label = tk.Label(subscribe_frame, text="QoS")
        sub_qos_label.grid(row=0, column=2, padx=5, pady=5, sticky='e')

        self.sub_qos_dropdown = ttk.Combobox(subscribe_frame, values=qos_options)
        self.sub_qos_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky='w')
        self.sub_qos_dropdown.current(0)

        subscribe_button = tk.Button(subscribe_frame, text="Subscribe", command=self.subscribe_click)
        subscribe_button.grid(row=0, column=4, padx=5, pady=5)

        unsubscribe_button = tk.Button(subscribe_frame, text="Unsubscribe", command=self.unsubscribe_click)
        unsubscribe_button.grid(row=0, column=5, padx=5, pady=5)

        # Subsection: Send Message
        send_message_frame = tk.LabelFrame(client_behaviour, text="Send Message", padx=10, pady=10)
        send_message_frame.pack(fill=tk.BOTH, expand=True)

        send_topic_label = tk.Label(send_message_frame, text="Topic")
        send_topic_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')

        self.send_topic_entry = tk.Entry(send_message_frame)
        self.send_topic_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        send_qos_label = tk.Label(send_message_frame, text="QoS")
        send_qos_label.grid(row=0, column=2, padx=5, pady=5, sticky='e')

        self.send_qos_dropdown = ttk.Combobox(send_message_frame, values=qos_options)
        self.send_qos_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky='w')
        self.send_qos_dropdown.current(0)

        self.send_retain_var = tk.BooleanVar()
        send_retain_checkbox = tk.Checkbutton(send_message_frame, text="Retain", variable=self.send_retain_var)
        send_retain_checkbox.grid(row=0, column=4, padx=5, pady=5, sticky='w')

        send_receiver_label = tk.Label(send_message_frame, text="Receiver")
        send_receiver_label.grid(row=0, column=5, padx=5, pady=5, sticky='w')

        self.send_receiver_entry = tk.Entry(send_message_frame)
        self.send_receiver_entry.grid(row=0, column=6, padx=5, pady=5, sticky='w')

        send_message_label = tk.Label(send_message_frame, text="Message")
        send_message_label.grid(row=1, column=0, padx=5, pady=5, sticky='e')

        self.send_message_text = tk.Text(send_message_frame, height=5, width=40)
        self.send_message_text.grid(row=2, column=0, columnspan=5, padx=5, pady=5, sticky='w')

        publish_button = tk.Button(send_message_frame, text="Publish", command=self.publish_click)
        publish_button.grid(row=3, column=4, padx=5, pady=5)

        publish_button = tk.Button(send_message_frame, text="Publish Private", command=self.publish_private_click)
        publish_button.grid(row=3, column=5, padx=5, pady=5)

    # Empty methods called by buttons (for now they just print the method name)
    def connect_click(self):
        host = self.entries_top['Host'].get()
        port = int(self.entries_top['Port'].get())
        username = self.entries_top['Username'].get()
        password = self.entries_top['Password'].get()

        clientId = self.entries_middle['Client ID'].get()
        keepalive = int(self.entries_middle['Keepalive'].get())
        timeout = int(self.entries_middle['Timeout'].get())

        tls = self.tls_var.get()
        cleanSession = self.clean_session_var.get()
        reconnect = self.clean_session_var.get()

        logging.basicConfig(level=logging.DEBUG)

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=clientId, clean_session=cleanSession)

        logger = logging.getLogger(__name__)
        self.client.enable_logger(logger)

        self.client.on_log = on_log
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        LWTopic = self.will_topic_entry.get()
        LWQos = int(self.qos_dropdown.get())
        LWMessage = self.will_message_text.get("1.0", tk.END).strip()
        LWRetain = self.retain_var.get()

        self.client.will_set(LWTopic, LWMessage, LWQos, LWRetain)
        self.client.username_pw_set(username, password)
        self.client.connect(host, port, keepalive)

        self.client.loop_start()

        # Each user should subscribe to his own private chat
        self.client.subscribe(f"/mschat/user/{clientId}/#", 0)

        print("connected")

    def disconnect_click(self):
        clientId = self.entries_middle['Client ID'].get()

        # Default unsubscribe from my private chat
        self.client.unsubscribe(f"/mschat/user/{clientId}/#")

        self.client.will_clear()

        self.client.disconnect()
        print("disconnected")

    def subscribe_click(self):
        topic = self.sub_topic_entry.get()
        qos = int(self.sub_qos_dropdown.get())

        self.client.subscribe(topic, qos)

        print(f"subscribed to {topic}")

    def unsubscribe_click(self):
        topic = self.sub_topic_entry.get()

        self.client.unsubscribe(topic)

        print(f"unsubscribed from {topic}")

    def publish_click(self):
        topic = self.send_topic_entry.get()
        qos = int(self.send_qos_dropdown.get())
        message = self.send_message_text.get("1.0", tk.END).strip()

        self.client.publish(topic, message, qos)

        print(f"published on {topic} with {qos} content {message}")

    def publish_private_click(self):
        receiver = self.send_receiver_entry.get()
        sender = self.entries_middle['Client ID'].get()
        topic = f"/mschat/user/{receiver}/{sender}"
        qos = int(self.send_qos_dropdown.get())
        message = self.send_message_text.get("1.0", tk.END).strip()

        self.client.publish(topic, message, qos)

        print(f"private published on {topic} with {qos} content {message}")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"Connected successfully")
        else:
            print(f"Failed to connect, return code {reason_code}")

    def connect_fail_callback(self, client, userdata):
        print(f"failed to connect {client} with {userdata}")

    # MQTT on_message callback
    def on_message(self, client, userdata, message):
        msg = f"{message.topic} - {message.payload} - {datetime.fromtimestamp(message.timestamp).isoformat()} - {message.qos}\n"

        print(msg)

        self.update_chat_window(msg)

    # Update chat window with new message
    def update_chat_window(self, message):
        self.chat_text.insert(tk.END, message)
        self.chat_text.see(tk.END)  # Scroll to the latest message

