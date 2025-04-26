#!/usr/bin/env python
"""
Entidades Processor Module

This module provides functions for processing entity entries using the OpenAI Assistant API.
"""

import json
from typing import Dict, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime

from jassist.logger_utils.logger_utils import setup_logger
from jassist.api_assistants_cliente.adapters.entidades_adapter import process_with_entidades_assistant
from jassist.entidades.utils.json_extractor import extract_json_from_text
from jassist.db_utils.db_connection import db_connection_handler

# Set up logger
logger = setup_logger("entidades_processor", module="entidades")

@db_connection_handler
def save_entity_to_db(conn, entity_data: Dict[str, Any], transcription_id: Optional[int] = None) -> Tuple[bool, int]:
    """
    Save entity data to database
    
    Args:
        conn: Database connection (from decorator)
        entity_data: Entity data to save
        transcription_id: Optional ID of associated transcription
        
    Returns:
        Tuple containing (success status, entity ID or error info)
    """
    try:
        logger.debug(f"Saving entity to DB - Parameters: entity_data={type(entity_data)}, transcription_id={type(transcription_id)}")
        
        cur = conn.cursor()
        
        # Extract and sanitize fields from entity data
        nome = entity_data.get('nome', '')
        if not nome:
            logger.error("Entity name is required")
            return False, {"error": "Entity name is required"}
            
        # Handle case where nome is a dictionary
        if isinstance(nome, dict):
            logger.debug("Converting nome from dict to JSON string")
            nome = json.dumps(nome)
        elif nome is None:
            nome = ''
            
        tipo = entity_data.get('tipo', '')
        if isinstance(tipo, dict):
            logger.debug("Converting tipo from dict to JSON string")
            tipo = json.dumps(tipo)
        elif tipo is None:
            tipo = ''
            
        contexto = entity_data.get('contexto', '')
        if isinstance(contexto, dict):
            logger.debug("Converting contexto from dict to JSON string")
            contexto = json.dumps(contexto)
        elif contexto is None:
            contexto = ''
        
        # Handle relevance score
        pontuacao_relevancia = entity_data.get('pontuacao_relevancia')
        if isinstance(pontuacao_relevancia, dict):
            logger.debug("Converting pontuacao_relevancia from dict to string first")
            pontuacao_relevancia = json.dumps(pontuacao_relevancia)
            
        try:
            pontuacao_relevancia = float(pontuacao_relevancia)
            # Ensure score is between 0 and 1
            pontuacao_relevancia = max(0.0, min(1.0, pontuacao_relevancia))
        except (ValueError, TypeError):
            logger.warning(f"Invalid relevance score: {pontuacao_relevancia}, using 0.5 as default")
            pontuacao_relevancia = 0.5
            
        logger.debug(f"DB parameters - nome: {type(nome)}, tipo: {type(tipo)}, contexto: {type(contexto)}, pontuacao_relevancia: {type(pontuacao_relevancia)}")
        
        # Insert into database
        cur.execute("""
            INSERT INTO entidades 
            (nome, tipo, contexto, pontuacao_relevancia, id_transcricao_origem)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (nome, tipo, contexto, pontuacao_relevancia, transcription_id))
        
        # Get the inserted ID
        entity_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"Entity saved to database with ID: {entity_id}")
        
        # If transcription ID was provided, mark it as processed
        if transcription_id:
            cur.execute("""
                UPDATE transcricoes
                SET processado = true, tabela_destino = 'entidades', id_destino = %s
                WHERE id = %s
            """, (entity_id, transcription_id))
            conn.commit()
            logger.debug(f"Marked transcription {transcription_id} as processed")
            
        return True, entity_id
    
    except Exception as e:
        conn.rollback()
        import traceback
        error_msg = f"Error saving entity to database: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, {"error": error_msg, "traceback": traceback.format_exc()}

def process_entity_entry(text: str, db_id: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Process an entity entry using the OpenAI Assistant API.
    
    Args:
        text: The text to process
        db_id: Optional database ID for this entry
        
    Returns:
        Tuple containing (success status, entity data or error info)
    """
    try:
        # Debug - check parameter types directly
        logger.debug(f"Processing entity entry - Input types: text: {type(text)}, db_id: {type(db_id)}")
        
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
        
        logger.debug(f"Processing entity entry: {text[:50]}...")
        
        # Process with the assistant
        response = process_with_entidades_assistant(text)
        logger.debug(f"Received response from assistant: {response[:100]}...")
        
        # Extract JSON from the response
        entity_data = extract_json_from_text(response)
        
        if not entity_data:
            logger.error("Failed to extract JSON from assistant response")
            return False, {"error": "Failed to extract JSON from assistant response"}
        
        logger.info(f"Successfully extracted entity data: {json.dumps(entity_data, ensure_ascii=False)[:100]}...")
        
        # Validate required fields
        if not entity_data.get('nome'):
            logger.error("Entity data missing required field: nome")
            return False, {"error": "Entity must have a name (nome)"}
        
        # Save to database
        db_success, db_result = save_entity_to_db(entity_data=entity_data, transcription_id=transcription_id)
        if not db_success:
            logger.error("Failed to save entity to database")
            return False, db_result
            
        # Add database ID to the entity data
        entity_data['id'] = db_result
        
        return True, entity_data
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error processing entity entry: {e}\n{error_traceback}")
        return False, {"error": str(e), "traceback": error_traceback}
