#!/usr/bin/env python
"""
Diario Processor Module

This module handles the processing of diary entries with OpenAI and database storage.
"""

import json
import yaml
import os
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import psycopg2
from psycopg2.extensions import register_adapter, AsIs

from jassist.logger_utils.logger_utils import setup_logger
from jassist.db_utils.db_connection import db_connection_handler
from jassist.diario.utils.config_manager import load_json_config, get_config_dir
from jassist.diario.utils.json_extractor import extract_json_from_text

# Import the adapter
try:
    from jassist.api_assistants_cliente.adapters.diario_adapter import process_with_diario_assistant
    ADAPTER_AVAILABLE = True
except ImportError:
    logger = setup_logger("diario_processor", module="diario")
    logger.warning("Could not import diario adapter, falling back to direct implementation")
    ADAPTER_AVAILABLE = False

# Set up logger if not already set up by the import attempt above
if 'logger' not in locals():
    logger = setup_logger("diario_processor", module="diario")

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
    return load_json_config("diario_assistant_config.json")

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
            logger.debug("Using diario adapter for processing")
            response = process_with_diario_assistant(text)
            return response
        except Exception as e:
            logger.error(f"Error using diario adapter: {e}")
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
        assistant_id = config.get('assistant_id_assistente_de_contactos')
        
        # If not found in config, check environment variables
        if not assistant_id:
            logger.debug("Assistant ID not found in config, checking environment variables")
            assistant_id = os.environ.get('OPENAI_ASSISTANT_ID_DIARIO')
            
        # If still not found, log error and return
        if not assistant_id:
            logger.error("Assistant ID not found in configuration or environment variables")
            return ""
            
        # Get or create thread
        thread_id = config.get('thread_id_assistente_de_contactos_default')
        if not thread_id:
            logger.debug("Creating new thread")
            thread = client.beta.threads.create()
            thread_id = thread.id
            
            # Save thread ID and creation time for future use
            config['thread_id_assistente_de_contactos_default'] = thread_id
            config['thread_id_assistente_de_contactos_default_created_at'] = time.time()
            
            config_path = get_config_dir() / "diario_assistant_config.json"
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

@db_connection_handler
def save_diary_to_db(conn, diary_data: Dict[str, Any], transcription_id: Optional[int] = None) -> Tuple[bool, int]:
    """
    Save diary entry data to database
    
    Args:
        conn: Database connection (from decorator)
        diary_data: Diary entry data to save
        transcription_id: Optional ID of associated transcription
        
    Returns:
        Tuple containing (success status, diary entry ID or error info)
    """
    try:
        logger.debug(f"Saving diary to DB - Parameters: diary_data={type(diary_data)}, transcription_id={type(transcription_id)}")
        
        # Extract and sanitize fields from diary data
        conteudo = diary_data.get('conteudo', '')
        if isinstance(conteudo, dict):
            conteudo = json.dumps(conteudo)
        elif conteudo is None:
            conteudo = ''
        
        estado_espirito = diary_data.get('estado_espirito', '')
        if isinstance(estado_espirito, dict):
            estado_espirito = json.dumps(estado_espirito)
        elif estado_espirito is None:
            estado_espirito = ''
        
        # Get etiquetas as string (we converted it in process_diary_entry)
        etiquetas_str = diary_data.get('etiquetas', '')
        if not isinstance(etiquetas_str, str):
            etiquetas_str = str(etiquetas_str)
            
        logger.debug(f"DB parameters - conteudo: {type(conteudo)}, estado_espirito: {type(estado_espirito)}, etiquetas_str: {type(etiquetas_str)}")
        
        # Insert directly using string_to_array
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO diario 
            (conteudo, estado_espirito, etiquetas, id_transcricao_origem)
            VALUES (%s, %s, STRING_TO_ARRAY(%s, ','), %s)
            RETURNING id
        """, (conteudo, estado_espirito, etiquetas_str, transcription_id))
        
        # Get the inserted ID
        diary_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"Diary entry saved to database with ID: {diary_id}")
        
        # If transcription ID was provided, mark it as processed
        if transcription_id:
            cur.execute("""
                UPDATE transcricoes
                SET processado = true, tabela_destino = 'diario', id_destino = %s
                WHERE id = %s
            """, (diary_id, transcription_id))
            conn.commit()
            logger.debug(f"Marked transcription {transcription_id} as processed")
            
        return True, diary_id
    
    except Exception as e:
        conn.rollback()
        import traceback
        error_msg = f"Error saving diary entry to database: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, {"error": error_msg, "traceback": traceback.format_exc()}

def process_diary_entry(text: str, db_id: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Process a diary entry from text
    
    Args:
        text: Text input to process
        db_id: Optional transcription ID to associate
        
    Returns:
        Tuple containing (success status, diary data or error info)
    """
    try:
        # Debug - check parameter types directly
        logger.debug(f"Processing diary entry - Input types: text: {type(text)}, db_id: {type(db_id)}")
        
        # Handle case where db_id is a dictionary
        transcription_id = None
        if isinstance(db_id, dict):
            logger.debug(f"db_id is a dictionary with keys: {list(db_id.keys())}")
            # Check for db_id key directly
            if 'db_id' in db_id:
                transcription_id = db_id.get('db_id')
                logger.debug(f"Extracted transcription_id from 'db_id' key: {transcription_id}")
            # Also check for id key as fallback
            elif 'id' in db_id:
                transcription_id = db_id.get('id')
                logger.debug(f"Extracted transcription_id from 'id' key: {transcription_id}")
        else:
            transcription_id = db_id
            
        logger.debug(f"Using transcription_id: {transcription_id}")
        
        # Log the start of processing
        logger.debug(f"Processing diary entry (length: {len(text)})")
        
        # Process text with OpenAI assistant
        response = process_with_assistant(text)
        if not response:
            logger.error("Empty response from assistant")
            return False, {"error": "Empty response from assistant"}
            
        # Extract structured data from response
        diary_data = extract_json_from_text(response)
        if not diary_data:
            logger.error("Failed to extract diary data from assistant response")
            logger.debug(f"Assistant response: {response[:100]}...")
            return False, {"error": "Failed to extract diary data from assistant response"}
            
        # Validate required fields
        if not diary_data.get('conteudo'):
            logger.error("Diary data missing required content field")
            return False, {"error": "Diary entry must have content field"}
            
        # Log the data before saving
        logger.debug(f"Diary data: {diary_data}")
        
        # Simplify for testing - convert diary_data to use string instead of array for etiquetas
        if 'etiquetas' in diary_data and isinstance(diary_data['etiquetas'], list):
            etiquetas_list = diary_data['etiquetas']
            # Convert to comma separated string
            etiquetas_str = ",".join(str(tag) for tag in etiquetas_list if tag)
            # Replace with the string version
            diary_data['etiquetas'] = etiquetas_str
            logger.debug(f"Converted etiquetas to string: {etiquetas_str}")
        
        # Save to database
        db_success, db_result = save_diary_to_db(diary_data=diary_data, transcription_id=transcription_id)
        if not db_success:
            logger.error("Failed to save diary entry to database")
            return False, db_result
            
        # Add database ID to the diary data
        diary_data['id'] = db_result
        
        return True, diary_data
        
    except Exception as e:
        import traceback
        error_msg = f"Error processing diary entry: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, {"error": error_msg, "traceback": traceback.format_exc()}
