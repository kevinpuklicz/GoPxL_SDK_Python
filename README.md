# GoPxL SDK (Python)

Lightweight Python SDK for **GoPxL / Gocator** sensors. Mirrors the official C++ SDK API (`GoSystem`, `GoRestClient`, `GoGdpClient`, discovery, GDP parsers, optional `GoResource`).

## Install

```bash
pip install git+https://github.com/kevinpuklicz/GoPxL_SDK_Python.git
```

Editable local install:

```bash
git clone https://github.com/kevinpuklicz/GoPxL_SDK_Python.git
cd GoPxL_SDK_Python
pip install -e .
```

Pin a release tag:

```bash
pip install git+https://github.com/kevinpuklicz/GoPxL_SDK_Python.git@v0.2.0
```

## Quick start

```python
from GoPxL_SDK_Py import GoSystem, GoGdpClient, MessageType

# --- Configuration  ------------------------------------------
ADDRESS = "192.168.1.10"
CONTROL_PORT = 3600
TIMEOUT_MS = 20000
NO_STOP = False # If True, don't call system.stop() at the end
# -------------------------------------------------------------------------

print(f"Connecting to {ADDRESS}:{CONTROL_PORT}...")
system = GoSystem(ADDRESS, CONTROL_PORT)
try:
    system.connect()
except Exception as exc:
    print("Failed to connect:", exc)
    raise SystemExit(1)

# Start the device only if it's not already running 
started = False
try:
    if system.running_state() != system.State.RUNNING:
        print("Starting device...")
        system.start()
        started = True
    else:
        print("Device already running — continuing")
except Exception:
    try:
        system.start()
        started = True
    except Exception:
        pass

print("Receiving one GDP dataset...")
ds = None
try:
    gdp = GoGdpClient()
    gdp.connect(system.address(), system.gdp_port())
    gdp.receive_data_sync(TIMEOUT_MS)
    ds = gdp.dataset()
except Exception as exc:
    print("GDP receive failed:", exc)

if not ds:
    print("No data received")
else:
    for msg in ds:
        if msg.type() == MessageType.MEASUREMENT:
            val = getattr(msg, "value", None)
            try:
                src = msg.data_source_id()
            except Exception:
                src = "<unknown>"
            if isinstance(val, float):
                print(f"{src}: {val:.6f}")
            else:
                print(f"{src}: {val}")

# Stop the device if this script started it
if started and not NO_STOP:
    try:
        print("Stopping device...")
        system.stop()
    except Exception:
        pass

print("Done.")
```

## Features

| Component | Description |
|-----------|-------------|
| `GoSystem` / `GoRestClient` | REST control, transactions, notification listeners |
| `GoGdpClient` | GDP TCP streaming |
| GDP parsers | Profile, Surface, Image, PointCloud, Mesh, Spots, Rendering, Features |
| `GoDiscoveryClient` | GoPxL UDP 3320 + Classic UDP 3220 (legacy sensors) |
| `GoResource` / `GoResourceManager` | Optional cached REST helpers |

## Requirements

- Python 3.9+
- `msgpack`

## License

MIT — see [LICENSE](LICENSE).
