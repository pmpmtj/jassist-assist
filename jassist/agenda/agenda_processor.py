"""
agenda processor module.

This module processes agenda entries and inserts them into 
the database and Google agenda.
"""

from typing import Dict, Any, Optional, Tuple
from .llm.openai_client import process_with_openai_assistant
from .utils.json_extractor import extract_json_from_text
from .db.agenda_db import save_agenda_event
from .google_agenda import insert_event_into_google_agenda
from .utils.config_manager import load_agenda_config
from jassist.logger_utils.logger_utils import setup_logger
from jassist.db_utils.db_manager import marcar_transcricao_processada

logger = setup_logger("agenda_processor", module="agenda")

def normalize_event_fields(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize event data fields from either English or Portuguese keys.
    
    Args:
        event_data: Original event data with mixed language fields
        
    Returns:
        Dict: Normalized event data with consistent field names
    """
    # Basic fields
    normalized = {}
    
    # Title/Summary field
    normalized["resumo"] = event_data.get("summary") or event_data.get("resumo", "")
    
    # Description field
    normalized["descricao"] = event_data.get("description") or event_data.get("descricao", "")
    
    # Location field
    normalized["localizacao"] = event_data.get("location") or event_data.get("localizacao", "")
    
    # Start time fields
    start_info = event_data.get("start") or event_data.get("inicio", {})
    normalized["inicio_data_hora"] = start_info.get("dateTime") or start_info.get("data_hora")
    normalized["inicio_fuso_horario"] = start_info.get("timeZone") or start_info.get("fuso_horario", "Europe/Lisbon")
    
    # End time fields
    end_info = event_data.get("end") or event_data.get("fim", {})
    normalized["fim_data_hora"] = end_info.get("dateTime") or end_info.get("data_hora")
    normalized["fim_fuso_horario"] = end_info.get("timeZone") or end_info.get("fuso_horario", "Europe/Lisbon")
    
    # Other fields
    normalized["participantes"] = event_data.get("attendees") or event_data.get("participantes")
    normalized["recorrencia"] = event_data.get("recurrence") or event_data.get("recorrencia")
    normalized["lembretes"] = event_data.get("reminders") or event_data.get("lembretes")
    normalized["visibilidade"] = event_data.get("visibility") or event_data.get("visibilidade")
    normalized["cor_id"] = event_data.get("colorId") or event_data.get("cor_id")
    normalized["transparencia"] = event_data.get("transparency") or event_data.get("transparencia")
    normalized["estado"] = event_data.get("status") or event_data.get("estado")
    
    return normalized

def process_agenda_entry(text: str, db_id: Optional[int] = None, 
                      skip_db: bool = False, skip_calendar: bool = False) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Process a voice entry for a agenda event.
    
    Args:
        text: The voice entry text
        db_id: Optional ID of the database record this is associated with
        skip_db: If True, skip database operations
        skip_calendar: If True, skip Google Calendar operations
        
    Returns:
        Tuple containing (success status, event data or error message)
    """
    try:
        logger.info("Processing agenda entry")
        event_data = None
        
        # Step 1: Process with OpenAI to extract agenda event data
        try:
            response = process_with_openai_assistant(text)
            logger.debug("OpenAI processing completed successfully")
        except Exception as e:
            logger.exception(f"Error processing with OpenAI: {e}")
            return False, {"error": f"OpenAI processing failed: {str(e)}"}
        
        # Step 2: Extract JSON from response
        try:
            event_data = extract_json_from_text(response)
            if not event_data:
                logger.error("Failed to extract JSON from LLM response")
                return False, {"error": "Failed to extract JSON from LLM response", "raw_response": response}
            
            # Debug output
            logger.info(f"Extracted event data: {event_data}")
        except Exception as e:
            logger.exception(f"Error extracting JSON: {e}")
            return False, {"error": f"JSON extraction failed: {str(e)}", "raw_response": response}
        
        # Normalize event fields to handle both English and Portuguese field names
        normalized_data = normalize_event_fields(event_data)
        
        # Step 3: Save to database (if not skipped)
        event_id = None
        if not skip_db:
            try:
                event_id = save_agenda_event(
                    resumo=normalized_data["resumo"],
                    descricao=normalized_data["descricao"],
                    localizacao=normalized_data["localizacao"],
                    inicio_data_hora=normalized_data["inicio_data_hora"],
                    fim_data_hora=normalized_data["fim_data_hora"],
                    inicio_fuso_horario=normalized_data["inicio_fuso_horario"],
                    fim_fuso_horario=normalized_data["fim_fuso_horario"],
                    participantes=normalized_data["participantes"],
                    recorrencia=normalized_data["recorrencia"],
                    lembretes=normalized_data["lembretes"],
                    visibilidade=normalized_data["visibilidade"],
                    cor_id=normalized_data["cor_id"],
                    transparencia=normalized_data["transparencia"],
                    estado=normalized_data["estado"],
                    criado_em=db_id
                )
                
                if event_id:
                    logger.info(f"Event saved to database with ID: {event_id}")
                else:
                    logger.error("Failed to save event to database")
                    if not skip_calendar:
                        # Continue if we're still adding to calendar
                        event_data["warning"] = "Failed to save to database, but continuing with Google Calendar"
                    else:
                        return False, {"error": "Database save failed", "event_data": event_data}
            except Exception as e:
                logger.exception(f"Error saving to database: {e}")
                if not skip_calendar:
                    # Continue if we're still adding to calendar
                    event_data["warning"] = f"Database error: {str(e)}, but continuing with Google Calendar"
                else:
                    return False, {"error": f"Database error: {str(e)}", "event_data": event_data}
        else:
            logger.info("Skipping database operations as requested")
            
        # Step 4: Add to Google Calendar (if not skipped)
        if not skip_calendar:
            try:
                link = insert_event_into_google_agenda(event_data)
                if link:
                    logger.info(f"Google agenda event created at: {link}")
                    event_data["google_agenda_link"] = link
                else:
                    logger.warning("Google agenda event creation failed")
                    event_data["warning"] = "Google Calendar event creation failed"
            except Exception as e:
                logger.exception(f"Error adding to Google Calendar: {e}")
                event_data["error"] = f"Google Calendar error: {str(e)}"
                # Continue even if Google Calendar fails
        else:
            logger.info("Skipping Google Calendar operations as requested")
        
        # Step 5: Mark transcription as processed (if applicable)
        if db_id and event_id:
            try:
                marcar_transcricao_processada(
                    id_transcricao=db_id,
                    destino_tabela="eventos_calendario",
                    destino_id=event_id
                )
                logger.info(f"Marked transcription {db_id} as processed")
            except Exception as e:
                logger.warning(f"Failed to mark transcription as processed: {e}")
                event_data["warning"] = f"Failed to mark transcription: {str(e)}"
                # Continue processing - this is not a critical error
        
        return True, event_data
        
    except Exception as e:
        logger.exception(f"Error during agenda processing: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        return False, {"error": f"Agenda processing error: {str(e)}", "traceback": error_traceback} 