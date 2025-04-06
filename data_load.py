# coding: utf-8
import numpy as np
import pandas as pd

import yaml

import os
current_dir = os.path.abspath(os.getcwd())
parent_dir = os.path.dirname(current_dir)

import sys
sys.path.append(current_dir)

def read_yaml_config(yaml_file: str, section: str) -> dict:
    """
    Reading yaml settings
    """
    with open(yaml_file, 'r') as yaml_stream:
        descriptor = yaml.full_load(yaml_stream)
        if section in descriptor:
            configuration = descriptor[section]
            return configuration
        else:
            print(f"Section {section} not find in the file '{yaml_file}'")

def get_data(query: str, file, section='logging') -> list:
    settings = read_yaml_config(file, section)
    conn = None
    try:
        conn = ps.connect(**settings)
        cur = conn.cursor()
        cur.execute(query)
        try:
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            df = pd.DataFrame(rows, columns=colnames)
        except:
            df=pd.DataFrame()
        cur.close()
        conn.close()
        return df
    except (Exception, ps.DatabaseError) as err:
        # logging.error(f"PostgreSQL can't execute query - {err}")
        print(f"PostgreSQL can't execute query - {err}")
    finally:
        if conn is not None:
            conn.close()
            

def get_engine(file, section='logging'):
    settings = read_yaml_config(file, section)
    from sqlalchemy import create_engine
    postgresql_engine_st = "postgresql://"+settings['user']+":"+settings['password']+"@"+settings['host']+"/"+settings['database']
    postgresql_engine = create_engine(postgresql_engine_st)

    return postgresql_engine

def insert_data(df_to_sql, schema, table_name):
    import datetime
    now = datetime.datetime.now()

    main_engine=get_engine('config.yaml')

    df_to_sql['insert_time'] = now
    df_to_sql.to_sql(
                            table_name, 
                            con=main_engine, 
                            schema=schema,
                            if_exists='append', 
                            index=False
                        )
    print(str(len(df_to_sql))+' rows inserted to  '+table_name)