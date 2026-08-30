import cv2
import os
import csv

import config

from reconhecimento_facial import validar_imagem_biometrica


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_BANCO = getattr(
    config,
    "PATH_BANCO_BIOMETRIA",
    "banco_biometria"
)

ARQUIVO_CSV = getattr(
    config,
    "PATH_DADOS_OPERADORES",
    os.path.join(
        PASTA_BANCO,
        "dados_operadores.csv"
    )
)


# ============================================================
# CRIA ESTRUTURA DO BANCO
# ============================================================

def preparar_banco():

    os.makedirs(
        PASTA_BANCO,
        exist_ok=True
    )

    if not os.path.exists(
        ARQUIVO_CSV
    ):

        with open(
            ARQUIVO_CSV,
            mode="w",
            newline="",
            encoding="utf-8"
        ) as arquivo:

            writer = csv.writer(
                arquivo
            )

            writer.writerow([
                "Matricula",
                "Nome",
                "Cargo"
            ])


# ============================================================
# NORMALIZAR MATRÍCULA
# ============================================================

def normalizar_matricula(
    matricula
):

    return str(
        matricula
    ).strip()


# ============================================================
# VERIFICA MATRÍCULA
# ============================================================

def matricula_existe(
    matricula
):

    matricula = normalizar_matricula(
        matricula
    )

    if not os.path.exists(
        ARQUIVO_CSV
    ):

        return False

    try:

        with open(
            ARQUIVO_CSV,
            mode="r",
            encoding="utf-8"
        ) as arquivo:

            reader = csv.DictReader(
                arquivo
            )

            for linha in reader:

                matricula_existente = (
                    normalizar_matricula(
                        linha.get(
                            "Matricula",
                            ""
                        )
                    )
                )

                if (
                    matricula_existente
                    == matricula
                ):

                    return True

    except Exception as erro:

        print(
            f"⚠️ Erro ao consultar cadastro: "
            f"{erro}"
        )

    return False


# ============================================================
# BUSCAR OPERADOR
# ============================================================

def buscar_operador(
    matricula
):

    matricula = normalizar_matricula(
        matricula
    )

    if not os.path.exists(
        ARQUIVO_CSV
    ):

        return None

    try:

        with open(
            ARQUIVO_CSV,
            mode="r",
            encoding="utf-8"
        ) as arquivo:

            reader = csv.DictReader(
                arquivo
            )

            for linha in reader:

                if (
                    normalizar_matricula(
                        linha.get(
                            "Matricula",
                            ""
                        )
                    )
                    == matricula
                ):

                    return {
                        "matricula": matricula,

                        "nome": str(
                            linha.get(
                                "Nome",
                                ""
                            )
                        ).strip(),

                        "cargo": str(
                            linha.get(
                                "Cargo",
                                ""
                            )
                        ).strip(),
                    }

    except Exception as erro:

        print(
            f"⚠️ Erro ao buscar operador: "
            f"{erro}"
        )

    return None


# ============================================================
# ESCOLHER CÂMERA PARA CADASTRO
# ============================================================

def obter_fonte_camera_cadastro(
    camera_id=None
):

    # --------------------------------------------------------
    # CÂMERA INFORMADA MANUALMENTE
    # --------------------------------------------------------

    if camera_id is not None:

        try:

            camera = config.obter_config_camera(
                camera_id
            )

            return (
                camera_id,
                camera.get(
                    "fonte",
                    camera_id
                )
            )

        except Exception:

            return (
                camera_id,
                camera_id
            )

    # --------------------------------------------------------
    # CASO NÃO SEJA INFORMADA
    #
    # Utiliza a primeira câmera ativa configurada.
    # --------------------------------------------------------

    try:

        cameras_ativas = (
            config.obter_cameras_ativas()
        )

        if cameras_ativas:

            primeiro_id = next(
                iter(
                    cameras_ativas
                )
            )

            dados = cameras_ativas[
                primeiro_id
            ]

            return (
                primeiro_id,
                dados.get(
                    "fonte",
                    primeiro_id
                )
            )

    except Exception:

        pass

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    return (
        0,
        0
    )


# ============================================================
# ABRIR CÂMERA
# ============================================================

def abrir_camera(
    fonte
):

    if isinstance(
        fonte,
        int
    ):

        cap = cv2.VideoCapture(
            fonte,
            cv2.CAP_DSHOW
        )

    else:

        cap = cv2.VideoCapture(
            fonte
        )

    if not cap.isOpened():

        return None

    # USB usa a resolução configurada; RTSP/Wi-Fi preserva
    # a resolução e a proporção nativas do stream.
    if isinstance(fonte, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, getattr(config, "LARGURA_CAM", 640))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, getattr(config, "ALTURA_CAM", 480))

    return cap


# ============================================================
# CAPTURA BIOMÉTRICA
# ============================================================

