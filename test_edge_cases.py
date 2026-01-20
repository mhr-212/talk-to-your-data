#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edge case testing for Talk to Your Data system
Tests: empty queries, SQL injection, rate limiting, invalid auth, cache behavior, etc.
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:5000"

# Test result indicators
PASS_INDICATOR = "[PASS]"
FAIL_INDICATOR = "[FAIL]"
INFO_INDICATOR = "[INFO]"

def print_test(name: str):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")

def print_pass(msg: str):
    print(f"{PASS_INDICATOR} {msg}")

def print_fail(msg: str):
    print(f"{FAIL_INDICATOR} {msg}")

def print_info(msg: str):
    print(f"{INFO_INDICATOR} {msg}")

def test_empty_query():
    """Test 1: Empty query string"""
    print_test("Empty Query String")
    response = requests.post(f"{BASE_URL}/query", json={"question": ""})
    
    if response.status_code == 400:
        print_pass(f"Correctly rejected empty query (HTTP {response.status_code})")
        print_info(f"Response: {response.json().get('error', 'No error message')}")
    else:
        print_fail(f"Expected 400, got {response.status_code}: {response.text}")

def test_sql_injection():
    """Test 2: SQL injection attempts"""
    print_test("SQL Injection Prevention")
    
    injection_attempts = [
        "'; DROP TABLE sales; --",
        "' OR '1'='1",
        "sales'; INSERT INTO sales VALUES (999, 1000, 'hack', NOW()); --",
        "'; DELETE FROM sales; --",
        "UNION SELECT * FROM information_schema.tables",
    ]
    
    for payload in injection_attempts:
        response = requests.post(f"{BASE_URL}/query", json={"question": payload})
        if response.status_code == 400:
            print_pass(f"Blocked injection: {payload[:40]}...")
        else:
            print_fail(f"Injection not blocked: {payload[:40]}... (HTTP {response.status_code})")

def test_invalid_table():
    """Test 3: Query on non-existent table"""
    print_test("Invalid Table Name")
    response = requests.post(f"{BASE_URL}/query", json={"question": "what is in the nonexistent_table"})
    
    if response.status_code == 400:
        print_pass(f"Correctly rejected invalid table (HTTP {response.status_code})")
        error_msg = response.json().get('error', '')
        if 'Available tables:' in error_msg:
            print_pass("Error message includes available tables")
        else:
            print_fail("Error message should list available tables")
    else:
        print_fail(f"Expected 400, got {response.status_code}")

def test_special_characters():
    """Test 4: Queries with special characters"""
    print_test("Special Characters in Query")
    
    special_queries = [
        "what are sales with price > 1000 & region = 'US'?",
        "show me sales: 2024-01-15 to 2024-02-15",
        "query: (total sales) by region",
    ]
    
    for query in special_queries:
        response = requests.post(f"{BASE_URL}/query", json={"question": query})
        if response.status_code == 200:
            print_pass(f"Handled: {query[:50]}...")
        else:
            print_info(f"Query '{query[:50]}...' returned HTTP {response.status_code}")

def test_rate_limiting():
    """Test 5: Rate limiting (20 per minute on /query)"""
    print_test("Rate Limiting (20 requests/minute on /query)")
    
    print_info("Sending 25 rapid requests to test rate limit...")
    success_count = 0
    rate_limited = 0
    
    for i in range(25):
        response = requests.post(f"{BASE_URL}/query", 
            json={"question": "what are total sales"})
        
        if response.status_code == 200:
            success_count += 1
        elif response.status_code == 429:
            rate_limited += 1
            print_pass(f"Rate limited at request #{i+1} (HTTP 429)")
            break
    
    if rate_limited > 0:
        print_pass(f"Rate limiting triggered correctly")
    elif success_count >= 20:
        print_info(f"All {success_count} requests succeeded (may need more requests to trigger limit)")
    else:
        print_fail(f"Unexpected result: {success_count} success, {rate_limited} rate limited")

