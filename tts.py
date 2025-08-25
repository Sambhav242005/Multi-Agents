import os
import json
import time
import tempfile
import subprocess
import shutil
import math
from typing import List
from pathlib import Path
import requests
import pygame
from env import GROQ_API_KEY

# TTS Configuration
SINGLE_VOICE = "Fritz-PlayAI"
TTS_MODEL = "playai-tts"
TTS_FORMAT = "wav"   # use wav for reliable concat

# Rate-limiting & chunking params (adjusted for Groq limits)
TPM_LIMIT = 1200                 # tokens-per-minute limit from your error message
MAX_TOKENS_PER_REQUEST = 600     # reduced to stay well under limits
SAFETY_MARGIN = 0.85             # increased safety margin
SECONDS_WINDOW = 60              # window length for TPM

# ----------------- helpers -----------------
def estimate_tokens(text: str) -> int:
    """
    More conservative token estimator: ~1 token per 3 characters.
    This is more conservative to avoid exceeding limits.
    """
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 3.0))  # Changed from 4.0 to 3.0

def chunk_text_by_tokens(text: str, max_tokens: int) -> List[str]:
    """
    Split text into chunks so each chunk estimates <= max_tokens.
    More aggressive splitting to ensure we stay under limits.
    """
    if estimate_tokens(text) <= max_tokens:
        return [text]

    # Try split by paragraphs first
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    current_tokens = 0

    def flush_current():
        nonlocal current, current_tokens
        if current.strip():
            chunks.append(current.strip())
        current = ""
        current_tokens = 0

    for p in paragraphs:
        p_tokens = estimate_tokens(p)
        if current_tokens + p_tokens <= max_tokens:
            current = (current + "\n\n" + p).strip()
            current_tokens += p_tokens
        else:
            # If single paragraph too large, split by sentences
            if p_tokens > max_tokens:
                sentences = [s.strip() for s in p.replace("\n"," ").split(". ") if s.strip()]
                for s in sentences:
                    s = s if s.endswith('.') else s + "."
                    s_tokens = estimate_tokens(s)
                    if current_tokens + s_tokens <= max_tokens:
                        current = (current + " " + s).strip()
                        current_tokens += s_tokens
                    else:
                        flush_current()
                        # if sentence itself larger than max, force-break it
                        if s_tokens > max_tokens:
                            # break by characters with smaller chunks
                            approx_chars = max_tokens * 3  # More conservative
                            i = 0
                            while i < len(s):
                                part = s[i:i+approx_chars]
                                chunks.append(part.strip())
                                i += approx_chars
                            current = ""
                            current_tokens = 0
                        else:
                            current = s
                            current_tokens = s_tokens
                # paragraph processed
            else:
                # close current and start with paragraph
                flush_current()
                current = p
                current_tokens = p_tokens
    flush_current()

    # If we still have chunks that are too large, split them further
    final_chunks = []
    for chunk in chunks:
        if estimate_tokens(chunk) > max_tokens:
            # Split this chunk into smaller pieces
            words = chunk.split()
            temp_chunk = ""
            temp_tokens = 0
            for word in words:
                word_tokens = estimate_tokens(word)
                if temp_tokens + word_tokens <= max_tokens:
                    temp_chunk = (temp_chunk + " " + word).strip()
                    temp_tokens += word_tokens
                else:
                    if temp_chunk:
                        final_chunks.append(temp_chunk)
                    temp_chunk = word
                    temp_tokens = word_tokens
            if temp_chunk:
                final_chunks.append(temp_chunk)
        else:
            final_chunks.append(chunk)

    return final_chunks

# ----------------- TTS + rate-limited synth -----------------
class TextToSpeech:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"Warning: pygame mixer init failed: {e}")

    def synthesize(self, text: str, voice: str = SINGLE_VOICE, response_format: str = TTS_FORMAT, timeout: int = 120) -> bytes:
        # Check token count before sending
        estimated_tokens = estimate_tokens(text)
        if estimated_tokens > MAX_TOKENS_PER_REQUEST:
            raise Exception(f"Text too large: {estimated_tokens} tokens (max {MAX_TOKENS_PER_REQUEST})")

        data = {
            "model": TTS_MODEL,
            "input": text,
            "voice": voice,
            "response_format": response_format
        }

        print(f"Sending TTS request with ~{estimated_tokens} tokens...")
        resp = requests.post(
            "https://api.groq.com/openai/v1/audio/speech",
            headers=self.headers,
            json=data,
            timeout=timeout,
        )

        if resp.status_code != 200:
            error_msg = resp.text
            print(f"TTS API error {resp.status_code}: {error_msg}")
            raise Exception(f"TTS API error {resp.status_code}: {error_msg}")
        return resp.content

