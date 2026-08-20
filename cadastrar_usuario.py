import cv2
import os
import csv

def cadastrar_operador():
    print("=== BASE DE CADASTRO DE OPERADORES ===")
    matricula = input("1. Digite a Matrícula (Ex: 4021): ").strip()
    nome = input("2. Digite o Nome Completo: ").strip()
    cargo = input("3. Digite o Cargo/Função (Ex: Soldador): ").strip()

    if not matricula or not nome or not cargo:
        print("❌ Erro: Todos os campos são obrigatórios.")
        return

    pasta_banco = "banco_biometria"
    os.makedirs(pasta_banco, exist_ok=True)
    arquivo_csv = os.path.join(pasta_banco, "dados_operadores.csv")

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # [ATIVO] Primária
    #cap = cv2.VideoCapture(1) # [DESATIVADO] Secundária

    print("\n📷 Câmera ligada. Olhe para a lente e aperte a tecla 's' para capturar a face.")

    while True:
        ret, frame = cap.read()
        if not ret: break

        cv2.imshow("Captura Biometrica - Aperte 's'", frame)

        if cv2.waitKey(1) & 0xFF == ord('s'):
            # 1. Salva a imagem com o nome sendo a MATRÍCULA
            caminho_foto = os.path.join(pasta_banco, f"{matricula}.jpg")
            cv2.imwrite(caminho_foto, frame)

            # 2. Salva os dados do cara na tabela CSV
            arquivo_ja_existe = os.path.exists(arquivo_csv)
            with open(arquivo_csv, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not arquivo_ja_existe:
                    writer.writerow(["Matricula", "Nome", "Cargo"]) # Cabeçalho
                writer.writerow([matricula, nome, cargo])

            print(f"\n✅ Operador {nome} cadastrado com sucesso!")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    cadastrar_operador()