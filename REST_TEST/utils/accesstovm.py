import paramiko

def ssh_connect(hostname, username, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=hostname, username=username, password=password)
    return ssh
def test_connection(hostname, username, password):
    """
    Test SSH connection. Raises exception if cannot connect.
    """
    ssh = None
    try:
        ssh = ssh_connect(hostname, username, password)
        return ssh  # Caller should close it
    except Exception as e:
        raise e

#
# def list_databases(ssh):
#     """
#     Execute MySQL/MariaDB command to list databases on the connected VM.
#     Returns a list of database names.
#     """
#     try:
#         # Works on most MySQL/MariaDB installs
#         cmd = 'mysql -u root -e "SHOW DATABASES;" -s -N'
#
#         stdin, stdout, stderr = ssh.exec_command(cmd)
#         output = stdout.read().decode().splitlines()
#         errors = stderr.read().decode().strip()
#
#         if errors:
#             return {"error": errors}
#         return output
#     except Exception as e:
#         return {"error": str(e)}


def run_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err
