import time
import undetected_chromedriver as uc
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
import PyPDF2
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from io import BytesIO

url1 = "https://www.voorburggroup.org/papers-eng.htm"
url2 = "https://www.voorburggroup.org/papers-archive-eng.htm"

def create_driver():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-extensions')
    options.add_argument('--start-maximized')

    driver = uc.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1200, 800)
    return driver

# Scrape the website
def scrape_website(url,file_name):
    driver = create_driver()
    try:
        # Open the website
        driver.get(url)

        # Wait for page to load (you can customize sleep or use explicit waits)
        time.sleep(5)

        # Locate the dropdown by name attribute
        dropdown = Select(driver.find_element(By.NAME, "wb-auto-1_length"))

        # Select the option with value '100'
        dropdown.select_by_value('100')
        time.sleep(5)  # Wait for the table to refresh after selecting the value

        # Initialize an empty list to hold all row data
        data = []

        # Loop through pagination
        while True:
            # Locate the table by its ID
            table = driver.find_element(By.ID, 'wb-auto-1')

            # Find all the rows in the table's body (or use thead for headers)
            rows = table.find_elements(By.XPATH, ".//thead/tr | .//tbody/tr")

            # Iterate over the rows and extract text
            for index, row in enumerate(rows):
                # Find all the cells in the row (both th and td)
                cells = row.find_elements(By.XPATH, ".//th | .//td")
                
                # Extract the text from each cell
                row_data = [cell.text for cell in cells]

                # If there are more than 10 columns, remove the last column
                if len(row_data) > 10:
                    row_data = row_data[:10]

                # Look for the hyperlink in the "Title" column (assuming it's the third column)
                try:
                    if index == 0:
                        row_data.append("Link")
                    else:
                        if file_name == "papers-archive-eng":
                            title_cell = cells[2]  # Adjust based on where the title is in your table (index 3 for the fourth column)
                        else:
                            title_cell = cells[3]  # Adjust based on where the title is in your table (index 3 for the fourth column)
                        link = title_cell.find_element(By.TAG_NAME, "a").get_attribute("href")
                        row_data.append(link)
                except:
                    # If no hyperlink is found, add a placeholder or skip
                    row_data.append("No link")
                
                    
                if index != 0:
                    data.append(row_data)
            
            # Try to find the 'Next' button and check if it's disabled
            next_button = driver.find_element(By.ID, 'wb-auto-1_next')
            if "disabled" in next_button.get_attribute("class"):
                break  # Stop if 'Next' is disabled (end of pages)
                
            # Click the 'Next' button to go to the next page
            next_button.click()
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(EC.staleness_of(next_button))
            time.sleep(5)
        
        # Create a DataFrame with the collected data
        if file_name == "papers-eng":
            columns = ['Year', 'Location', 'Format', 'Title', 'ISIC Section', '2 digit ISIC Division', 'Author', 'Type', 'Theme', 'Topic', 'Link']
        if file_name == "papers-archive-eng":
            columns = ['Year', 'Location', 'Title', 'Author', 'Link']
        df = pd.DataFrame(data, columns=columns)

        # Display the DataFrame (optional)
        print(df)

        # Optionally, you can save it to a CSV file
        df.to_csv(file_name+'.csv', index=False)

    finally:
        # Always close the driver after scraping
        driver.quit()
    
def download_and_extract_text_from_pdf(pdf_url):
    try:
        print(pdf_url)
        # Step 1: Download the PDF from the URL
        response = requests.get(pdf_url)
        if response.status_code == 200:
            pdf_file = BytesIO(response.content)
        else:
            return f"Failed to download PDF. Status code: {response.status_code}"

        # Step 2: Try to extract text using PyPDF2 (for non-flattened PDFs)
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()

            # If text is found, return it
            if text.strip():
                return text
        except Exception as e:
            print(f"Error during PyPDF2 extraction: {e}")
        
        # Step 3: If no text is extracted or PyPDF2 fails, fallback to OCR
        print("Falling back to OCR...")
        # Reset the file pointer to the start
        pdf_file.seek(0)
        
        # Convert PDF pages to images using pdf2image
        images = convert_from_bytes(pdf_file.read())

        extracted_text = ""
        for image in images:
            # Use Tesseract to extract text from each image
            extracted_text += pytesseract.image_to_string(image)

        return extracted_text if extracted_text.strip() else "No text could be extracted."
    
    except Exception as e:
        return f"An error occurred: {e}"


if __name__ == "__main__":
    target_url = "https://example.com"  # Replace with your target URL
    url1 = "https://www.voorburggroup.org/papers-eng.htm"
    url2 = "https://www.voorburggroup.org/papers-archive-eng.htm"
    #scrape_website(url1,"papers-eng")
    #scrape_website(url2,"papers-archive-eng")

    df = pd.read_csv("papers-eng.csv")
    df['extracted_text'] = df['Link'].apply(download_and_extract_text_from_pdf)
    df.to_csv("papers_with_extracted_text.csv", index=False)