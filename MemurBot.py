from difflib import SequenceMatcher
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
import tkinter as tk
from tkinter import scrolledtext


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

def soru_cevaplari_yukle(dosya_yolu="soru_cevaplar.json"):
    """
    JSON dosyasından soru-cevap çiftlerini yükler.
    Dosya formatı:
    [
        {"soru": "Okul kayıtları ne zaman başlıyor?", "cevap": "Okul kayıtları genellikle Ağustos ayında başlar. Güncel tarihler için web sitemizi takip edebilirsiniz."},
        {"soru": "Devamsızlık hakkım kaç gün?", "cevap": "Lise öğrencileri için toplam özürsüz devamsızlık hakkı 10 gündür. Özürlü devamsızlık ise 20 günü geçemez."}
    ]
    """
    try:
        with open(dosya_yolu, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Uyarı: '{dosya_yolu}' bulunamadı. Yerel S-C veritabanı boş olacak.")
        return []
    except json.JSONDecodeError:
        print(f"Hata: '{dosya_yolu}' geçerli bir JSON dosyası değil.")
        return []
    
def yerel_cevap_bul(soru, soru_cevap_listesi, esik=0.7):
    """
    1. Soru ile veri tabanındaki sorular arasında benzerlik oranı hesaplanır.
    2. En yüksek benzerlikteki soru ve cevabı bulunur.
    3. Eğer benzerlik düşükse, LLM ile en uygun cevabı bulmaya çalışır.
    """
    soru_lower = soru.lower().strip()
    en_iyi_benzerlik = 0
    en_iyi_cevap = None
    en_iyi_soru = None

    for sc_cifti in soru_cevap_listesi:
        sc_soru = sc_cifti["soru"].lower().strip()
        benzerlik = SequenceMatcher(None, soru_lower, sc_soru).ratio()
        if benzerlik > en_iyi_benzerlik:
                    en_iyi_benzerlik = benzerlik
                    en_iyi_cevap = sc_cifti["cevap"]
                    en_iyi_soru = sc_cifti["soru"]

    if en_iyi_benzerlik >= esik:
                return en_iyi_cevap

    if soru_cevap_listesi:
                sc_listesi_str = "\n".join(
                    [f"Soru: {sc['soru']}\nCevap: {sc['cevap']}" for sc in soru_cevap_listesi]
                )
                prompt = f"""
        Aşağıda okul ile ilgili sık sorulan sorular ve cevapları var:
        {sc_listesi_str}

        Kullanıcıdan gelen yeni soru: "{soru}"

        Yapman gereken:
        - Kullanıcı sorusunu dikkatlice analiz et.
        - Eğer aşağıdaki sorulardan biriyle çok benzerse, o sorunun cevabını döndür.
        - Eğer tam olarak eşleşmiyorsa ama mantıksal olarak en yakın cevabı seç.
        - Eğer cevap bulamadıysan, bilmediğini söyle.
        - Eğer sorulan soru çok genelse, cevap olarak aşağıdaki soruların cevaplarıyla genel bir cevap ver. verdiğin cevap maksimum 2 cümleden oluşsun.
        - Eğer hiçbir cevap uygun değilse, hangi konularda yardımcı olabileceğini ve isterlerse okul idaresiyle görüşebilecekleriyle ilgili bir yazı yaz. yazı maksimum 2 cümle olsun. ekstra bilgi verme. eğer kişisel bir soruysa kişisel bilgilerini paylaşamayacağını söyle.
        

        Sadece en uygun cevabı döndür.
        """
                try:
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    response = model.generate_content(prompt)
                    return response.text.strip()
                except Exception as e:
                    print(f"LLM ile gelişmiş arama hatası: {e}")
                    return None

    return None

class MemurBotApp:
    def __init__(self, master):
        self.master = master
        master.title("Okul Memur Botu")
        master.geometry("600x500")

        self.sc_veritabani = soru_cevaplari_yukle("soru_cevaplar.json")

        self.chat_area = scrolledtext.ScrolledText(master, wrap=tk.WORD, state='disabled', font=("Arial", 12))
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.entry_frame = tk.Frame(master)
        self.entry_frame.pack(fill=tk.X, padx=10, pady=(0,10))

        self.entry = tk.Entry(self.entry_frame, font=("Arial", 12))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(self.entry_frame, text="Gönder", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT)

        self.add_bot_message("Okul Memur Botuna Hoş Geldiniz! Size nasıl yardımcı olabilirim?\nÇıkmak için pencereyi kapatabilirsiniz.")

    def add_bot_message(self, message):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"Memur Bot: {message}\n")
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

    def add_user_message(self, message):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"Siz: {message}\n")
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

    def send_message(self, event=None):
        user_input = self.entry.get().strip()
        if not user_input:
            return
        self.add_user_message(user_input)
        self.entry.delete(0, tk.END)

        cevap = yerel_cevap_bul(user_input, self.sc_veritabani)
        if cevap:
            self.add_bot_message(cevap)
        

if __name__ == "__main__":
    root = tk.Tk()
    app = MemurBotApp(root)
    root.mainloop()