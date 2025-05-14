import os
import re
import torch
import json
import random
import requests
import subprocess
import gradio as gr
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from sentence_transformers import SentenceTransformer, util
import webbrowser
import tempfile
import base64

# --- Load Models ---
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
blip_model.to("cuda" if torch.cuda.is_available() else "cpu")

embedder = SentenceTransformer("all-MiniLM-L6-v2")

# --- Constants ---
IMAGE_DIR = "llava-images"
OUTPUT_HTML_FILE = "prototype-final.html"
OLLAMA_MODEL = "deepseek-r1:7b"

# --- Step 1: Generate Image Captions ---
def generate_image_captions():
    captions = {}
    for filename in os.listdir(IMAGE_DIR):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            path = os.path.join(IMAGE_DIR, filename)
            try:
                image = Image.open(path).convert("RGB")
                inputs = blip_processor(image, return_tensors="pt").to(blip_model.device)
                out = blip_model.generate(**inputs)
                caption = blip_processor.decode(out[0], skip_special_tokens=True)
                captions[path] = caption
            except Exception as e:
                print(f"Skipping {filename}: {e}")
    return captions

# --- Step 2: Get Health Tips ---
def get_health_tips(age, gender):
    gender = gender.lower()
    url = f"https://odphp.health.gov/myhealthfinder/api/v3/myhealthfinder.json?age={age}&sex={gender}"

    try:
        response = requests.get(url)
        data = response.json()
        resources = data["Result"]["Resources"]["all"]["Resource"]
        tips = []
        for res in resources:
            title = res.get("MyHFTitle", "No Title")
            desc_html = res.get("MyHFDescription", "")
            desc = re.sub(r"<.*?>", "", desc_html).strip()
            tips.append((title, desc))
        return random.sample(tips, k=min(5, len(tips)))
    except Exception as e:
        print(f"API error: {e}")
        return []

# --- Step 3: Match Tips with Images ---
def match_tips_with_images(tips, image_captions):
    used = set()
    tip_texts = [f"{t[0]}. {t[1]}" for t in tips]
    tip_embeddings = embedder.encode(tip_texts, convert_to_tensor=True)

    image_texts = list(image_captions.values())
    image_paths = list(image_captions.keys())
    image_embeddings = embedder.encode(image_texts, convert_to_tensor=True)

    results = []

    for i, tip_emb in enumerate(tip_embeddings):
        sims = util.cos_sim(tip_emb, image_embeddings)[0]
        sorted_indices = torch.argsort(sims, descending=True)

        for idx in sorted_indices:
            img_path = image_paths[idx]
            if img_path not in used:
                used.add(img_path)
                results.append({
                    "title": tips[i][0],
                    "description": tips[i][1],
                    "image": img_path.replace("\\", "/")
                })
                break
    return results

def generate_page_title(age, gender):
    if age < 13:
        return "Health Suggestions for Children"
    elif 13 <= age <= 19:
        return "Health Tips for Teens"
    elif 20 <= age <= 40:
        return "Health Recommendations for Young Adults"
    elif 41 <= age <= 59:
        return "Health Guidance for Adults"
    else:
        return "Health Tips for Seniors"

# --- Step 4: Generate Prompt for LLM ---
def generate_prompt(matched_data, age, gender):
    # --- Design preferences based on user profile ---
    if gender.lower() == "male" and age < 30:
        design_note = "Use a modern, minimalistic layout with bold fonts and strong contrast."
    elif gender.lower() == "female" and age < 30:
        design_note = "Use an engaging layout with soft colors, rounded components, and clear structure."
    elif age >= 60:
        design_note = "Ensure accessibility with large fonts, high contrast, and simple layout."
    else:
        design_note = "Use a clean, readable layout with balanced colors and structured spacing."

    print(f"[INFO] Design note: {design_note}")

    page_title = generate_page_title(age, gender)

    prompt = (
        f"Generate a simple HTML page for a healthcare website titled '{page_title}'.\n"
        f"{design_note}\n"
        "- Add a main heading at the top of the page using <h1> that shows a related title.\n"
        "- For each health tip:\n"
        "  - Wrap the tip content in a <div style='margin: 20px 0;'> block.\n"
        "  - Inside the div, include:\n"
        "    - A heading using <h2> for the title.\n"
        "    - A <p> tag for the description.\n"
        "    - An <img> tag for the image using inline style 'width: 300px'.\n"
        "- Do not use JavaScript or external CSS frameworks.\n"
    )

    for item in matched_data:
        prompt += f"Title: {item['title']}\n"
        prompt += f"Description: {item['description']}\n"
        prompt += f"Image: {item['image']}\n\n"

    return prompt

