-- Initialize PostgreSQL database for multi-tenant application

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended', 'pending');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE tenant_status AS ENUM ('active', 'inactive', 'suspended', 'trial', 'pending_setup');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE tenant_db TO tenant_admin;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS tenant_schema;

-- Set search path
ALTER DATABASE tenant_db SET search_path TO public, tenant_schema;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END $$;