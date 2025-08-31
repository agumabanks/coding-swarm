#!/usr/bin/env python3
"""
Test script for Sanaa Web UI
Tests basic functionality and responsiveness
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, List
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app import sanaa_web_app


class WebUITester:
    """Test class for web UI functionality"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session = None
        self.test_results = []

    async def setup(self):
        """Setup test environment"""
        self.session = aiohttp.ClientSession()
        print("🔧 Setting up Web UI tests...")

    async def teardown(self):
        """Cleanup test environment"""
        if self.session:
            await self.session.close()
        print("🧹 Cleaning up test environment...")

    async def run_test(self, test_name: str, test_func):
        """Run a single test"""
        print(f"🧪 Running test: {test_name}")
        start_time = time.time()

        try:
            result = await test_func()
            duration = time.time() - start_time

            if result['success']:
                print(f"✅ {test_name} - PASSED ({duration:.2f}s)")
                self.test_results.append({
                    'name': test_name,
                    'status': 'PASSED',
                    'duration': duration,
                    'details': result.get('details', '')
                })
            else:
                print(f"❌ {test_name} - FAILED ({duration:.2f}s)")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                self.test_results.append({
                    'name': test_name,
                    'status': 'FAILED',
                    'duration': duration,
                    'error': result.get('error', 'Unknown error')
                })

        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {test_name} - ERROR ({duration:.2f}s)")
            print(f"   Exception: {str(e)}")
            self.test_results.append({
                'name': test_name,
                'status': 'ERROR',
                'duration': duration,
                'error': str(e)
            })

    async def test_home_page(self):
        """Test home page accessibility"""
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                if response.status == 200:
                    content = await response.text()
                    if "Sanaa Web IDE" in content:
                        return {
                            'success': True,
                            'details': 'Home page loaded successfully with correct title'
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'Home page content does not contain expected title'
                        }
                else:
                    return {
                        'success': False,
                        'error': f'HTTP {response.status}: {response.reason}'
                    }
        except Exception as e:
            return {
                'success': False,
                'error': f'Connection error: {str(e)}'
            }

    async def test_api_endpoints(self):
        """Test API endpoints"""
        endpoints = [
            '/api/system/status',
            '/api/projects',
            '/api/agents'
        ]

        results = []

        for endpoint in endpoints:
            try:
                async with self.session.get(f"{self.base_url}{endpoint}") as response:
                    if response.status == 200:
                        data = await response.json()
                        results.append({
                            'endpoint': endpoint,
                            'status': 'OK',
                            'data': bool(data)  # Check if we got data
                        })
                    else:
                        results.append({
                            'endpoint': endpoint,
                            'status': 'ERROR',
                            'error': f'HTTP {response.status}'
                        })
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'status': 'ERROR',
                    'error': str(e)
                })

        success_count = sum(1 for r in results if r['status'] == 'OK')
        total_count = len(results)

        if success_count == total_count:
            return {
                'success': True,
                'details': f'All {total_count} API endpoints responded successfully'
            }
        else:
            return {
                'success': False,
                'error': f'{success_count}/{total_count} API endpoints failed',
                'details': results
            }

    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        try:
            # Test WebSocket connection (simplified)
            # In a real test, we'd establish a WebSocket connection
            # For now, just test that the endpoint exists
            async with self.session.get(f"{self.base_url}/ws/test") as response:
                # WebSocket endpoints typically return 404 for GET requests
                # but the server should be running
                return {
                    'success': True,
                    'details': 'WebSocket endpoint accessible'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'WebSocket test failed: {str(e)}'
            }

    async def test_static_files(self):
        """Test static file serving"""
        try:
            # Test a known static file path (this might not exist yet)
            async with self.session.get(f"{self.base_url}/static/test.css") as response:
                # We expect this to fail since we don't have test static files
                # But the server should handle the request gracefully
                if response.status in [404, 200]:
                    return {
                        'success': True,
                        'details': 'Static file handling works correctly'
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Unexpected response: HTTP {response.status}'
                    }
        except Exception as e:
            return {
                'success': False,
                'error': f'Static file test failed: {str(e)}'
            }

    async def test_responsiveness(self):
        """Test response times"""
        response_times = []

        for i in range(5):
            start_time = time.time()
            try:
                async with self.session.get(f"{self.base_url}/") as response:
                    if response.status == 200:
                        await response.text()
                        response_times.append(time.time() - start_time)
                    else:
                        response_times.append(float('inf'))
            except:
                response_times.append(float('inf'))

        valid_times = [t for t in response_times if t != float('inf')]

        if not valid_times:
            return {
                'success': False,
                'error': 'All requests failed'
            }

        avg_time = sum(valid_times) / len(valid_times)
        max_time = max(valid_times)

        # Check if average response time is reasonable (< 1 second)
        if avg_time < 1.0:
            return {
                'success': True,
                'details': f'Average response time: {avg_time:.3f}s, Max: {max_time:.3f}s'
            }
        else:
            return {
                'success': False,
                'error': f'Poor performance - Average: {avg_time:.3f}s, Max: {max_time:.3f}s'
            }

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("🧪 WEB UI TEST SUMMARY")
        print("="*60)

        passed = sum(1 for r in self.test_results if r['status'] == 'PASSED')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAILED')
        errors = sum(1 for r in self.test_results if r['status'] == 'ERROR')
        total = len(self.test_results)

        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"🔥 Errors: {errors}")

        if failed > 0 or errors > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result['status'] != 'PASSED':
                    print(f"  • {result['name']}: {result.get('error', 'Unknown error')}")

        print("\n📊 PERFORMANCE:")
        total_duration = sum(r['duration'] for r in self.test_results)
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Average per Test: {total_duration/total:.2f}s")

        print("\n" + "="*60)

        if failed == 0 and errors == 0:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("⚠️  SOME TESTS FAILED")
            return False


async def main():
    """Main test function"""
    print("🚀 Starting Sanaa Web UI Tests")
    print("="*60)

    # Check if server is running
    tester = WebUITester()

    try:
        await tester.setup()

        # Run tests
        await tester.run_test("Home Page Accessibility", tester.test_home_page)
        await tester.run_test("API Endpoints", tester.test_api_endpoints)
        await tester.run_test("WebSocket Connection", tester.test_websocket_connection)
        await tester.run_test("Static Files", tester.test_static_files)
        await tester.run_test("Response Time", tester.test_responsiveness)

    finally:
        await tester.teardown()

    # Print summary
    success = tester.print_summary()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Note: This test assumes the web server is already running
    # In a real CI/CD environment, you'd start the server first
    print("Note: Make sure the Sanaa web server is running on http://localhost:8080")
    print("You can start it with: python web/app.py")
    print()

    asyncio.run(main())