import csv
from pathlib import Path

from tqdm import tqdm

from gmail_cleaner.gmail_api import get_gmail_service


def load_messages_to_delete(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csvfile:
        reader = csv.DictReader(csvfile)
        messages = list(reader)

    return messages


def dry_run(path):
    messages = load_messages_to_delete(path)

    print("\n=== DRY-RUN ===")
    print(f"Archivo: {path}")
    print(f"Mensajes seleccionados: {len(messages)}")

    if not messages:
        print("No hay mensajes para procesar.")
        return

    print("\nMensajes que se enviarían a la papelera:\n")

    for message in messages:
        print(
            f"{message.get('id', '')}  "
            f"{message.get('date', '')}  "
            f"{message.get('from', '')}  "
            f"{message.get('subject', '')}"
        )

    print(
        f"\nDRY-RUN: se procesarían "
        f"{len(messages)} mensajes."
    )
    print("No se ha modificado Gmail.")


def move_to_trash(path):
    messages = load_messages_to_delete(path)

    if not messages:
        print("No hay mensajes para procesar.")
        return

    message_ids = [
        message.get("id")
        for message in messages
        if message.get("id")
    ]

    print("\n=== PAPELERA ===")
    print(f"Archivo: {path}")
    print(f"Mensajes seleccionados: {len(message_ids)}")

    print(
        "\nATENCIÓN: estos mensajes se enviarán "
        "a la papelera de Gmail."
    )

    confirmation = input(
        "\nEscribe 'SI' para confirmar: "
    ).strip()

    if confirmation != "SI":
        print("\nOperación cancelada.")
        print("No se ha modificado Gmail.")
        return

    service = get_gmail_service()

    batch_size = 1000
    processed = 0
    failed = 0

    batches = [
        message_ids[i:i + batch_size]
        for i in range(
            0,
            len(message_ids),
            batch_size,
        )
    ]

    print(
        f"\nProcesando {len(message_ids)} mensajes "
        f"en {len(batches)} lotes..."
    )

    progress = tqdm(
        total=len(message_ids),
        desc="Enviando a Papelera",
        unit="msg",
    )

    try:
        for batch in batches:
            try:
                (
                    service.users()
                    .messages()
                    .batchModify(
                        userId="me",
                        body={
                            "ids": batch,
                            "addLabelIds": ["TRASH"],
                        },
                    )
                    .execute()
                )

                processed += len(batch)
                progress.update(len(batch))

            except Exception as error:
                failed += len(batch)

                print(
                    f"\nERROR en lote de {len(batch)} mensajes: "
                    f"{error}"
                )

    finally:
        progress.close()

    print("\nFinalizado.")
    print(f"Procesados: {processed}")
    print(f"Errores: {failed}")
