# Umbra

> **Passive, non-decrypting cryptographic posture and forensics console for IPsec (IKEv2 / ESP) packet captures.**

Umbra inspects `.pcap` and `.pcapng` network traces, dissects the IKE handshake via `tshark`, infers ESP data-plane cipher properties from wire framing and sizing arithmetic, evaluates security posture against formal cryptographic policy rules, and provides interactive inspection across both terminal and web consoles.

Every finding and observation carries an explicit **provenance tier** that strictly distinguishes ground-truth wire data from mathematical side-channel inferences. ESP payloads remain completely opaque—**zero decryption keys are extracted, required, or used**.

---

## Interfaces

Umbra provides three presentation layers built on top of a shared frozen analysis engine (`findings.json` Schema 1.0):

```
                                  ┌─────────────────────────────┐
                                  │      Wire PCAP / PCAPNG     │
                                  └──────────────┬──────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │    Umbra Analysis Core      │
                                  │ (IKE Dissection + ESP Math) │
                                  └──────────────┬──────────────┘
                                                 │ Schema 1.0 JSON
                     ┌───────────────────────────┼───────────────────────────┐
                     ▼                           ▼                           ▼
        ┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
        │  Illuminated Web UI     │ │  Interactive TUI        │ │  Headless CLI & HTML    │
        │  http://localhost:8765  │ │  Textual Terminal App   │ │  Standalone Report    │
        │  (React + Tailwind)     │ │  (Python Textual)       │ │  (CI / CD Pipelines)   │
        └─────────────────────────┘ └─────────────────────────┘ └─────────────────────────┘
```

1. **Illuminated Evidence Web UI**: A local-only, dark-mode security console (`http://localhost:8765/`) featuring dynamic SVG evidence topology visuals, TanStack tables, staged candidate elimination lattices, and live capture ingestion.
2. **Interactive Terminal UI (TUI)**: A fast, keyboard-driven Textual terminal console with 5 synchronized forensic screens, live fuzzy search, and drawer inspection (`./umbra-tui` or `./umbra tui`).
3. **Headless Command-Line Interface (CLI)**: A headless analyzer suited for scripts, CI/CD pipelines, and automated reporting (`./umbra <capture.pcap>`) that generates standalone zero-dependency HTML audit reports and `findings.json`.

---

## Quick Start (Two Ways to Run)

Umbra runs seamlessly across **Linux**, **macOS** (Intel & Apple Silicon), and **Windows** (PowerShell & WSL2). You can run it either via **Docker** (reproducible, zero host dependencies) or **natively** (using host Python and `tshark`).

```
                      ┌─────────────────────────────────────────┐
                      │              Choose Method              │
                      └────────────────────┬────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
          Method 1: With Docker                         Method 2: Native Local
    (No dependencies except Docker)                 (Fastest if Python+TShark exist)
                    │                                             │
      docker compose up                             pip install -e .
      ./umbra-web  /  ./umbra-tui                   ./umbra-web  /  ./umbra-tui
```

---

### Method 1: Running with Docker (Recommended)

Docker packages Python 3.11, all required libraries, a pinned `tshark` binary, and pre-built Web UI assets into containerized environments. **No host dependencies other than Docker are required.**

