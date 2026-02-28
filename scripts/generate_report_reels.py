import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.generate_reels import create_cinematic_reel

def generate_report_reels():
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    print("🎬 Generating reels from the Instagram Strategy Report...\n")

    reels_data = [
        {
            "name": "Idea 1: The Weight of Unseen Effort",
            "hook": "They see the victory.",
            "reflective": "They don't see the war.",
            "query": "cinematic dark mountains",
            "file": "report_reel_1.mp4"
        },
        {
            "name": "Idea 2: The Forge of Adversity",
            "hook": "Comfort never forged a warrior.",
            "reflective": "Pressure breaks the weak, but molds the unyielding.",
            "query": "dark stormy ocean waves",
            "file": "report_reel_2.mp4"
        },
        {
            "name": "Idea 3: Beyond the Horizon of Doubt",
            "hook": "Doubt whispers promises of comfort.",
            "reflective": "But courage sees beyond the visible.",
            "query": "cinematic dark mist forest",
            "file": "report_reel_3.mp4"
        }
    ]

    results = []
    for i, data in enumerate(reels_data):
        print(f"\n=========================================")
        print(f"Generating: {data['name']}")
        print(f"=========================================")
        
        output_path = os.path.join(output_dir, data['file'])
        
        # In case previous broken runs left a corrupted file
        if os.path.exists(output_path):
            os.remove(output_path)
            
        result_path = create_cinematic_reel(
            hook_line=data['hook'],
            reflective_line=data['reflective'],
            scene_query=data['query'],
            output_path=output_path,
            video_index=i # cycle through pexels results so they don't all look the same
        )
        
        if result_path:
            results.append(result_path)
            print(f"✅ Success: {data['name']}")
        else:
            print(f"❌ Failed: {data['name']}")

    print("\n🎉 All target reels generated!")
    for r in results:
        print(f" - {r}")

if __name__ == "__main__":
    generate_report_reels()