# ----------------- orchestrator -----------------
def synthesize_text_with_rate_limit(tts: TextToSpeech, full_text: str, out_path: str = "podcast.mp3"):
    """
    Main function with improved rate limiting and chunking.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH. Please install ffmpeg to use this function.")

    total_estimated_tokens = estimate_tokens(full_text)
    print(f"Total text estimated tokens: {total_estimated_tokens}")

    # If single-shot is small, just do it
    if total_estimated_tokens <= int(MAX_TOKENS_PER_REQUEST * SAFETY_MARGIN):
        print("Single-shot synth fits token limit; sending one request.")
        try:
            audio_bytes = tts.synthesize(full_text, SINGLE_VOICE, response_format="mp3")
            with open(out_path, "wb") as f:
                f.write(audio_bytes)
            return out_path
        except Exception as e:
            print(f"Single-shot synthesis failed: {e}")
            # Fall back to chunking even for small texts
            print("Falling back to chunked synthesis...")

    # Otherwise, chunk the text
    max_req_tokens = int(MAX_TOKENS_PER_REQUEST * SAFETY_MARGIN)
    chunks = chunk_text_by_tokens(full_text, max_req_tokens)
    print(f"Text will be synthesized in {len(chunks)} chunks (est tokens total {total_estimated_tokens}).")

    # Print chunk sizes for debugging
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: ~{estimate_tokens(chunk)} tokens")

    # Prepare sliding-window token counter for TPM
    sent_tokens_window = []  # list of (timestamp_seconds, tokens_sent)
    tmp_wav_paths = []

    def window_tokens_sum() -> int:
        now = time.time()
        # purge old entries
        while sent_tokens_window and (now - sent_tokens_window[0][0]) > SECONDS_WINDOW:
            sent_tokens_window.pop(0)
        return sum(t for _, t in sent_tokens_window)

    for i, chunk in enumerate(chunks):
        chunk_tokens = estimate_tokens(chunk)

        # Wait until sending this chunk won't exceed TPM_LIMIT
        while True:
            current_window_tokens = window_tokens_sum()
            if current_window_tokens + chunk_tokens <= int(TPM_LIMIT * SAFETY_MARGIN):
                break
            # compute how long until earliest timestamp falls out of window
            oldest_ts = sent_tokens_window[0][0] if sent_tokens_window else time.time()
            wait_for = (oldest_ts + SECONDS_WINDOW) - time.time() + 0.1
            if wait_for > 0:
                print(f"TPM limit reached. Sleeping {wait_for:.1f}s before sending chunk {i+1}/{len(chunks)}...")
                time.sleep(wait_for)
            else:
                break

        # send chunk
        print(f"Synthesizing chunk {i+1}/{len(chunks)} (est {chunk_tokens} tokens)...")
        try:
            audio_bytes = tts.synthesize(chunk, SINGLE_VOICE, response_format="wav")
        except Exception as e:
            print(f"Failed to synthesize chunk {i+1}: {e}")
            continue  # Skip this chunk and continue with the next

        tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tf.write(audio_bytes)
        tf.flush()
        tf.close()
        tmp_wav_paths.append(tf.name)

        # record tokens sent at timestamp
        sent_tokens_window.append((time.time(), chunk_tokens))

    if not tmp_wav_paths:
        raise Exception("No audio chunks were successfully synthesized")

    # Concatenate WAV files using ffmpeg concat demuxer into final mp3
    list_tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
    try:
        for p in tmp_wav_paths:
            posix_path = Path(p).as_posix()
            escaped = posix_path.replace("'", "'\\''")
            list_tmp.write(f"file '{escaped}'\n")
        list_tmp.flush()
        list_tmp.close()

        combined_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        combined_wav.close()

        try:
            # concat into combined wav
            cmd_concat = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_tmp.name,
                "-c", "copy",
                combined_wav.name
            ]
            subprocess.run(cmd_concat, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # convert combined wav to mp3
            cmd_convert = [
                "ffmpeg", "-y",
                "-i", combined_wav.name,
                "-vn",
                "-ar", "44100",
                "-ac", "2",
                "-b:a", "192k",
                out_path
            ]
            subprocess.run(cmd_convert, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        finally:
            try:
                os.unlink(combined_wav.name)
            except Exception:
                pass
    finally:
        try:
            os.unlink(list_tmp.name)
        except Exception:
            pass

    # cleanup temps
    for p in tmp_wav_paths:
        try:
            os.unlink(p)
        except Exception:
            pass

    return out_path

# ----------------- Example usage -----------------
if __name__ == "__main__":
    tts = TextToSpeech(GROQ_API_KEY)

    # Use a shorter summary for testing
    summary = """
    Artificial intelligence has transformed many industries.
    Machine learning powers recommendation systems and autonomous vehicles.
    AI advancement raises excitement and concerns about societal impact.
    While AI solves complex problems, ethical considerations around privacy and bias remain important.
    Researchers develop transparent and fair AI systems aligned with human values.
    """

    try:
        out_file = synthesize_text_with_rate_limit(tts, summary, out_path="podcast.mp3")
        print("Saved to:", out_file)

        # play
        try:
            pygame.mixer.music.load(out_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(1)
        except Exception as e:
            print("Playback failed:", e)
    except Exception as e:
        print("Synthesis failed:", e)
