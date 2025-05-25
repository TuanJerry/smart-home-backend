from scipy.io.wavfile import write
from sklearn.metrics.pairwise import cosine_similarity
from app.utils import AImodel, model_ready

import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import torch
import time
import os
import re

# Mẫu câu lệnh và intent tương ứng
intent_templates = {
    "bật đèn": "TURN_ON_LIGHT",
    # "mở đèn": "TURN_ON_LIGHT",
    # "đèn bật": "TURN_ON_LIGHT",
    "không tắt đèn": "TURN_ON_LIGHT",
    # "đèn sáng": "TURN_ON_LIGHT",
    "tối quá": "TURN_ON_LIGHT",
    "không thấy gì": "TURN_ON_LIGHT",
    "tối như mực": "TURN_ON_LIGHT",
    "tối rồi": "TURN_ON_LIGHT",
    # "đèn tắt": "TURN_OFF_LIGHT",
    "tắt đèn": "TURN_OFF_LIGHT",
    # "đèn không sáng": "TURN_OFF_LIGHT",
    # "đèn không mở": "TURN_OFF_LIGHT",
    "không bật đèn": "TURN_OFF_LIGHT",
    "sáng quá": "TURN_OFF_LIGHT",
    "chói quá": "TURN_OFF_LIGHT",
    "sáng rồi": "TURN_OFF_LIGHT",

    "bật quạt": "TURN_ON_FAN",
    "tắt quạt": "TURN_OFF_FAN",
    # "quạt chạy": "TURN_ON_FAN",
    "quạt không ngừng": "TURN_ON_FAN",
    "nóng quá": "TURN_ON_FAN",
    "hầm quá": "TURN_ON_FAN",
    # "mở quạt": "TURN_ON_FAN",
    # "quạt mở": "TURN_ON_FAN",
    "quạt ngừng": "TURN_OFF_FAN",
    # "quạt không chạy": "TURN_OFF_FAN",
    "không tắt quạt": "TURN_ON_FAN",
    # "quạt không mở": "TURN_OFF_FAN",
    "không bật quạt": "TURN_OFF_FAN",
    "lạnh quá": "TURN_OFF_FAN",
    # "rét quá": "TURN_OFF_FAN",

    "mở cửa": "OPEN_DOOR",
    "mở khóa cửa": "OPEN_DOOR",
    "tắt khóa cửa": "OPEN_DOOR",
    # "cửa mở": "OPEN_DOOR",
    "không đóng cửa": "OPEN_DOOR",
    # "tôi chuẩn bị ra ngoài": "OPEN_DOOR",
    "tôi sắp ra ngoài": "OPEN_DOOR",
    "tôi chuẩn bị về nhà": "OPEN_DOOR",
    # "tôi đi ra ngoài": "OPEN_DOOR",
    "đóng cửa": "CLOSE_DOOR",
    "khóa cửa": "CLOSE_DOOR",
    # "cửa đóng": "CLOSE_DOOR",
    "không mở cửa": "CLOSE_DOOR",
    "tôi ra ngoài rồi": "CLOSE_DOOR",
    # "tôi về nhà rồi": "CLOSE_DOOR",
    "tôi vô nhà rồi": "CLOSE_DOOR",
    # "tôi về rồi": "CLOSE_DOOR",

    "bật chế độ ban đêm": "TURN_ON_LIGHT_AND_TURN_ON_FAN_AND_CLOSE_DOOR",
    "tắt chế độ ban đêm": "TURN_OFF_LIGHT_AND_TURN_OFF_FAN_AND_OPEN_DOOR",
    "bật chế độ an ninh": "CLOSE_DOOR_AND_TURN_ON_FACE_DETECTION",
    "tắt chế độ an ninh": "OPEN_DOOR_AND_TURN_OFF_FACE_DETECTION",
    "bật tất cả thiết bị": "TURN_ON_LIGHT_AND_TURN_ON_FAN_AND_OPEN_DOOR",
    "tắt tất cả thiết bị": "TURN_OFF_LIGHT_AND_TURN_OFF_FAN_AND_CLOSE_DOOR",
}

