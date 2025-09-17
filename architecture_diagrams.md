# RiseNow DSPy System Architecture Diagrams

## 1. System Component Overview

```mermaid
graph TB
    subgraph "Entry Points"
        M[main.py]
        EP[example_pestle.py]
    end

    subgraph "Configuration Layer"
        CE[config/environment.py]
        CE -->|Validates| ENV[Environment Variables]
        CE -->|Configures| LC[LM Configs]
        CE -->|Sets| GS[GEPA Settings]
    end

    subgraph "Model Layer"
        MV[models/vendor.py]
        MP[models/pestle.py]
        MV -->|Defines| VS[VendorSearchResult]
        MV -->|Contains| VM[Vendor Model]
        MP -->|Defines| PA[PESTLEAnalysis]
        MP -->|Contains| PMA[PESTLEMarketAnalysis]
    end

    subgraph "Agent Layer"
        AP[agents/pestle_agent.py]
        AP -->|Creates| RA[ReAct Agent]
        AP -->|Or| COT[ChainOfThought]
    end

    subgraph "Tool Layer"
        WT[tools/web_tools.py]
        WT -->|Wraps| TC[Tavily Client]
        WT -->|Provides| DST[DSPy Tools]
        WT -->|Caches| PC[Page Cache]
    end

    subgraph "Metrics Layer"
        MS[metrics/scoring.py]
        MPS[metrics/pestle_scoring.py]
        MS -->|Creates| LJ[LLM Judge]
        MPS -->|Creates| PLJ[PESTLE Judge]
    end

    subgraph "Data Layer"
        DE[data/examples.py]
        DE -->|Provides| TS[Training Sets]
    end

    subgraph "Optimization"
        GEPA[GEPA Optimizer]
        GEPA -->|Uses| REF[Reflection LM]
        GEPA -->|Optimizes| AGT[Agents]
    end

    M --> CE
    M --> MV
    M --> MS
    M --> WT
    M --> AP
    M --> GEPA

    EP --> AP
    EP --> MPS

    style M fill:#e1f5fe
    style EP fill:#e1f5fe
    style GEPA fill:#fff3e0
    style TC fill:#f3e5f5
```

## 2. Main Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant Main
    participant Env as Environment
    participant DSPy
    participant GEPA
    participant ReAct
    participant Tools as Tavily Tools
    participant Judge as LLM Judge
    participant PESTLE as PESTLE Agent

    User->>Main: run_with_pestle()
    Main->>Env: validate_environment()
    Env-->>Main: API keys validated

    Main->>DSPy: configure(primary_lm)
    Main->>DSPy: create reflection_lm

    rect rgb(200, 230, 255)
        Note over Main,Judge: Vendor Discovery Phase
        Main->>Tools: create_dspy_tools()
        Tools-->>Main: [search, extract, crawl, map]

        Main->>ReAct: Create agent with tools
        Main->>Judge: create llm_judge_metric()

        Main->>GEPA: compile(react, trainset)
        loop Optimization iterations
            GEPA->>ReAct: Execute with example
            ReAct->>Tools: Search vendors
            Tools-->>ReAct: Results
            ReAct-->>GEPA: Prediction
            GEPA->>Judge: Evaluate quality
            Judge-->>GEPA: Score & feedback
            GEPA->>GEPA: Reflect & improve
        end
        GEPA-->>Main: Optimized program

        Main->>ReAct: Execute optimized search
        ReAct->>Tools: Multiple searches
        Tools-->>ReAct: Vendor data
        ReAct-->>Main: vendor_list
    end

    rect rgb(255, 230, 200)
        Note over Main,PESTLE: PESTLE Analysis Phase
        Main->>PESTLE: create_pestle_agent()
        Main->>PESTLE: optimize with GEPA
        Main->>PESTLE: Run analysis
        PESTLE->>Tools: Research market
        Tools-->>PESTLE: Market data
        PESTLE-->>Main: pestle_analysis
    end

    Main-->>User: Combined results
