import cv2
import os
import csv
from deepface import DeepFace

def carregar_banco_de_dados():
    """Lê o arquivo CSV e monta um dicionário em memória com os dados dos operadores"""
    arquivo_csv = os.path.join("banco_biometria", "dados_operadores.csv")
    operadores = {}
    if os.path.exists(arquivo_csv):
        with open(arquivo_csv, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for linha in reader:
                operadores[linha["Matricula"]] = {"nome": linha["Nome"], "cargo": linha["Cargo"]}
    return operadores

def rodar_leitor_biometrico():
    pasta_banco = "banco_biometria"
    dados_operadores = carregar_banco_de_dados()

    if not os.path.exists(pasta_banco) or len(dados_operadores) == 0:
        print("❌ Nenhum operador cadastrado no sistema. Rode o script de cadastro antes.")
        return

    print("Carregando IA de detecção facial...")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    print("\n🟢 Scanner Biométrico Online. (Aperte 'q' para fechar)")

    while True:
        ret, frame = cap.read()
        if not ret: break

        try:
            # Procura a face atual dentro da pasta de fotos
            resultados = DeepFace.find(
                img_path=frame, 
                db_path=pasta_banco, 
                model_name="Facenet", 
                enforce_detection=False, 
                silent=True
            )

            if len(resultados) > 0 and not resultados[0].empty:
                # Achou a foto! Pega o caminho dela (Ex: 'banco_biometria/4021.jpg')
                caminho_foto_encontrada = resultados[0].iloc[0]["identity"]
                
                # Extrai apenas o '4021' do nome do arquivo
                matricula_detectada = os.path.splitext(os.path.basename(caminho_foto_encontrada))[0]
                
                # Puxa o nome e o cargo atrelados a essa matrícula
                info = dados_operadores.get(matricula_detectada, {"nome": "Desconhecido", "cargo": ""})
                
                texto_exibicao = f"{info['nome']} - {info['cargo']}"
                cor = (0, 255, 0) # Verde
            else:
                texto_exibicao = "ROSTO NAO CADASTRADO"
                cor = (0, 0, 255) # Vermelho

        except Exception:
            texto_exibicao = "Buscando face..."
            cor = (0, 255, 255) # Amarelo

        # Estampa o resultado na tela
        cv2.putText(frame, texto_exibicao, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2, cv2.LINE_AA)
        cv2.imshow("Ponto Eletronico / Identificador", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    rodar_leitor_biometrico()