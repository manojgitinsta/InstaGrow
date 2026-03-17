import requests
import random
import os
from moviepy import VideoFileClip

from dotenv import load_dotenv

# Load env from root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

def fetch_pexels_video(keyword="motivation", output_path="temp_bg_video.mp4", use_local=False, result_index=0):
    """
    Fetches a vertical video from Pexels API or a local folder.
    result_index: Which video from the results to pick (0-based).
    """
    local_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "local_videos")
    
    # 1. Local Fallback Mode
    if use_local or PEXELS_API_KEY == "YOUR_PEXELS_API_KEY":
        print("📁 Using Local Video Library...")
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
            
        videos = [f for f in os.listdir(local_dir) if f.endswith(('.mp4', '.mov'))]
        if not videos:
            print(f"⚠️ No videos found in '{local_dir}'. Please add some .mp4 files.")
            return False
            
        chosen_video = random.choice(videos)
        local_path = os.path.join(local_dir, chosen_video)
        
        # Copy to output path
        import shutil
        shutil.copy(local_path, output_path)
        print(f"✅ Selected local video: {chosen_video}")
        return True

    # 2. Pexels API Mode
    print(f"[PEXELS] Searching Pexels for vertical video: {keyword}...")
    headers = {"Authorization": PEXELS_API_KEY}
    
    # Randomize page offset (1-5) for variety across runs
    random_page = random.randint(1, 5)
    url = f"https://api.pexels.com/videos/search?query={keyword}&orientation=portrait&per_page=40&page={random_page}"
    
    try:
        print(f"[API] Query: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("videos"):
            # If random page had no results, try page 1
            if random_page != 1:
                print(f"[WARN] Page {random_page} empty, trying page 1...")
                url = f"https://api.pexels.com/videos/search?query={keyword}&orientation=portrait&per_page=40&page=1"
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
            
            if not data.get("videos"):
                print(f"[WARN] No videos found on Pexels for query: '{keyword}'. Trying fallback...")
                if keyword != "cinematic nature":
                    return fetch_pexels_video("cinematic nature", output_path, use_local=use_local, result_index=result_index)
                return False
        
        total_found = len(data["videos"])
        print(f"[DONE] Found {total_found} videos on page {random_page}.")
        
        # RANDOMIZE: pick a random video from the results for maximum variety
        v_idx = random.randint(0, total_found - 1)
        video_data = data["videos"][v_idx]
        print(f"[INFO] Randomly selected video index {v_idx} out of {total_found}")
        
        # Find the best vertical MP4 link
        video_files = video_data.get("video_files", [])
        best_link = None
        
        # Sort by resolution descending, but prioritize vertical orientation
        for vf in sorted(video_files, key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True):
            w, h = vf.get('width', 0), vf.get('height', 0)
            if vf.get('file_type') == 'video/mp4' and h > w:
                best_link = vf.get('link')
                break
                
        # If no vertical found, just take the biggest MP4
        if not best_link:
            for vf in sorted(video_files, key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True):
                if vf.get('file_type') == 'video/mp4':
                    best_link = vf.get('link')
                    break
        
        if not best_link:
            print(f"[WARN] Could not extract a valid MP4 link from Pexels result index {v_idx}.")
            # If this specific index failed, try the first one as a last resort
            if v_idx != 0:
                print("[INFO] Retrying with index 0...")
                return fetch_pexels_video(keyword, output_path, use_local=use_local, result_index=0)
            return False
            
        print(f"[DOWNLOAD] Downloading Pexels video...")
        vid_response = requests.get(best_link, stream=True)
        vid_response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in vid_response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print("[DONE] Pexels video downloaded successfully.")
        return True
        
    except Exception as e:
        print(f"❌ Pexels API Error: {e}")
        return False

# Test the function
if __name__ == "__main__":
    fetch_pexels_video("ocean", "test_video.mp4", use_local=True)
