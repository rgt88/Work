import pandas as pd
import pywhatkit as kit

# Membaca data dari file Excel
# Pastikan file 'contacts.xlsx' berada di direktori yang sama dengan script atau berikan path yang benar
df = pd.read_excel('C:/Users/......../Documents/Coding/Muamalat/Whatsapp Blast/contacts.xlsx')

# Loop untuk mengirim pesan ke setiap nomor
for index, row in df.iterrows():
    name = row['Name']  # Nama kolom harus sesuai dengan yang ada di file Excel
    number = row['Phone']  # Nama kolom harus sesuai dengan yang ada di file Excel
    message = f"Hello {name}, this message is sent to you just for test. hehehe. Happy nice day!"

    # Mengirim pesan
    kit.sendwhatmsg_instantly(f"+{number}", message)

print("Pesan telah dikirim ke semua kontak.")
