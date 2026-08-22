import cv2
import os
import csv


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_BANCO = "banco_biometria"

ARQUIVO_CSV = os.path.join(
    PASTA_BANCO,
    "dados_operadores.csv"
)

CAMERA_CADASTRO = 0


# ============================================================
# CRIA ESTRUTURA DO BANCO
# ============================================================

def preparar_banco():

    os.makedirs(
        PASTA_BANCO,
        exist_ok=True
    )

    if not os.path.exists(ARQUIVO_CSV):

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
# VERIFICA SE MATRÍCULA JÁ EXISTE
# ============================================================

def matricula_existe(matricula):

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

                if (
                    str(
                        linha.get(
                            "Matricula",
                            ""
                        )
                    ).strip()
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
# CAPTURA BIOMÉTRICA
# ============================================================

def capturar_biometria(
    matricula
):

    caminho_foto = os.path.join(
        PASTA_BANCO,
        f"{matricula}.jpg"
    )

    cap = cv2.VideoCapture(
        CAMERA_CADASTRO,
        cv2.CAP_DSHOW
    )

    if not cap.isOpened():

        print(
            "❌ Não foi possível abrir "
            "a câmera para cadastro."
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
        "Posicione o rosto de frente para a câmera."
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

    while True:

        ret, frame = cap.read()

        if not ret:

            print(
                "❌ Falha ao capturar imagem."
            )

            break

        # --------------------------------------------
        # INSTRUÇÕES NA TELA
        # --------------------------------------------

        cv2.putText(
            frame,
            "Olhe para a camera",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            "S = Capturar | Q = Cancelar",
            (20, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        cv2.imshow(
            "Cadastro Biometrico",
            frame
        )

        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord("s"):

            if frame is None or frame.size == 0:

                print(
                    "❌ Imagem inválida."
                )

                continue

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
                    "❌ Não foi possível salvar "
                    "a foto."
                )

            break

        if tecla == ord("q"):

            print(
                "⚠️ Cadastro cancelado."
            )

            break

    cap.release()

    cv2.destroyAllWindows()

    return sucesso


# ============================================================
# SALVA OPERADOR
# ============================================================

def salvar_operador(
    matricula,
    nome,
    cargo
):

    arquivo_ja_existe = os.path.exists(
        ARQUIVO_CSV
    )

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

            if not arquivo_ja_existe:

                writer.writerow([
                    "Matricula",
                    "Nome",
                    "Cargo"
                ])

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
# CADASTRO PRINCIPAL
# ============================================================

def cadastrar_usuario():

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

    # --------------------------------------------------------
    # MATRÍCULA
    # --------------------------------------------------------

    matricula = input(
        "Matrícula: "
    ).strip()

    if not matricula:

        print(
            "❌ Matrícula obrigatória."
        )

        return

    if matricula_existe(
        matricula
    ):

        print()
        print(
            f"⚠️ A matrícula {matricula} "
            "já está cadastrada."
        )

        return

    # --------------------------------------------------------
    # NOME
    # --------------------------------------------------------

    nome = input(
        "Nome completo: "
    ).strip()

    if not nome:

        print(
            "❌ Nome obrigatório."
        )

        return

    # --------------------------------------------------------
    # CARGO
    # --------------------------------------------------------

    cargo = input(
        "Cargo/Função: "
    ).strip()

    if not cargo:

        print(
            "❌ Cargo obrigatório."
        )

        return

    # --------------------------------------------------------
    # CAPTURA
    # --------------------------------------------------------

    print()

    foto_salva = capturar_biometria(
        matricula
    )

    if not foto_salva:

        print(
            "❌ Cadastro não concluído."
        )

        return

    # --------------------------------------------------------
    # SALVA DADOS
    # --------------------------------------------------------

    if salvar_operador(
        matricula,
        nome,
        cargo
    ):

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
            f"Biometria: banco_biometria/{matricula}.jpg"
        )
        print(
            "=========================================="
        )

    else:

        # Se a foto foi salva mas o CSV falhou,
        # não deixamos um cadastro inconsistente
        # sem avisar o usuário.

        print()
        print(
            "⚠️ A biometria foi salva, "
            "mas os dados não foram registrados "
            "no CSV."
        )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    cadastrar_usuario()