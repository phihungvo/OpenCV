-- THIS FILE IS GENERATED. DO NOT EDIT IT.
-- Instead, edit the schema/db.sql file and run the 'npm run generate' command.
-- This file to DELETE ALL DATA from all tables in the public schema.


DO
$$
BEGIN
    -- Disable constraints temporarily
    EXECUTE (
        SELECT string_agg('ALTER TABLE ' || quote_ident(schemaname) || '.' || quote_ident(tablename) || ' DISABLE TRIGGER ALL;', ' ')
        FROM pg_tables
        WHERE schemaname = 'public'
    );

    -- Truncate all tables
    EXECUTE (
        SELECT string_agg('TRUNCATE TABLE ' || quote_ident(schemaname) || '.' || quote_ident(tablename) || ' CASCADE;', ' ')
        FROM pg_tables
        WHERE schemaname = 'public'
    );

    -- Enable constraints again
    EXECUTE (
        SELECT string_agg('ALTER TABLE ' || quote_ident(schemaname) || '.' || quote_ident(tablename) || ' ENABLE TRIGGER ALL;', ' ')
        FROM pg_tables
        WHERE schemaname = 'public'
    );
END;
$$;


