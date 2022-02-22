
        DROP TRIGGER IF EXISTS outbound_msg_insert ON "UserMessages_outgoingmessage";
        CREATE TRIGGER outbound_msg_insert AFTER INSERT ON "UserMessages_outgoingmessage" 
        FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

        DROP FUNCTION IF EXISTS table_update_notify CASCADE;