📄 README.md 
# FASTAPI

## 🚀 How to Run

### 1. Setup virtual environment

```bash
python3 -m venv app_env
source app_env/bin/activate
2. Install dependencies
pip install -r requirements.txt
3. Run FastAPI server
uvicorn src.main:app --reload --port 8089
🧠 WORD WORKER
▶️ Run Word Worker
chmod +x run_word_worker.sh
./run_word_worker.sh

Nhập số lượng worker khi được hỏi.

📂 Worker Logs

Logs được lưu tại thư mục:

logs/
 ├── word_worker_1.log
 ├── word_worker_2.log
 └── ...
👀 Xem log từng worker
Xem realtime
tail -f logs/word_worker_1.log
Xem toàn bộ log
cat logs/word_worker_1.log
Xem 50 dòng cuối
tail -n 50 logs/word_worker_1.log
🔍 Kiểm tra worker đang chạy
pgrep -af word_worker
❌ Kill tất cả worker
pkill -f word_worker