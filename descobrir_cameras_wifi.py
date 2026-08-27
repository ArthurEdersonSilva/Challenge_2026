import cv2
import json
import os
import re
import socket
import ipaddress
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


PASTA_WIFI = "camera_wifi"
ARQUIVO_CONFIG = os.path.join(PASTA_WIFI, "cameras_wifi.json")

TIMEOUT_CONEXAO = 0.35
MAX_WORKERS = 64

PORTAS_CAMERA = [80, 443, 554, 1935, 8000, 8080, 8554, 8899]

CAMINHOS_RTSP_COMUNS = [
    "/",
    "/stream1",
    "/stream2",
    "/live",
    "/live/ch00_0",
    "/h264",
    "/video",
    "/cam/realmonitor?channel=1&subtype=0",
    "/Streaming/Channels/101",
]

PORTA_ONVIF_DISCOVERY = 3702
MULTICAST_ONVIF = "239.255.255.250"
TIMEOUT_ONVIF = 2.0


def garantir_pasta():
    os.makedirs(PASTA_WIFI, exist_ok=True)


def texto_sim_nao(mensagem, padrao=False):
    sufixo = " [S/n]: " if padrao else " [s/N]: "
    resposta = input(mensagem + sufixo).strip().lower()
    if not resposta:
        return padrao
    return resposta in ("s", "sim", "y", "yes")


def obter_ip_local():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        sock.close()
    return ip


def obter_rede_padrao():
    ip_local = obter_ip_local()
    if ip_local.startswith("127."):
        return None
    return ipaddress.ip_network(f"{ip_local}/24", strict=False)


def porta_aberta(ip, porta, timeout=TIMEOUT_CONEXAO):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((str(ip), int(porta))) == 0
    except Exception:
        return False
    finally:
        sock.close()


def testar_host(ip):
    abertas = []
    for porta in PORTAS_CAMERA:
        if porta_aberta(ip, porta):
            abertas.append(porta)

    if not abertas:
        return None

    return {
        "ip": str(ip),
        "portas": abertas,
    }


def criar_probe_onvif():
    return """<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope
 xmlns:e="http://www.w3.org/2003/05/soap-envelope"
 xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
 xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
 xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
 <e:Header>
  <w:MessageID>uuid:2d09c8bd-8f62-4c8c-bf77-000000000001</w:MessageID>
  <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
  <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
 </e:Header>
 <e:Body>
  <d:Probe>
   <d:Types>dn:NetworkVideoTransmitter</d:Types>
  </d:Probe>
 </e:Body>
</e:Envelope>""".encode("utf-8")


def extrair_dados_onvif(resposta):
    try:
        texto = resposta.decode("utf-8", errors="ignore")
    except Exception:
        return None

    xaddrs = re.findall(
        r"<(?:\w+:)?XAddrs>(.*?)</(?:\w+:)?XAddrs>",
        texto,
        flags=re.I | re.S
    )

    scopes = re.findall(
        r"<(?:\w+:)?Scopes.*?>(.*?)</(?:\w+:)?Scopes>",
        texto,
        flags=re.I | re.S
    )

    enderecos = []
    for bloco in xaddrs:
        for item in bloco.split():
            item = item.strip()
            if item:
                enderecos.append(item)

    if not enderecos:
        return None

    scopes_texto = " ".join(scopes)
    nome = None
    modelo = None

    for padrao in [
        r"onvif://www\.onvif\.org/name/([^ \t\r\n<]+)",
        r"onvif://www\.onvif\.org/hardware/([^ \t\r\n<]+)",
    ]:
        match = re.search(padrao, scopes_texto, flags=re.I)
        if match:
            valor = urllib.parse.unquote(match.group(1))
            if nome is None:
                nome = valor
            elif modelo is None:
                modelo = valor

    resultados = []

    for endereco in enderecos:
        try:
            parsed = urllib.parse.urlparse(endereco)
            if not parsed.hostname:
                continue

            resultados.append({
                "ip": parsed.hostname,
                "onvif": True,
                "onvif_url": endereco,
                "porta_onvif": parsed.port,
                "nome_onvif": nome,
                "modelo_onvif": modelo,
            })
        except Exception:
            continue

    return resultados


