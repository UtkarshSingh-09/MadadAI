from cryptography.fernet import Fernet

# Generate a key
key = Fernet.generate_key()

# Save it to a file
with open("secret.key", "wb") as key_file:
    key_file.write(key)

print(f"🔑 Key Generated: {key}")
print("✅ Saved to 'secret.key'. COPY THIS FILE TO THE HQ LAPTOP!")