#### 1. Start the Web UI (Default Service)
```bash
# Start the Web UI console via Docker Compose
docker compose up

# Or launch directly with the launcher script:
./umbra-web
# (or: ./umbra web)
```
Open your browser at **[http://localhost:8765/](http://localhost:8765/)** (or `http://127.0.0.1:8765/`).

> [!NOTE]
> Inside the container, the web server binds to `0.0.0.0:8765` to enable container port forwarding, and is published directly to your machine's loopback interface at `127.0.0.1:8765`. Server logs will explicitly show `http://localhost:8765/` for immediate browser access.

#### 2. Launch the Interactive Terminal UI (TUI)
```bash
# Launch interactive TUI console
./umbra-tui
# (or: docker compose run --rm tui)
```

#### 3. Run Headless Analysis (CLI)
```bash
# Analyze a packet capture file
./umbra captures/ikev2-decrypt-aes128ccm12.pcap
# (or: docker compose run --rm umbra captures/ikev2-decrypt-aes128ccm12.pcap)
```
This automatically produces:
* `<capture>.report.html`: Self-contained interactive HTML audit report.
* `<capture>.findings.json`: Machine-readable Schema 1.0 JSON findings.

#### 4. Run the Automated Test Suite
```bash
docker compose run --rm test
# (or: make test)
```

---

### Method 2: Running Natively (Without Docker)

If your machine has Python 3.10+ and `tshark` (Wireshark CLI) installed (Ubuntu, Debian, Fedora, Arch, NixOS, macOS Homebrew):

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate       # On Windows PowerShell: .venv\Scripts\Activate.ps1

# 2. Install Python package in editable mode
pip install -e .

# 3. Build Web UI frontend assets (Node.js 18+ required)
cd web-ui && npm ci && npm run build && cd ..

# 4. Launch Web UI server
python -m ipsec_analyzer.web
# Now navigate to http://localhost:8765/

# 5. Or launch the Terminal UI (TUI)
umbra-tui

# 6. Or run CLI analysis
umbra captures/ikev2-decrypt-aes128ccm12.pcap

# 7. Run Python unit tests
pytest -v
```

---

## Illuminated Evidence Web UI

The Umbra Web UI is an offline forensic instrument designed with strict terminal discipline and dark-mode aesthetics.

```
┌─────┬──────────────────┬────────────────────────────────────────────────────────┐
│ nav │ capture explorer │ top bar: capture · status · run · [sample data]        │
│ 5   │ (collapsible)    ├────────────────────────────────────────────────────────┤
│     │                  │ page content                                  [drawer] │
├─────┴──────────────────┴────────────────────────────────────────────────────────┤
│ status bar: capture · commit · engine · route · ? help                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Core Web Views

1. **Landing & Capture Inlet (`/`)**: Dropzone for `.pcap`/`.pcapng` uploads, real `/api/status` diagnostics (tshark version, rule counter, engine health), and provenance tier hierarchy reference.
2. **Overview (`/app/overview`)**: High-level cryptographic posture, primary verdicts banner, rule assessment summary, and provenance distribution chart.
3. **Findings & Passes (`/app/findings`)**: Full security audit findings table with severity indicators, frame-level scope, and RFC recommendations. Includes dedicated tab for clean passes.
4. **Tunnels & Elimination (`/app/tunnels`)**: Deep-dive into ESP Child SAs and SPI pairs. Visualizes the surviving cryptographic suite universe against mathematical elimination stages (e.g. padding block size GCD, ICV bounds).
5. **Claims & Coverage (`/app/claims`, `/app/coverage`)**:
   - **Claims Ledger**: Wire observations with exact provenance tier, confidence, and RFC framing caveats.
   - **Coverage Accounting**: Verification matrix tracking audited checks vs. observed data vs. coverage gaps.

### Keyboard Shortcuts (Web UI & TUI)

| Key | Action | Description |
|:---:|---|---|
| <kbd>1</kbd> | Overview | Jump to Overview screen |
| <kbd>2</kbd> | Findings | Jump to Findings & Assessment screen |
| <kbd>3</kbd> | Tunnels | Jump to Tunnels & Candidate Elimination screen |
| <kbd>4</kbd> | Claims | Jump to Claims Provenance screen |
| <kbd>5</kbd> | Coverage | Jump to Coverage Accounting screen |
| <kbd>/</kbd> | Filter / Search | Focus search/filter input |
| <kbd>a</kbd> | Analyze | Run analyzer on selected capture |
| <kbd>r</kbd> | Refresh | Rescan capture directory |
| <kbd>j</kbd> | View JSON | Open formatted Schema 1.0 JSON modal |
| <kbd>Ctrl</kbd>+<kbd>K</kbd> / <kbd>:</kbd> | Command Palette | Open quick navigation and action palette |
| <kbd>?</kbd> | Help | Open keyboard shortcut cheatsheet |
| <kbd>Esc</kbd> | Clear / Close | Dismiss drawer, modal, or search filter |

---

## Provenance Tier Lattice

The core principle of Umbra: **The more directly something was observed, the more light it gets.** Non-observable data is dark.

| Tier | Glyph | Confidence | Description |
|---|:---:|:---:|---|
| `OBSERVED` | ● Solid Disc | **1.0 (Certain)** | Directly parsed from packet bytes via `tshark` (IKE transforms, notify payloads, SPIs, IP headers). |
| `INFERRED_SIDE_CHANNEL` | ◕ 3/4 Disc | Calculated | Derived deterministically from wire framing arithmetic (e.g. ESP padding block size GCD, ICV length constraints). |
| `INFERRED_IMPLEMENTATION_DEFAULT` | ◑ 1/2 Disc | Reserved | Derived from known RFC or vendor implementation defaults (never assumed without explicit basis). |
| `ML_PREDICTION` | ◌ Dashed Ring | Statistical | Statistical/heuristic inference (strictly gated, never elevated). |
| `NOT_OBSERVABLE` | ⬡ Hatched Ring | **None (Gap)** | Wire evidence is insufficient (e.g. truncated capture, uniform sizes). Rendered as an em dash (`—`) gap. |

### Hard Security Guarantees

* **No Tier Promotion**: A derived finding's tier is strictly bounded by the weakest tier of its supporting inputs.
* **`OBSERVED` is strictly 1.0**: Certainty is never approximated as a percentage or bar.
* **`NOT_OBSERVABLE` carries no value**: Gaps are stated explicitly rather than filled with guesses or default values.
* **Zero Network Traffic**: No external CDN calls, remote fonts, or telemetry. Operates entirely air-gapped.
* **Sample Data Identification**: Any session utilizing mock fixtures displays a persistent, non-dismissible amber warning badge.

---

## Docker Configuration & Architecture

The repository provides production-hardened Docker configurations:

* **[`Dockerfile`](file:///C:/Users/garri/Desktop/sayitsus/SIH-160/ipsec/Dockerfile)**: Pinned Debian base with Python 3.11 and TShark `4.4.18-0+deb13u1`. Package is installed directly into site-packages.
* **[`Dockerfile.web`](file:///C:/Users/garri/Desktop/sayitsus/SIH-160/ipsec/Dockerfile.web)**: Multi-stage build pairing Node.js 20 frontend compilation with the Python analysis backend. Includes container healthcheck via standard library `urllib`.
* **[`docker-compose.yml`](file:///C:/Users/garri/Desktop/sayitsus/SIH-160/ipsec/docker-compose.yml)**: Profiles for `web` (default, port 8765), `tui` (interactive terminal), `umbra` (CLI), and `test` (Pytest).

### Port Mapping & Address Binding

When running containerized web services:
- Inside container: Server binds to `0.0.0.0:8765` so Docker port publishing functions correctly.
- Host machine: Port is forwarded to `127.0.0.1:8765:8765` (or `8765:8765`).
- Server logs clearly output: `Umbra Web UI listening at http://localhost:8765/ (http://127.0.0.1:8765/)`.

---

## Sample Captures

Real and synthetic test captures are located in `captures/`:

```bash
# Run headless analysis against sample vectors
./umbra captures/ikev2-decrypt-aes128ccm12.pcap
./umbra captures/ikev2-decrypt-3des-sha1_160.pcap
./umbra captures/ikev2-decrypt-aes256cbc.pcapng
```

To fetch the full Wireshark IKEv2 test suite, consult [`captures/FETCH.md`](file:///C:/Users/garri/Desktop/sayitsus/SIH-160/ipsec/captures/FETCH.md).

---

## License & Compliance

Umbra is built for passive security audits and network forensics. It performs zero active packet transmission, zero key extraction, and zero wire decryption.