def capturar_biometria(
    matricula,
    camera_id=None
):
    matricula = normalizar_matricula(matricula)
    caminho_foto = os.path.join(PASTA_BANCO, f"{matricula}.jpg")

    id_camera, fonte = obter_fonte_camera_cadastro(camera_id)
    cap = abrir_camera(fonte)

    if cap is None:
        print(f"❌ Não foi possível abrir a câmera {id_camera} para cadastro.")
        return False

    print()
    print("==========================================")
    print(" CAPTURA BIOMÉTRICA")
    print("==========================================")
    print(f"Câmera utilizada: {id_camera + 1}")
    print("Posicione o rosto de frente para a câmera.")
    print("Pressione S quando a caixa estiver VERDE.")
    print("Pressione Q para cancelar.")
    print("==========================================")

    nome_janela = "Cadastro Biometrico"
    sucesso = False

    try:
        from deepface import DeepFace
    except Exception as erro:
        print(f"❌ DeepFace indisponível: {erro}")
        cap.release()
        return False

    # Somente para o cadastro. Nenhum outro arquivo é alterado.
    # RetinaFace é a primeira opção; MTCNN e SSD ficam como fallback.
    backends_cadastro = ("retinaface", "mtcnn", "ssd", "opencv")
    backend_ativo = None
    rostos_atuais = []
    contador_frame = 0
    intervalo_deteccao = 5

    cv2.namedWindow(
        nome_janela,
        cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO
    )

    try:
        while True:
            ret, frame = cap.read()

            if not ret or frame is None or frame.size == 0:
                print("❌ Falha ao capturar imagem.")
                break

            frame_visual = frame.copy()
            altura, largura = frame_visual.shape[:2]
            contador_frame += 1

            # Não roda o detector pesado em todos os frames.
            if contador_frame == 1 or contador_frame % intervalo_deteccao == 0:
                rostos_atuais = []
                backend_encontrado = None

                ordem_backends = (
                    (backend_ativo,) if backend_ativo else backends_cadastro
                )

                for backend in ordem_backends:
                    if backend is None:
                        continue

                    try:
                        faces_extraidas = DeepFace.extract_faces(
                            img_path=frame,
                            detector_backend=backend,
                            enforce_detection=True,
                            align=True,
                        )
                    except Exception:
                        if backend_ativo is not None:
                            backend_ativo = None
                        continue

                    candidatos = []

                    for face_info in faces_extraidas or []:
                        area = face_info.get("facial_area") or {}
                        x = int(area.get("x", 0) or 0)
                        y = int(area.get("y", 0) or 0)
                        w = int(area.get("w", 0) or 0)
                        h = int(area.get("h", 0) or 0)
                        confianca = float(
                            face_info.get("confidence", 1.0) or 0.0
                        )

                        if (
                            w >= int(getattr(config, "BIOMETRIA_DIMENSAO_ROSTO_MINIMA", 48))
                            and h >= int(getattr(config, "BIOMETRIA_DIMENSAO_ROSTO_MINIMA", 48))
                        ):
                            candidatos.append((x, y, w, h, confianca))

                    if candidatos:
                        rostos_atuais = candidatos
                        backend_encontrado = backend
                        backend_ativo = backend
                        break

                if backend_encontrado is None:
                    backend_ativo = None

            exatamente_um_rosto = len(rostos_atuais) == 1

            if exatamente_um_rosto:
                x, y, w, h, confianca = rostos_atuais[0]
                cor = (0, 255, 0)
                mensagem = "ROSTO DETECTADO - S = CAPTURAR"

                cv2.rectangle(
                    frame_visual,
                    (x, y),
                    (x + w, y + h),
                    cor,
                    3
                )

                cv2.putText(
                    frame_visual,
                    f"Detector: {backend_ativo}",
                    (20, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )

            elif len(rostos_atuais) == 0:
                cor = (0, 0, 255)
                mensagem = "ROSTO NAO DETECTADO"

            else:
                cor = (0, 165, 255)
                mensagem = "MANTENHA APENAS UM ROSTO NA CAMERA"

                for x, y, w, h, confianca in rostos_atuais:
                    cv2.rectangle(
                        frame_visual,
                        (x, y),
                        (x + w, y + h),
                        cor,
                        3
                    )

            cv2.putText(
                frame_visual,
                mensagem,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                cor,
                2,
                cv2.LINE_AA
            )

            cv2.putText(
                frame_visual,
                "Q = Cancelar",
                (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # Mantém proporção da imagem e limita apenas o tamanho da janela.
            max_largura = 1280
            max_altura = 720
            fator = min(
                max_largura / float(largura),
                max_altura / float(altura),
                1.0
            )

            largura_exibicao = max(1, int(round(largura * fator)))
            altura_exibicao = max(1, int(round(altura * fator)))

            if fator < 1.0:
                exibicao = cv2.resize(
                    frame_visual,
                    (largura_exibicao, altura_exibicao),
                    interpolation=cv2.INTER_AREA
                )
            else:
                exibicao = frame_visual

            cv2.resizeWindow(
                nome_janela,
                largura_exibicao,
                altura_exibicao
            )
            cv2.imshow(nome_janela, exibicao)

            tecla = cv2.waitKey(1) & 0xFF

            if tecla == ord("s"):
                if not exatamente_um_rosto or backend_ativo is None:
                    print(
                        "❌ Captura bloqueada: "
                        "é necessário exatamente um rosto detectado."
                    )
                    continue

                # Validação final usando o MESMO backend que realmente
                # conseguiu localizar o rosto durante o cadastro.
                validacao = validar_imagem_biometrica(
                    frame,
                    detector_backend=backend_ativo,
                    confianca_minima=0.0,
                    dimensao_minima=int(getattr(
                        config,
                        "BIOMETRIA_DIMENSAO_ROSTO_MINIMA",
                        48
                    )),
                )

                if not validacao.valida:
                    print("❌ Cadastro rejeitado:")
                    print(f"   Motivo: {validacao.motivo}")
                    print(
                        f"   Rostos utilizáveis: "
                        f"{validacao.quantidade_rostos}"
                    )
                    continue

                sucesso = cv2.imwrite(caminho_foto, frame)

                if sucesso:
                    print()
                    print("✅ Foto biométrica salva:")
                    print(f"   {caminho_foto}")
                    print(f"   Detector utilizado: {backend_ativo}")
                else:
                    print("❌ Não foi possível salvar a foto.")

                break

            if tecla == ord("q"):
                print("⚠️ Cadastro cancelado.")
                break

    finally:
        cap.release()
        try:
            cv2.destroyWindow(nome_janela)
        except cv2.error:
            pass

    return sucesso


# ============================================================
# SALVA OPERADOR
# ============================================================

def salvar_operador(
    matricula,
    nome,
    cargo
):

    preparar_banco()

    matricula = normalizar_matricula(
        matricula
    )

    nome = str(
        nome
    ).strip()

    cargo = str(
        cargo
    ).strip()

    if matricula_existe(
        matricula
    ):

        print(
            f"⚠️ Matrícula {matricula} "
            "já cadastrada."
        )

        return False

    try:

        with open(
            ARQUIVO_CSV,
            mode="a",
            newline="",
            encoding="utf-8"
        ) as arquivo:

            writer = csv.writer(
                arquivo
            )

            writer.writerow([
                matricula,
                nome,
                cargo
            ])

        return True

    except Exception as erro:

        print(
            f"❌ Erro ao salvar operador: "
            f"{erro}"
        )

        return False


# ============================================================
# REMOVER FOTO EM CASO DE ERRO
# ============================================================

def remover_foto_biometrica(
    matricula
):

    caminho = os.path.join(
        PASTA_BANCO,
        f"{matricula}.jpg"
    )

    try:

        if os.path.exists(
            caminho
        ):

            os.remove(
                caminho
            )

    except Exception:

        pass


# ============================================================
# CADASTRO PRINCIPAL
# ============================================================

def cadastrar_usuario(
    camera_id=None
):

    preparar_banco()

    print()
    print(
        "=========================================="
    )
    print(
        "      CADASTRO DE FUNCIONÁRIO"
    )
    print(
        "=========================================="
    )

    # ========================================================
    # MATRÍCULA
    # ========================================================

    matricula = normalizar_matricula(
        input(
            "Matrícula: "
        )
    )

    if not matricula:

        print(
            "❌ Matrícula obrigatória."
        )

        return False

    if matricula_existe(
        matricula
    ):

        print()
        print(
            f"⚠️ A matrícula {matricula} "
            "já está cadastrada."
        )

        return False

    # ========================================================
    # NOME
    # ========================================================

    nome = input(
        "Nome completo: "
    ).strip()

    if not nome:

        print(
            "❌ Nome obrigatório."
        )

        return False

    # ========================================================
    # CARGO
    # ========================================================

    cargo = input(
        "Cargo/Função: "
    ).strip()

    if not cargo:

        print(
            "❌ Cargo obrigatório."
        )

        return False

    # ========================================================
    # CAPTURA
    # ========================================================

    foto_salva = (
        capturar_biometria(
            matricula,
            camera_id=camera_id
        )
    )

    if not foto_salva:

        print(
            "❌ Cadastro não concluído."
        )

        return False

    # ========================================================
    # SALVA DADOS
    # ========================================================

    dados_salvos = salvar_operador(
        matricula,
        nome,
        cargo
    )

    if not dados_salvos:

        # ----------------------------------------------------
        # Evita foto sem registro correspondente.
        # ----------------------------------------------------

        remover_foto_biometrica(
            matricula
        )

        print(
            "❌ Cadastro não concluído."
        )

        return False

    print()
    print(
        "=========================================="
    )
    print(
        "✅ FUNCIONÁRIO CADASTRADO"
    )
    print(
        "=========================================="
    )

    print(
        f"Matrícula: {matricula}"
    )

    print(
        f"Nome:      {nome}"
    )

    print(
        f"Cargo:     {cargo}"
    )

    print(
        f"Biometria: "
        f"{os.path.join(PASTA_BANCO, matricula + '.jpg')}"
    )

    print(
        "=========================================="
    )

    return True


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    cadastrar_usuario()