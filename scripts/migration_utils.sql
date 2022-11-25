-- Copyright (c) 2009 www.cryer.co.uk
-- Script is free to use provided this copyright header is included.
-- (The script has been slightly modified.)
drop procedure if exists AddColumnUnlessExists;
delimiter '//'

create procedure AddColumnUnlessExists(
    IN tableName tinytext,
    IN fieldName tinytext,
    IN fieldDef text)
begin
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS
        WHERE column_name=fieldName
        and table_name=tableName
        and table_schema=DATABASE()
        )
    THEN
        set @ddl=CONCAT('ALTER TABLE ',tableName,
            ' ADD COLUMN ',fieldName,' ',fieldDef);
        prepare stmt from @ddl;
        execute stmt;
    END IF;
end;
//

delimiter ';'
-- end script


-- http://stackoverflow.com/questions/3919226/mysql-add-constraint-if-not-exists
DROP PROCEDURE IF EXISTS AddForeignKeyUnlessExists;

DELIMITER '//'

CREATE PROCEDURE AddForeignKeyUnlessExists(
    IN tableName tinytext,
    IN fieldName tinytext,
    IN targetTableName tinytext)
BEGIN
    SET @constraintName = CONCAT(tableName, '_', fieldName);
    IF NOT EXISTS (SELECT * FROM information_schema.TABLE_CONSTRAINTS WHERE
                       CONSTRAINT_SCHEMA = DATABASE() AND
                       CONSTRAINT_NAME   = @constraintName AND
                       CONSTRAINT_TYPE   = 'FOREIGN KEY') THEN
        SET @cmd = CONCAT('ALTER TABLE `', tableName, '` '
                'ADD CONSTRAINT `', @constraintName, '` ',
                'FOREIGN KEY (`', fieldName, '`) ',
                'REFERENCES `', targetTableName, '` (`id`);');
        PREPARE stmt from @cmd;
        EXECUTE stmt;
    END IF;
END;
//

DELIMITER ';'
-- end script


-- http://dba.stackexchange.com/questions/24531/mysql-create-index-if-not-exists
DELIMITER $$

DROP PROCEDURE IF EXISTS AddIndexUnlessExists $$
CREATE PROCEDURE AddIndexUnlessExists(
    given_table    VARCHAR(64),
    given_index    VARCHAR(64),
    given_columns  VARCHAR(64)
)
BEGIN

    DECLARE IndexIsThere INTEGER;

    SELECT COUNT(1) INTO IndexIsThere
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE table_schema = DATABASE()
    AND   table_name   = given_table
    AND   index_name   = given_index;

    IF IndexIsThere = 0 THEN
        SET @sqlstmt = CONCAT('CREATE INDEX ',given_index,' ON ',
        given_table,' (',given_columns,')');
        PREPARE st FROM @sqlstmt;
        EXECUTE st;
        DEALLOCATE PREPARE st;
    ELSE
        SELECT CONCAT('Index ',given_index,' already exists on Table ',
        given_table) CreateindexErrorMessage;
    END IF;

END $$

DELIMITER ;


DELIMITER $$
DROP PROCEDURE IF EXISTS ResizeVarcharIfShorter $$
CREATE PROCEDURE ResizeVarcharIfShorter(
    given_table   VARCHAR(64),
    given_column  VARCHAR(64),
    new_length    INTEGER)
BEGIN
    DECLARE column_len INTEGER;
    SELECT CHARACTER_MAXIMUM_LENGTH INTO column_len
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema = DATABASE()
        AND   table_name   = given_table
        AND   column_name  = given_column;

    IF column_len < new_length THEN
        SET @statement = CONCAT('ALTER TABLE ', given_table, ' MODIFY COLUMN ', given_column, ' VARCHAR(', new_length, ')');
        PREPARE st FROM @statement;
        EXECUTE st;
        DEALLOCATE PREPARE st;
        SELECT CONCAT('Executed: ', @statement) AS '';
    END IF;
END $$
DELIMITER ;
