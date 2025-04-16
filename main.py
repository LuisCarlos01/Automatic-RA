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

# Default prompt for OpenAI
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", 
    "Você é um atendente profissional da empresa iPass. "
    "Responda a reclamação de forma cordial, resolutiva e empática. "
    "Use linguagem formal e profissional, mas amigável. "
    "Peça desculpas pelo transtorno, reconheça o problema e "
    "ofereça soluções práticas. Encerre agradecendo a oportunidade "
    "de resolver a situação. "
    "Limite a resposta a um máximo de 500 caracteres."
)

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
            response_text = responder.generate_response(complaint['text'], system_prompt=SYSTEM_PROMPT)
            
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

# Custom Jinja2 filter for newlines
@app.template_filter('nl2br')
def nl2br(value):
    """Convert newlines to <br> tags for display in HTML."""
    if value:
        return value.replace('\n', '<br>')
    return ''

@app.route('/test', methods=['GET'])
def test_page():
    """Page to test OpenAI response generation."""
    return render_template('test_response.html')

@app.route('/test_response', methods=['POST'])
def test_response():
    """Generate a test AI response."""
    customer_name = request.form.get('customer_name', 'Cliente Teste')
    complaint_text = request.form.get('complaint_text', '')
    
    if not complaint_text:
        flash('Por favor, insira o texto da reclamação.', 'warning')
        return redirect(url_for('test_page'))
    
    try:
        # Initialize OpenAI responder
        responder = IAResponder(api_key=OPENAI_API_KEY)
        
        # Time the response generation
        start_time = time.time()
        response_text = responder.generate_response(complaint_text)
        generation_time = round(time.time() - start_time, 2)
        
        return render_template(
            'test_response.html',
            customer_name=customer_name,
            complaint_text=complaint_text,
            response_text=response_text,
            generation_time=generation_time,
            model_name=responder.model
        )
        
    except Exception as e:
        logger.error(f"Error generating test response: {str(e)}")
        flash(f'Erro ao gerar resposta: {str(e)}', 'danger')
        return redirect(url_for('test_page'))

@app.route('/save_test', methods=['POST'])
def save_test():
    """Save test complaint and response to database."""
    customer_name = request.form.get('customer_name', 'Cliente Teste')
    complaint_text = request.form.get('complaint_text', '')
    response_text = request.form.get('response_text', '')
    
    if not all([customer_name, complaint_text, response_text]):
        flash('Dados incompletos para salvar.', 'warning')
        return redirect(url_for('test_page'))
    
    # Generate a unique ID for this test complaint
    import uuid
    complaint_id = f"TEST-{uuid.uuid4().hex[:8]}"
    
    # Save to database
    success = db_instance.save_complaint(
        complaint_id=complaint_id,
        customer_name=customer_name,
        complaint_text=complaint_text,
        response_text=response_text,
        status="completed"
    )
    
    if success:
        flash('Teste salvo com sucesso no banco de dados!', 'success')
    else:
        flash('Erro ao salvar teste no banco de dados.', 'danger')
    
    return redirect(url_for('index'))

@app.route('/config', methods=['GET'])
def config_page():
    """Configuration page."""
    return render_template('config.html',
                          RECLAMEAQUI_EMAIL=RECLAMEAQUI_EMAIL,
                          RECLAMEAQUI_PASSWORD=RECLAMEAQUI_PASSWORD,
                          OPENAI_API_KEY=OPENAI_API_KEY,
                          CHECK_INTERVAL_MINUTES=CHECK_INTERVAL_MINUTES,
                          BROWSER_TYPE=BROWSER_TYPE,
                          SYSTEM_PROMPT=SYSTEM_PROMPT)

