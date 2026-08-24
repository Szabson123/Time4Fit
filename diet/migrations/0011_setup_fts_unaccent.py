from django.db import migrations


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('diet', '0010_product_product_pop_id_idx'),
    ]

    operations = [
        # Krok 1: Rozszerzenie i konfiguracja FTS
        migrations.RunSQL(
            sql="""
            CREATE EXTENSION IF NOT EXISTS unaccent;

            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'unaccent_simple') THEN
                    CREATE TEXT SEARCH CONFIGURATION unaccent_simple (COPY = simple);
                    ALTER TEXT SEARCH CONFIGURATION unaccent_simple
                        ALTER MAPPING FOR hword, hword_part, word
                        WITH unaccent, simple;
                END IF;
            END
            $$;
            """,
            reverse_sql="""
            DROP TEXT SEARCH CONFIGURATION IF EXISTS unaccent_simple;
            """
        ),

        # Krok 2: Dodanie wyliczanej kolumny tsvector
        migrations.RunSQL(
            sql="""
            ALTER TABLE public.diet_product 
            ADD COLUMN IF NOT EXISTS search_vector tsvector 
            GENERATED ALWAYS AS (
                to_tsvector('unaccent_simple', coalesce(title, '') || ' ' || coalesce(brand, ''))
            ) STORED;
            """,
            reverse_sql="""
            ALTER TABLE public.diet_product DROP COLUMN IF EXISTS search_vector;
            """
        ),

        # Krok 3: Samotny CREATE INDEX CONCURRENTLY (teraz Postgres nie ma aktywnej transakcji)
        migrations.RunSQL(
            sql="""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_search_vector_pub 
            ON public.diet_product USING gin (search_vector) 
            WHERE user_id IS NULL;
            """,
            reverse_sql="""
            DROP INDEX CONCURRENTLY IF EXISTS idx_product_search_vector_pub;
            """
        ),
    ]