```

## 3. Tool Integration Architecture

```mermaid
graph LR
    subgraph "DSPy Tools Interface"
        DT[dspy.Tool]
        DT -->|search| TS[tavily_search]
        DT -->|extract| TE[tavily_extract]
        DT -->|crawl| TC[tavily_crawl]
        DT -->|map| TM[tavily_map_url]
    end

    subgraph "Tavily API Layer"
        TS --> TAV[TavilyClient]
        TE --> TAV
        TC --> TAV
        TM --> TAV
        TAV -->|HTTP| API[Tavily API]
    end

    subgraph "Caching Layer"
        TE --> CACHE[_page_cache]
        TC --> CACHE
        CACHE -->|Stores| FP[Fetched Pages]
    end

    subgraph "Results Processing"
        API --> RES[Raw Results]
        RES --> PROC[Process & Format]
        PROC --> OUT[Structured Output]
    end

    style DT fill:#e8f5e9
    style TAV fill:#fff3e0
    style CACHE fill:#fce4ec
```

## 4. GEPA Optimization Process

```mermaid
flowchart TB
    Start([Start GEPA])

    Init[Initialize with<br/>metric & reflection_lm]
    Init --> CreateEx[Create trainset examples]

    CreateEx --> Loop{More iterations?<br/>i < max_metric_calls}

    Loop -->|Yes| Execute[Execute student program]
    Execute --> Evaluate[Evaluate with metric]
    Evaluate --> Score[Get score & feedback]

    Score --> Reflect[Reflection LM analyzes:<br/>- What worked<br/>- What failed<br/>- How to improve]

    Reflect --> Update[Update prompts &<br/>few-shot examples]
    Update --> Loop

    Loop -->|No| Return[Return optimized program]
    Return --> End([End])

    Start --> Init

    style Start fill:#c8e6c9
    style End fill:#c8e6c9
    style Reflect fill:#fff9c4
    style Score fill:#ffccbc
```

## 5. Data Models & Signatures

```mermaid
classDiagram
    class Vendor {
        +String name
        +String website
        +String description
        +String justification
        +List~ContactEmail~ contact_emails
        +List~PhoneNumber~ phone_numbers
        +List~String~ countries_served
    }

    class ContactEmail {
        +String email
        +String description
    }

    class PhoneNumber {
        +String number
        +String description
    }

    class VendorSearchResult {
        <<DSPy Signature>>
        +String category [input]
        +Int n [input]
        +String country_or_region [input]
        +List~Vendor~ vendor_list [output]
    }

    class PESTLEAnalysis {
        +Dict~String,List~ political
        +Dict~String,List~ economic
        +Dict~String,List~ social
        +Dict~String,List~ technological
        +Dict~String,List~ legal
        +Dict~String,List~ environmental
        +String executive_summary
        +List~String~ opportunities
        +List~String~ threats
        +List~String~ strategic_recommendations
    }

    class PESTLEMarketAnalysis {
        <<DSPy Signature>>
        +String category [input]
        +String region [input]
        +List~String~ focus_areas [input]
        +PESTLEAnalysis pestle_analysis [output]
    }

    Vendor --> ContactEmail : contains
    Vendor --> PhoneNumber : contains
    VendorSearchResult --> Vendor : outputs
    PESTLEMarketAnalysis --> PESTLEAnalysis : outputs
```

## 6. Scoring & Metrics Flow

```mermaid
graph TD
    subgraph "Vendor Scoring"
        VS[vendor_list] --> VM[make_llm_judge_metric]
        VM --> VC[Validate contacts]
        VC --> VG[Check geographic coverage]
        VG --> VQ[Assess overall quality]
        VQ --> VSC[Score: 0.0-1.0]
        VSC --> VFB[Feedback text]
    end

    subgraph "PESTLE Scoring"
        PA[pestle_analysis] --> PM[make_pestle_llm_judge_metric]
        PM --> PC[Check completeness]
        PC --> PD[Assess depth]
        PD --> PR[Evaluate relevance]
        PR --> PSC[Score: 0.0-1.0]
        PSC --> PFB[Feedback text]
    end

    subgraph "GEPA Integration"
        VSC --> GEPA[GEPA Metric Wrapper]
        PSC --> GEPA
        GEPA --> PRED[Prediction object]
        PRED -->|score| OPT[Optimization loop]
        PRED -->|feedback| OPT
    end

    style VSC fill:#c5e1a5
    style PSC fill:#c5e1a5
    style GEPA fill:#ffecb3
