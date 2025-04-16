import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

logger = logging.getLogger(__name__)

class ReclamaBot:
    """Class for handling all Reclame Aqui website interactions via Selenium."""
    
    def __init__(self, email, password, browser_type="chrome"):
        """
        Initialize ReclamaBot with login credentials and browser configuration.
        
        Args:
            email (str): Email for Reclame Aqui login
            password (str): Password for Reclame Aqui login
            browser_type (str): Browser to use - 'chrome' or 'firefox'
        """
        self.email = email
        self.password = password
        self.browser_type = browser_type
        self.driver = None
        self.base_url = "https://www.reclameaqui.com.br"
        
        self._initialize_driver()
    
    def _initialize_driver(self):
        """Initialize the WebDriver for the specified browser."""
        try:
            if self.browser_type == "chrome":
                options = webdriver.ChromeOptions()
                options.add_argument("--headless")  # Optional: run in headless mode
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                self.driver = webdriver.Chrome(options=options)
            elif self.browser_type == "firefox":
                options = webdriver.FirefoxOptions()
                options.add_argument("--headless")  # Optional: run in headless mode
                options.add_argument("--width=1920")
                options.add_argument("--height=1080")
                self.driver = webdriver.Firefox(options=options)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
            
            self.driver.implicitly_wait(10)
            logger.info(f"Initialized {self.browser_type} WebDriver")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise
    
    def login(self):
        """
        Log in to Reclame Aqui using the provided credentials.
        
        Returns:
            bool: True if login was successful, False otherwise
        """
        try:
            logger.info("Attempting to login to Reclame Aqui")
            
            # Navigate to the login page
            self.driver.get(f"{self.base_url}/login")
            
            # Wait for the login form to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            
            # Enter email
            email_field = self.driver.find_element(By.ID, "email")
            email_field.clear()
            email_field.send_keys(self.email)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for the dashboard to load
            WebDriverWait(self.driver, 15).until(
                EC.url_contains("/dashboard") or EC.url_contains("/empresa")
            )
            
            logger.info("Login successful")
            return True
            
        except TimeoutException:
            logger.error("Login timed out - check credentials or website structure")
            return False
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
    
    def get_new_complaints(self):
        """
        Retrieve new complaints from Reclame Aqui dashboard.
        
        Returns:
            list: List of dictionaries with complaint details
        """
        complaints = []
        
        try:
            logger.info("Fetching new complaints")
            
            # Navigate to the complaints page
            # Note: The actual URL may vary depending on the company's dashboard structure
            self.driver.get(f"{self.base_url}/empresa/dashboard/reclamacoes/novas")
            
            # Wait for complaints to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".complaint-list-item, .reclamacao-item"))
            )
            
            # Get all complaint items
            complaint_elements = self.driver.find_elements(By.CSS_SELECTOR, ".complaint-list-item, .reclamacao-item")
            
            logger.info(f"Found {len(complaint_elements)} complaint items in the page")
            
            # Extract information from each complaint
            for element in complaint_elements:
                try:
                    # Extract complaint ID (might be in different formats depending on the website structure)
                    complaint_id = element.get_attribute("data-id") or element.get_attribute("id").split("-")[-1]
                    
                    # Extract customer name
                    customer_name_element = element.find_element(By.CSS_SELECTOR, ".customer-name, .nome-cliente")
                    customer_name = customer_name_element.text.strip()
                    
                    # Open the complaint to get full text
                    element.click()
                    
                    # Wait for complaint details to load
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".complaint-text, .texto-reclamacao"))
                    )
                    
                    # Extract complaint text
                    complaint_text_element = self.driver.find_element(By.CSS_SELECTOR, ".complaint-text, .texto-reclamacao")
                    complaint_text = complaint_text_element.text.strip()
                    
                    # Add complaint to list
                    complaints.append({
                        "id": complaint_id,
                        "customer_name": customer_name,
                        "text": complaint_text
                    })
                    
                    # Go back to the complaints list
                    self.driver.back()
                    
                    # Wait for the list to reload
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".complaint-list-item, .reclamacao-item"))
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing a complaint item: {str(e)}")
                    continue
            
            logger.info(f"Successfully extracted {len(complaints)} complaints")
            
        except Exception as e:
            logger.error(f"Error getting complaints: {str(e)}")
        
        return complaints
    
    def submit_response(self, complaint_id, response_text):
        """
        Submit a response to a specific complaint.
        
        Args:
            complaint_id (str): ID of the complaint to respond to
            response_text (str): Text of the response to submit
            
        Returns:
            bool: True if response was submitted successfully, False otherwise
        """
        try:
            logger.info(f"Submitting response to complaint ID: {complaint_id}")
            
            # Navigate to the specific complaint
            self.driver.get(f"{self.base_url}/empresa/reclamacao/{complaint_id}")
            
            # Wait for the response form to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.response-field, #response-textarea"))
            )
            
            # Find the response textarea
            response_field = self.driver.find_element(By.CSS_SELECTOR, "textarea.response-field, #response-textarea")
            
            # Clear and fill the response
            response_field.clear()
            # Enter text character by character to avoid detection as a bot
            for char in response_text:
                response_field.send_keys(char)
                time.sleep(0.01)
            
            # Find and click the submit button
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button.submit-response, #submit-button")
            submit_button.click()
            
            # Wait for confirmation message
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".success-message, .message-success"))
            )
            
            logger.info(f"Response to complaint ID {complaint_id} submitted successfully")
            return True
            
        except TimeoutException:
            logger.error(f"Timed out while submitting response to complaint ID {complaint_id}")
            return False
        except Exception as e:
            logger.error(f"Error submitting response to complaint ID {complaint_id}: {str(e)}")
            return False
    
    def close(self):
        """Close the WebDriver if it exists."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")
