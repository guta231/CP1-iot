import tkinter as tk


def interface():
    root = tk. Tk( )
    root. title("Smart Gym - Estacao 01")
    root.geometry("400x200") 

 
    label_boas_vindas = tk.Label(root, text="Aproxime seu cartao ... ", font=("Arial", 16) )
    btn_sair = tk.Button(root, text="Sair", command=root.quit)

    label_boas_vindas.pack(pady=20)
    btn_sair.pack( )

    root.mainloop( )