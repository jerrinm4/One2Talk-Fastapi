"""
Vote Load Testing Script
Generates bulk voting data with random users for testing purposes.
"""

import asyncio
import aiohttp
import random
import string
import time
from dataclasses import dataclass
from typing import List

# Configuration
BASE_URL = "http://localhost:4050"
CATEGORIES_ENDPOINT = f"{BASE_URL}/api/categories"
VOTE_ENDPOINT = f"{BASE_URL}/api/vote"

# Random data generators
FIRST_NAMES = ["John", "Jane", "Mike", "Sarah", "Alex", "Emma", "Chris", "Lisa", "David", "Amy", 
               "Tom", "Kate", "James", "Anna", "Ryan", "Olivia", "Ethan", "Sophia", "Noah", "Mia"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", 
              "Rodriguez", "Martinez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Lee"]


def generate_random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_random_email() -> str:
    name = ''.join(random.choices(string.ascii_lowercase, k=8))
    num = random.randint(100, 999)
    domain = random.choice(["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "test.com"])
    return f"{name}{num}@{domain}"


def generate_random_phone() -> str:
    return ''.join(random.choices(string.digits, k=10))


@dataclass
class TestResult:
    success: int = 0
    failed: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


async def fetch_categories(session: aiohttp.ClientSession) -> List[dict]:
    """Fetch all categories and their cards"""
    async with session.get(CATEGORIES_ENDPOINT) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("categories", [])
        else:
            raise Exception(f"Failed to fetch categories: {resp.status}")


async def submit_vote(session: aiohttp.ClientSession, categories: List[dict], result: TestResult):
    """Submit a single vote with random user data"""
    start = time.time()
    
    # Generate random user
    user = {
        "name": generate_random_name(),
        "email": generate_random_email(),
        "phone": generate_random_phone()
    }
    
    # Generate votes for each category (pick random card from each)
    votes = []
    for cat in categories:
        if cat.get("cards"):
            card = random.choice(cat["cards"])
            votes.append({
                "category_id": cat["id"],
                "card_id": card["id"]
            })
    
    payload = {
        "user": user,
        "votes": votes
    }
    
    try:
        async with session.post(VOTE_ENDPOINT, json=payload) as resp:
            elapsed = time.time() - start
            result.total_time += elapsed
            result.min_time = min(result.min_time, elapsed)
            result.max_time = max(result.max_time, elapsed)
            
            if resp.status == 200:
                result.success += 1
            else:
                result.failed += 1
                error_text = await resp.text()
                result.errors.append(f"Status {resp.status}: {error_text[:100]}")
    except Exception as e:
        elapsed = time.time() - start
        result.total_time += elapsed
        result.failed += 1
        result.errors.append(str(e)[:100])


async def run_batch(session: aiohttp.ClientSession, categories: List[dict], 
                    batch_size: int, result: TestResult):
    """Run a batch of concurrent votes"""
    tasks = [submit_vote(session, categories, result) for _ in range(batch_size)]
    await asyncio.gather(*tasks)


async def run_load_test(total_requests: int, concurrent_requests: int):
    """Main load test runner"""
    print("\n" + "="*60)
    print("🚀 VOTE LOAD TEST")
    print("="*60)
    print(f"📊 Total Requests: {total_requests}")
    print(f"⚡ Concurrent Requests: {concurrent_requests}")
    print("="*60 + "\n")
    
    result = TestResult()
    overall_start = time.time()
    
    async with aiohttp.ClientSession() as session:
        # Fetch categories first
        print("📥 Fetching categories...")
        try:
            categories = await fetch_categories(session)
            print(f"✅ Found {len(categories)} categories\n")
        except Exception as e:
            print(f"❌ Failed to fetch categories: {e}")
            return
        
        if not categories:
            print("❌ No categories found. Please add categories first.")
            return
        
        # Check if all categories have cards
        empty_cats = [c["name"] for c in categories if not c.get("cards")]
        if empty_cats:
            print(f"⚠️  Warning: Categories without cards: {empty_cats}")
        
        # Run load test in batches
        completed = 0
        print("🔄 Running load test...")
        
        while completed < total_requests:
            batch_size = min(concurrent_requests, total_requests - completed)
            await run_batch(session, categories, batch_size, result)
            completed += batch_size
            
            # Progress update
            progress = (completed / total_requests) * 100
            print(f"   Progress: {completed}/{total_requests} ({progress:.1f}%)", end="\r")
        
        print()  # New line after progress
    
    overall_time = time.time() - overall_start
    
    # Print results
    print("\n" + "="*60)
    print("📈 RESULTS")
    print("="*60)
    print(f"✅ Successful: {result.success}")
    print(f"❌ Failed: {result.failed}")
    print(f"📊 Success Rate: {(result.success / total_requests * 100):.1f}%")
    print("-"*60)
    print(f"⏱️  Total Time: {overall_time:.2f}s")
    print(f"⚡ Requests/sec: {total_requests / overall_time:.2f}")
    print("-"*60)
    print(f"📉 Min Response: {result.min_time * 1000:.2f}ms")
    print(f"📈 Max Response: {result.max_time * 1000:.2f}ms")
    print(f"📊 Avg Response: {(result.total_time / total_requests) * 1000:.2f}ms")
    print("="*60)
    
    # Print unique errors
    if result.errors:
        unique_errors = list(set(result.errors))[:5]  # Show max 5 unique errors
        print(f"\n⚠️  Sample Errors ({len(unique_errors)} unique):")
        for err in unique_errors:
            print(f"   • {err}")
    
    print()


def main():
    print("\n" + "="*60)
    print("       VOTE LOAD TESTING TOOL")
    print("       For Testing Purposes Only")
    print("="*60 + "\n")
    
    # Get user input
    try:
        total_requests = int(input("Enter total number of vote requests: "))
        concurrent_requests = int(input("Enter concurrent requests: "))
        
        if total_requests <= 0 or concurrent_requests <= 0:
            print("❌ Please enter positive numbers.")
            return
        
        if concurrent_requests > total_requests:
            concurrent_requests = total_requests
            print(f"⚠️  Concurrent requests adjusted to {concurrent_requests}")
        
        # Confirm
        print(f"\n⚠️  This will create {total_requests} test votes!")
        confirm = input("Continue? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("❌ Cancelled.")
            return
        
        # Run the test
        asyncio.run(run_load_test(total_requests, concurrent_requests))
        
    except ValueError:
        print("❌ Invalid input. Please enter numbers only.")
    except KeyboardInterrupt:
        print("\n\n❌ Test cancelled by user.")


if __name__ == "__main__":
    main()
