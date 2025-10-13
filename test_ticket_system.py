#!/usr/bin/env python3
"""
Test script for the Ticket System functionality.
This script tests both the API endpoints and verifies the database integration.
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_feedback_api():
    """Test the feedback submission API"""
    print("🧪 Testing Feedback API Submission...")

    url = f"{BASE_URL}/tickets/api/feedback/"
    test_data = {
        "description": f"Test automated feedback - {datetime.now().isoformat()}",
        "ticket_type": "bug",
        "priority": "high",
        "page_url": "http://localhost:8000/test",
        "user_agent": "TestBot/1.0",
        "browser_info": json.dumps({
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "viewport": {"width": 1920, "height": 1080}
        })
    }

    try:
        response = requests.post(url, json=test_data)

        if response.status_code == 201:
            data = response.json()
            if data.get('success'):
                print("✅ Feedback API test PASSED")
                print(f"   📝 Ticket ID: {data['ticket']['id']}")
                print(f"   📊 Status: {data['ticket']['status']}")
                print(f"   🎯 Priority: {data['ticket']['priority']}")
                return True
            else:
                print("❌ Feedback API test FAILED - Success flag is False")
                print(f"   📄 Response: {data}")
                return False
        else:
            print(f"❌ Feedback API test FAILED - HTTP {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Feedback API test ERROR: {e}")
        return False

def test_demo_page():
    """Test the demo page accessibility"""
    print("🧪 Testing Demo Page...")

    url = f"{BASE_URL}/tickets/demo/"

    try:
        response = requests.get(url)

        if response.status_code == 200:
            if "Demo del Sistema di Feedback" in response.text:
                print("✅ Demo Page test PASSED")
                return True
            else:
                print("❌ Demo Page test FAILED - Content not found")
                return False
        else:
            print(f"❌ Demo Page test FAILED - HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Demo Page test ERROR: {e}")
        return False

def test_static_files():
    """Test if static files are accessible"""
    print("🧪 Testing Static Files...")

    static_files = [
        "/static/tickets/css/feedback-widget.css",
        "/static/tickets/js/feedback-widget.js"
    ]

    all_passed = True

    for static_file in static_files:
        url = f"{BASE_URL}{static_file}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"✅ Static file {static_file} - OK")
            else:
                print(f"❌ Static file {static_file} - HTTP {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"❌ Static file {static_file} - ERROR: {e}")
            all_passed = False

    if all_passed:
        print("✅ Static Files test PASSED")
    else:
        print("❌ Static Files test FAILED")

    return all_passed

def test_multiple_submissions():
    """Test multiple rapid submissions"""
    print("🧪 Testing Multiple Rapid Submissions...")

    url = f"{BASE_URL}/tickets/api/feedback/"
    success_count = 0
    total_tests = 3

    for i in range(total_tests):
        test_data = {
            "description": f"Bulk test feedback #{i+1} - {datetime.now().isoformat()}",
            "ticket_type": ["bug", "feature", "improvement"][i % 3],
            "priority": ["low", "medium", "high"][i % 3]
        }

        try:
            response = requests.post(url, json=test_data)
            if response.status_code == 201:
                data = response.json()
                if data.get('success'):
                    success_count += 1
                    print(f"   ✅ Submission {i+1}/3 - Ticket #{data['ticket']['id']}")
                else:
                    print(f"   ❌ Submission {i+1}/3 - Success flag False")
            else:
                print(f"   ❌ Submission {i+1}/3 - HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ Submission {i+1}/3 - ERROR: {e}")

    if success_count == total_tests:
        print("✅ Multiple Submissions test PASSED")
        return True
    else:
        print(f"❌ Multiple Submissions test FAILED - {success_count}/{total_tests} succeeded")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Ticket System Tests")
    print("=" * 50)

    tests = [
        ("Feedback API", test_feedback_api),
        ("Demo Page", test_demo_page),
        ("Static Files", test_static_files),
        ("Multiple Submissions", test_multiple_submissions)
    ]

    passed_tests = 0
    total_tests = len(tests)

    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        if test_func():
            passed_tests += 1
        print("-" * 30)

    print(f"\n📊 TEST RESULTS:")
    print(f"   ✅ Passed: {passed_tests}/{total_tests}")
    print(f"   ❌ Failed: {total_tests - passed_tests}/{total_tests}")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! The ticket system is working correctly.")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())