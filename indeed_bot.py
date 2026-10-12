import time
import random
import csv
import ollama
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
SEARCH_QUERY = "Data Analyst"
LOCATION = "Remote"
BASE_CV = "5 years Python, SQL, Tableau. Experience in data cleaning and dashboard creation."
MAX_JOBS = 3 

# --- 1. LLM FUNCTION ---
def extract_and_tailor(raw_card_text):
    prompt = f"""
    You are an expert resume writer and data extractor. 
    Here is the raw text from a job posting: 
    {raw_card_text}
    
    Base CV: {BASE_CV}
    
    Task:
    1. Extract the Job Title and Company Name from the raw text.
    2. Rewrite the Base CV to perfectly match the job description. Highlight relevant skills and add keywords.
    
    Output STRICTLY in this exact format (no extra text):
    Title: [Job Title]
    Company: [Company Name]
    Tailored_CV: [Your rewritten CV text here]
    """
    response = ollama.chat(model='qwen2.5:14b', messages=[{'role': 'user', 'content': prompt}])
    return response['message']['content']

# --- 2. BROWSER AUTOMATION ---
def scrape_and_process():
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        url = f"https://www.indeed.com/jobs?q={SEARCH_QUERY}&l={LOCATION}"
        page.goto(url)
        time.sleep(random.uniform(4, 6))
        
        # Try to find job cards (Indeed changes these often, so we have a fallback)
        job_cards = page.query_selector_all('.job_seen_beacon')
        if not job_cards:
            job_cards = page.query_selector_all('ul.jobsearch-ResultsList > li')
            
        for i, card in enumerate(job_cards[:MAX_JOBS]):
            try:
                # Extract ALL text from the card (immune to HTML changes)
                raw_text = card.inner_text()
                
                # Extract URL from the first link in the card
                link_el = card.query_selector('a')
                job_url = link_el.get_attribute('href') if link_el else page.url
                if job_url.startswith('/'):
                    job_url = f"https://www.indeed.com{job_url}"
                
                print(f"Processing job {i+1}...")
                
                # Send raw text to Qwen to extract info and tailor CV
                qwen_output = extract_and_tailor(raw_text)
                
                # Parse Qwen's output
                title, company, tailored_cv = "Unknown", "Unknown", ""
                for line in qwen_output.split('\n'):
                    if line.startswith("Title:"): title = line.replace("Title:", "").strip()
                    elif line.startswith("Company:"): company = line.replace("Company:", "").strip()
                    elif line.startswith("Tailored_CV:"): tailored_cv = line.replace("Tailored_CV:", "").strip()
                
                results.append({
                    'Title': title,
                    'Company': company,
                    'URL': job_url,
                    'Tailored_CV': tailored_cv.replace('\n', ' ')
                })
                
                # Random delay to mimic human behavior
                time.sleep(random.uniform(4, 8))
                
            except Exception as e:
                print(f"Error on job {i+1}: {e}")
                continue
                
        browser.close()
    return results

# --- 3. SAVE REPORT ---
def save_report(data):
    with open('indeed_job_report.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Title', 'Company', 'URL', 'Tailored_CV'])
        writer.writeheader()
        writer.writerows(data)
    print("✅ Report saved to indeed_job_report.csv")

if __name__ == "__main__":
    print("🚀 Starting Indeed automation on macOS...")
    jobs_data = scrape_and_process()
    save_report(jobs_data)

