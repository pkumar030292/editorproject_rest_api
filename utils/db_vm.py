# utils/db_vm.py
from .accesstovm import ssh_connect, run_command

def list_databases_vm(ip, user, password):
    try:
        ssh = ssh_connect(ip, user, password)
        cmd = 'sudo mariadb -e "SHOW DATABASES;" -s -N'
        out, err = run_command(ssh, cmd)
        ssh.close()
        if err:
            return {"success": False, "message": err}
        dbs = out.splitlines()
        return {"success": True, "databases": dbs}
    except Exception as e:
        return {"success": False, "message": str(e)}

def list_tables_vm(ip, user, password, dbName):
    try:
        ssh = ssh_connect(ip, user, password)
        cmd = f'sudo mariadb -D {dbName} -e "SHOW TABLES;" -s -N'
        out, err = run_command(ssh, cmd)
        ssh.close()
        if err:
            return {"success": False, "message": err}
        tables = out.splitlines()
        return {"success": True, "tables": tables}
    except Exception as e:
        return {"success": False, "message": str(e)}

def describe_table_vm(ip, user, password, db_name, table_name):
    try:
        ssh = ssh_connect(ip, user, password)
        cmd = f'sudo mariadb -D {db_name} -e "DESCRIBE {table_name};"'
        out, err = run_command(ssh, cmd)
        ssh.close()
        if err:
            return {"success": False, "message": err}

        # Parse DESCRIBE output (tab-separated)
        lines = out.splitlines()
        headers = lines[0].split("\t")
        details = [dict(zip(headers, row.split("\t"))) for row in lines[1:]]
        return {"success": True, "details": details}
    except Exception as e:
        return {"success": False, "message": str(e)}
