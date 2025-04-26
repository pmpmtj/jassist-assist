#!/usr/bin/env python
"""
Contas Processor Module

This module handles the processing of financial transactions with OpenAI and database storage.
"""

import json
import yaml
import os
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime

from jassist.logger_utils.logger_utils import setup_logger
from jassist.db_utils.db_connection import db_connection_handler
from jassist.contas.utils.config_manager import load_json_config, get_config_dir
from jassist.contas.utils.json_extractor import extract_json_from_text

# Import the adapter
try:
    from jassist.api_assistants_cliente.adapters.contas_adapter import process_with_contas_assistant
    ADAPTER_AVAILABLE = True
except ImportError:
    logger = setup_logger("contas_processor", module="contas")
    logger.warning("Could not import contas adapter, falling back to direct implementation")
    ADAPTER_AVAILABLE = False

# Set up logger if not already set up by the import attempt above
if 'logger' not in locals():
    logger = setup_logger("contas_processor", module="contas")

def load_prompts() -> Dict[str, Any]:
    """
    Load prompt templates from prompts.yaml
    
    Returns:
        Dict containing prompt templates
    """
    try:
        prompts_path = get_config_dir() / "prompts.yaml"
        
        if not prompts_path.exists():
            logger.error(f"Prompts file not found: {prompts_path}")
            return {}
            
        with open(prompts_path, 'r', encoding='utf-8') as f:
            prompts_config = yaml.safe_load(f)
            
        return prompts_config.get('prompts', {})
    except Exception as e:
        logger.error(f"Error loading prompts: {e}")
        return {}

def get_assistant_config() -> Dict[str, Any]:
    """
    Load OpenAI assistant configuration
    
    Returns:
        Dict containing assistant configuration
    """
    return load_json_config("contas_assistant_config.json")

def process_with_assistant(text: str) -> str:
    """
    Process text input with OpenAI assistant
    
    Args:
        text: The text to process
        
    Returns:
        String containing the assistant's response
    """
    # First try using the adapter if available
    if ADAPTER_AVAILABLE:
        try:
            logger.debug("Using contas adapter for processing")
            response = process_with_contas_assistant(text)
            return response
        except Exception as e:
            logger.error(f"Error using contas adapter: {e}")
            logger.debug("Falling back to direct implementation")
    
    # Fall back to direct implementation if adapter isn't available or failed
    try:
        # Load configuration
        config = get_assistant_config()
        prompts = load_prompts()
        
        if not config:
            logger.error("Failed to load assistant configuration")
            return ""
            
        # Check for API key in config file
        api_key = config.get('api_key')
        
        # If not found in config, check environment variables
        if not api_key:
            logger.debug("API key not found in config, checking environment variables")
            api_key = os.environ.get('OPENAI_API_KEY')
            
        # If still not found, log error and return
        if not api_key:
            logger.error("OpenAI API key not found in configuration or environment variables")
            return ""
            
        # Configure client
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Get assistant ID from config
        assistant_id = config.get('assistant_id_assistente_de_contas')
        
        # If not found in config, check environment variables
        if not assistant_id:
            logger.debug("Assistant ID not found in config, checking environment variables")
            assistant_id = os.environ.get('OPENAI_ASSISTANT_ID_CONTAS')
            
        # If still not found, log error and return
        if not assistant_id:
            logger.error("Assistant ID not found in configuration or environment variables")
            return ""
            
        # Get or create thread
        thread_id = config.get('thread_id_assistente_de_contas_default')
        if not thread_id:
            logger.debug("Creating new thread")
            thread = client.beta.threads.create()
            thread_id = thread.id
            
            # Save thread ID and creation time for future use
            config['thread_id_assistente_de_contas_default'] = thread_id
            config['thread_id_assistente_de_contas_default_created_at'] = time.time()
            
            config_path = get_config_dir() / "contas_assistant_config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        
        # Get prompt template
        parse_entry_template = prompts.get('parse_entry_prompt', {}).get('template', '')
        if not parse_entry_template:
            logger.warning("Parse entry prompt template not found, using raw text")
            formatted_prompt = text
        else:
            # Format prompt with entry content
            formatted_prompt = parse_entry_template.format(entry_content=text)
        
        # Add message to thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=formatted_prompt
        )
        
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        # Wait for completion
        max_wait_time = 60  # Maximum wait time in seconds
        start_time = time.time()
        
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
                
            if run_status.status in ['failed', 'cancelled', 'expired']:
                logger.error(f"Run failed with status: {run_status.status}")
                return ""
                
            # Check timeout
            if time.time() - start_time > max_wait_time:
                logger.error("Timeout waiting for assistant response")
                client.beta.threads.runs.cancel(
                    thread_id=thread_id,
                    run_id=run.id
                )
                return ""
                
            # Wait before checking again
            time.sleep(1)
        
        # Get messages (most recent first)
        messages = client.beta.threads.messages.list(
            thread_id=thread_id
        )
        
        # Get assistant's response (first message should be most recent)
        for message in messages.data:
            if message.role == "assistant":
                # Extract text content from message
                content_parts = message.content
                message_text = ""
                
                for part in content_parts:
                    if hasattr(part, 'text') and part.text:
                        message_text += part.text.value
                
                return message_text
                
        logger.error("No assistant response found in messages")
        return ""
        
    except Exception as e:
        import traceback
        logger.error(f"Error processing with assistant: {e}")
        logger.error(traceback.format_exc())
        return ""

def parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a datetime string into a datetime object.
    
    Args:
        date_str: Date string to parse or None
        
    Returns:
        datetime object or None if parsing failed
    """
    if not date_str:
        return None
        
    # Try various date formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO format with microseconds and Z
        "%Y-%m-%dT%H:%M:%SZ",     # ISO format with Z
        "%Y-%m-%dT%H:%M:%S",      # ISO format without Z
        "%Y-%m-%d %H:%M:%S",      # Standard format
        "%Y-%m-%d",               # Just date
        "%d/%m/%Y %H:%M:%S",      # European format with time
        "%d/%m/%Y",               # European format just date
        "%d-%m-%Y %H:%M:%S",      # European format with dashes
        "%d-%m-%Y"                # European format with dashes, just date
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    logger.warning(f"Could not parse date string: {date_str}")
    return None

@db_connection_handler
def save_transaction_to_db(conn, transaction_data: Dict[str, Any], transcription_id: Optional[int] = None) -> Tuple[bool, int]:
    """
    Save financial transaction data to database
    
    Args:
        conn: Database connection (from decorator)
        transaction_data: Transaction data to save
        transcription_id: Optional ID of associated transcription
        
    Returns:
        Tuple containing (success status, transaction ID or error info)
    """
    try:
        cur = conn.cursor()
        
        # Extract fields from transaction data
        tipo_lancamento = transaction_data.get('tipo_lancamento', '').lower()
        if tipo_lancamento not in ['receita', 'despesa']:
            logger.error(f"Invalid transaction type: {tipo_lancamento}")
            return False, {"error": f"Invalid transaction type: {tipo_lancamento}. Must be 'receita' or 'despesa'"}
            
        valor = transaction_data.get('valor', 0)
        try:
            valor = float(valor)
        except (ValueError, TypeError):
            logger.error(f"Invalid transaction amount: {valor}")
            return False, {"error": f"Invalid transaction amount: {valor}. Must be a number"}
            
        moeda = transaction_data.get('moeda', 'EUR')
        nota = transaction_data.get('nota', '')
        
        # Handle date if provided
        data_str = transaction_data.get('data')
        data = parse_datetime(data_str)
        data_db = data.isoformat() if data else None
        
        # Insert into database
        cur.execute("""
            INSERT INTO contas 
            (tipo_lancamento, valor, moeda, nota, data, id_transcricao_origem)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (tipo_lancamento, valor, moeda, nota, data_db, transcription_id))
        
        # Get the inserted ID
        transaction_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"Transaction saved to database with ID: {transaction_id}")
        
        # If transcription ID was provided, mark it as processed
        if transcription_id:
            cur.execute("""
                UPDATE transcricoes
                SET processado = true, tabela_destino = 'contas', id_destino = %s
                WHERE id = %s
            """, (transaction_id, transcription_id))
            conn.commit()
            logger.debug(f"Marked transcription {transcription_id} as processed")
            
        return True, transaction_id
    
    except Exception as e:
        conn.rollback()
        import traceback
        error_msg = f"Error saving transaction to database: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, {"error": error_msg, "traceback": traceback.format_exc()}

def process_transaction_entry(text: str, db_id: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Process a financial transaction entry from text
    
    Args:
        text: Text input to process
        db_id: Optional transcription ID to associate
        
    Returns:
        Tuple containing (success status, transaction data or error info)
    """
    try:
        # Log the start of processing
        logger.debug(f"Processing transaction entry (length: {len(text)})")
        
        # Process text with OpenAI assistant
        response = process_with_assistant(text)
        if not response:
            logger.error("Empty response from assistant")
            return False, {"error": "Empty response from assistant"}
            
        # Extract structured data from response
        transaction_data = extract_json_from_text(response)
        if not transaction_data:
            logger.error("Failed to extract transaction data from assistant response")
            logger.debug(f"Assistant response: {response[:100]}...")
            return False, {"error": "Failed to extract transaction data from assistant response"}
            
        # Validate required fields
        if not transaction_data.get('tipo_lancamento'):
            logger.error("Transaction data missing required tipo_lancamento field")
            return False, {"error": "Transaction must have tipo_lancamento field (receita or despesa)"}
            
        if 'valor' not in transaction_data:
            logger.error("Transaction data missing required valor field")
            return False, {"error": "Transaction must have valor field (numerical amount)"}
            
        # Save to database
        db_success, db_result = save_transaction_to_db(transaction_data, transcription_id=db_id)
        if not db_success:
            logger.error("Failed to save transaction to database")
            return False, db_result
            
        # Add database ID to the transaction data
        transaction_data['id'] = db_result
        
        return True, transaction_data
        
    except Exception as e:
        import traceback
        error_msg = f"Error processing transaction entry: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, {"error": error_msg, "traceback": traceback.format_exc()}
