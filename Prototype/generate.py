import gradio as gr
import ollama
import webbrowser
import os
import re

# Determine age group based on inputted age
def determine_age_group(age):
    if 1 <= age <= 12:
        return "child"
    elif 13 <= age <= 19:
        return "teen"
    elif 20 <= age <= 29:
        return "young adult"
    elif 30 <= age <= 59:
        return "adult"
    elif age >= 60:
        return "senior"
    else:
        return "unknown"

# Function to clean unnecessary text and artifacts from the generated template
def clean_generated_code(raw_template):
    # Remove code block delimiters like ```html or ```
    cleaned_template = re.sub(r"```.*?\n", "", raw_template, flags=re.DOTALL)
    # Remove explanatory text like "This HTML code creates a webpage..."
    cleaned_template = re.sub(r"This .*?screens\.", "", cleaned_template, flags=re.DOTALL)
    # Remove any lingering text outside valid HTML tags
    cleaned_template = re.sub(r"^[^<]*", "", cleaned_template, flags=re.DOTALL)
    # Remove trailing non-HTML content after </html>
    cleaned_template = re.sub(r"</html>.*", "</html>", cleaned_template, flags=re.DOTALL)
    return cleaned_template.strip()

# Generate the webpage template dynamically using LLM
def generate_template(age, gender):
    # Validate age input
    try:
        age = int(age)
        age_group = determine_age_group(age)
        if age_group == "unknown":
            return "Invalid age entered. Please enter a valid age."
    except ValueError:
        return "Invalid input. Please enter a numeric age."

    # Validate gender input
    gender = gender.lower()
    if gender not in ["male", "female"]:
        return "Invalid gender entered. Please select Male or Female."

    # Construct the prompt for the LLM
    template_prompt = f"""
        Generate an HTML and CSS template for a health-related webpage tailored specifically to a {gender} {age_group}.
        The content should include only health tips that are relevant to this demographic. The tips should be short,
        concise, and no longer than one or two lines. Examples:

        - For a senior male: "Stretch regularly to maintain flexibility."
        - For a young adult female: "Incorporate yoga to relieve stress."

        Requirements:
        1. **Content**:
            - Include exactly 5-7 health tips specifically for a {gender} {age_group}.
            - Avoid including any irrelevant tips or placeholders for other demographics.

        2. **Visual Design**:
            - Use a structured, clean layout with colors appropriate for the user:
                - For males, use cool tones (blue/green).
                - For females, use warm tones (pink/peach).
            - Use a modern and readable font.

        3. **Layout**:
            - Include a header with the webpage title ("Personalized Health Tips for {gender.capitalize()} {age_group.capitalize()}").
            - Display the health tips in a responsive list or grid layout.
            - Ensure the layout is visually appealing and adjusts well to both desktop and mobile screens.

        4. **Styling**:
            - Use internal CSS in a `<style>` tag within the `<head>` section.
            - Ensure that the design matches the preferences for the specified demographic.

        5. **Accessibility**:
            - Include accessibility features, such as high contrast, adjustable font sizes, and proper semantic tags for screen readers.

        **Important**:
        - Generate only valid HTML and CSS code for the webpage.
        - Do not include any explanatory text, descriptions, or comments in the output.
        - The output must start with <!DOCTYPE html> and end with </html>.
    """

    # Generate the template using the LLM
    template_response = ollama.generate(model="llama3.2", prompt=template_prompt)

    # Ensure a valid response is received
    raw_template = template_response.get("response", "") if isinstance(template_response, dict) else str(template_response)

    # Clean the HTML template
    cleaned_template = clean_generated_code(raw_template)

    # Ensure the cleaned template is not empty
    if not cleaned_template:
        return "The generated template was empty. Please try again with different inputs."

    # Write the HTML to a file
    output_file = "generated_template.html"
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(cleaned_template)

    # Open the HTML file in the default web browser
    webbrowser.open(f"file://{os.path.abspath(output_file)}")

    return "Template generated successfully! The HTML file has been opened in your browser."

# Gradio Interface
with gr.Blocks() as demo:
    with gr.Row():
        gr.Markdown("## Dynamic HTML Template Generator for Personalized Health Tips")
    with gr.Row():
        age_input = gr.Textbox(label="Enter your age:", placeholder="e.g., 25")
        gender_input = gr.Dropdown(label="Select your gender:", choices=["Male", "Female"], value="Male")
    with gr.Row():
        submit_button = gr.Button("Generate HTML Template")
    with gr.Row():
        output_message = gr.Textbox(label="Status", interactive=False)

    # Link button to the function
    submit_button.click(generate_template, inputs=[age_input, gender_input], outputs=[output_message])

# Launch the Gradio interface
demo.launch()
