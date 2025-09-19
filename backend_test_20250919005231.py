import requests
import sys
import json
from datetime import datetime

class NYCTaxiAPITester:
    def __init__(self, base_url="https://delay-predict.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, timeout=timeout)
            elif method == 'POST':
                response = self.session.post(url, json=data, timeout=timeout)
            elif method == 'PUT':
                response = self.session.put(url, json=data, timeout=timeout)
            elif method == 'DELETE':
                response = self.session.delete(url, timeout=timeout)

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - {name}")
                
                # Try to parse JSON response
                try:
                    json_response = response.json()
                    print(f"   Response preview: {str(json_response)[:200]}...")
                    return True, json_response
                except:
                    print(f"   Response (text): {response.text[:200]}...")
                    return True, response.text
            else:
                print(f"❌ FAILED - {name}")
                print(f"   Expected status: {expected_status}, got: {response.status_code}")
                print(f"   Response: {response.text[:500]}...")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ FAILED - {name} (Timeout after {timeout}s)")
            return False, {}
        except Exception as e:
            print(f"❌ FAILED - {name} (Error: {str(e)})")
            return False, {}

    def test_health_check(self):
        """Test API health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET", 
            "health",
            200
        )
        
        if success and isinstance(response, dict):
            if response.get('status') == 'healthy':
                print("   ✓ Database connection verified")
                return True
            else:
                print(f"   ⚠️  Health status: {response.get('status')}")
        
        return success

    def test_data_ingestion(self):
        """Test taxi data ingestion"""
        success, response = self.run_test(
            "Data Ingestion",
            "POST",
            "ingest-taxi-data", 
            200,
            timeout=60  # Longer timeout for data processing
        )
        
        if success and isinstance(response, dict):
            trips_loaded = response.get('trips_loaded', 0)
            print(f"   ✓ Loaded {trips_loaded} taxi trips")
            if trips_loaded == 1000:
                print("   ✓ Expected 1000 trips loaded successfully")
                return True
            else:
                print(f"   ⚠️  Expected 1000 trips, got {trips_loaded}")
        
        return success

    def test_analytics_overview(self):
        """Test overview analytics endpoint"""
        success, response = self.run_test(
            "Analytics Overview",
            "GET",
            "analytics/overview",
            200
        )
        
        if success and isinstance(response, dict):
            # Verify required fields
            required_fields = [
                'total_trips', 'avg_trip_duration', 'avg_fare', 
                'total_revenue', 'delayed_trips_count', 'delay_percentage', 'avg_wait_time'
            ]
            
            missing_fields = [field for field in required_fields if field not in response]
            if not missing_fields:
                print("   ✓ All required analytics fields present")
                
                # Validate data types and ranges
                if response['total_trips'] > 0:
                    print(f"   ✓ Total trips: {response['total_trips']}")
                if 0 <= response['delay_percentage'] <= 100:
                    print(f"   ✓ Delay percentage: {response['delay_percentage']}%")
                if response['total_revenue'] > 0:
                    print(f"   ✓ Total revenue: ${response['total_revenue']}")
                
                return True
            else:
                print(f"   ❌ Missing fields: {missing_fields}")
        
        return success

    def test_hourly_analytics(self):
        """Test hourly analytics endpoint"""
        success, response = self.run_test(
            "Hourly Analytics",
            "GET",
            "analytics/hourly",
            200
        )
        
        if success and isinstance(response, list):
            if len(response) == 24:
                print("   ✓ 24 hourly data points returned")
                
                # Check first few entries
                for i, hour_data in enumerate(response[:3]):
                    if all(key in hour_data for key in ['hour', 'avg_wait_time', 'trip_count', 'delay_percentage']):
                        print(f"   ✓ Hour {hour_data['hour']}: {hour_data['avg_wait_time']}min wait, {hour_data['trip_count']} trips")
                    else:
                        print(f"   ❌ Hour {i} missing required fields")
                        return False
                
                return True
            else:
                print(f"   ❌ Expected 24 hours, got {len(response)}")
        
        return success

    def test_zone_analytics(self):
        """Test zone analytics endpoint"""
        success, response = self.run_test(
            "Zone Analytics", 
            "GET",
            "analytics/zones",
            200
        )
        
        if success and isinstance(response, list):
            if len(response) <= 20:  # Should return top 20 zones
                print(f"   ✓ {len(response)} zone analytics returned (max 20)")
                
                # Check first few zones
                for i, zone_data in enumerate(response[:3]):
                    required_fields = ['location_id', 'zone_name', 'trip_count', 'avg_wait_time', 'delay_percentage']
                    if all(key in zone_data for key in required_fields):
                        print(f"   ✓ {zone_data['zone_name']}: {zone_data['trip_count']} trips, {zone_data['delay_percentage']}% delayed")
                    else:
                        print(f"   ❌ Zone {i} missing required fields")
                        return False
                
                return True
            else:
                print(f"   ❌ Too many zones returned: {len(response)}")
        
        return success

    def test_business_logic(self):
        """Test business logic calculations"""
        print(f"\n🧮 Testing Business Logic...")
        
        # Get overview data
        success, overview = self.run_test("Overview for Logic Test", "GET", "analytics/overview", 200)
        if not success:
            return False
            
        # Get hourly data  
        success, hourly = self.run_test("Hourly for Logic Test", "GET", "analytics/hourly", 200)
        if not success:
            return False
            
        # Verify delay calculation logic
        if overview['delay_percentage'] >= 0 and overview['delay_percentage'] <= 100:
            print("   ✓ Delay percentage within valid range")
        else:
            print(f"   ❌ Invalid delay percentage: {overview['delay_percentage']}")
            return False
            
        # Verify total trips consistency
        total_hourly_trips = sum(hour['trip_count'] for hour in hourly)
        if total_hourly_trips == overview['total_trips']:
            print("   ✓ Trip counts consistent between overview and hourly data")
        else:
            print(f"   ⚠️  Trip count mismatch: overview={overview['total_trips']}, hourly_sum={total_hourly_trips}")
            
        # Check for realistic values
        if 5 <= overview['avg_trip_duration'] <= 120:  # 5-120 minutes reasonable
            print("   ✓ Average trip duration is realistic")
        else:
            print(f"   ⚠️  Unusual trip duration: {overview['avg_trip_duration']} minutes")
            
        if 1 <= overview['avg_fare'] <= 200:  # $1-200 reasonable for NYC
            print("   ✓ Average fare is realistic")
        else:
            print(f"   ⚠️  Unusual fare amount: ${overview['avg_fare']}")
            
        return True

def main():
    print("🚕 NYC Taxi Analytics API Testing")
    print("=" * 50)
    
    tester = NYCTaxiAPITester()
    
    # Test sequence
    tests = [
        ("Health Check", tester.test_health_check),
        ("Data Ingestion", tester.test_data_ingestion), 
        ("Analytics Overview", tester.test_analytics_overview),
        ("Hourly Analytics", tester.test_hourly_analytics),
        ("Zone Analytics", tester.test_zone_analytics),
        ("Business Logic", tester.test_business_logic)
    ]
    
    print(f"Running {len(tests)} test suites...\n")
    
    failed_tests = []
    for test_name, test_func in tests:
        try:
            if not test_func():
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            failed_tests.append(test_name)
    
    # Final results
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    print(f"Total API calls: {tester.tests_run}")
    print(f"Successful calls: {tester.tests_passed}")
    print(f"Failed calls: {tester.tests_run - tester.tests_passed}")
    
    if failed_tests:
        print(f"\n❌ Failed test suites: {', '.join(failed_tests)}")
        return 1
    else:
        print(f"\n✅ All {len(tests)} test suites passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())