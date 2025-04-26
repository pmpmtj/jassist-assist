#!/usr/bin/env python
"""
Tarefas Processor Module

This module provides functions for processing task entries using the OpenAI Assistant API.
"""

import json
from typing import Dict, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime

from jassist.logger_utils.logger_utils import setup_logger
from jassist.api_assistants_cliente.adapters.tarefas_adapter import process_with_tarefas_assistant
from jassist.tarefas.utils.json_extractor import extract_json_from_text
from jassist.db_utils.db_connection import db_connection_handler

# Set up logger
logger = setup_logger("tarefas_processor", module="tarefas")

@db_connection_handler
def save_task_to_db(conn, task_data: Dict[str, Any], transcription_id: Optional[int] = None) -> Tuple[bool, int]:
    """
    Save task data to database
    
    Args:
        conn: Database connection (from decorator)
        task_data: Task data to save
        transcription_id: Optional ID of associated transcription
        
    Returns:
        Tuple containing (success status, task ID or error info)
    """
    try:
        cur = conn.cursor()
        
        # Extract fields from task data
        tarefa = task_data.get('tarefa', '')
        if not tarefa:
            logger.error("Task description is required")
            return False, {"error": "Task description is required"}
            
        # Handle date if provided
        prazo_str = task_data.get('prazo')
        prazo_db = None
        if prazo_str:
            try:
                # Try to parse the date in ISO format
                prazo_dt = datetime.fromisoformat(prazo_str.replace('Z', '+00:00'))
                prazo_db = prazo_dt.isoformat()
            except (ValueError, TypeError):
                logger.warning(f"Could not parse deadline date: {prazo_str}, storing as NULL")
        
        prioridade = task_data.get('prioridade', '')
        estado = task_data.get('estado', 'pendente')
        
        # Insert into database
        cur.execute("""
            INSERT INTO tarefas 
            (tarefa, prazo, prioridade, estado, id_transcricao_origem)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (tarefa, prazo_db, prioridade, estado, transcription_id))
        
        # Get the inserted ID
        task_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"Task saved to database with ID: {task_id}")
        
        # If transcription ID was provided, mark it as processed
        if transcription_id:
            cur.execute("""
                UPDATE transcricoes
                SET processado = true, tabela_destino = 'tarefas', id_destino = %s
                WHERE id = %s
            """, (task_id, transcription_id))
            conn.commit()
            logger.debug(f"Marked transcription {transcription_id} as processed")
            
        return True, task_id
    
    except Exception as e:
        conn.rollback()
        import traceback
        error_msg = f"Error saving task to database: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, {"error": error_msg, "traceback": traceback.format_exc()}

def process_task_entry(text: str, db_id: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Process a task entry using the OpenAI Assistant API.
    
    Args:
        text: The text to process
        db_id: Optional database ID for this entry
        
    Returns:
        Tuple containing (success status, task data or error info)
    """
    try:
        logger.debug(f"Processing task entry: {text[:50]}...")
        
        # Process with the assistant
        response = process_with_tarefas_assistant(text)
        logger.debug(f"Received response from assistant: {response[:100]}...")
        
        # Extract JSON from the response
        task_data = extract_json_from_text(response)
        
        if not task_data:
            logger.error("Failed to extract JSON from assistant response")
            return False, {"error": "Failed to extract JSON from assistant response"}
        
        logger.info(f"Successfully extracted task data: {json.dumps(task_data, ensure_ascii=False)[:100]}...")
        
        # Validate required fields
        if not task_data.get('tarefa'):
            logger.error("Task data missing required field: tarefa")
            return False, {"error": "Task must have a description (tarefa)"}
        
        # Save to database
        db_success, db_result = save_task_to_db(task_data, transcription_id=db_id)
        if not db_success:
            logger.error("Failed to save task to database")
            return False, db_result
            
        # Add database ID to the task data
        task_data['id'] = db_result
        
        return True, task_data
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error processing task entry: {e}\n{error_traceback}")
        return False, {"error": str(e), "traceback": error_traceback}