def test_invalid_auth():
    """Test 6: Invalid JWT token"""
    print_test("Invalid JWT Authentication")
    
    invalid_tokens = [
        "invalid.token.here",
        "Bearer invalid",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
    ]
    
    for token in invalid_tokens:
        response = requests.post(f"{BASE_URL}/query", 
            json={"question": "total sales"},
            headers={"Authorization": f"Bearer {token}"})
        
        # Endpoint should either reject auth or succeed with fallback
        if response.status_code in [401, 200]:
            print_pass(f"Handled invalid token: {token[:30]}...")
        else:
            print_fail(f"Unexpected status {response.status_code} for invalid token")

def test_cache_behavior():
    """Test 7: Cache hit/miss behavior"""
    print_test("Cache Hit/Miss Tracking")
    
    query = {"question": "what are total sales by region"}
    
    # First request - should miss cache
    print_info("First request (cache miss expected)...")
    response1 = requests.post(f"{BASE_URL}/query", json=query)
    t1 = response1.elapsed.total_seconds()
    print_info(f"First request took {t1*1000:.1f}ms")
    
    time.sleep(0.1)
    
    # Second request - should hit cache
    print_info("Second request (cache hit expected)...")
    response2 = requests.post(f"{BASE_URL}/query", json=query)
    t2 = response2.elapsed.total_seconds()
    print_info(f"Second request took {t2*1000:.1f}ms")
    
    if t2 < t1:
        print_pass(f"Cache improved performance: {t1*1000:.1f}ms → {t2*1000:.1f}ms")
    else:
        print_info(f"Cache timing: {t1*1000:.1f}ms → {t2*1000:.1f}ms (network jitter)")

def test_export_formats():
    """Test 8: Export with different formats"""
    print_test("Export Format Support")
    
    formats = ["csv", "json", "invalid"]
    query = {"question": "what are sales", "format": None}
    
    for fmt in formats:
        query["format"] = fmt
        response = requests.post(f"{BASE_URL}/query/export", json=query)
        
        if fmt in ["csv", "json"]:
            if response.status_code == 200:
                print_pass(f"Export as {fmt.upper()} successful")
            else:
                print_fail(f"Export as {fmt.upper()} failed (HTTP {response.status_code})")
        else:
            if response.status_code == 400:
                print_pass(f"Correctly rejected invalid format '{fmt}'")
            else:
                print_info(f"Invalid format '{fmt}' returned HTTP {response.status_code}")

def test_very_long_query():
    """Test 9: Very long query string"""
    print_test("Very Long Query String (1000+ chars)")
    
    long_query = "what are the total sales " * 100  # ~2500 characters
    response = requests.post(f"{BASE_URL}/query", json={"question": long_query})
    
    if response.status_code in [200, 400]:  # Either processes or rejects gracefully
        print_pass(f"Handled long query ({len(long_query)} chars) - HTTP {response.status_code}")
    else:
        print_fail(f"Unexpected response to long query: HTTP {response.status_code}")

def test_null_field():
    """Test 10: Null/missing required field"""
    print_test("Missing Required Fields")
    
    # Missing 'question' field entirely
    response = requests.post(f"{BASE_URL}/query", json={})
    if response.status_code == 400:
        print_pass(f"Correctly rejected missing 'question' field (HTTP {response.status_code})")
    else:
        print_fail(f"Expected 400 for missing field, got {response.status_code}")
    
    # Null value
    response = requests.post(f"{BASE_URL}/query", json={"question": None})
    if response.status_code == 400:
        print_pass(f"Correctly rejected null 'question' (HTTP {response.status_code})")
    else:
        print_fail(f"Expected 400 for null question, got {response.status_code}")