# --- Step 5: Run Ollama Model Locally ---
def call_ollama(prompt):
    try:
        result = subprocess.run(
            ["ollama", "run", OLLAMA_MODEL],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )
        return result.stdout.decode("utf-8")
    except Exception as e:
        print(f"Ollama error: {e}")
        return ""

# --- Clean Generated HTML from unwanted code ---
def extract_valid_html(content):
    start = content.lower().find("<!doctype html")
    end = content.lower().find("</html>") + len("</html>")
    if start != -1 and end != -1:
        return content[start:end]
    return content  # fallback: return everything if not well-formatted

def remove_javascript(content):
    return re.sub(r"<script.*?>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)

def resize_images_inline(content, width_px=300):
    return re.sub(r'<img([^>]+)>', rf'<img\1 style="width: {width_px}px;">', content, flags=re.IGNORECASE)

def insert_healthfinder_badge(content):
    badge_html = """
    <div class="text-center mt-5 pb-5">
        <a href="https://odphp.health.gov/myhealthfinder" title="MyHealthfinder">
            <img src="https://odphp.health.gov/themes/custom/healthfinder/images/MyHF.svg" alt="MyHealthfinder" style="max-width: 200px;" />
        </a>
    </div>
    """

    # Insert just before </body>
    if "</body>" in content:
        content = content.replace("</body>", badge_html + "\n</body>")
    else:
        content += badge_html

    return content

# --- Step 6: Save HTML ---
def save_html(content):
    cleaned_html = remove_javascript(content)
    resized_html = resize_images_inline(cleaned_html)
    with open(OUTPUT_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(resized_html)
    return f"HTML page saved to: {OUTPUT_HTML_FILE}"

def apply_bootstrap_to_html(filepath):
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    # Inject Bootstrap CDN
    bootstrap_link = (
        '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" '
        'rel="stylesheet" integrity="sha384-..." crossorigin="anonymous">'
    )
    html = html.replace("<head>", f"<head>\n  {bootstrap_link}")

    # Wrap body content in a Bootstrap container
    html = re.sub(r"<body>", "<body>\n  <div class=\"container mt-4\">", html, flags=re.IGNORECASE)
    html = re.sub(r"</body>", "  </div>\n</body>", html, flags=re.IGNORECASE)

    # Add 'img-fluid' class to images
    html = re.sub(r"<img([^>]*?)>", r'<img\1 class="img-fluid">', html, flags=re.IGNORECASE)

    # Optional: add spacing classes to headers
    html = re.sub(r"<h1>", '<h1 class="text-center mb-4">', html)
    html = re.sub(r"<h2>", '<h2 class="mt-4">', html)

    # Save modified file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[INFO] Bootstrap added to: {filepath}")

def clean_up_generated_html(filepath):
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    # Fix malformed image style tags
    html = re.sub(
        r"<img([^>]*?)style=['\"]?[^>]*?['\"]?\s*style=['\"]?[^>]*?['\"]?",
        r'<img\1',
        html,
        flags=re.IGNORECASE,
    )

    # Fix any broken quote in style
    html = re.sub(
        r'style=[\'\"]([^\'\"]+)[\'\"]([^>]*)style=[\'\"][^\'\"]+[\'\"]',
        r'style="\1"\2',
        html
    )

    # Simplify image tags to use a single clean style
    html = re.sub(
        r'<img([^>]*?)>',
        r'<img\1 style="width: 300px;" class="img-fluid">',
        html
    )

    # Remove nested .container
    html = html.replace('<div class="container">', '')  # remove inner
    html = html.replace('</div>\n  </div>', '</div>')  # close only once

    # Optionally remove unused inline CSS block
    html = re.sub(r"<style>.*?</style>", "", html, flags=re.DOTALL)

    # Save cleaned result
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[INFO] Cleaned up and saved: {filepath}")

def apply_gender_theming(filepath, gender):
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    # Determine color
    primary_color = "#4a90e2" if gender.lower() == "male" else "#e26aa5"

    # Inject a <style> block just before </head>
    style_block = f"""
    <style>
        body {{
            background-color: #f8f9fa;
        }}
        h1 {{
            background-color: {primary_color};
            color: white;
            padding: 20px;
            border-radius: 8px;
        }}
    </style>
    """

    html = html.replace("</head>", style_block + "\n</head>")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[INFO] Gender theme applied for: {gender}")

def wrap_health_tips_in_cards(filepath, page_title="Health Tips"):
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    # Find sequences of <h2>, <p>, and <img>
    tip_blocks = re.findall(
        r'(<h2[^>]*?>.*?</h2>\s*<p[^>]*?>.*?</p>\s*<img[^>]*?>)',
        html,
        flags=re.DOTALL | re.IGNORECASE
    )

    if not tip_blocks:
        print("[WARN] No tip blocks matched. Check HTML structure.")
        return

    # Extract existing badge (if it exists)
    badge_match = re.search(
        r'(<a href="https://odphp\.health\.gov/myhealthfinder".*?</a>)',
        html,
        flags=re.DOTALL | re.IGNORECASE
    )
    badge_html = f"""
    <div class="text-center mt-5">
      {badge_match.group(1)}
    </div>
    """ if badge_match else ""

    # Build Bootstrap cards
    card_html = ""
    for block in tip_blocks:
        title = re.search(r'<h2[^>]*?>(.*?)</h2>', block, re.DOTALL)
        desc = re.search(r'<p[^>]*?>(.*?)</p>', block, re.DOTALL)
        img = re.search(r'<img[^>]*?>', block, re.DOTALL)

        if title and desc and img:
            card = f"""
            <div class="card mb-4 p-3 shadow-sm" style="width: 100%; max-width: 600px;">
              <h2 class="card-title">{title.group(1).strip()}</h2>
              <p class="card-text">{desc.group(1).strip()}</p>
              {img.group(0).replace('<img', '<img class="img-fluid rounded-3 mx-auto d-block"')}
            </div>
            """
            card_html += card

    layout = f"""
    <div class="d-flex flex-column align-items-center">
      {card_html}
      {badge_html}
    </div>
    """

    # Replace <body> content without deleting the badge
    html = re.sub(
        r'(?is)<body.*?>.*?</body>',
        f'<body>\n  <div class="container mt-4">\n  <h1 class="text-center mb-4">{page_title}</h1>\n{layout}\n</div>\n</body>',
        html
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print("[INFO] Health tips wrapped in Bootstrap cards with badge preserved.")

# --- Pipeline Triggered by Gradio ---
def gradio_callback(age, gender):
    print(f"\n[INFO] Starting pipeline for Age={age}, Gender={gender}")

    tips = get_health_tips(age, gender)
    if not tips:
        return "No health tips found.", ""

    image_captions = generate_image_captions()
    matched_data = match_tips_with_images(tips, image_captions)

    prompt = generate_prompt(matched_data, age, gender)
    raw_output = call_ollama(prompt)
    html_output = extract_valid_html(raw_output)
    html_output = insert_healthfinder_badge(html_output)

    if "<html" in html_output.lower():
        page_title = generate_page_title(age, gender)

        save_html(html_output)
        apply_bootstrap_to_html(OUTPUT_HTML_FILE)
        clean_up_generated_html(OUTPUT_HTML_FILE)
        apply_gender_theming(OUTPUT_HTML_FILE, gender)
        wrap_health_tips_in_cards(OUTPUT_HTML_FILE, page_title)

        # Read final HTML
        with open(OUTPUT_HTML_FILE, "r", encoding="utf-8") as f:
            final_html = f.read()

        # Encode to base64 and embed using data URI
        b64_html = base64.b64encode(final_html.encode("utf-8")).decode("utf-8")
        iframe_code = f'<iframe src="data:text/html;base64,{b64_html}" width="100%" height="600px" style="border:1px solid #ccc;"></iframe>'

        return "Page generated successfully.", iframe_code
    else:
        print(html_output)
        return "Failed to generate valid HTML from Ollama.", ""

# --- Gradio UI ---
with gr.Blocks() as demo:
    gr.Markdown("## Generate Personalized Health Tips Page")

    with gr.Row():
        age_input = gr.Number(label="Age", minimum=0)
        gender_input = gr.Dropdown(choices=["Male", "Female"], label="Gender")

    submit_btn = gr.Button("Generate HTML Page")
    result_output = gr.Textbox(label="Status")
    html_preview = gr.HTML()

    submit_btn.click(
        fn=gradio_callback,
        inputs=[age_input, gender_input],
        outputs=[result_output, html_preview]
    )

demo.launch(share=True)