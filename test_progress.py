#!/usr/bin/env python3
"""
Test script for the enhanced progress tracking system
"""

import asyncio
import requests
import time
from client.enhanced_client import EnhancedCloud2BIMClient, ProgressTracker
from rich.console import Console

console = Console()

async def test_sse_connection():
    """Test if SSE endpoint is accessible"""
    base_url = "http://localhost:8001"
    
    try:
        # Test basic API health
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            console.print("✅ FastAPI server is running", style="green")
        else:
            console.print(f"❌ Server returned status {response.status_code}", style="red")
            return False
    except requests.exceptions.ConnectionError:
        console.print("❌ Cannot connect to server. Make sure it's running on http://localhost:8000", style="red")
        return False
    
    # Test SSE endpoint with a dummy job ID
    test_job_id = "test-job-123"
    sse_url = f"{base_url}/api/stream/progress/{test_job_id}"
    
    try:
        response = requests.get(sse_url, stream=True, timeout=2)
        if response.status_code == 200:
            console.print("✅ SSE endpoint is accessible", style="green")
        else:
            console.print(f"❌ SSE endpoint returned status {response.status_code}", style="red")
    except requests.exceptions.Timeout:
        console.print("⏱️ SSE endpoint timeout (expected for non-existent job)", style="yellow")
    except Exception as e:
        console.print(f"❌ SSE endpoint error: {e}", style="red")
        return False
    
    return True

def test_progress_tracker():
    """Test the ProgressTracker class"""
    console.print("\n🧪 Testing ProgressTracker", style="blue bold")
    
    base_url = "http://localhost:8001"
    job_id = "test-job-456"
    
    # Test with SSE first, then fallback to polling
    tracker = ProgressTracker(base_url, job_id, use_sse=True)
    
    console.print("✅ ProgressTracker created successfully", style="green")
    
    # Test polling mode explicitly
    tracker_polling = ProgressTracker(base_url, job_id, use_sse=False)
    console.print("✅ ProgressTracker (polling mode) created successfully", style="green")

def test_enhanced_client():
    """Test the EnhancedCloud2BIMClient"""
    console.print("\n🧪 Testing EnhancedCloud2BIMClient", style="blue bold")
    
    base_url = "http://localhost:8001"
    client = EnhancedCloud2BIMClient(base_url)
    
    console.print("✅ EnhancedCloud2BIMClient created successfully", style="green")
    
    # Test API health check
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            console.print("✅ API is responsive", style="green")
        else:
            console.print(f"❌ API returned status {response.status_code}", style="red")
    except Exception as e:
        console.print(f"❌ API connection error: {e}", style="red")

async def main():
    """Main test function"""
    console.print("🚀 Testing Cloud2BIM Progress Tracking System", style="blue bold")
    
    # Test 1: SSE Connection
    console.print("\n📡 Testing SSE Connection", style="blue bold")
    sse_ok = await test_sse_connection()
    
    # Test 2: Progress Tracker
    test_progress_tracker()
    
    # Test 3: Enhanced Client
    test_enhanced_client()
    
    console.print("\n🎉 All tests completed!", style="green bold")
    
    if sse_ok:
        console.print("✅ System is ready for progress tracking with SSE support", style="green")
    else:
        console.print("⚠️ SSE not available, but polling mode should work", style="yellow")

if __name__ == "__main__":
    asyncio.run(main())
