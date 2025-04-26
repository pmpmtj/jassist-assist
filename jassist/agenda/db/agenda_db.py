"""
Database operations for agenda events.

This module handles database operations specific to agenda events.
"""

import json
from typing import Dict, Any, Optional, List
from jassist.logger_utils.logger_utils import setup_logger
from jassist.db_utils.db_connection import db_connection_handler

logger = setup_logger("agenda_db", module="agenda")

def save_agenda_event(
    resumo: str,
    localizacao: str,
    descricao: str,
    inicio_data_hora: str,
    inicio_fuso_horario: str,
    fim_data_hora: str,
    fim_fuso_horario: str,
    participantes: Optional[List[Dict[str, Any]]] = None,
    recorrencia: Optional[List[str]] = None,
    lembretes: Optional[Dict[str, Any]] = None,
    visibilidade: Optional[str] = None,
    cor_id: Optional[str] = None,
    transparencia: Optional[str] = None,
    estado: Optional[str] = None,
    criado_em: Optional[str] = None
) -> Optional[int]:
    """
    Save a agenda event to the database.
    
    Args:
        resumo: Event title/summary
        inicio_data_hora: Start date and time in ISO format
        fim_data_hora: End date and time in ISO format
        localizacao: Event location
        descricao: Event description
        inicio_fuso_horario: Timezone for start time
        fim_fuso_horario: Timezone for end time
        participantes: List of attendees
        recorrencia: Recurrence rules
        lembretes: Reminder configuration
        visibilidade: Event visibility
        cor_id: Event color
        transparencia: Whether event blocks time
        estado: Event status
        criado_em: Optional ID of the transcription this event is from
        
    Returns:
        int: ID of the saved event, or None if save failed
    """
    try:
        logger.debug(f"Saving agenda event: {resumo}")
            
        # Log key details for debugging
        logger.debug(f"Event details: summary={resumo}, location={localizacao}")
        logger.debug(f"Event times: start={inicio_data_hora}, end={fim_data_hora}")
            
        # Save to database
        event_id = _save_agenda_event_to_db_direct(
            resumo=resumo,
            descricao=descricao,
            localizacao=localizacao,
            inicio_data_hora=inicio_data_hora,
            inicio_fuso_horario=inicio_fuso_horario,
            fim_data_hora=fim_data_hora,
            fim_fuso_horario=fim_fuso_horario,
            participantes=participantes,
            recorrencia=recorrencia,
            lembretes=lembretes,
            visibilidade=visibilidade,
            cor_id=cor_id,
            transparencia=transparencia,
            estado=estado,
            id_transcricao=criado_em
        )
        
        if event_id:
            logger.info(f"Successfully saved agenda event with ID: {event_id}")
        else:
            logger.error("Failed to save agenda event to database")
            
        return event_id
        
    except Exception as e:
        logger.exception(f"Error saving agenda event to database: {e}")
        return None

@db_connection_handler
def _save_agenda_event_to_db_direct(
    conn, 
    resumo, 
    descricao, 
    localizacao, 
    inicio_data_hora, 
    inicio_fuso_horario,
    fim_data_hora, 
    fim_fuso_horario,
    participantes=None,
    recorrencia=None,
    lembretes=None,
    visibilidade=None,
    cor_id=None,
    transparencia=None,
    estado=None, 
    id_transcricao=None
) -> int:
    """
    Direct function to save an agenda event to the database with explicit parameters.
    
    Args:
        conn: Database connection (injected by decorator)
        resumo: Event summary
        descricao: Event description
        localizacao: Event location
        inicio_data_hora: Start date and time
        inicio_fuso_horario: Start timezone
        fim_data_hora: End date and time
        fim_fuso_horario: End timezone
        participantes: Event attendees
        recorrencia: Recurrence rules
        lembretes: Reminders
        visibilidade: Visibility
        cor_id: Color ID
        transparencia: Transparency
        estado: Status
        id_transcricao: Optional ID of the transcription this event is from
        
    Returns:
        int: ID of the saved event, or None if save failed
    """
    try:
        cur = conn.cursor()
        
        # Better debugging info
        logger.debug(f"DB insertion data: resumo={resumo}, descricao={descricao}, localizacao={localizacao}")
        logger.debug(f"DB insertion time: inicio_data_hora={inicio_data_hora}, fim_data_hora={fim_data_hora}")
        
        # Insert the event - corrected for the actual database schema
        cur.execute("""
        INSERT INTO agenda
        (resumo, descricao, localizacao, 
         inicio_data_hora, inicio_fuso_horario,
         fim_data_hora, fim_fuso_horario,
         participantes, recorrencia, lembretes,
         visibilidade, cor_id, transparencia, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """, (
            resumo,
            descricao,
            localizacao,
            inicio_data_hora,
            inicio_fuso_horario,
            fim_data_hora,
            fim_fuso_horario,
            json.dumps(participantes) if participantes else None,
            json.dumps(recorrencia) if recorrencia else None,
            json.dumps(lembretes) if lembretes else None,
            visibilidade,
            cor_id,
            transparencia,
            estado
        ))
        
        # Get the ID of the inserted record
        result = cur.fetchone()
        event_id = result[0] if result else None
        
        conn.commit()
        
        logger.info(f"Agenda event saved to database with ID: {event_id}")
        
        return event_id
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving agenda event to database: {e}")
        return None


