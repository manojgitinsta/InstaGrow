"""
Daily Runner — Scheduled carousel (4 PM) + reel (10 PM) posting.
═══════════════════════════════════════════════════════════════════════════════════
Usage:
    python run_daily.py                # Full scheduled run (waits for 4PM + 10PM)
    python run_daily.py --now          # Run both immediately (no scheduling)
    python run_daily.py --dry-run      # Generate only, skip posting
    python run_daily.py --carousel     # Only run carousel
    python run_daily.py --reel         # Only run reel
    python run_daily.py --daemon       # Run as background daemon (repeats daily)
"""

import os
import sys
import time
from datetime import datetime, timedelta

# Ensure Windows console handles emojis/unicode correctly
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# ─── Schedule Config ────────────────────────────────────────────────────────────

STORY_TIME = os.getenv("STORY_POST_TIME", "09:00")        # 9 AM
CAROUSEL_TIME = os.getenv("CAROUSEL_POST_TIME", "16:00")  # 4 PM
REEL_TIME = os.getenv("REEL_POST_TIME", "22:00")          # 10 PM


def parse_time(time_str):
    """Parse HH:MM string into (hour, minute) tuple."""
    parts = time_str.strip().split(":")
    return int(parts[0]), int(parts[1])


def wait_until(target_hour, target_minute, label=""):
    """Wait until a specific time today (or tomorrow if already passed)."""
    now = datetime.now()
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

    if target <= now:
        # Already passed today — if running with --now, skip waiting
        print(f"   {label} time ({target_hour:02d}:{target_minute:02d}) already passed today.")
        return False

    wait_secs = (target - now).total_seconds()
    hours = int(wait_secs // 3600)
    mins = int((wait_secs % 3600) // 60)

    print(f"\n   Waiting for {label} at {target_hour:02d}:{target_minute:02d}...")
    print(f"   ({hours}h {mins}m from now)")

    # Wait in 60-second intervals so we can show progress
    while datetime.now() < target:
        remaining = (target - datetime.now()).total_seconds()
        if remaining > 60:
            time.sleep(60)
        else:
            time.sleep(max(0, remaining))

    print(f"   [{label}] Time reached! Starting...")
    return True


# ─── Pipeline Functions ─────────────────────────────────────────────────────────

def run_story(dry_run=False):
    """Fetch positive news, generate story image, and post."""
    print("\n" + "=" * 60)
    print("  PHASE 0: MORNING STORY")
    print("=" * 60)

    try:
        from agents.story_agent import run_story_agent
        success = run_story_agent(dry_run=dry_run)
        if success:
            print("  Story phase complete!")
        else:
            print("  Story phase had issues.")
        return success
    except Exception as e:
        print(f"  Story phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_carousel(dry_run=False):
    """Generate and post a carousel."""
    print("\n" + "=" * 60)
    print("  PHASE 1: CAROUSEL POST")
    print("=" * 60)

    try:
        from agents.carousel_agent import run_carousel_agent
        success = run_carousel_agent(dry_run=dry_run)
        if success:
            print("  Carousel phase complete!")
        else:
            print("  Carousel phase had issues.")
        return success
    except Exception as e:
        print(f"  Carousel phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_auto_commenter_phase(dry_run=False):
    """Scan and reply to recent comments."""
    print("\n" + "=" * 60)
    print("  PHASE 1.5: ENGAGEMENT AUTO-RESPONDER")
    print("=" * 60)

    try:
        from agents.auto_commenter import run_auto_commenter
        # If the whole pipeline is in dry_run, the commenter is too
        # If pipeline is live, commenter is live
        run_auto_commenter(dry_run=dry_run)
        print("  Engagement phase complete!")
        return True
    except Exception as e:
        print(f"  Engagement phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_reel(dry_run=False):
    """Generate and post a reel."""
    print("\n" + "=" * 60)
    print("  PHASE 2: REEL GENERATION + POST")
    print("=" * 60)

    try:
        # Step 1: Generate quotes if needed
        from agents.generate_quotes_agent import generate_quotes
        print("\n  Generating fresh quotes...")
        generate_quotes()

        # Step 2: Generate reel content
        from agents.content_flood import generate_flood_content
        print("\n  Generating cinematic reel...")
        generate_flood_content()

        if dry_run:
            print("\n  DRY RUN — Skipping reel posting.")
            return True

        # Step 3: Post to Instagram
        from agents.instagram_agent import run_agent
        print("\n  Posting reel to Instagram...")
        run_agent()

        print("  Reel phase complete!")
        return True

    except Exception as e:
        print(f"  Reel phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─── Main Scheduler ─────────────────────────────────────────────────────────────

def run_scheduled(dry_run=False, only_carousel=False, only_reel=False, only_story=False):
    """Run with scheduled timing: story at 9AM, carousel at 4PM, reel at 10PM."""
    story_h, story_m = parse_time(STORY_TIME)
    carousel_h, carousel_m = parse_time(CAROUSEL_TIME)
    reel_h, reel_m = parse_time(REEL_TIME)

    results = {}
    
    # Story at 9 AM
    if not only_carousel and not only_reel:
        print(f"\n  STORY scheduled for {STORY_TIME}")
        wait_until(story_h, story_m, "STORY")
        results['story'] = run_story(dry_run=dry_run)

    # Carousel at 4 PM
    if not only_reel and not only_story:
        print(f"\n  CAROUSEL scheduled for {CAROUSEL_TIME}")
        wait_until(carousel_h, carousel_m, "CAROUSEL")
        results['carousel'] = run_carousel(dry_run=dry_run)
        
        # Run engagement sweeper after carousel
        print(f"\n  Checking engagement...")
        results['engagement'] = run_auto_commenter_phase(dry_run=dry_run)

    # Reel at 10 PM
    if not only_carousel:
        print(f"\n  REEL scheduled for {REEL_TIME}")
        wait_until(reel_h, reel_m, "REEL")
        results['reel'] = run_reel(dry_run=dry_run)

    return results


def run_now(dry_run=False, only_carousel=False, only_reel=False, only_story=False):
    """Run immediately without waiting."""
    results = {}

    if not only_carousel and not only_reel:
        results['story'] = run_story(dry_run=dry_run)
        if not only_story:
            print("\n  Waiting 30 seconds between posts...")
            time.sleep(30)

    if not only_reel and not only_story:
        results['carousel'] = run_carousel(dry_run=dry_run)
        results['engagement_1'] = run_auto_commenter_phase(dry_run=dry_run)
        if not only_carousel and not only_story:
            print("\n  Waiting 30 seconds between posts...")
            time.sleep(30)

    if not only_carousel and not only_story:
        results['reel'] = run_reel(dry_run=dry_run)
        results['engagement_2'] = run_auto_commenter_phase(dry_run=dry_run)

    return results


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    only_carousel = "--carousel" in args
    only_reel = "--reel" in args
    only_story = "--story" in args
    run_immediately = "--now" in args
    daemon_mode = "--daemon" in args

    print("=" * 60)
    print(f"  INSTAGROW DAILY RUNNER")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    if run_immediately:
        print(f"  Schedule: IMMEDIATE (--now)")
    else:
        print(f"  Schedule: Story @ {STORY_TIME} | Carousel @ {CAROUSEL_TIME} | Reel @ {REEL_TIME}")
    if only_carousel:
        print(f"  Scope: Carousel only")
    elif only_reel:
        print(f"  Scope: Reel only")
    elif only_story:
        print(f"  Scope: Story only")
    else:
        print(f"  Scope: Full (Story + Carousel + Reel)")
    print("=" * 60)

    if daemon_mode:
        print("\n  DAEMON MODE: Will repeat daily")
        while True:
            results = run_scheduled(dry_run, only_carousel, only_reel, only_story)
            _print_summary(results)
            # Sleep until next day's story time
            nxt_h, nxt_m = parse_time(STORY_TIME)
            tomorrow = datetime.now().replace(
                hour=nxt_h, minute=nxt_m, second=0
            ) + timedelta(days=1)
            sleep_secs = (tomorrow - datetime.now()).total_seconds()
            print(f"\n  Next run in {sleep_secs / 3600:.1f} hours...")
            time.sleep(max(0, sleep_secs))
    elif run_immediately:
        results = run_now(dry_run, only_carousel, only_reel, only_story)
        _print_summary(results)
    else:
        results = run_scheduled(dry_run, only_carousel, only_reel, only_story)
        _print_summary(results)


def _print_summary(results):
    print("\n" + "=" * 60)
    print("  DAILY RUN SUMMARY")
    print("=" * 60)
    for key, success in results.items():
        status = "  Success" if success else "  Issues"
        print(f"  {key.upper()}: {status}")
    print("=" * 60)


if __name__ == "__main__":
    main()
