import re
import time
import random
import csv
import ollama
from playwright.sync_api import sync_playwright

print("DEBUG 1: Imports successful")

# --- CONFIGURATION ---
SEARCH_QUERY = "Junior Python ML"
LOCATION = "Remote"
MAX_JOBS = 1
MAX_DESC_CHARS = 6000

try:
    with open('base_cv.txt', 'r', encoding='utf-8') as file:
        BASE_CV = file.read().strip()
    print("DEBUG 2: base_cv.txt loaded successfully")
except FileNotFoundError:
    BASE_CV = "Fallback CV text."
    print("DEBUG 2: base_cv.txt NOT found, using fallback")

def extract_and_tailor(job_text):
    print("DEBUG 4: Sending text to Ollama...")
    prompt = f"Extract Title, Company, and tailor this CV: {BASE_CV} to this job: {job_text[:MAX_DESC_CHARS]}. Output strictly as: Title: [x]\nCompany: [y]\nTailored_CV: [z]"
    response = ollama.chat(model="qwen2.5:7b", messages=[{"role": "user", "content": prompt}])
    print("DEBUG 5: Ollama responded!")
    return response["message"]["content"]

def parse_output(text):
    title = re.search(r"Title:\s*(.+)", text, re.IGNORECASE)
    company = re.search(r"Company:\s*(.+)", text, re.IGNORECASE)
    cv = re.search(r"Tailored_CV:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    return (
        title.group(1).strip() if title else "Unknown",
        company.group(1).strip() if company else "Unknown",
        re.sub(r"\s+", " ", cv.group(1)).strip() if cv else "",
    )

def scrape_and_process():
    results = []
    print("DEBUG 3: Launching Playwright browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        print("DEBUG 3b: Browser launched. Opening new page...")
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        print(f"DEBUG 3c: Going to Indeed for {SEARCH_QUERY}...")
        page.goto(f"https://www.indeed.com/jobs?q={SEARCH_QUERY}&l={LOCATION}")
        time.sleep(5)
        print("DEBUG 3d: Page loaded. Looking for jobs...")

        job_cards = page.query_selector_all(".job_seen_beacon") or page.query_selector_all("ul.jobsearch-ResultsList > li")
        
        if not job_cards:
            print("DEBUG ERROR: No job cards found!")
        else:
            print(f"DEBUG: Found {len(job_cards)} job cards. Processing first {MAX_JOBS}...")

        for i, card in enumerate(job_cards[:MAX_JOBS]):
            try:
                print(f"\n--- Processing Job {i+1} ---")
                link = card.query_selector("h2 a") or card.query_selector("a")
                job_url = link.get_attribute("href") if link else page.url
                
                print("DEBUG: Clicking job to get full description...")
                try:
                    link.click()
                    page.wait_for_selector("#jobDescriptionText", timeout=5000)
                    description = page.inner_text("#jobDescriptionText")
                except:
                    description = card.inner_text()
                
                print("DEBUG: Got description. Calling AI...")
                ai_response = extract_and_tailor(description)
                title, company, tailored_cv = parse_output(ai_response)
                
                results.append({"Title": title, "Company": company, "URL": job_url, "Tailored_CV": tailored_cv})
                print(f"DEBUG: Job {i+1} complete!")
                time.sleep(3)
            except Exception as e:
                print(f"DEBUG ERROR on job {i+1}: {e}")
                continue

        browser.close()
    return results

def save_report(data):
    with open("indeed_job_report.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Title", "Company", "URL", "Tailored_CV"])
        writer.writeheader()
        writer.writerows(data)
    print("✅ Report saved to indeed_job_report.csv")

if __name__ == "__main__":
    print("🚀 Starting Indeed automation...")
    save_report(scrape_and_process())

