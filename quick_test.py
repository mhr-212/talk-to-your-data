# -*- coding: utf-8 -*-
"""Quick edge case tests for Talk to Your Data"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test(name, func):
    print(f"\n{'='*60}\nTEST: {name}\n{'='*60}")
    try:
        func()
    except Exception as e:
        print(f"[ERROR] {e}")

def empty_query():
    r = requests.post(f"{BASE_URL}/query", json={"question": ""})
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
    assert r.status_code == 400, "Should reject empty query"
    print("[PASS] Empty query rejected")

def sql_injection():
    payloads = [
        "'; DROP TABLE sales; --",
        "' OR '1'='1",
        "UNION SELECT * FROM information_schema.tables"
    ]
    for p in payloads:
        r = requests.post(f"{BASE_URL}/query", json={"question": p})
        assert r.status_code == 400, f"Should block: {p}"
        print(f"[PASS] Blocked: {p[:40]}")

def invalid_table():
    r = requests.post(f"{BASE_URL}/query", json={"question": "select from fake_table"})
    print(f"Status: {r.status_code}")
    if r.status_code == 400:
        error = r.json().get('error', '')
        print(f"Error: {error[:100]}")
        if 'Available tables' in error:
            print("[PASS] Lists available tables in error")
        else:
            print("[INFO] Error: " + error)

def valid_query():
    r = requests.post(f"{BASE_URL}/query", json={"question": "what are total sales"})
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"SQL: {data.get('sql', 'N/A')}")
        print(f"Rows: {len(data.get('result', {}).get('rows', []))}")
        print("[PASS] Valid query executed")
    else:
        print(f"[FAIL] {r.json()}")

def cache_test():
    query = {"question": "total sales by region"}
    import time
    
    # First request
    start = time.time()
    r1 = requests.post(f"{BASE_URL}/query", json=query)
    t1 = time.time() - start
    
    time.sleep(0.1)
    
    # Second request (cached)
    start = time.time()
    r2 = requests.post(f"{BASE_URL}/query", json=query)
    t2 = time.time() - start
    
    print(f"First: {t1*1000:.1f}ms, Second: {t2*1000:.1f}ms")
    if t2 < t1:
        print(f"[PASS] Cache improved performance by {((t1-t2)/t1*100):.0f}%")
    else:
        print(f"[INFO] Times similar (may be network jitter)")

def health_check():
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"DB Status: {data.get('database', 'unknown')}")
    print(f"Fallback: {data.get('config', {}).get('dev_fallback_mode', 'unknown')}")
    assert r.status_code == 200
    print("[PASS] Health check OK")

def export_test():
    query = {"question": "show sales", "format": "csv"}
    r = requests.post(f"{BASE_URL}/query/export", json=query)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
        print(f"Size: {len(r.content)} bytes")
        print("[PASS] CSV export works")
    else:
        print(f"[FAIL] {r.text[:100]}")

def null_field():
    r = requests.post(f"{BASE_URL}/query", json={})
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
    assert r.status_code == 400
    print("[PASS] Missing field rejected")

def analytics():
    r = requests.get(f"{BASE_URL}/analytics/dashboard")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Total queries: {data.get('total_queries', 0)}")
        print(f"Success rate: {data.get('success_rate', 0):.1f}%")
        print("[PASS] Analytics accessible")

def long_query():
    long = "what are sales " * 200  # ~3000 chars
    r = requests.post(f"{BASE_URL}/query", json={"question": long})
    print(f"Status: {r.status_code}")
    print(f"Query length: {len(long)} chars")
    if r.status_code in [200, 400]:
        print("[PASS] Handled long query gracefully")

print("\n" + "="*60)
print("EDGE CASE TEST SUITE")
print("="*60)

test("1. Empty Query", empty_query)
test("2. SQL Injection", sql_injection)
test("3. Invalid Table", invalid_table)
test("4. Valid Query", valid_query)
test("5. Cache Performance", cache_test)
test("6. Health Check", health_check)
test("7. Export CSV", export_test)
test("8. Null Field", null_field)
test("9. Analytics", analytics)
test("10. Long Query", long_query)

print("\n" + "="*60)
print("TESTS COMPLETE")
print("="*60 + "\n")