def descobrir_onvif():
    encontrados = {}

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
        socket.IPPROTO_UDP
    )

    sock.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_MULTICAST_TTL,
        2
    )

    sock.settimeout(TIMEOUT_ONVIF)

    try:
        sock.sendto(
            criar_probe_onvif(),
            (MULTICAST_ONVIF, PORTA_ONVIF_DISCOVERY)
        )

        while True:
            try:
                resposta, origem = sock.recvfrom(65535)
            except socket.timeout:
                break
            except Exception:
                break

            dados = extrair_dados_onvif(resposta)
            if not dados:
                continue

            for item in dados:
                ip = item.get("ip") or origem[0]
                encontrados[ip] = item

    finally:
        sock.close()

    return encontrados


def descobrir_por_portas(rede):
    resultados = {}

    if rede is None:
        return resultados

    hosts = list(rede.hosts())

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futuros = {
            executor.submit(testar_host, ip): ip
            for ip in hosts
        }

        for futuro in as_completed(futuros):
            try:
                dados = futuro.result()
            except Exception:
                dados = None

            if dados:
                resultados[dados["ip"]] = dados

    return resultados


def inferir_protocolos(portas):
    protocolos = []

    if (
        554 in portas
        or 8554 in portas
        or 1935 in portas
    ):
        protocolos.append("RTSP")

    if 80 in portas or 8080 in portas or 8000 in portas:
        protocolos.append("HTTP")

    if 443 in portas:
        protocolos.append("HTTPS")

    if 8899 in portas:
        protocolos.append("ONVIF?")

    return protocolos


def consolidar_candidatos(onvif, portas):
    ips = set(onvif.keys()) | set(portas.keys())
    candidatos = []

    for ip in sorted(
        ips,
        key=lambda valor: tuple(int(x) for x in valor.split("."))
    ):
        dados_portas = portas.get(ip, {})
        dados_onvif = onvif.get(ip, {})
        portas_abertas = dados_portas.get("portas", [])
        protocolos = inferir_protocolos(portas_abertas)

        if dados_onvif and "ONVIF" not in protocolos:
            protocolos.insert(0, "ONVIF")

        candidatos.append({
            "ip": ip,
            "portas": portas_abertas,
            "protocolos": protocolos,
            "onvif": bool(dados_onvif),
            "onvif_url": dados_onvif.get("onvif_url"),
            "nome_onvif": dados_onvif.get("nome_onvif"),
            "modelo_onvif": dados_onvif.get("modelo_onvif"),
        })

    return candidatos


def montar_url_rtsp(ip, porta, caminho, usuario=None, senha=None):
    if not caminho.startswith("/"):
        caminho = "/" + caminho

    credenciais = ""

    if usuario:
        usuario_url = urllib.parse.quote(usuario, safe="")
        senha_url = urllib.parse.quote(senha or "", safe="")
        credenciais = f"{usuario_url}:{senha_url}@"

    return f"rtsp://{credenciais}{ip}:{int(porta)}{caminho}"


def testar_stream(url):
    cap = None

    try:
        cap = cv2.VideoCapture(url)

        if not cap.isOpened():
            return None

        ret, frame = cap.read()

        if not ret or frame is None or frame.size == 0:
            return None

        altura, largura = frame.shape[:2]
        fps = cap.get(cv2.CAP_PROP_FPS)

        if fps is None or fps <= 0 or fps > 240:
            fps = None

        return {
            "url": url,
            "largura": int(largura),
            "altura": int(altura),
            "fps": round(float(fps), 2) if fps else None,
        }

    except Exception:
        return None

    finally:
        if cap is not None:
            cap.release()