@app.route('/save_config', methods=['POST'])
def save_config():
    """Save configuration to .env file."""
    global RECLAMEAQUI_EMAIL, RECLAMEAQUI_PASSWORD, OPENAI_API_KEY, CHECK_INTERVAL_MINUTES, BROWSER_TYPE
    
    # Get form data
    reclameaqui_email = request.form.get('reclameaqui_email', '')
    reclameaqui_password = request.form.get('reclameaqui_password', '')
    openai_api_key = request.form.get('openai_api_key', '')
    check_interval = request.form.get('check_interval', '60')
    browser_type = request.form.get('browser_type', 'chrome')
    
    # Validate inputs
    try:
        check_interval_int = int(check_interval)
        if check_interval_int < 5 or check_interval_int > 1440:
            raise ValueError("Intervalo deve estar entre 5 e 1440 minutos")
    except ValueError:
        flash('Intervalo de verificação inválido. Deve ser um número entre 5 e 1440.', 'danger')
        return redirect(url_for('config_page'))
    
    if browser_type not in ['chrome', 'firefox']:
        flash('Tipo de navegador inválido.', 'danger')
        return redirect(url_for('config_page'))
    
    # Update environment variables
    RECLAMEAQUI_EMAIL = reclameaqui_email
    RECLAMEAQUI_PASSWORD = reclameaqui_password
    OPENAI_API_KEY = openai_api_key
    CHECK_INTERVAL_MINUTES = check_interval_int
    BROWSER_TYPE = browser_type
    
    # Update .env file
    try:
        with open('.env', 'w') as f:
            f.write(f"# Reclame Aqui login credentials\n")
            f.write(f"RECLAMEAQUI_EMAIL={reclameaqui_email}\n")
            f.write(f"RECLAMEAQUI_PASSWORD={reclameaqui_password}\n")
            f.write(f"\n# OpenAI API Key\n")
            f.write(f"OPENAI_API_KEY={openai_api_key}\n")
            f.write(f"\n# How often to check for new complaints (in minutes)\n")
            f.write(f"CHECK_INTERVAL_MINUTES={check_interval_int}\n")
            f.write(f"\n# Browser type (chrome or firefox)\n")
            f.write(f"BROWSER_TYPE={browser_type}\n")
            
            # Preserve system prompt if it exists
            if SYSTEM_PROMPT:
                f.write(f"\n# System prompt for OpenAI\n")
                f.write(f"SYSTEM_PROMPT=\"{SYSTEM_PROMPT}\"\n")
        
        flash('Configurações salvas com sucesso!', 'success')
        logger.info("Configuration updated and saved to .env file")
        
    except Exception as e:
        flash(f'Erro ao salvar configurações: {str(e)}', 'danger')
        logger.error(f"Error saving configuration to .env file: {str(e)}")
    
    return redirect(url_for('config_page'))

@app.route('/save_prompt', methods=['POST'])
def save_prompt():
    """Save system prompt to .env file."""
    global SYSTEM_PROMPT
    
    # Get form data
    system_prompt = request.form.get('system_prompt', '')
    
    if not system_prompt:
        flash('O prompt não pode estar vazio.', 'warning')
        return redirect(url_for('config_page'))
    
    # Update environment variable
    SYSTEM_PROMPT = system_prompt
    
    # Update .env file
    try:
        # Read existing .env file content
        env_content = ""
        with open('.env', 'r') as f:
            env_content = f.read()
        
        # Check if SYSTEM_PROMPT already exists
        if "SYSTEM_PROMPT=" in env_content:
            # Replace existing prompt
            import re
            pattern = r'SYSTEM_PROMPT=.*(\n|$)'
            env_content = re.sub(pattern, f'SYSTEM_PROMPT="{system_prompt}"\n', env_content)
            
            with open('.env', 'w') as f:
                f.write(env_content)
        else:
            # Append to file
            with open('.env', 'a') as f:
                f.write(f"\n# System prompt for OpenAI\n")
                f.write(f'SYSTEM_PROMPT="{system_prompt}"\n')
        
        # Update prompt in IAResponder class
        flash('Prompt do sistema salvo com sucesso!', 'success')
        logger.info("System prompt updated and saved to .env file")
        
    except Exception as e:
        flash(f'Erro ao salvar prompt: {str(e)}', 'danger')
        logger.error(f"Error saving system prompt to .env file: {str(e)}")
    
    return redirect(url_for('config_page'))

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
