## Includes

- heartbeat
- dynamic discovery
- fault tolerance
- total reliable ordered multicast
- leader election via LCR
- uses Broadcast, IP Multicast, reliable Unicast
- runs on windos, linux, macos

## Start

```
python server.py
python client.py
python monitor.py
```

 `Debug` can be set in config (also if heartbeat will be shown etc.)

**It is possible to run several servers/clients on the same machine and let them communicate via unicast
as always a new, random port will be assigned to each host at the start. All identification is done via IDs**

## Good to know

- The same port on the one machine can be used (bind to) by several sockets with SO_REUSEADDR, but for unicast only one
  will receive a message
- If just sendTo is used, a random port is used and can be simply answered by using the provided address
- If no messages go through, restart router
- Windows does not allow the usage of SO_REUSEPORT

````python
if os.name != 'nt':
    from socket import SO_REUSEPORT

    self.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
````

- MacOS and Linux usually returns for `socket.gethostbyname(socket.gethostname())` 'localhost' or '127.0.0.1', which is
  not helpful for getting messages from other machines. Use:

````python
def get_local_address():
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_address = s.getsockname()[0]
        return local_address
    finally:
        if s:
            s.close()
````
