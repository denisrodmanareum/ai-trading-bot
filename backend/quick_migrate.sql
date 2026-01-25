-- Quick migration for trades table
-- Run this after stopping the backend server

ALTER TABLE trades ADD COLUMN roi FLOAT NULL;
ALTER TABLE trades ADD COLUMN entry_time DATETIME NULL;
ALTER TABLE trades ADD COLUMN exit_time DATETIME NULL;
ALTER TABLE trades ADD COLUMN status VARCHAR DEFAULT 'CLOSED';

-- Verify
SELECT name FROM pragma_table_info('trades');
