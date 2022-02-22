
        CREATE OR REPLACE FUNCTION table_update_notify()  RETURNS TRIGGER AS $body$
        DECLARE
            v_old_data json;
            v_new_data json;
        BEGIN
            IF (TG_OP = 'INSERT') THEN
                    v_new_data := row_to_json(NEW);
                    PERFORM pg_notify('outbound_msg_insert', json_build_object('table_name',
                        TG_TABLE_NAME::TEXT, 'method', TG_OP,'new_data', v_new_data)::TEXT);
                    RETURN NEW; 
            ELSE
                RETURN NULL;
            END IF;
        END;
        $body$ LANGUAGE plpgsql;
            
        
        DROP TRIGGER IF EXISTS outbound_msg_insert ON "UserMessages_outgoingmessage";
        CREATE TRIGGER outbound_msg_insert AFTER INSERT ON "UserMessages_outgoingmessage" 
        FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

        