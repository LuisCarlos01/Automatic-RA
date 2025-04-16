import os
import logging
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

logger = logging.getLogger(__name__)

class IAResponder:
    """Class for generating AI responses to customer complaints using OpenAI API."""
    
    def __init__(self, api_key=None):
        """
        Initialize the AI responder with an OpenAI API key.
        
        Args:
            api_key (str, optional): OpenAI API key. If None, will attempt to get from environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OpenAI API key not provided or found in environment")
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"  # Using the latest model
        
        logger.info("IAResponder initialized with OpenAI API")
    
    def generate_response(self, complaint_text, system_prompt=None):
        """
        Generate a response to a customer complaint using the OpenAI API.
        
        Args:
            complaint_text (str): The text of the customer complaint
            system_prompt (str, optional): Custom system prompt to use for this response
            
        Returns:
            str: AI-generated response to the complaint
        """
        try:
            logger.info(f"Generating response for complaint: {complaint_text[:50]}...")
            
            # Create the prompt for the AI
            if system_prompt is None:
                # Try to get the system prompt from environment
                import os
                system_prompt = os.getenv("SYSTEM_PROMPT")
                
                # If still None, use default
                if system_prompt is None:
                    system_prompt = (
                        "Você é um atendente profissional da empresa iPass. "
                        "Responda a reclamação de forma cordial, resolutiva e empática. "
                        "Use linguagem formal e profissional, mas amigável. "
                        "Peça desculpas pelo transtorno, reconheça o problema e "
                        "ofereça soluções práticas. Encerre agradecendo a oportunidade "
                        "de resolver a situação. "
                        "Limite a resposta a um máximo de 500 caracteres."
                    )
            
            user_prompt = f"Reclamação: '{complaint_text}'. Responda de forma clara e objetiva."
            
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content.strip()
            
            logger.info(f"Generated response: {response_text[:50]}...")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            # Return a default response in case of an error
            return (
                "Agradecemos pelo seu contato. Lamentamos pelo ocorrido e gostaríamos "
                "de analisar melhor o seu caso. Nossa equipe entrará em contato em até "
                "48 horas úteis para resolver sua situação. Pedimos desculpas pelo "
                "transtorno e agradecemos sua compreensão."
            )
