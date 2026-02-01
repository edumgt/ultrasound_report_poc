# Ultrasound Auto Report PoC (Windows / Python)

## Setup
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```powershell
python app.py
```

## Usage
- F2: Start/Stop
- F3: Reset
- Ctrl+Enter: Generate report
- Ctrl+S: Save session to data/sessions/<timestamp>/

## Notes
- STT model loads only when you press Start (F2).
- Default model is 'tiny' for fast/robust first test.
- For stability, CT2_FORCE_CPU_ISA is set to GENERIC if not already set.
