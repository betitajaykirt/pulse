-- close_case_migration.sql
-- Add fields to surveillance_reports table for the Close Case workflow

ALTER TABLE surveillance_reports 
ADD COLUMN resolution_outcome VARCHAR(50) NULL,
ADD COLUMN closed_at DATETIME NULL;