```

## 7. Environment Configuration

```mermaid
graph LR
    subgraph "Required Environment Variables"
        OAI[OPENAI_API_KEY]
        TAV[TAVILY_API_KEY]
    end

    subgraph "Model Configuration"
        PM[DSPY_MODEL<br/>default: gpt-5-mini]
        PT[DSPY_TEMPERATURE<br/>default: 1.0]
        PMT[DSPY_MAX_TOKENS<br/>default: 100000]
    end

    subgraph "Reflection Model"
        RM[DSPY_REFLECTION_MODEL<br/>default: gpt-5]
        RT[DSPY_REFLECTION_TEMPERATURE<br/>default: 1.0]
        RMT[DSPY_REFLECTION_MAX_TOKENS<br/>default: 32000]
    end

    subgraph "GEPA Settings"
        GMC[GEPA_MAX_METRIC_CALLS<br/>default: 60]
        GNT[GEPA_NUM_THREADS<br/>default: 3]
    end

    OAI --> CONFIG[DSPy Configuration]
    TAV --> TOOLS[Tool Creation]
    PM --> CONFIG
    PT --> CONFIG
    PMT --> CONFIG
    RM --> REFL[Reflection LM]
    RT --> REFL
    RMT --> REFL
    GMC --> OPTIMIZER[GEPA Optimizer]
    GNT --> OPTIMIZER

    style OAI fill:#ffcdd2
    style TAV fill:#ffcdd2
```

## 8. Module Dependency Graph

```mermaid
graph BT
    subgraph "External Dependencies"
        DSPY[dspy]
        TAV[tavily]
        PYDANTIC[pydantic]
        MLFLOW[mlflow]
        HTTPX[httpx]
        BS4[beautifulsoup4]
    end

    subgraph "Core Modules"
        ENV[config/environment]
        VENDOR[models/vendor]
        PESTLE[models/pestle]
        TOOLS[tools/web_tools]
        SCORE[metrics/scoring]
        PSCORE[metrics/pestle_scoring]
        PAGENT[agents/pestle_agent]
        EXAMPLES[data/examples]
    end

    subgraph "Entry Points"
        MAIN[main.py]
        EXPESTLE[example_pestle.py]
    end

    ENV --> DSPY
    VENDOR --> PYDANTIC
    VENDOR --> DSPY
    PESTLE --> PYDANTIC
    PESTLE --> DSPY
    TOOLS --> TAV
    TOOLS --> HTTPX
    TOOLS --> BS4
    TOOLS --> ENV
    SCORE --> DSPY
    PSCORE --> DSPY
    PAGENT --> DSPY
    PAGENT --> TOOLS
    MAIN --> ENV
    MAIN --> VENDOR
    MAIN --> PESTLE
    MAIN --> TOOLS
    MAIN --> SCORE
    MAIN --> PSCORE
    MAIN --> PAGENT
    MAIN --> MLFLOW
    EXPESTLE --> PAGENT

    style MAIN fill:#e3f2fd
    style EXPESTLE fill:#e3f2fd
```

## Summary

This system implements a sophisticated vendor discovery and market analysis pipeline using:

1. **DSPy Framework**: For prompt optimization and agent orchestration
2. **GEPA Optimization**: Few-shot reflective learning to improve agent performance
3. **Tavily Integration**: Web search and extraction capabilities
4. **Dual Analysis**: Both vendor discovery and PESTLE market analysis
5. **LLM-based Evaluation**: Automated quality scoring with feedback
6. **Modular Architecture**: Clear separation of concerns across layers

The system is designed to be extensible, with clear interfaces between components and comprehensive configuration options through environment variables.