def test_saved_queries_edge_cases():
    """Test 11: Saved queries edge cases"""
    print_test("Saved Queries Edge Cases")
    
    # Try to get non-existent saved query
    response = requests.get(f"{BASE_URL}/saved-queries/nonexistent-id")
    if response.status_code == 404:
        print_pass("Correctly returned 404 for non-existent saved query")
    else:
        print_info(f"Non-existent query returned HTTP {response.status_code}")
    
    # Try to delete non-existent saved query
    response = requests.delete(f"{BASE_URL}/saved-queries/nonexistent-id")
    if response.status_code in [404, 200]:  # Either not found or idempotent delete
        print_pass(f"Delete non-existent query handled (HTTP {response.status_code})")
    else:
        print_fail(f"Unexpected HTTP {response.status_code} for delete")

def test_analytics_without_queries():
    """Test 12: Analytics dashboard when empty"""
    print_test("Analytics Dashboard")
    
    response = requests.get(f"{BASE_URL}/analytics/dashboard")
    if response.status_code == 200:
        data = response.json()
        print_pass(f"Analytics accessible: total={data.get('total_queries', 'N/A')}, "
                   f"success_rate={data.get('success_rate', 'N/A')}")
    else:
        print_fail(f"Analytics failed (HTTP {response.status_code})")

def test_health_check():
    """Test 13: Health check endpoint"""
    print_test("Health Check Endpoint")
    
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print_pass(f"Health check passed: {data.get('status', 'unknown')}")
        if data.get('database') == 'connected':
            print_pass("Database connected")
        else:
            print_fail(f"Database status: {data.get('database', 'unknown')}")
    else:
        print_fail(f"Health check failed (HTTP {response.status_code})")

def test_malformed_json():
    """Test 14: Malformed JSON payload"""
    print_test("Malformed JSON Payload")
    
    response = requests.post(f"{BASE_URL}/query", 
        data="{invalid json}", 
        headers={"Content-Type": "application/json"})
    
    if response.status_code == 400:
        print_pass(f"Correctly rejected malformed JSON (HTTP {response.status_code})")
    else:
        print_info(f"Malformed JSON returned HTTP {response.status_code}")

def test_concurrent_queries():
    """Test 15: Multiple queries in quick succession"""
    print_test("Concurrent Queries (Sequential Rapid Requests)")
    
    queries = [
        "what are total sales",
        "show sales by region",
        "how many sales records",
    ]
    
    times = []
    for i, query in enumerate(queries, 1):
        response = requests.post(f"{BASE_URL}/query", json={"question": query})
        elapsed = response.elapsed.total_seconds()
        times.append(elapsed)
        
        if response.status_code == 200:
            print_pass(f"Query {i} succeeded in {elapsed*1000:.1f}ms")
        else:
            print_fail(f"Query {i} failed with HTTP {response.status_code}")
    
    avg_time = sum(times) / len(times) if times else 0
    print_info(f"Average response time: {avg_time*1000:.1f}ms")

def main():
    print(f"\n{'='*60}")
    print(f"EDGE CASE TEST SUITE - Talk to Your Data")
    print(f"{'='*60}\n")
    
    try:
        # Run all tests
        test_empty_query()
        test_sql_injection()
        test_invalid_table()
        test_special_characters()
        test_rate_limiting()
        test_invalid_auth()
        test_cache_behavior()
        test_export_formats()
        test_very_long_query()
        test_null_field()
        test_saved_queries_edge_cases()
        test_analytics_without_queries()
        test_health_check()
        test_malformed_json()
        test_concurrent_queries()
        
        print(f"\n{'='*60}")
        print(f"TEST SUITE COMPLETE")
        print(f"{'='*60}\n")
        
    except requests.exceptions.ConnectionError:
        print(f"\n{FAIL_INDICATOR} ERROR: Could not connect to {BASE_URL}")
        print(f"  Make sure the Flask server is running on port 5000\n")
    except Exception as e:
        print(f"\n{FAIL_INDICATOR} ERROR: {e}\n")

if __name__ == "__main__":
    main()
