import datetime
from pathlib import Path

from jassist.transcribe.config_loader import load_config, load_environment
from jassist.transcribe.model_handler import get_openai_client, get_transcription_model
from jassist.transcribe.audio_files_processor import get_audio_files, calculate_duration
from jassist.transcribe.transcriber import transcribe_file
from jassist.utils.file_tools import clean_directory
from jassist.logger_utils.logger_utils import setup_logger
from jassist.transcribe.db.transcribe_db import initialize_transcription_db, save_raw_transcription
from jassist.utils.path_utils import resolve_path

logger = setup_logger("transcribe_cli", module="transcribe")

def save_to_text_file(transcription: str, output_dir: Path, prefix: str):
    """Guarda o texto da transcrição num ficheiro com o timestamp no nome do ficheiro."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}_{prefix}.txt"
        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcription)
        logger.info(f"Transcrição guardada para: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Falha ao guardar a transcrição para o ficheiro: {e}")
        return False

def main():
    logger.info("Iniciando a CLI de transcrição...")

    # Step 1: Load config and env
    load_environment()
    config = load_config()

    # Get the model name that will be used for transcription
    model_name = get_transcription_model(config)
    logger.info(f"Usando o modelo de transcrição: {model_name}")

    # Step 2: Initialize OpenAI
    client = get_openai_client()
    if not client:
        logger.error("Não é possível continuar sem o cliente OpenAI.")
        return
    
    # Step 3: Initialize database
    if not initialize_transcription_db():
        logger.error("Falha na inicialização da base de dados.")
        return

    # Step 4: Resolve paths with absolute paths
    script_dir = Path(__file__).resolve().parent
    voice_diary_dir = script_dir.parent

    # Hardcoded downloads directory path (design decision)
    downloads_dir = "downloaded"
    logger.info(f"Using hardcoded downloads directory: {downloads_dir}")
    
    # Get output directory from transcribe config's paths section
    output_dir_config = config.get("paths", {}).get("output_dir", "transcriptions")
    
    # Create absolute paths using the consistent resolver function
    downloads_dir = resolve_path(downloads_dir, voice_diary_dir)
    output_dir = resolve_path(output_dir_config, voice_diary_dir)
    
    logger.info(f"Usando o diretório de downloads: {downloads_dir}")
    logger.info(f"Usando o diretório de saída: {output_dir}")

    # Verify the downloads directory exists
    if not downloads_dir.exists():
        logger.error(f"Diretório de downloads não encontrado: {downloads_dir}. Não é possível continuar.")
        return

    # Step 5: Get files
    files = get_audio_files(downloads_dir)
    if not files:
        logger.warning("Nenhum ficheiro de áudio encontrado.")
        return

    successful = 0
    failed = 0

    # Step 6: Process each file
    for file_path in files:
        try:
            logger.info(f"Processando o ficheiro: {file_path.name}")
            duration = calculate_duration(file_path)
            if duration is None:
                logger.warning(f"Não foi possível determinar a duração do ficheiro {file_path.name}, usando o valor padrão de 0.0")
                duration = 0.0

    
            transcription = transcribe_file(client, file_path, config)
            if not transcription:
                logger.error(f"Falha na transcrição do ficheiro: {file_path.name}")
                failed += 1
                continue

            # Get the text from the transcription
            transcription_text = transcription.get("text", "") if isinstance(transcription, dict) else transcription
            
            # STEP 1: SAVE RAW TRANSCRIPTION TO DATABASE IMMEDIATELY
            try:
                raw_db_id = save_raw_transcription(
                    conteudo=transcription_text,
                    nome_ficheiro=file_path.name,
                    caminho_audio=str(file_path),
                    duracao_segundos=duration,
                    modelo_usado=model_name
                )
                
                if not raw_db_id:
                    logger.error("Falha ao guardar a transcrição bruta na base de dados.")
            except Exception as e:
                logger.error(f"Erro ao guardar a transcrição bruta na base de dados: {e}")
                # Continue processing even if database save fails
            
            # STEP 2: SAVE TO TEXT FILE
            if not save_to_text_file(transcription_text, output_dir, file_path.stem):
                logger.warning(f"Continuando o processamento apesar do erro de salvamento do ficheiro para {file_path.name}")
            else:
                successful += 1
                logger.info(f"Ficheiro processado com sucesso: {file_path.name}")
            
            
        except Exception as e:
            logger.error(f"Erro não tratado ao processar o ficheiro {file_path.name}: {e}")
            failed += 1

    # Step 7: Summary
    total = successful + failed
    logger.info(f"Completado {total} ficheiro(s): {successful} bem sucedidos, {failed} falhados.")

    
    # Step 8: Clean the downloads directory after processing
    if len(files) > 0:  # Only clean if there were files to process
        try:
            logger.info("Limpando o diretório de downloads...")
            clean_result = clean_directory(downloads_dir)
            if clean_result["status"] == "success":
                logger.info(f"{clean_result.get('files_deleted', 0)} ficheiros eliminados do diretório de downloads.")
            else:
                logger.error(f"Falha ao limpar o diretório de downloads: {clean_result.get('message', 'Erro desconhecido')}")
        except Exception as e:
            logger.error(f"Erro durante a limpeza do diretório de downloads: {e}")

if __name__ == "__main__":
    main()
