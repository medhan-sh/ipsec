# IPsec Analyzer

A passive, non-decrypting security assessment platform for IPsec (IKEv2/ESP) network packet captures.

It inspects `.pcap` and `.pcapng` traces, dissects the IKE handshake via `tshark`, infers ESP data-plane cipher properties from packet framing and sizing arithmetic, evaluates the posture against formal policy rules, and generates both an interactive standalone HTML report and a machine-readable `findings.json` document. Every finding and observation carries an explicit **provenance tier** distinguishing verified wire data from mathematical side-channel inferences.

The platform provides two presentation interfaces:
1. **Interactive Terminal Console (TUI)**: A rich, keyboard-driven Textual console featuring 5 specialized security screens and real-time search.
2. **Command-Line Interface (CLI)**: A headless analyzer suited for scripts, CI/CD pipelines, and automated reporting.

---

## Quick Start (Two Ways to Run)

The analyzer is designed to run seamlessly on any device (**Linux**, **macOS**, or **Windows**). You can run it either via **Docker** (no local dependencies needed) or **natively** (if you have Python and `tshark` installed).

```
                      ┌─────────────────────────────────────────┐
                      │             Choose Method               │
                      └────────────────────┬────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
          Method 1: With Docker                         Method 2: Native Local
    (Portable across all OS & devices)              (Fastest if Python+TShark exist)
                    │                                             │
      ./ipsec-analyze <capture.pcap>                 pip install -e .
      ./ipsec-tui                                    ./ipsec-tui
```

---

### Method 1: Running with Docker (Recommended for Portability)

Docker packages Python, all library dependencies, and a pinned `tshark` binary into a reproducible container. **No host dependencies other than Docker are required.**

From a clean clone:

#### 1. Run the Headless Analyzer
```bash
# Automatically builds the container on first run and analyzes the capture
./ipsec-analyze captures/ikev2-decrypt-aes128ccm12.pcap
```
* Generates `captures/ikev2-decrypt-aes128ccm12.report.html` (open directly in your browser).
* Generates `captures/ikev2-decrypt-aes128ccm12.findings.json` (raw findings document).

#### 2. Launch the Interactive Terminal UI (TUI)
```bash
# Launches the interactive security console in your terminal
./ipsec-tui
```

#### 3. Run with Docker Compose
If you prefer Docker Compose:
```bash
# Run analysis on a capture file
docker compose run --rm analyzer captures/ikev2-decrypt-aes128ccm12.pcap

# Launch the interactive TUI
docker compose run --rm tui

# Run the automated test suite
docker compose run --rm test
```

#### 4. Run directly via Docker CLI
```bash
# Build the image
docker build -t ipsec-analyzer:dev .

# Analyze a capture
docker run --rm -v "$PWD":/work ipsec-analyzer:dev captures/ikev2-decrypt-aes128ccm12.pcap

# Launch the TUI (requires -it for interactive terminal)
docker run -it --rm -v "$PWD":/work ipsec-analyzer:dev ipsec-tui
```

---

### Method 2: Running Natively (Without Docker)

If your machine already has Python 3.10+ and `tshark` (Wireshark CLI) installed (e.g. NixOS, Arch, Ubuntu, Debian, macOS via Homebrew):

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies and the analyzer in editable mode
pip install -e .

# 3. Run the interactive TUI
./ipsec-tui

# 4. Or run the headless CLI analyzer
./ipsec-analyze captures/ikev2-decrypt-aes128ccm12.pcap
# (or: python -m ipsec_analyzer.cli captures/ikev2-decrypt-aes128ccm12.pcap)