class VoiceRecordingService:
    def __init__(self):
        os.makedirs("app/voices", exist_ok=True)
        # Lưu sẵn embeddings của intent mẫu
        self.template_embeddings = None

    async def init_embeddings(self, intent_templates: dict):
        if self.template_embeddings is None:
            self.template_embeddings = {
                k: await self.get_sentence_embedding(k)
                for k in intent_templates.keys()
            }

    # Voice recording service for handling audio input into strings
    def countdown_timer(self, duration):
        for remaining in range(duration, 0, -1):
            print(f"⏳ Còn lại: {remaining} giây", end='\r')
            time.sleep(1)
        print("⏳ Còn lại: 0 giây         ")

    def is_valid_audio(self, file_path, min_rms=0.01, max_silence_ratio=0.9):
        audio, sr = sf.read(file_path)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)  # Convert to mono

        rms = np.sqrt(np.mean(audio**2))
        if rms < min_rms:
            print("⚠️ Âm lượng quá nhỏ.")
            return False

        frame_len = 2048
        hop_len = 512
        frame_count = 1 + (len(audio) - frame_len) // hop_len
        energies = np.array([
            np.sqrt(np.mean(audio[i*hop_len:i*hop_len+frame_len]**2))
            for i in range(frame_count)
        ])
        silence_ratio = np.mean(energies < min_rms)

        if silence_ratio > max_silence_ratio:
            print("⚠️ Quá nhiều khoảng im lặng.")
            return False

        return True

    def preprocess_audio(self, file_path, processed_path="app/voices/processed.wav", target_sr=16000):
        audio, sr = sf.read(file_path)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)  # Convert to mono

        if sr != target_sr:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
            sr = target_sr

        # Chuẩn hóa
        audio = audio / np.max(np.abs(audio))

        sf.write(processed_path, audio, sr, subtype='PCM_16')
        print("✅ Đã tiền xử lý âm thanh.")
        return processed_path

    def record_audio(self, filename="app/voices/recorded.wav", duration=3, fs=16000):
        print(f"🎙️ Đang ghi âm trong {duration} giây...")

        timer_thread = threading.Thread(target=self.countdown_timer, args=(duration,))
        timer_thread.start()

        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        timer_thread.join()

        write(filename, fs, recording)
        print("✅ Ghi âm xong.")

        start_time = time.time()

        # return filename, start_time

        # Kiểm tra chất lượng
        if self.is_valid_audio(filename):
            return self.preprocess_audio(filename), start_time
            # return filename, start_time
        else:
            print("❌ Âm thanh không đạt yêu cầu. Hãy thử lại.")
            return None, start_time
        
    # Text from audio handling by NLP model
    async def get_sentence_embedding(self, sentence: str) -> torch.Tensor:
        """Chuyển câu thành vector embedding trung bình (mean pooling)."""
        await model_ready.wait()  # ✅ Chờ mô hình sẵn sàng
        input_ids = AImodel.tokenizer.encode(sentence, return_tensors='pt')
        with torch.no_grad():
            outputs = AImodel.nlp_model(input_ids)
            last_hidden_state = outputs[0]  # (1, seq_len, hidden_dim)
            sentence_embedding = last_hidden_state.mean(dim=1)  # (1, hidden_dim)
        return sentence_embedding.squeeze(0)  # (hidden_dim,)

    # # Hàm embedding
    # def get_sentence_embedding(sentence: str) -> torch.Tensor:
    #     input_ids = AImodel.tokenizer.encode(sentence, return_tensors='pt')
    #     with torch.no_grad():
    #         outputs = AImodel.nlp_model(input_ids)
    #         last_hidden_state = outputs[0]
    #         sentence_embedding = last_hidden_state.mean(dim=1)
    #     return sentence_embedding.squeeze(0)

    # Trích xuất điều kiện số (temperature, humidity, time)
    def extract_numeric_condition(self, sentence: str) -> dict:
        patterns = [
           # Nhiệt độ
            (# vd: nhiệt độ khoảng 30 độ C
                r"(nhiệt độ|nóng|lạnh) .*? (\d+)? .*?",
                "temperature"
            ),
            (# vd: nhiệt độ 30 độ C
                r"(nhiệt độ|nóng|lạnh) (\d+)? .*?",
                "temperature"
            ),
            (# vd: nhiệt độ cao/thấp
                r"(nhiệt độ|nóng|lạnh) .*?",
                "temperature"
            ),
            (
                r"(nóng|lạnh)",
                "temperature"
            ),
            # Độ ẩm
            (# vd: độ ẩm khoảng 70%
                r"(độ ẩm|nồm|khô) .*? (\d+)?",
                "humidity"
            ),
            (# vd: độ ẩm 70%
                r"(độ ẩm|nồm|khô) (\d+)? .*?",
                "humidity"
            ),
            (# vd: độ ẩm cao/thấp/khô/ẩm/ít/nhiều
                r"(độ ẩm|nồm|khô) .*?",
                "humidity"
            ),
            (
                r"(ẩm|nồm|khô)",
                "humidity"
            ),
            # Ánh sáng
            (
                r"(sáng|tối)",
                "light"
            ),
            # Quạt
            (# vd: mức khoảng 70%
                r"(mức|tốc độ|quay) .*? (\d+)?",
                "fan"
            ),
            (# vd: mức 70%
                r"(mức|tốc độ|quay) (\d+)? .*?",
                "fan"
            ),
            (# vd: mức 1/2/3
                r"(mức|tốc độ) (\d+)?",
                "fan"
            ),
            (# vd: mức cao/thấp/vừa
                r"(mức|tốc độ|quay) .*?",
                "fan"
            ),
            (
                r"(nhanh|mạnh|cao|chậm|yếu|thấp|vừa|thường)",
                "fan"
            ),
            # Thời gian
            (
                r"(sau)\s*"
                r"(?:(?P<hour>\d+)\s*(giờ|h|g)\s*)?"
                r"(?:(?P<minute>\d+)\s*(phút|p|m)\s*)?"
                r"(?:(?P<second>\d+)\s*(giây|s))?",
                "time"
            )
        ]

        for pattern, sensor in patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            # print(pattern)
            if match:
                val = None
                unit = ""
                op = "="
                if any(kw in sentence for kw in ["trên", "nóng", "nhiều hơn", "ẩm", "nồm", "cao"]):
                    op = ">"
                    if "độ ẩm" in sentence and not any(kw in sentence for kw in ["trên", "nhiều hơn", "nồm", "cao"]):
                        op = "="
                elif any(kw in sentence for kw in ["dưới", "lạnh", "ít hơn", "khô", "thấp"]):
                    op = "<"
                print(f"match: {match.groups()}")
                if sensor == "time":
                    unit = "seconds"
                    hour = int(match.group("hour")) if match.group("hour") else 0
                    minute = int(match.group("minute")) if match.group("minute") else 0
                    second = int(match.group("second")) if match.group("second") else 0
                    val = hour * 3600 + minute * 60 + second
                elif sensor == "temperature":
                    unit = "°C"
                    if len(match.groups()) > 1:
                        if match.group(2):
                            op = "="
                            val = int(match.group(2))
                            if any(kw in sentence for kw in ["độ k", "°k", "°ka", "độ ka", "độ ca", "°ca"]) and "độ khoảng" not in sentence:
                                val -= 273
                    elif any(kw in sentence for kw in ["nóng", "cao"]):
                        val = 30
                    elif any(kw in sentence for kw in ["lạnh", "thấp"]):
                        val = 20
                elif sensor == "humidity":
                    unit = "%"
                    if len(match.groups()) > 1:
                        if match.group(2):
                            op = "="
                            val = int(match.group(2))
                    elif any(kw in sentence for kw in ["khô", "thấp", "ít"]):
                        val = 30
                    elif "nồm" in sentence:
                        val = 90
                    elif any(kw in sentence for kw in ["cao", "nhiều"]):
                        val = 70
                    elif "ẩm" in sentence and "độ ẩm" not in sentence:
                        val = 70
                elif sensor == "light":
                    unit = "lux"
                    if "tối" in sentence:
                        op = "<"
                        val = 20
                    elif "sáng" in sentence:
                        op = ">"
                        val = 30
                elif sensor == "fan":
                    unit = "%"
                    if len(match.groups()) > 1:
                        if match.group(2):
                            op = "="
                            val = int(match.group(2))
                            if val == 1:# 1 là mức thấp nhất
                                val = 30
                            elif val == 2:
                                val = 70
                            elif val == 3:
                                val = 100
                    elif any(kw in sentence for kw in ["nhanh", "mạnh", "cao"]):
                        val = 100
                    elif any(kw in sentence for kw in ["chậm", "yếu", "thấp"]):

                        val = 30
                    elif any(kw in sentence for kw in ["vừa", "thường"]):

                        val = 70
                return {
                    "sensor": sensor,
                    "op": op,
                    "value": val,
                    "unit": unit
                }

        return None

    async def nlp_pipeline(self, sentence: str) -> dict:
        await self.init_embeddings(intent_templates=intent_templates)
        condition = self.extract_numeric_condition(sentence)
        sentence_wo_condition = re.sub(r"khi .*|nếu .*|lúc .*|khi trời .*|nếu trời .*|lúc trời .*|sau .*", "", sentence).strip()

        emb = (await self.get_sentence_embedding(sentence_wo_condition)).unsqueeze(0)
        sims = {}
        for template, template_emb in self.template_embeddings.items():
            template_emb = template_emb.unsqueeze(0)
            sim = cosine_similarity(emb, template_emb)[0][0]
            sims[template] = sim
        best_template = max(sims, key=sims.get)

        return {
            "sentence": sentence,
            "intent": intent_templates[best_template],
            "matched_template": best_template,
            "similarity": float(sims[best_template]),
            "condition": condition
        }

voice_service = VoiceRecordingService()