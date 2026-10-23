import select
import socket
import sys

# what the error codes mean (table from the spec)
ERRORS = {
    "0": "that username is already taken",
    "1": "invalid username (1-32 characters, no spaces)",
    "2": "that user isn't in the chat",
    "3": "invalid or unexpected message",
}

users = []   # my own copy of who's online. the protocol has no list command so I keep track myself
buf = b""    # bytes from the server that aren't a full line yet


def send(sock, line):
    try:
        sock.sendall((line + "\n").encode())
    except OSError:
        print("lost connection to the server")
        sys.exit(1)


def read_line(sock):
    # wait until the server sends a whole line (TCP gives in pieces sometimes)
    global buf
    while b"\n" not in buf:
        data = sock.recv(4096)
        if not data:
            print("server disconnected")
            sys.exit(1)
        buf += data
    line, buf = buf.split(b"\n", 1)
    return line.decode(errors="replace").rstrip("\r")


def handle_server_line(line):
    # print whatever the server sent as is then deal w it
    print(line)
    parts = line.split(" ")

    if parts[0] == "ERR":
        print("error:", ERRORS.get(parts[1], "unknown error"))

    elif parts[0] == "MSG" and parts[1] == "SERVER" and len(parts) >= 5:
        # "MSG SERVER bob has joined the chat" or "MSG SERVER bob has left the chat"
        # this is how my user list stays up to date
        name = parts[2]
        if parts[4] == "joined" and name not in users:
            users.append(name)
        elif parts[4] == "left" and name in users:
            users.remove(name)

    elif parts[0] == "ACK":
        # once I'm registered the only ACK I can get is the one for my EXIT, so I'm done
        print("you left the chat")
        sys.exit(0)


def main():
    global buf, users

    host = input("server hostname or IP: ")
    port = input("port: ")
    try:
        sock = socket.create_connection((host, int(port)))
    except (ValueError, OSError) as e:
        print("couldn't connect:", e)
        sys.exit(1)
    print(f"connected to {host} on port {port}")

    # keep trying usernames until the server takes one n the server will handle it
    name = input("username: ")
    while True:
        send(sock, "REG " + name)
        reply = read_line(sock)
        print(reply)
        if reply.startswith("ACK"):
            break
        print("error:", ERRORS.get(reply[4:], "unknown error"))
        name = input("try a different username: ")

    users = reply.split(" ")[2:]   # "ACK 2 alice bob" -> ["alice", "bob"]
    print("registered! commands: MESG <message>, PMSG <user> <message>, LIST, EXIT")

    # select() wakes me up when I type something OR the server sends something
    while True:
        readable, _, _ = select.select([sock, sys.stdin], [], [])

        if sys.stdin in readable:
            text = sys.stdin.readline()
            if not text:
                # leave n wait for the ACK
                send(sock, "EXIT")
                while True:
                    handle_server_line(read_line(sock))
            text = text.rstrip("\n")
            if text == "LIST":
                print(f"{len(users)} user(s) in the chat: {' '.join(users)}")
            elif text:
                send(sock, text)   # MESG / PMSG / EXIT go to server for checking

        if sock in readable:
            data = sock.recv(4096)
            if not data:
                print("server disconnected")
                sys.exit(1)
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                handle_server_line(line.decode(errors="replace").rstrip("\r"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # dip without EXIT 
        print()
