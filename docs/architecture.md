# Architecture

```mermaid
flowchart TD
    START --> SUP[Supervisor<br/>classify_intent]
    SUP -->|route| ING[Ingestion]
    SUP -->|route| EXT[Extraction]
    SUP -->|route| KG[Graph Update]
    SUP -->|route| QRY[Query]
    SUP -->|route| HYP[Hypothesis]
    SUP -->|route| EXP[Experiment]
    SUP -->|route| EVO[Evolution]
    ING --> CRT[Critic]
    EXT --> CRT
    KG --> CRT
    QRY --> CRT
    HYP --> CRT
    EXP --> CRT
    EVO --> CRT
    CRT -->|ok| END
    CRT -->|errors| RPL[Replan]
    RPL --> SUP

