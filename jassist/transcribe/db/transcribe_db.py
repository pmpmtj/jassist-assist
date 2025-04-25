"""
Operações de base de dados para transcrições.

Este módulo lida com operações de base de dados específicas para transcrições.
"""

import datetime
import json
from typing import Optional, Dict, Any
from jassist.logger_utils.logger_utils import setup_logger
from jassist.db_utils.db_manager import initialize_db, create_tables
from jassist.db_utils.db_connection import db_connection_handler
import psycopg2.errors

logger = setup_logger("transcribe_db", module="transcribe")

def initialize_transcription_db() -> bool:
    """
    Inicializa a base de dados para operações de transcrição.
    
    Returns:
        bool: True se a inicialização foi bem sucedida, False caso contrário
    """
    try:
   
        # Initialize the database connection
        if not initialize_db():
            logger.error("Falha na inicialização da conexão com a base de dados")
            return False
            
        # # Create tables
        # logger.info("Criando tabelas da base de dados...")
        # try:
        #     create_tables()
        #     logger.info("Tabelas da base de dados criadas com sucesso")
        # except Exception as e:
        #     # If we get a DuplicateObject error, the tables/triggers already exist, which is fine
        #     if isinstance(e, psycopg2.errors.DuplicateObject):
        #         logger.info("As tabelas já existem, continuando com o esquema existente")
        #     else:
        #         logger.error(f"Falha ao criar as tabelas da base de dados: {e}")
        #         return False
            
        logger.info("Base de dados inicializada com sucesso")
        return True
    except Exception as e:
        logger.error(f"Falha ao inicializar a base de dados: {e}")
        return False

@db_connection_handler
def save_transcription(
    conn,
    conteudo: str,
    nome_ficheiro: str = None,
    caminho_audio: str = None,
    duracao_segundos: Optional[float] = None,
    metadados: Optional[Dict[str, Any]] = None,
    etiqueta: str = None,
    tabela_destino: str = None,
    id_destino: int = None
) -> Optional[int]:
    """
    Guarda uma transcrição na base de dados.
    
    Args:
        conn: Conexão com a base de dados (injetada pelo decorador)
        conteudo: O conteúdo da transcrição
        nome_ficheiro: Nome do ficheiro de áudio transcrito
        caminho_audio: Caminho para o ficheiro de áudio
        duracao_segundos: Duração do áudio em segundos
        metadados: Metadados adicionais como um dicionário
        etiqueta: Etiqueta para categorizar a transcrição
        tabela_destino: Tabela de destino se esta transcrição estiver ligada a outro registo
        id_destino: ID na tabela de destino se estiver ligada
        
    Returns:
        int: ID da transcrição guardada, ou None se o guardado falhou
    """
    try:
        cur = conn.cursor()
        
        # Convert metadata to JSON if provided
        metadados_json = json.dumps(metadados) if metadados else None
        
        # Insert the transcription
        cur.execute("""
        INSERT INTO transcricoes
        (conteudo, nome_ficheiro, caminho_audio, duracao_segundos, metadados, etiqueta, tabela_destino, id_destino)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """, (
            conteudo,
            nome_ficheiro,
            caminho_audio,
            duracao_segundos,
            metadados_json,
            etiqueta,
            tabela_destino,
            id_destino
        ))
        
        # Get the ID of the inserted record
        result = cur.fetchone()
        id_transcricao = result[0] if result else None
        
        conn.commit()
        
        logger.info(f"Transcricao guardada na base de dados com ID: {id_transcricao}")
        return id_transcricao
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao guardar a transcricao na base de dados: {e}")
        return None

def save_raw_transcription(
    conteudo: str,
    nome_ficheiro: str,
    caminho_audio: str,
    duracao_segundos: Optional[float] = None,
    modelo_usado: Optional[str] = None
) -> Optional[int]:
    """
    Guarda uma transcrição bruta na base de dados.
    
    Args:
        conteudo: O conteúdo da transcrição
        nome_ficheiro: Nome do ficheiro de áudio transcrito
        caminho_audio: Caminho para o ficheiro de áudio
        duracao_segundos: Duração opcional do áudio em segundos
        modelo_usado: Nome opcional do modelo usado para a transcrição
        
    Returns:
        int: ID da transcrição guardada, ou None se o guardado falhou
    """
    try:
        metadados = {
            "modelo_usado": modelo_usado,
            "transcrito_em": datetime.datetime.now().isoformat(),
            "raw": True  # Mark this as a raw transcription
        }
        
        # Save the transcription with a raw_transcription tag
        id_transcricao = save_transcription(
            conteudo=conteudo,
            nome_ficheiro=nome_ficheiro,
            caminho_audio=caminho_audio,
            duracao_segundos=duracao_segundos,
            metadados=metadados,
            etiqueta="transcricao_bruta"  # Special tag for raw transcriptions
        )
        
        if id_transcricao:
            logger.info(f"Transcricao bruta guardada na base de dados com ID: {id_transcricao}")
        else:
            logger.error("Falha ao guardar a transcricao bruta na base de dados")
            
        return id_transcricao
        
    except Exception as e:
        logger.error(f"Erro ao guardar a transcricao bruta na base de dados: {e}")
        return None 