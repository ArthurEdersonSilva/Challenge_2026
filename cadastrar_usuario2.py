import cv2
import os
import csv

import config


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

    cap.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        getattr(
            config,
            "LARGURA_CAM",
            640
        )
    )

    cap.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        getattr(
            config,
            "ALTURA_CAM",
            480
        )
    )

    return cap


# ============================================================
# CAPTURA BIOMÉTRICA
# ============================================================

def capturar_biometria(
    matricula,
    camera_id=None
):

    matricula = normalizar_matricula(
        matricula
    )

    caminho_foto = os.path.join(
        PASTA_BANCO,
        f"{matricula}.jpg"
    )

    id_camera, fonte = (
        obter_fonte_camera_cadastro(
            camera_id
        )
    )

    cap = abrir_camera(
        fonte
    )

    if cap is None:

        print(
            f"❌ Não foi possível abrir "
            f"a câmera {id_camera} "
            "para cadastro."
        )

        return False

    print()
    print(
        "=========================================="
    )
    print(
        " CAPTURA BIOMÉTRICA"
    )
    print(
        "=========================================="
    )

    print(
        f"Câmera utilizada: "
        f"{id_camera + 1}"
    )

    print(
        "Posicione o rosto de frente "
        "para a câmera."
    )

    print(
        "Pressione S para capturar."
    )

    print(
        "Pressione Q para cancelar."
    )

    print(
        "=========================================="
    )

    sucesso = False

    try:

        while True:

            ret, frame = cap.read()

            if not ret:

                print(
                    "❌ Falha ao capturar imagem."
                )

                break

            frame_visual = (
                frame.copy()
            )

            altura, largura = (
                frame_visual.shape[:2]
            )

            # =================================================
            # GUIA VISUAL PARA O ROSTO
            # =================================================

            centro_x = (
                largura // 2
            )

            centro_y = (
                altura // 2
            )

            largura_guia = int(
                largura * 0.30
            )

            altura_guia = int(
                altura * 0.55
            )

            x1 = (
                centro_x
                - largura_guia // 2
            )

            y1 = (
                centro_y
                - altura_guia // 2
            )

            x2 = (
                centro_x
                + largura_guia // 2
            )

            y2 = (
                centro_y
                + altura_guia // 2
            )

            cv2.rectangle(
                frame_visual,
                (x1, y1),
                (x2, y2),
                (0, 255, 255),
                2
            )

            cv2.putText(
                frame_visual,
                "Posicione o rosto dentro da area",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            cv2.putText(
                frame_visual,
                "S = Capturar | Q = Cancelar",
                (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

            cv2.imshow(
                "Cadastro Biometrico",
                frame_visual
            )

            tecla = (
                cv2.waitKey(1)
                & 0xFF
            )

            # =================================================
            # CAPTURAR
            # =================================================

            if tecla == ord("s"):

                if (
                    frame is None
                    or frame.size == 0
                ):

                    print(
                        "❌ Imagem inválida."
                    )

                    continue

                # ---------------------------------------------
                # Salva a imagem original.
                # Não salva retângulos/textos.
                # ---------------------------------------------

                sucesso = cv2.imwrite(
                    caminho_foto,
                    frame
                )

                if sucesso:

                    print()
                    print(
                        "✅ Foto biométrica salva:"
                    )

                    print(
                        f"   {caminho_foto}"
                    )

                else:

                    print(
                        "❌ Não foi possível "
                        "salvar a foto."
                    )

                break

            # =================================================
            # CANCELAR
            # =================================================

            if tecla == ord("q"):

                print(
                    "⚠️ Cadastro cancelado."
                )

                break

    finally:

        cap.release()

        cv2.destroyWindow(
            "Cadastro Biometrico"
        )

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