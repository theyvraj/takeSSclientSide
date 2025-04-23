import wmi
import getpass

username = getpass.getuser()

c = wmi.WMI()

system_uuid = None
for system in c.Win32_ComputerSystemProduct():
    system_uuid = system.UUID
    break

print(f"Username: {username}")
print(f"System UUID: {system_uuid}")
