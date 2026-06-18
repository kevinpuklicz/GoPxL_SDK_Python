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
from gopxl import GoDiscoveryClient, GoSystem, GoGdpClient

disc = GoDiscoveryClient()
disc.blocking_discover(3000, classic_discover=True)

system = GoSystem("192.168.1.10", 3600)
system.connect()
system.start()

system_res = system.resource("/system")
print(system_res.get_value("runState"))

gdp = GoGdpClient()
gdp.connect(system.address(), system.gdp_port())
gdp.receive_data_sync(20000)
for msg in gdp.dataset():
    print(msg.type())
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