# 5. Run the test suite
pytest
```

---

## Interactive Security Console (TUI)

The Textual-based TUI (`./ipsec-tui`) provides an interactive interface to inspect, filter, and audit IPsec traffic:

```
┌───────────────────────────────────┬────────────────────────────────────────────────────────┐
│ CAPTURE EXPLORER                  │ [1] Overview  [2] Findings  [3] Tunnels  [4] Claims... │
├───────────────────────────────────┼────────────────────────────────────────────────────────┤
│ ▼ captures                        │ STATUS: ✔ Complete (0.7s) | Findings: Yes              │
│   ├── ikev2-aes128ccm12.pcap      │                                                        │
│   ├── ikev2-3des-sha1.pcap        │ FINDINGS TABLE [/ to filter]                           │
│   └── weberblog_ikev2.pcap        │ ┌──────────┬─────────────────────────────────────────┐ │
│                                   │ │ HIGH     │ Weak IKE SA cipher (DES / 3DES)         │ │
│ [ Preview Card ]                  │ │ MEDIUM   │ Weak IKE SA integrity (MD5 / SHA-1)     │ │
│ Size: 1.9 KB                      │ └──────────┴─────────────────────────────────────────┘ │
│ Modified: 2026-09-22              │                                                        │
│ Findings: Yes | Report: Yes       │ RECOMMENDATION & RFC CITATIONS                         │
│                                   │ Upgrade proposal to AES-GCM (RFC 5282) or AES-CBC...   │
│ [ Analyze (a) ] [ Refresh (r) ]   │                                                        │
└───────────────────────────────────┴────────────────────────────────────────────────────────┘
```

### Keyboard Navigation & Shortcuts

| Shortcut | Action | Description |
|---|---|---|
| <kbd>1</kbd> or <kbd>o</kbd> / <kbd>F1</kbd> | **Overview Screen** | Capture metadata, truncation banner, rule summary, IKE SA params, risk verdicts |
| <kbd>2</kbd> or <kbd>f</kbd> / <kbd>F2</kbd> | **Findings Screen** | Security issues table, severity badges, frame scope, RFC recommendations |
| <kbd>3</kbd> or <kbd>t</kbd> / <kbd>F3</kbd> | **Tunnels Screen** | ESP candidate universe, visual ratio bar, surviving suites, elimination reasons |
| <kbd>4</kbd> or <kbd>c</kbd> / <kbd>F4</kbd> | **Claims Screen** | Wire observations, provenance tiers, confidence scores, framing caveats |
| <kbd>5</kbd> or <kbd>v</kbd> / <kbd>F5</kbd> | **Coverage Screen** | Policy rules breakdown: found issues, clean passes, and coverage gaps |
| <kbd>/</kbd> | **Filter / Search** | Focus real-time search input on Findings, Claims, or Coverage screens |
| <kbd>Esc</kbd> | **Clear / Dismiss** | Clear current filter search query or dismiss open modal dialog |
| <kbd>a</kbd> | **Analyze** | Execute analyzer subprocess against currently selected capture |
| <kbd>r</kbd> | **Refresh** | Re-scan the filesystem directory tree in sidebar |
| <kbd>b</kbd> | **Browser Report** | Open generated `<capture>.report.html` in your default browser |
| <kbd>j</kbd> | **View JSON** | Open formatted `<capture>.findings.json` in modal code viewer |
| <kbd>[</kbd> / <kbd>]</kbd> | **Cycle Tunnels** | Navigate between multiple ESP Child SAs / SPIs |
| <kbd>?</kbd> or <kbd>h</kbd> | **Help** | Display keyboard shortcuts reference modal |
| <kbd>q</kbd> or <kbd>Ctrl+C</kbd> | **Quit** | Exit the application |

---

## Deploying on Other Devices & Platforms

### Linux (Ubuntu, Debian, Fedora, RHEL, NixOS, Arch)
- **Permissions**: Output files are automatically mapped to your calling host user UID/GID (`--user $(id -u):$(id -g)`), ensuring generated `.html` and `.json` files can be edited or deleted without `sudo`.
- **Headless execution**: Run `./ipsec-analyze capture.pcap` directly in server environments.

### macOS (Apple Silicon M1/M2/M3/M4 & Intel)
- Docker Desktop automatically reconciles file ownership across the macOS hypervisor boundary.
- Both native ARM64 (`linux/arm64`) and x86_64 (`linux/amd64`) container builds are supported.

### Windows (PowerShell & WSL2)
- **Under WSL2** (Recommended): Works exactly like native Linux:
  ```bash
  ./ipsec-analyze captures/test.pcap
  ./ipsec-tui
  ```
- **Under PowerShell with Docker Desktop**:
  ```powershell
  # Build
  docker build -t ipsec-analyzer:dev .

  # Run analysis
  docker run --rm -v "${PWD}:/work" ipsec-analyzer:dev captures/test.pcap

  # Run TUI
  docker run -it --rm -v "${PWD}:/work" ipsec-analyzer:dev ipsec-tui
  ```

### Multi-Architecture Image Distribution
To build and publish a multi-architecture image (`amd64` and `arm64`):

```bash
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t your-registry/ipsec-analyzer:latest . --push
```

---

## Test Captures

Sample packet captures from Wireshark's test suite and real firewall traces are cataloged in [`captures/FETCH.md`](file:///home/sybqu/Desktop/sih/ipsec/captures/FETCH.md).

To download the test vectors into `captures/`:

### Dropping the `./`

`./ipsec-analyze` works from a clone with no setup. To run it as
`ipsec-analyze` from anywhere, symlink it onto your PATH:

```bash
mkdir -p ~/.local/bin
ln -s "$PWD/ipsec-analyze" ~/.local/bin/ipsec-analyze
```

(any directory on your `PATH` works; `~/.local/bin` just avoids needing
`sudo`). The wrapper resolves symlinks before locating its own Dockerfile,
so the first-run auto-build still works when invoked through one. It
always mounts the *current* directory, so the capture still has to live
somewhere under wherever you run it from.

To run the test suite instead:
```bash
# Wireshark IKEv2 decrypt test suite
curl -sL -o captures/ikev2-decrypt-aes128ccm12.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-aes128ccm12.pcap"
curl -sL -o captures/ikev2-decrypt-3des-sha1_160.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-3des-sha1_160.pcap"
curl -sL -o captures/ikev2-decrypt-aes192ctr.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-aes192ctr.pcap"
curl -sL -o captures/ikev2-decrypt-aes256cbc.pcapng "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-aes256cbc.pcapng"
curl -sL -o captures/ikev2-decrypt-aes256gcm16.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-aes256gcm16.pcap"
curl -sL -o captures/ikev2-decrypt-aes256gcm8.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-aes256gcm8.pcap"
```

To run the automated test suite:
```bash
make test
# or with pytest locally:
pytest -v
```

---

## Provenance Tiers

Every fact the tool reports is an atomic `Claim` carrying one of five provenance tiers, ordered weakest to strongest. An assessment result is only as certain as the weakest tier supporting it:

| Tier | Meaning | Confidence |
|---|---|---|
| `OBSERVED` | Read directly off the wire by `tshark`'s protocol dissector (e.g. IKE transform ID, notify payload presence, IP protocol number). | 1.0 (Exact) |
| `INFERRED_SIDE_CHANNEL` | Derived deterministically from packet framing, padding arithmetic, or TCP ACK anchors (e.g. ESP padding granularity from GCD of packet size deltas). | Heuristic |
| `INFERRED_IMPLEMENTATION_DEFAULT` | Assumed from known implementation defaults (reserved for future extensions; never fabricated in current MVP). | Reserved |
| `ML_PREDICTION` | Statistical classifier output (reserved for future phases; never fabricated in current MVP). | Reserved |
| `NOT_OBSERVABLE` | The question cannot be answered from the capture (e.g. receiver anti-replay policy, or insufficient packets for size-based elimination). | None (Gap) |

---

## Security Guarantees & Constraints

1. **Zero Decryption**: ESP payloads remain completely opaque. The platform does not extract or require cryptographic keys.
2. **Strictly Passive**: No packets are transmitted; no endpoints are probed or modified.
3. **No Fabricated Data**: If a capture is truncated, incomplete, or uniform in packet size, an explicit **coverage gap** is reported rather than a fabricated guess.
4. **Frozen Schema**: `findings.json` strictly adheres to the frozen `1.0` contract for external consumption.
