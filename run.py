from playwright.sync_api import sync_playwright
import colorama
import requests
from colorama import Fore, Style
from urllib.parse import urlparse

colorama.init()

def print_transcript(transcript):
    """Print formatted transcript with colors and emojis"""
    print(Fore.BLUE + Style.BRIGHT + "\n📄 Transcript Output:" + Style.RESET_ALL)
    for line in transcript.split('\n'):
        stripped_line = line.strip()
        if not stripped_line:
            print()
            continue
        if line.startswith('# '):
            print(Fore.BLUE + Style.BRIGHT + "📺 " + line[2:].strip() + Style.RESET_ALL)
        elif line.startswith('###'):
            print(Fore.GREEN + "📌 " + line[3:].strip() + Style.RESET_ALL)
        else:
            print(Fore.WHITE + stripped_line + Style.RESET_ALL)

def get_main_choice():
    """Get user choice for main actions"""
    print(Fore.CYAN + Style.BRIGHT + "\n📝 Main Menu:" + Style.RESET_ALL)
    print(Fore.YELLOW + "1. Print transcript to screen")
    print("2. Save transcript to file")
    print("3. Download thumbnail image")
    print("4. Get video description")
    print("5. Do actions 2-5" + Style.RESET_ALL)
    
    while True:
        choice = input(Fore.CYAN + "Enter your choice (1-5): " + Style.RESET_ALL).strip()
        if choice in {'1', '2', '3', '4', '5'}:
            return choice
        print(Fore.RED + "❌ Invalid choice. Please enter 1-5." + Style.RESET_ALL)

def sanitize_filename(name):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()[:50]
    
def save_transcript(data):
    """Save transcript to file with filename validation"""

    print("\n📝 Save Transcript to File:")
    
    default_filename = sanitize_filename(data['title']) + ".md"
    filename = input(Fore.CYAN + f"Enter filename (default: '{default_filename}'): " + Style.RESET_ALL).strip()
    
    if not filename:
        filename = default_filename
    else:
        filename = sanitize_filename(filename)
        if not filename.endswith('.md'):
            filename += '.md'
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(data['transcript'])
        print(Fore.GREEN + f"✅ Transcript saved to {filename}!" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"❌ Error saving file: {e}" + Style.RESET_ALL)

def download_thumbnail(url, title):
    """Download and save video thumbnail"""

    print("\n📷 Download Thumbnail Image:")
    
    try:
        if not url:
            raise ValueError("No thumbnail URL found")
        
        response = requests.get(url)
        response.raise_for_status()
        
        parsed_url = urlparse(url)
        default_filename = f"{title}_thumbnail{parsed_url.path[-4:]}"
        filename = input(Fore.CYAN + f"Enter filename (default: '{default_filename}'): " + Style.RESET_ALL).strip()
    
        if not filename:
            filename = default_filename
        else:
            filename = sanitize_filename(filename)
        if not filename.endswith(parsed_url.path[-4:]):
            filename += parsed_url.path[-4:]
        with open(filename, 'wb') as f:
            f.write(response.content)

        print(Fore.GREEN + f"✅ Thumbnail downloaded as {filename}!" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"❌ Error downloading thumbnail: {e}" + Style.RESET_ALL)

def show_description(description):
    """Display video description with formatting"""
    print(Fore.BLUE + Style.BRIGHT + "\n📝 Video Description:" + Style.RESET_ALL)
    print(Fore.WHITE + description + Style.RESET_ALL)

with sync_playwright() as p:
    try:
        browser = p.chromium.launch()
        
        # Get URL and navigate
        url = input(Fore.CYAN + "Enter the URL of the YouTube video: " + Style.RESET_ALL)
        print(Fore.BLUE + f"🌐 Navigating to {url}..." + Style.RESET_ALL)
        page = browser.new_page()
        page.goto(url)

        # Extract metadata
        print(Fore.BLUE + "🔍 Extracting metadata..." + Style.RESET_ALL)
        page.wait_for_selector("#title > h1 > yt-formatted-string")
        thumbnail_url = page.query_selector('meta[property="og:image"]').get_attribute('content')
        description = page.query_selector('meta[name="description"]').get_attribute('content')
        title = page.query_selector("#title > h1 > yt-formatted-string").inner_text()
        page.get_by_role("button", name="...more").click()
        page.get_by_role("button", name="Show transcript").click()

        # Process transcript
        page.wait_for_selector("#segments-container")
        page.wait_for_selector("#content > ytd-transcript-renderer")
        print(Fore.BLUE + "⏳ Extracting transcript..." + Style.RESET_ALL)
        
        transcript = ""
        capitalize = True
        segment_div = page.query_selector("#content > ytd-transcript-renderer")
        start = 0

        for segment in segment_div.query_selector_all("div"):
            if segment.query_selector("yt-shelf-header-layout > div > div > h2 > span"):
                start += 1
                if start < 4:
                    continue
                title = segment.query_selector("yt-shelf-header-layout > div > div > h2 > span").inner_text()
                transcript += f"\n\n###{title}\n\n"
                continue
            
            if not segment.query_selector("yt-formatted-string"):
                continue
            
            text = segment.query_selector("yt-formatted-string").inner_text().replace("\n", "").strip()
            if not text:
                transcript += "\n\n\n"
                continue
            
            if transcript and transcript[-1] not in (" ", "\n"):
                transcript += " "
            
            if text[-1] in (".", "!", "?"):
                transcript += text
                capitalize = True
            else:
                if capitalize:
                    transcript += text[0].upper() + text[1:].lower()
                    capitalize = False
                else:
                    transcript += " " + text.lower()

        # Final processing
        transcript = transcript.replace("No results found Tap to retry", "").strip()
        transcript = f"# {title}\n\n" + transcript
        
        data = {
            "title": page.title().replace(" - YouTube", ""),
            "transcript": transcript,
            "thumbnail_url": thumbnail_url,
            "description": description
        }
        
        print(Fore.GREEN + "✅ All data fetched successfully!" + Style.RESET_ALL)
        browser.close()

        # Handle user choices
        choice = get_main_choice()
        
        if choice in ('4', '5'):
            show_description(data['description'])

        if choice in ('1'):
            print_transcript(data['transcript'])
        
        if choice in ('2', '5'):
            save_transcript(data)
            
        if choice in ('3', '5'):
            download_thumbnail(data['thumbnail_url'], data['title'])

    except Exception as e:
        print(Fore.RED + f"❌ Error occurred: {e}" + Style.RESET_ALL)
        if 'browser' in locals():
            browser.close()
