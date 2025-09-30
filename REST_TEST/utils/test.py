from accesstovm import ssh_connect

# 1️⃣ SSH into VM
ssh = ssh_connect("192.168.56.101", "cisco", "password")



# 3️⃣ Create Table inside DB
table_structure = """
id INT AUTO_INCREMENT PRIMARY KEY,
username VARCHAR(50) NOT NULL,
password VARCHAR(100) NOT NULL,
address VARCHAR(255),
email VARCHAR(100)
"""



# 4️⃣ Close SSH
ssh.close()
