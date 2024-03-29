from src.Config import DEFAULT_TRIGGER_OPTIONS


# noinspection SqlResolve,PyPep8Naming
def generate_triggers(service_name, table_name, save_file=True, options: DEFAULT_TRIGGER_OPTIONS = None) -> list[str]:
    """
    Creates triggers with the given SERVICE_NAME and appends '_update', '_insert' or '_delete'
    to corresponding triggers
    :return: [setup sql, cleanup sql]
    """

    if options is None:
        options = DEFAULT_TRIGGER_OPTIONS
    else:
        for k in DEFAULT_TRIGGER_OPTIONS.keys():
            if not options.get(k):
                options[k] = DEFAULT_TRIGGER_OPTIONS[k]

    triggers = options['triggers'] if len(options.get('triggers', [])) else DEFAULT_TRIGGER_OPTIONS['triggers']
    _update_name = f'{service_name}_update' if not options.get(
        'trigger_names', {}).get('update') else options['trigger_names']['update']

    _del_name = f'{service_name}_delete' if not options.get(
        'trigger_names', {}).get('delete') else options['trigger_names']['delete']
    _insert_name = f'{service_name}_insert' if not options.get(
        'trigger_names', {}).get('insert') else options['trigger_names']['insert']

    _update_blk = f"""(TG_OP = 'UPDATE') THEN
                    v_old_data := row_to_json(OLD);
                    v_new_data := row_to_json(NEW);
                    PERFORM pg_notify('{_update_name}', json_build_object('table_name',
                        TG_TABLE_NAME::TEXT, 'method', TG_OP,
                        'new_data', v_new_data)::TEXT);
                    RETURN NEW;"""

    _del_blk = f"""(TG_OP = 'DELETE') THEN
                    v_old_data := row_to_json(OLD);
                    PERFORM pg_notify('{_del_name}', json_build_object('table_name',
                        TG_TABLE_NAME::TEXT, 'method', TG_OP,'old_data', v_old_data)::TEXT);
                    RETURN OLD;"""

    __insert_blk = f"""(TG_OP = 'INSERT') THEN
                    v_new_data := row_to_json(NEW);
                    PERFORM pg_notify('{_insert_name}', json_build_object('table_name',
                        TG_TABLE_NAME::TEXT, 'method', TG_OP,'new_data', v_new_data)::TEXT);
                    RETURN NEW;"""
    _t_map = {
        'update': _update_blk,
        'delete': _del_blk,
        'insert': __insert_blk
    }
    t_init = {
        'update': f"""
         DROP TRIGGER IF EXISTS {_update_name}  ON "{table_name}";
         CREATE TRIGGER {_update_name} AFTER UPDATE ON "{table_name}"
         FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

         """,
        'delete': f"""
        DROP TRIGGER IF EXISTS {_del_name} ON "{table_name}";
        CREATE TRIGGER {_del_name} AFTER DELETE ON "{table_name}" 
        FOR EACH ROW EXECUTE PROCEDURE table_update_notify(); 

        """,
        'insert': f"""
        DROP TRIGGER IF EXISTS {_insert_name} ON "{table_name}";
        CREATE TRIGGER {_insert_name} AFTER INSERT ON "{table_name}" 
        FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

        """
    }

    func_body = ""
    for i, _trig in enumerate(triggers):
        if i == 0:
            func_body += f"IF {_t_map[_trig]} "
        else:
            func_body += f"ELSIF {_t_map[_trig]}"
    # noinspection SqlUnused
    SQL = f"""
        CREATE OR REPLACE FUNCTION table_update_notify()  RETURNS TRIGGER AS $body$
        DECLARE
            v_old_data json;
            v_new_data json;
        BEGIN
            {func_body}
            ELSE
                RETURN NULL;
            END IF;
        END;
        $body$ LANGUAGE plpgsql;
            
        """
    CLEAN_UP_SQL = f""""""
    for _trig in triggers:
        SQL += t_init[_trig]
        CLEAN_UP_SQL += t_init[_trig]
    CLEAN_UP_SQL += f"""DROP FUNCTION IF EXISTS table_update_notify CASCADE;"""
    if save_file:
        with open(options['output_file'], 'w') as file:
            file.write(SQL)
        with open(options['output_file'].replace(".sql", "_cleanup.sql"), 'w') as file:
            file.write(CLEAN_UP_SQL)
    return [SQL, CLEAN_UP_SQL]


# if __name__ == "__main__":
#     generate_trigger_sql('outbound_msg', 'UserMessages_outgoingmessage')
