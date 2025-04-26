"""
Database Manager Module

This module serves as a facade for the database components.
It provides a centralized interface to the database operations.
"""

from jassist.db_utils.db_connection import (
    initialize_db, 
    close_all_connections,
    db_connection_handler
)
from jassist.db_utils.db_schema import create_tables
from jassist.logger_utils.logger_utils import setup_logger

logger = setup_logger("db_manager", module="db_utils")

# @db_connection_handler
# def mark_transcription_processed(conn, transcription_id, destination_table, destination_id):
#     """
#     Mark a transcription as processed in the database.
#     English function name for consistency.
    
#     Args:
#         conn: Database connection (injected by decorator)
#         transcription_id: ID of the transcription to mark
#         destination_table: Name of the table where the processed data was stored
#         destination_id: ID of the record in the destination table
        
#     Returns:
#         bool: True if successful, False otherwise
#     """
#     return marcar_transcricao_processada(
#         transcription_id=transcription_id, 
#         destino_tabela=destination_table, 
#         destino_id=destination_id
#     )

@db_connection_handler
def marcar_transcricao_processada(conn, id_transcricao, destino_tabela, destino_id):
    """
    Marca uma transcrição como processada no banco de dados.
    Portuguese function name for backward compatibility.
    
    Args:
        conn: Conexão com o banco de dados (injetado pelo decorador)
        id_transcricao: ID da transcrição a ser marcada
        destino_tabela: Nome da tabela onde os dados processados foram armazenados
        destino_id: ID do registro na tabela de destino
        
    Returns:
        bool: True se bem-sucedido, False caso contrário
    """
    try:
        cur = conn.cursor()
        
        # Update the processing status
        # Note: Column names must match the database schema
        cur.execute("""
        UPDATE transcricoes
        SET processado = TRUE,
            tabela_destino = %s,
            id_destino = %s
        WHERE id = %s
        """, (destino_tabela, destino_id, id_transcricao))
        
        # Check if any rows were affected
        if cur.rowcount == 0:
            logger.warning(f"No transcription found with ID {id_transcricao}")
            return False
            
        conn.commit()
        logger.info(f"Transcription {id_transcricao} marked as processed")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.exception(f"Error marking transcription as processed: {e}")
        return False

# Re-export initialize_db to maintain backward compatibility
__all__ = [
    # Connection management
    'initialize_db',
    'close_all_connections',
    'create_tables',
    'db_connection_handler',
    
    # Transcription management
    'marcar_transcricao_processada',
]

