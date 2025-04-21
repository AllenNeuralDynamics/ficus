/********************************************************************
 *
 *  Database setup script for PostgreSQL
 *
 ********************************************************************/

-- CREATE TABLE rigs(
--     id 
--         INTEGER
--         PRIMARY KEY
--         GENERATED ALWAYS AS IDENTITY,
--     full_name text,
--     rig_type text,
--     comp_type text,
--     instance text,
--     host_name varchar(255)
-- );

-- CREATE TABLE calibrations(
--     id 
--         INTEGER
--         PRIMARY KEY
--         GENERATED ALWAYS AS IDENTITY,
--     rig_id integer REFERENCES rigs(id),
--     device_name text,
--     description text,
--     date timestamp,
--     input_data json, 
--     output_data json,
--     notes text
-- );