def tentar_rtsp_comum(ip, portas, usuario=None, senha=None):
    portas_rtsp = [
        porta
        for porta in (
            554,
            8554,
            1935
        )
        if porta in portas
    ]

    for porta in portas_rtsp:
        for caminho in CAMINHOS_RTSP_COMUNS:
            url = montar_url_rtsp(
                ip,
                porta,
                caminho,
                usuario,
                senha
            )

            dados = testar_stream(url)

            if dados:
                return dados

    return None


def configurar_candidato(candidato, indice):
    ip = candidato["ip"]

    print()
    print("------------------------------------------")
    print(f"CANDIDATO {indice}")
    print("------------------------------------------")
    print(f"IP: {ip}")
    print(
        "Protocolos detectados: "
        + (
            ", ".join(candidato.get("protocolos", []))
            or "Não identificado"
        )
    )
    print(
        "Portas relevantes: "
        + (
            ", ".join(
                str(porta)
                for porta in candidato.get("portas", [])
            )
            or "Nenhuma"
        )
    )
    print("ONVIF: " + ("SIM" if candidato.get("onvif") else "NÃO"))

    if candidato.get("nome_onvif"):
        print(f"Nome ONVIF: {candidato['nome_onvif']}")

    if candidato.get("modelo_onvif"):
        print(f"Modelo ONVIF: {candidato['modelo_onvif']}")

    if not texto_sim_nao(
        "Deseja tentar adicionar este dispositivo?"
    ):
        return None

    nome_padrao = (
        candidato.get("nome_onvif")
        or f"Camera WiFi {indice:02d}"
    )

    nome = input(
        f"Nome da câmera [{nome_padrao}]: "
    ).strip() or nome_padrao

    usuario = input(
        "Usuário da câmera (Enter se não houver): "
    ).strip()

    senha = ""

    if usuario:
        try:
            import getpass
            senha = getpass.getpass("Senha da câmera: ")
        except Exception:
            senha = input("Senha da câmera: ")

    stream = tentar_rtsp_comum(
        ip,
        candidato.get("portas", []),
        usuario=usuario or None,
        senha=senha or None
    )

    if stream is None:
        print()
        print(
            "Não foi possível descobrir automaticamente "
            "um stream de vídeo."
        )
        print(
            "Se a câmera/app fornecer uma URL RTSP ou HTTP, "
            "cole abaixo."
        )

        url_manual = input(
            "URL do stream (Enter para ignorar): "
        ).strip()

        if not url_manual:
            return None

        stream = testar_stream(url_manual)

        if stream is None:
            print("❌ Não foi possível abrir a URL informada.")

            if not texto_sim_nao(
                "Deseja salvar mesmo assim?"
            ):
                return None

            stream = {
                "url": url_manual,
                "largura": None,
                "altura": None,
                "fps": None,
            }

    print()
    print("✅ STREAM DE VÍDEO CONFIRMADO")
    print(f"Fonte: {stream['url']}")

    if stream.get("largura") and stream.get("altura"):
        print(
            f"Resolução: "
            f"{stream['largura']}x{stream['altura']}"
        )

    if stream.get("fps"):
        print(f"FPS: {stream['fps']}")

    if not texto_sim_nao(
        "Salvar esta câmera?",
        padrao=True
    ):
        return None

    protocolo = (
        "rtsp"
        if stream["url"].lower().startswith("rtsp://")
        else "http"
    )

    return {
        "nome": nome,
        "tipo": protocolo,
        "fonte": stream["url"],
        "ip": ip,
        "ativa": True,
        "onvif": bool(candidato.get("onvif")),
        "portas_detectadas": candidato.get("portas", []),
        "resolucao": {
            "largura": stream.get("largura"),
            "altura": stream.get("altura"),
        },
        "fps": stream.get("fps"),
    }


