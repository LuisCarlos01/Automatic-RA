import os
import time
import threading
import schedule
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from reclama_bot import ReclamaBot
from database import Database
from ia_responder import IAResponder

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reclame_aqui_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration from environment variables
RECLAMEAQUI_EMAIL = os.getenv("RECLAMEAQUI_EMAIL")
RECLAMEAQUI_PASSWORD = os.getenv("RECLAMEAQUI_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chrome").lower()  # chrome or firefox

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "reclameaqui-bot-secret-key")

# Create a global database instance
db_instance = Database()

# Flag to track if the bot is currently running
is_bot_running = False
scheduler_thread = None

def process_complaints():
    """Main function to process complaints."""
    global is_bot_running
    
    try:
        # Set the running flag
        is_bot_running = True
        
        # Initialize OpenAI responder
        responder = IAResponder(api_key=OPENAI_API_KEY)
        
        # Initialize browser automation
        reclama_bot = ReclamaBot(
            email=RECLAMEAQUI_EMAIL,
            password=RECLAMEAQUI_PASSWORD,
            browser_type=BROWSER_TYPE
        )
        
        logger.info("Starting complaint processing")
        
        # Login to Reclame Aqui
        login_success = reclama_bot.login()
        if not login_success:
            logger.error("Failed to login. Exiting.")
            return
        
        # Get new complaints
        complaints = reclama_bot.get_new_complaints()
        logger.info(f"Found {len(complaints)} new complaints")
        
        # Process each complaint
        for complaint in complaints:
            # Check if we've already responded to this complaint
            if db_instance.is_complaint_processed(complaint['id']):
                logger.info(f"Complaint ID {complaint['id']} already processed. Skipping.")
                continue
            
            logger.info(f"Processing complaint ID: {complaint['id']}")
            
            # Generate AI response
            response_text = responder.generate_response(complaint['text'])
            
            # Submit response
            response_success = reclama_bot.submit_response(complaint['id'], response_text)
            
            # Save to database
            db_instance.save_complaint(
                complaint_id=complaint['id'],
                customer_name=complaint['customer_name'],
                complaint_text=complaint['text'],
                response_text=response_text,
                status="completed" if response_success else "failed"
            )
            
            logger.info(f"Complaint ID {complaint['id']} processed with status: {'success' if response_success else 'failed'}")
            
            # Small delay to avoid being flagged as a bot
            time.sleep(2)
        
        logger.info("Completed complaint processing cycle")
        
    except Exception as e:
        logger.error(f"Error in process_complaints: {str(e)}", exc_info=True)
    
    finally:
        # Ensure the browser is closed even if there's an error
        if 'reclama_bot' in locals():
            reclama_bot.close()
        
        # Reset the running flag
        is_bot_running = False

def run_scheduler():
    """Run the scheduler to periodically check for complaints."""
    logger.info(f"Starting scheduler to run every {CHECK_INTERVAL_MINUTES} minutes")
    
    # Run immediately the first time
    process_complaints()
    
    # Schedule to run periodically
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(process_complaints)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler_thread():
    """Start the scheduler in a separate thread."""
    global scheduler_thread
    
    # Only start if not already running
    if scheduler_thread is None or not scheduler_thread.is_alive():
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True  # Daemon thread will be killed when the main process exits
        scheduler_thread.start()
        logger.info("Scheduler thread started")
        return True
    
    return False

# Flask routes
@app.route('/')
def index():
    """Main dashboard page"""
    # Get statistics
    stats = db_instance.get_statistics()
    
    # Get the most recent complaints
    complaints = db_instance.get_all_complaints(limit=10)
    
    return render_template('index.html', 
                          stats=stats, 
                          complaints=complaints, 
                          bot_running=is_bot_running,
                          CHECK_INTERVAL_MINUTES=CHECK_INTERVAL_MINUTES,
                          BROWSER_TYPE=BROWSER_TYPE,
                          RECLAMEAQUI_EMAIL=RECLAMEAQUI_EMAIL,
                          RECLAMEAQUI_PASSWORD=RECLAMEAQUI_PASSWORD,
                          OPENAI_API_KEY=OPENAI_API_KEY)

@app.route('/complaints')
def view_complaints():
    """View all complaints"""
    complaints = db_instance.get_all_complaints(limit=100)
    return render_template('complaints.html', complaints=complaints)

@app.route('/start_bot', methods=['POST'])
def start_bot():
    """Start the bot manually"""
    if not all([RECLAMEAQUI_EMAIL, RECLAMEAQUI_PASSWORD, OPENAI_API_KEY]):
        flash("Erro: Faltam variáveis de ambiente. Verifique seu arquivo .env", "danger")
        return redirect(url_for('index'))
    
    success = start_scheduler_thread()
    
    if success:
        flash("Bot iniciado com sucesso! Verificando reclamações...", "success")
    else:
        flash("O bot já está em execução!", "info")
    
    return redirect(url_for('index'))

@app.route('/run_once', methods=['POST'])
def run_once():
    """Run the bot once manually"""
    if is_bot_running:
        flash("O bot já está em execução. Aguarde a conclusão.", "warning")
        return redirect(url_for('index'))
    
    # Start in a separate thread to not block the web server
    threading.Thread(target=process_complaints).start()
    flash("Processamento manual iniciado!", "success")
    
    return redirect(url_for('index'))

@app.route('/export', methods=['POST'])
def export_data():
    """Export complaint data to JSON"""
    success = db_instance.export_to_json()
    
    if success:
        flash("Dados exportados com sucesso para 'complaints_export.json'", "success")
    else:
        flash("Erro ao exportar dados", "danger")
    
    return redirect(url_for('index'))

@app.route('/api/stats')
def api_stats():
    """API endpoint for current statistics"""
    return jsonify(db_instance.get_statistics())

@app.route('/api/status')
def api_status():
    """API endpoint for bot status"""
    return jsonify({"running": is_bot_running})

# Create templates directory and needed templates
if not os.path.exists('templates'):
    os.makedirs('templates')

if __name__ == "__main__":
    # Check if required environment variables are set
    if not all([RECLAMEAQUI_EMAIL, RECLAMEAQUI_PASSWORD, OPENAI_API_KEY]):
        logger.error("Missing required environment variables. Please check your .env file.")
        # Don't exit, let the web interface handle it
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
