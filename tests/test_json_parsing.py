"""
Test the improved JSON extraction logic
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.llm_client import clean_llm_response, extract_json

# Test cases
test_cases = [
    # Case 1: Clean JSON
    ('{"type": "test", "value": 123}', {"type": "test", "value": 123}),
    
    # Case 2: JSON with thinking tags
    ('<think>Let me think...</think>{"type": "test", "value": 456}', {"type": "test", "value": 456}),
    
    # Case 3: JSON with markdown
    ('```json\n{"type": "test", "value": 789}\n```', {"type": "test", "value": 789}),
    
    # Case 4: JSON with both
    ('<think>Analyzing...</think>```json\n{"result": "success"}\n```', {"result": "success"}),
    
    # Case 5: Nested thinking
    ('<THINK>First thought</THINK><think>Second</think>{"data": "ok"}', {"data": "ok"}),
    
    # Case 6: JSON with text before/after
    ('Some text before {"key": "value"} and after', {"key": "value"}),
]

print("Testing JSON Extraction Logic\n" + "="*50)

passed = 0
failed = 0

for i, (input_text, expected) in enumerate(test_cases, 1):
    result = extract_json(input_text)
    
    if result == expected:
        print(f"[PASS] Test {i}")
        passed += 1
    else:
        print(f"[FAIL] Test {i}")
        print(f"  Input: {input_text[:60]}...")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")
        failed += 1

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")

if failed == 0:
    print("[SUCCESS] All tests passed!")
else:
    print(f"[ERROR] {failed} test(s) failed")
    sys.exit(1)