def salvar_configuracao(cameras):
    garantir_pasta()

    dados = {
        "versao": 1,
        "atualizado_em": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "modo": "wifi",
        "cameras": cameras,
    }

    with open(
        ARQUIVO_CONFIG,
        "w",
        encoding="utf-8"
    ) as arquivo:
        json.dump(
            dados,
            arquivo,
            indent=4,
            ensure_ascii=False
        )


def adicionar_manual(numero):
    print()
    print("==========================================")
    print(" ADICIONAR CÂMERA MANUALMENTE")
    print("==========================================")

    nome = input(
        f"Nome [Camera WiFi {numero:02d}]: "
    ).strip()

    if not nome:
        nome = f"Camera WiFi {numero:02d}"

    url = input("URL RTSP/HTTP: ").strip()

    if not url:
        return None

    dados = testar_stream(url)

    if dados is None:
        print("❌ Não consegui abrir o stream.")

        if not texto_sim_nao(
            "Deseja salvar mesmo assim?"
        ):
            return None

        dados = {
            "url": url,
            "largura": None,
            "altura": None,
            "fps": None,
        }

    parsed = urllib.parse.urlparse(url)

    return {
        "nome": nome,
        "tipo": parsed.scheme.lower() if parsed.scheme else "desconhecido",
        "fonte": url,
        "ip": parsed.hostname,
        "ativa": True,
        "onvif": False,
        "portas_detectadas": [parsed.port] if parsed.port else [],
        "resolucao": {
            "largura": dados.get("largura"),
            "altura": dados.get("altura"),
        },
        "fps": dados.get("fps"),
    }


def main():
    garantir_pasta()

    print()
    print("==========================================")
    print(" DESCOBERTA DE CÂMERAS WIFI / IP")
    print("==========================================")

    ip_local = obter_ip_local()
    print(f"IP deste computador: {ip_local}")

    rede = obter_rede_padrao()

    if rede is None:
        print("❌ Não foi possível identificar a rede local.")
        return

    print(f"Rede analisada: {rede}")

    print()
    print("1/2 - Procurando câmeras ONVIF...")
    encontrados_onvif = descobrir_onvif()
    print(f"ONVIF encontrados: {len(encontrados_onvif)}")

    print()
    print("2/2 - Verificando serviços de câmera na rede local...")
    encontrados_portas = descobrir_por_portas(rede)

    candidatos = consolidar_candidatos(
        encontrados_onvif,
        encontrados_portas
    )

    print()
    print("==========================================")
    print(f" CANDIDATOS ENCONTRADOS: {len(candidatos)}")
    print("==========================================")

    cameras_salvas = []

    for indice, candidato in enumerate(
        candidatos,
        start=1
    ):
        camera = configurar_candidato(
            candidato,
            indice
        )

        if camera:
            cameras_salvas.append(camera)

    print()

    if texto_sim_nao(
        "Deseja adicionar uma câmera informando a URL manualmente?"
    ):
        while True:
            camera = adicionar_manual(
                len(cameras_salvas) + 1
            )

            if camera:
                cameras_salvas.append(camera)

            if not texto_sim_nao(
                "Adicionar outra câmera manual?"
            ):
                break

    if not cameras_salvas:
        print()
        print("Nenhuma câmera Wi-Fi foi salva.")

        if os.path.exists(
            ARQUIVO_CONFIG
        ):
            print(
                "⚠️ Já existe uma configuração Wi-Fi anterior."
            )
            print(
                f"Arquivo atual: {ARQUIVO_CONFIG}"
            )
            print(
                "Ela NÃO será apagada automaticamente."
            )
        else:
            print(
                "O main.py continuará podendo usar as câmeras USB."
            )

        return

    salvar_configuracao(cameras_salvas)

    print()
    print("==========================================")
    print(" CONFIGURAÇÃO WIFI SALVA")
    print("==========================================")
    print(f"Arquivo: {ARQUIVO_CONFIG}")
    print(f"Câmeras salvas: {len(cameras_salvas)}")
    print("==========================================")


if __name__ == "__main__":
    main()
