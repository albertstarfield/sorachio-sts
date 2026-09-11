# Sorachio-STS

**Speech To Speech AI Companion System**  
*Foundation for a future robotics companion platform*

Sorachio-STS is a fully local, real-time Speech-to-Speech AI companion that runs entirely on your machine with zero cloud dependencies. It uses a dual-LLM architecture — a fast Cognitive Gateway (LLM #1) for intent routing and emotion detection, and a Personality Core (LLM #2) for natural conversation — with automatic English/Indonesian bilingual support, streaming TTS that speaks before the LLM finishes generating, calibration-based adaptive echo cancellation, ChromaDB vector memory for cross-session recall, and VAD-based barge-in for natural turn-taking. Built as a scalable companion OS designed for future robotics expansion with ROS2 integration, sensor fusion, and multi-agent coordination.

---

### System in Action (CLI Showcase)

Here is a preview of how the interactive CLI behaves in voice mode, showcasing the real-time **Cognitive Gateway** status bar and state transitions.

#### 1. Full Voice/Run Mode (`python main.py run`)
In voice mode, the pipeline continuously monitors microphone input using VAD. Once speech is detected and transcribed, the Cognitive Gateway immediately computes the emotional state and topic, seamlessly transitioning into the streaming audio playback phase. Filler or hesitant speech (e.g., "Um...") is filtered out and marked as `X ignore`.

![Sorachio-STS Voice Mode](docs/ss-run.png)

#### 2. Interactive Text Mode (`python main.py text`)
In text mode, you can chat with the companion using keyboard inputs. Perfect for testing prompts and observing Cognitive Gateway filtering without needing a microphone.

![Sorachio-STS Text Mode](docs/ss-txt.png)

---

## Table of Contents

1. [Project Overview](docs/overview.md)
2. [Architecture Diagram](docs/architecture.md)
3. [Data Flow](docs/data-flow.md)
4. [Folder Structure](docs/folder-structure.md)
5. [Threading Model](docs/threading.md)
6. [Installation](docs/installation.md)
7. [Model Setup](docs/model-setup.md)
8. [Running the System](docs/running.md)
9. [Configuration Guide](docs/configuration.md)
10. [Cognitive Gateway Explained](docs/cognitive-gateway.md)
11. [Acoustic Intelligence Layer](docs/acoustic-layer.md)
12. [Bilingual Language Routing](docs/bilingual-routing.md)
13. [Streaming Pipeline Explained](docs/streaming.md)
14. [Memory Architecture](docs/memory.md)
15. [CLI Reference](docs/cli-reference.md)
16. [MBG System](docs/mbg-system.md)
17. [Troubleshooting](docs/troubleshooting.md)
18. [Future Robotics Expansion](docs/future-expansion.md)

---

## License

MIT License — see [LICENSE](LICENSE)

## Contributing

- Bug fixes and improvements
- New sensor/actuator integrations
- Alternative STT/TTS backends
- Wake word detection integration (e.g. `openwakeword`)
- ROS2 bridge
