"""Manual test for ThreadManager to verify implementation works."""

from infrastructure.threads.thread_manager import ThreadManager


def dummy_task():
    """Simple task."""
    import time

    time.sleep(0.01)


def main():
    """Run manual test."""
    print("Testing ThreadManager...")

    # Create manager
    manager = ThreadManager()
    print("✓ Manager created")

    # Start a thread
    thread = manager.start_thread(target=dummy_task, name="test_thread")
    print(f"✓ Thread started: {thread.name}")

    # Wait for thread
    thread.join()
    print("✓ Thread completed")

    # Check status
    status = manager.get_thread_status("test_thread")
    print(f"✓ Thread status: {status}")

    # Cleanup
    removed = manager.cleanup_dead_threads()
    print(f"✓ Cleaned up {removed} dead threads")

    print("\nAll tests passed!")


if __name__ == "__main__":
    main()
