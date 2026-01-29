# Datathon26

# 🚢 Freight Decision Assistant

An interactive Streamlit application for vessel-cargo assignment optimization with real-time bunker price sensitivity analysis and AI-powered recommendations.

## 📋 Overview

The Freight Decision Assistant helps freight operators make data-driven decisions on vessel-cargo assignments by:
- Computing optimal voyage economics based on bunker prices, vessel speed, and port delays
- Ranking assignments by adjusted profit and TCE (Time Charter Equivalent)
- Providing sensitivity analysis for market scenarios
- Offering AI-powered insights via an integrated chatbot

## 🎯 Features

### 1. **Interactive Recommendation Engine** (Tab 1)
- Real-time profit and TCE calculations
- Dynamic recommendation status (ASSIGN / HEDGE / DECLINE)
- Adjustable inputs: VLSFO price, MGO price, speed, and waiting days
- Instant feedback on assignment profitability

### 2. **Top Assignments Ranking** (Tab 2)
- Ranks all vessel-cargo combinations by adjusted profit
- Displays top 10 most profitable assignments
- Highlights your current selection
- Accounts for all market inputs in real-time

### 3. **Risk & Context Analysis** (Tab 3)
- Risk assessment reports
- Market context and historical data
- JSON-formatted risk metrics

### 4. **AI Chatbot Assistant** (Tab 4)
- Powered by Ollama (local LLM)
- Natural language queries about voyage recommendations
- Contextual analysis of trade-offs

## 🛠️ Installation

### Setup

1. **Clone the repository:**
```bash
git clone https://github.com/MuskanDhamuria/Datathon26.git
cd Datathon26/cargill-datathon-2026
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Install Ollama (for chatbot):**
```bash
curl https://ollama.ai/install.sh | sh
```

5. **Pull a lightweight LLM model:**
```bash
ollama pull tinyllama
```

## 🚀 Usage

### Start Ollama (for chatbot)

In a separate terminal:
```bash
ollama serve
```

Then test connectivity:
```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"tinyllama","prompt":"Hello","stream":false}'
```

### Run the Streamlit App

```bash
cd cargill-datathon-2026/output/
streamlit run app_streamlit.py
```

The app will open at `http://localhost:8501`



## 📊 How It Works

### Input Parameters (Sidebar)
| Parameter | Range | Unit | Description |
|-----------|-------|------|-------------|
| **Vessel** | Dropdown | - | Select vessel from dataset |
| **Cargo / Route** | Dropdown | - | Select cargo route |
| **VLSFO Price** | 300-800 | $/MT | Bunker fuel price |
| **MGO Price** | 400-1000 | $/MT | Marine gas oil price |
| **Speed** | 9-16 | knots | Operating vessel speed |
| **Extra Waiting Days** | 0-30 | days | Port delays or diversions |

### Computation Flow

```
User Input
    ↓
run_partial_voyage() → Adjusted Economics
    ↓
compute_adjusted_profit() → Profit/TCE/Days
    ↓
Display Recommendation & Rankings
```

## 🤖 Chatbot Models

The app supports multiple Ollama models. Choose based on your system RAM:

| Model | Size | RAM Required | Speed |
|-------|------|--------------|-------|
| `tinyllama` | 1.3 GB | ~2 GB | Fast |
| `orca-mini` | 2.7 GB | ~3.5 GB | Balanced |
| `mistral` | 4 GB | ~5 GB | Better quality |
| `llama2` | 7 GB | ~8 GB | Best quality |

**Current setting:** `tinyllama` (for 3.3 GB RAM environments)

To change the model:
```python
# In app_streamlit.py, line ~180
"model": "tinyllama"  # Change this
```

## 🐛 Troubleshooting

### Ollama Connection Error
```
Error: Ollama not running. Start it with: `ollama serve`
```

**Solution:**
```bash
ollama serve  # In a separate terminal
```

### Ollama Out of Memory (500 Error)
```
Error: model requires more system memory (5.5 GiB) than is available (3.3 GiB)
```

**Solution:** Use a smaller model
```bash
ollama pull tinyllama
# Then restart the app
```


## 📞 Support

For issues or questions:
Contact Product Manager, Raye Yap, at rayeyap.work@gmail.com 

## 📝 License

This project is part of the Cargill Datathon 2026.

## 👥 Contributors

- **Muskan Dhamuria** - Developer, Cybersecurity VP
- **Tan Mei Yu** - Developer, HR VP
- **Raye Yap** - Developer, Product VP

---

