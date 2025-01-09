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


-- ----------------------------
-- Checks structure for table attendance
-- ----------------------------
ALTER TABLE "public"."attendance" ADD CONSTRAINT "attendance_status_check" CHECK (status::text = ANY (ARRAY['Có mặt'::character varying, 'vắng'::character varying, 'trễ'::character varying]::text[]));
ALTER TABLE "public"."attendance" ADD CONSTRAINT "attendance_confidence_score_check" CHECK (confidence_score >= 0::double precision AND confidence_score <= 100::double precision);


ALTER TABLE "public"."attendance" DROP CONSTRAINT "attendance_status_check";
ALTER TABLE "public"."attendance" DROP CONSTRAINT "attendance_confidence_score_check";


ALTER TABLE "public"."attendance" 
ADD CONSTRAINT "attendance_status_check" 
CHECK (status::text = ANY (ARRAY['Có mặt'::character varying, 'Vắng'::character varying, 'Trễ'::character varying]::text[]));

ALTER TABLE "public"."attendance" 
ADD CONSTRAINT "attendance_confidence_score_check" 
CHECK (confidence_score >= 0::double precision AND confidence_score <= 100::double precision);