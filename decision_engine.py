import cv2
import csv
import os
import winsound
from datetime import datetime

limite_frames_fadiga = 90  
contador_postura_inadequada = 0
ultimo_estado_severidade = "NORMAL"

def verificar_ponto_em_poligono(ponto, poligono):
    return cv2.pointPolygonTest(poligono, ponto, False)

def avaliar_fadiga_ergonomica(ombro, quadril):
    global contador_postura_inadequada
    if (ombro[0] == 0 and ombro[1] == 0) or (quadril[0] == 0 and quadril[1] == 0):
        return False
        
    distancia_vertical = abs(quadril[1] - ombro[1])
    limiar_dinamico = 85 
    
    if distancia_vertical < limiar_dinamico: 
        contador_postura_inadequada += 1
    else:
        contador_postura_inadequada = max(0, contador_postura_inadequada - 1)
        
    return contador_postura_inadequada > limite_frames_fadiga

def registrar_incidente_csv(severidade, infracoes, matricula, operador, frame):
    from config import PATH_LOGS_CSV
    
    pasta_provas = "provas_incidentes"
    os.makedirs(pasta_provas, exist_ok=True)
    
    timestamp_log = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_arquivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    lista_infracoes = "; ".join(infracoes) if len(infracoes) > 0 else "Fadiga Ergonomica"
    
    nome_foto = f"infra_{matricula}_{timestamp_arquivo}.jpg"
    caminho_foto = os.path.join(pasta_provas, nome_foto)
    
    if frame is not None:
        cv2.imwrite(caminho_foto, frame)
    else:
        caminho_foto = "FALHA_NA_CAPTURA_DO_FRAME"

    arquivo_novo = not os.path.exists(PATH_LOGS_CSV)
    
    try:
        with open(PATH_LOGS_CSV, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if arquivo_novo:
                writer.writerow(["Timestamp", "Matricula", "Operador", "Severidade", "Infracoes_Mapeadas", "Foto_Prova"])
            writer.writerow([timestamp_log, matricula, operador, severidade, lista_infracoes, caminho_foto])
    except Exception:
        pass

def disparar_alerta_proativo(severidade):
    from config import FREQ_BEEP_CRITICO, DURACAO_BEEP_CRITICO
    if severidade == "CRITICA":
        winsound.Beep(FREQ_BEEP_CRITICO, DURACAO_BEEP_CRITICO)

def calcular_nivel_severidade(tem_pessoa_na_zona, infracoes_detectadas, fadiga_detectada, matricula, operador, frame):
    global ultimo_estado_severidade

    if len(infracoes_detectadas) == 0 and not fadiga_detectada:
        ultimo_estado_severidade = "NORMAL"
        return "NORMAL"

    if tem_pessoa_na_zona and "Without Helmet" in infracoes_detectadas:
        severidade_atual = "CRITICA"
    elif len(infracoes_detectadas) > 0 or fadiga_detectada:
        severidade_atual = "ALTA"
    else:
        severidade_atual = "INFORMATIVA"

    if severidade_atual != ultimo_estado_severidade:
        if severidade_atual in ["CRITICA", "ALTA"]:
            registrar_incidente_csv(severidade_atual, infracoes_detectadas, matricula, operador, frame)
        disparar_alerta_proativo(severidade_atual)
        ultimo_estado_severidade = severidade_atual

    return severidade_atual

def processar_regras_situacionais(results, poligono_risco, matricula, operador, frame, ombro=None, quadril=None):
    tem_pessoa_na_zona = False
    pontos_pes = []
    infracoes_detectadas = []

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = r.names[cls_id]

            if label == "person":
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                ponto_base = (int((x1 + x2) / 2), y2) 
                pontos_pes.append(ponto_base)
                
                if verificar_ponto_em_poligono(ponto_base, poligono_risco) >= 0:
                    tem_pessoa_na_zona = True

            if label in ["Without Helmet", "Without Glass", "Without Mask", "Without Glove", "Without Ear Protectors", "Without Safety Vest"]:
                infracoes_detectadas.append(label)

    fadiga_detectada = False
    if ombro is not None and quadril is not None:
        fadiga_detectada = avaliar_fadiga_ergonomica(ombro, quadril)

    severidade = calcular_nivel_severidade(tem_pessoa_na_zona, infracoes_detectadas, fadiga_detectada, matricula, operador, frame)

    return severidade, pontos_pes, infracoes_detectadas