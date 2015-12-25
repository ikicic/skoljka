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
