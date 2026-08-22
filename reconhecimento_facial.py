import os
from deepface import DeepFace

class ReconhecedorFacial:
    def __init__(self, db_path="banco_biometria"):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path, exist_ok=True)
        print(f"🤖 Motor DeepFace inicializado. Monitorando a pasta: {self.db_path}")

    def identificar_rosto(self, frame_crop):
        """Recebe o recorte do rosto e busca quem é na pasta de biometria"""
        try:
            # silent=True evita que ele polua o terminal com logs do TensorFlow
            # enforce_detection=False evita que o código quebre se o operador virar o rosto de lado
            resultados = DeepFace.find(
                img_path=frame_crop, 
                db_path=self.db_path, 
                model_name="Facenet", 
                enforce_detection=False,
                silent=True
            )

            # O retorno é uma lista de DataFrames do Pandas
            if len(resultados) > 0 and not resultados[0].empty:
                df = resultados[0]
                # Pega o caminho completo do arquivo que deu match (ex: 'banco_biometria/Arthur.jpg')
                caminho_match = df.iloc[0]["identity"]
                # Extrai apenas o nome do arquivo sem a extensão
                nome_identificado = os.path.splitext(os.path.basename(caminho_match))[0]
                return nome_identificado
                
        except Exception as e:
            # Em caso de detecção inconclusiva
            pass
            
        return "Desconhecido"