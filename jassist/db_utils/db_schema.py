from jassist.db_utils.db_connection import db_connection_handler
from jassist.logger_utils.logger_utils import setup_logger
import traceback

logger = setup_logger("db_schema", module="db_utils")

@db_connection_handler
def create_tables(conn):
    """Criar todas as tabelas da base de dados com pesquisa em texto completo e relacionamentos"""
    try:
        cur = conn.cursor()

        # Função FTS Partilhada
        cur.execute("""
        CREATE OR REPLACE FUNCTION atualizar_vetor_pesquisa()
        RETURNS trigger AS $$
        DECLARE
            nome_tabela text := TG_TABLE_NAME;
        BEGIN
            IF nome_tabela = 'diario' THEN
                NEW.vetor_pesquisa := to_tsvector('portuguese',
                    coalesce(NEW.conteudo, '') ||
                    coalesce(NEW.estado_espirito, '')
                );
            ELSIF nome_tabela = 'tarefas' THEN
                NEW.vetor_pesquisa := to_tsvector('portuguese',
                    coalesce(NEW.tarefa, '') ||
                    coalesce(NEW.prioridade, '') ||
                    coalesce(NEW.estado, '')
                );
            ELSIF nome_tabela = 'agenda' THEN
                NEW.vetor_pesquisa := to_tsvector('portuguese',
                    coalesce(NEW.resumo, '') ||
                    coalesce(NEW.descricao, '') ||
                    coalesce(NEW.localizacao, '')
                );
            ELSIF nome_tabela = 'contactos' THEN
                NEW.vetor_pesquisa := to_tsvector('portuguese',
                    coalesce(NEW.nome_proprio, '') ||
                    coalesce(NEW.apelido, '') ||
                    coalesce(NEW.email, '') ||
                    coalesce(NEW.telefone, '') ||
                    coalesce(NEW.nota, '')
                );
            ELSIF nome_tabela = 'entidades' THEN
                NEW.vetor_pesquisa := to_tsvector('portuguese',
                    coalesce(NEW.nome, '') ||
                    coalesce(NEW.tipo, '') ||
                    coalesce(NEW.contexto, '')
                );
            ELSIF nome_tabela = 'contas' THEN
                NEW.vetor_pesquisa := to_tsvector('portuguese',
                    coalesce(NEW.tipo_lancamento, '') ||
                    coalesce(NEW.nota, '') ||
                    coalesce(NEW.moeda, '')
                );
            ELSE
                NEW.vetor_pesquisa := to_tsvector('portuguese', '');
            END IF;
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """)

        # Aqui segue a tradução completa das tabelas, respeitando o original:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS transcricoes (
            id SERIAL PRIMARY KEY,
            conteudo TEXT NOT NULL,
            nome_ficheiro TEXT,
            caminho_audio TEXT,
            criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            duracao_segundos FLOAT,
            metadados JSONB,
            etiqueta TEXT,
            tabela_destino TEXT,
            id_destino INTEGER,
            processado BOOLEAN DEFAULT FALSE
        )
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_transcricoes_criado_em ON transcricoes(criado_em)
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS resumos_diarios (
            id SERIAL PRIMARY KEY,
            conteudo TEXT NOT NULL,
            data_resumo TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            nome_ficheiro TEXT,
            intervalo_inicio TIMESTAMP WITH TIME ZONE,
            intervalo_fim TIMESTAMP WITH TIME ZONE,
            vetor_pesquisa tsvector
        )
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_resumos_diarios_data ON resumos_diarios(data_resumo)
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_resumos_diarios_vetor_pesquisa ON resumos_diarios USING GIN(vetor_pesquisa)
        """)
        cur.execute("""
        DROP TRIGGER IF EXISTS trg_atualizar_vetor_resumos ON resumos_diarios;
        """)
        cur.execute("""
        CREATE TRIGGER trg_atualizar_vetor_resumos
        BEFORE INSERT OR UPDATE ON resumos_diarios
        FOR EACH ROW EXECUTE FUNCTION atualizar_vetor_pesquisa()
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id SERIAL PRIMARY KEY,
            resumo TEXT,
            localizacao TEXT,
            descricao TEXT,
            inicio_data_hora TEXT,
            inicio_fuso_horario TEXT,
            fim_data_hora TEXT,
            fim_fuso_horario TEXT,
            participantes TEXT,
            recorrencia TEXT,
            lembretes TEXT,
            visibilidade TEXT,
            cor_id TEXT,
            transparencia TEXT,
            estado TEXT,
            criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            vetor_pesquisa tsvector
        )
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_eventos_inicio ON agenda(inicio_data_hora)
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_eventos_fim ON agenda(fim_data_hora)
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_eventos_intervalo ON agenda(inicio_data_hora, fim_data_hora)
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_eventos_vetor_pesquisa ON agenda USING GIN(vetor_pesquisa)
        """)
        cur.execute("""
        DROP TRIGGER IF EXISTS trg_atualizar_vetor_eventos ON agenda;
        """)
        cur.execute("""
        CREATE TRIGGER trg_atualizar_vetor_eventos
        BEFORE INSERT OR UPDATE ON agenda
        FOR EACH ROW EXECUTE FUNCTION atualizar_vetor_pesquisa()
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS diario (
            id SERIAL PRIMARY KEY,
            conteudo TEXT NOT NULL,
            data_entrada TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            estado_espirito TEXT,
            etiquetas TEXT[],
            vetor_pesquisa tsvector,
            id_transcricao_origem INTEGER REFERENCES transcricoes(id) ON DELETE SET NULL
        )
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_diario_data_entrada ON diario(data_entrada)
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_diario_vetor_pesquisa ON diario USING GIN(vetor_pesquisa)
        """)
        cur.execute("""
        DROP TRIGGER IF EXISTS trg_atualizar_vetor_diario ON diario;
        """)
        cur.execute("""
        CREATE TRIGGER trg_atualizar_vetor_diario
        BEFORE INSERT OR UPDATE ON diario
        FOR EACH ROW EXECUTE FUNCTION atualizar_vetor_pesquisa()
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tarefas (
            id SERIAL PRIMARY KEY,
            tarefa TEXT NOT NULL,
            prazo TIMESTAMP WITH TIME ZONE,
            prioridade TEXT,
            estado TEXT DEFAULT 'pendente',
            criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            vetor_pesquisa tsvector,
            id_transcricao_origem INTEGER REFERENCES transcricoes(id) ON DELETE SET NULL
        )
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_tarefas_prazo ON tarefas(prazo)
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_tarefas_vetor_pesquisa ON tarefas USING GIN(vetor_pesquisa)
        """)
        cur.execute("""
        DROP TRIGGER IF EXISTS trg_atualizar_vetor_tarefas ON tarefas;
        """)
        cur.execute("""
        CREATE TRIGGER trg_atualizar_vetor_tarefas
        BEFORE INSERT OR UPDATE ON tarefas
        FOR EACH ROW EXECUTE FUNCTION atualizar_vetor_pesquisa()
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS contactos (
            id SERIAL PRIMARY KEY,
            nome_proprio TEXT,
            apelido TEXT,
            telefone TEXT,
            email TEXT,
            nota TEXT,
            criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            vetor_pesquisa tsvector,
            id_transcricao_origem INTEGER REFERENCES transcricoes(id) ON DELETE SET NULL
        )
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_contactos_vetor_pesquisa ON contactos USING GIN(vetor_pesquisa)
        """)
        cur.execute("""
        DROP TRIGGER IF EXISTS trg_atualizar_vetor_contactos ON contactos;
        """)
        cur.execute("""
        CREATE TRIGGER trg_atualizar_vetor_contactos
        BEFORE INSERT OR UPDATE ON contactos
        FOR EACH ROW EXECUTE FUNCTION atualizar_vetor_pesquisa()
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS entidades (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            tipo TEXT,
            contexto TEXT,
            pontuacao_relevancia FLOAT,
            criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            vetor_pesquisa tsvector,
            id_transcricao_origem INTEGER REFERENCES transcricoes(id) ON DELETE SET NULL
        )
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_entidades_vetor_pesquisa ON entidades USING GIN(vetor_pesquisa)
        """)
        cur.execute("""
        DROP TRIGGER IF EXISTS trg_atualizar_vetor_entidades ON entidades;
        """)
        cur.execute("""
        CREATE TRIGGER trg_atualizar_vetor_entidades
        BEFORE INSERT OR UPDATE ON entidades
        FOR EACH ROW EXECUTE FUNCTION atualizar_vetor_pesquisa()
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS contas (
            id SERIAL PRIMARY KEY,
            tipo_lancamento TEXT CHECK (tipo_lancamento IN ('receita', 'despesa')) NOT NULL,
            valor NUMERIC(12, 2) NOT NULL,
            moeda TEXT DEFAULT 'EUR',
            nota TEXT,
            data TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            vetor_pesquisa tsvector,
            id_transcricao_origem INTEGER REFERENCES transcricoes(id) ON DELETE SET NULL
        )
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_contas_data ON contas(data)
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_contas_vetor_pesquisa ON contas USING GIN(vetor_pesquisa)
        """)
        cur.execute("""
        DROP TRIGGER IF EXISTS trg_atualizar_vetor_contas ON contas;
        """)
        cur.execute("""
        CREATE TRIGGER trg_atualizar_vetor_contas
        BEFORE INSERT OR UPDATE ON contas
        FOR EACH ROW EXECUTE FUNCTION atualizar_vetor_pesquisa()
        """)

        conn.commit()
        logger.info("Todas as tabelas com FTS criadas com sucesso.")
        return True

    except Exception as e:
        conn.rollback()
        logger.error("Erro durante a criação das tabelas.")
        logger.error(traceback.format_exc())
        raise
