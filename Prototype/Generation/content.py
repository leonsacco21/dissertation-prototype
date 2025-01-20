import requests
from bs4 import BeautifulSoup
from googlesearch import search
from template import generate_template, determine_age_group
import os

# Scraping content from a webpage
def scrape_page(url):
    """
    Scrape text content from the given URL.
    """
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Extract paragraphs from the page
        paragraphs = soup.find_all("p")
        text_content = " ".join([para.get_text() for para in paragraphs])

        # Limit content to 500 characters for readability
        return text_content[:500].strip()
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"

# Performing a Google search for content
def google_search(query, num_results=1):
    """
    Perform a Google search for the given query.
    """
    try:
        return list(search(query, num_results=num_results))
    except Exception as e:
        return []

# Fetching personalized content based on user inputs
def fetch_content_for_articles(age_group):
    """
    Fetch content for the three articles based on the user's age group.
    """
    # Define search queries for the articles
    queries = [
        f"site:who.int health information for {age_group} users",
        f"site:healthline.com mental health tips for {age_group} users",
        f"site:medlineplus.gov fitness advice for {age_group} users",
    ]

    article_contents = []
    for query in queries:
        # Search for relevant content
        search_results = google_search(query)
        if search_results:
            # Scrape content from the top result
            content = scrape_page(search_results[0])
            article_contents.append(content if content else "Content not available.")
        else:
            article_contents.append("Content not available.")
    
    return article_contents

# Generate the template and populate it with content
def generate_populated_website(age):
    """
    Generate a populated website based on the user's age.
    """
    try:
        # Validate and determine age group
        age_group = determine_age_group(int(age))
        if age_group == "unknown":
            return "Invalid age entered. Please try again with a valid age."

        # Generate the template
        print("Generating template...")
        template_html = generate_template(age)
        if "Invalid" in template_html:
            return template_html

        # Fetch content for the articles
        print("Fetching content for articles...")
        article_contents = fetch_content_for_articles(age_group)

        # Display fetched content in the terminal
        print("\n--- Fetched Content for Articles ---")
        for idx, content in enumerate(article_contents, start=1):
            print(f"\nArticle {idx} Content:\n{content}")

        # Replace placeholders in the template with the content
        populated_html = (
            template_html
            .replace('<div id="article-1"></div>', f'<div id="article-1"><h2>Article 1</h2><p>{article_contents[0]}</p></div>')
            .replace('<div id="article-2"></div>', f'<div id="article-2"><h2>Article 2</h2><p>{article_contents[1]}</p></div>')
            .replace('<div id="article-3"></div>', f'<div id="article-3"><h2>Article 3</h2><p>{article_contents[2]}</p></div>')
        )

        # Save the populated website
        output_file = "final_personalized_website.html"
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(populated_html)

        # Open the generated website in the browser
        print("\nOpening the populated website...")
        os.system(f"start {output_file}" if os.name == "nt" else f"open {output_file}")

        return "Website generated successfully! The populated HTML has been saved."
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Example Usage
if __name__ == "__main__":
    age = input("Enter the user's age: ").strip()
    result = generate_populated_website(age)
    print(result)
